# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re
from multiprocessing import current_process
from os import path
from string import Template
from sys import argv

from click import secho
from flask import Response as FlaskResponse
from flask import make_response, redirect, request, session, url_for

from server import hipparchia
from server.dbsupport.citationfunctions import findvalidlevelvalues
from server.dbsupport.dblinefunctions import dblineintolineobject, grabbundlesoflines, grabonelinefromwork, \
	returnfirstorlastlinenumber
from server.dbsupport.miscdbfunctions import findselectionboundaries
from server.formatting.bibliographicformatting import formatauthinfo, formatauthorandworkinfo, formatname, \
	woformatworkinfo
from server.formatting.wordformatting import depunct
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.parsingobjects import StructureInputParsingObject
from server.listsandsession.searchlistmanagement import compilesearchlist, sortsearchlist
from server.listsandsession.sessionfunctions import modifysessionselections, modifysessionvariable, parsejscookie

try:
	from server.semanticvectors.vectorgraphing import fetchvectorgraph
except ImportError:
	fetchvectorgraph = None
	if current_process().name == 'MainProcess':
		secho('could not import "fetchvectorgraph": graphing will be unavailable', fg='bright_black')
from server.startup import authordict, authorgenresdict, authorlocationdict, listmapper, workdict, workgenresdict, \
	workprovenancedict
from server.semanticvectors.vectorhelpers import vectorranges

JSON_STR = str

# getselections is in selectionroutes.py
# getauthorhint, etc. are in hintroutes.py

"""

	RESPONSE ROUTES

"""


@hipparchia.route('/get/response/<fnc>/<param>')
def responsegetter(fnc: str, param: str) -> FlaskResponse:
	"""

	dispatcher for "/get/response/" requests

	"""

	param = depunct(param)

	knownfunctions = {'cookie':
						{'fnc': cookieintosession, 'param': [param]},
					'vectorfigure':
						{'fnc': fetchstoredimage, 'param': [param]},
					}

	if fnc not in knownfunctions:
		response = redirect(url_for('frontpage'))
	else:
		f = knownfunctions[fnc]['fnc']
		p = knownfunctions[fnc]['param']
		response = f(*p)

	return response


def cookieintosession(cookienum) -> FlaskResponse:
	"""

	take a stored cookie and convert its values into the current session instance

	:return:
	"""

	response = redirect(url_for('frontpage'))

	try:
		session['authorssummary']
	except KeyError:
		# cookies are not enabled
		return response

	cookienum = cookienum[0:2]

	thecookie = request.cookies.get('session' + cookienum)

	# comes back as a string that needs parsing
	cookiedict = parsejscookie(thecookie)

	refusetoset = {'loggedin', 'userid'}
	thingswecanset = {k: cookiedict[k] for k in cookiedict if k not in refusetoset}

	for key, value in thingswecanset.items():
		modifysessionvariable(key, value)

	# you need a master list out of authorgenresdict = { 'gk': gklist, 'lt': ltlist, 'in': inlist, 'dp': dplist }

	authorgenreslist = list()
	for db in authorgenresdict:
		authorgenreslist += authorgenresdict[db]
	authorgenreslist = list(set(authorgenreslist))

	workgenreslist = list()
	for db in workgenresdict:
		workgenreslist += workgenresdict[db]
	workgenreslist = list(set(workgenreslist))

	authorlocationlist = list()
	for db in authorlocationdict:
		authorlocationlist += authorlocationdict[db]
	authorlocationlist = list(set(authorlocationlist))

	workprovenancelist = list()
	for db in workprovenancedict:
		workprovenancelist += workprovenancedict[db]
	workprovenancelist = list(set(workprovenancelist))

	modifysessionselections(cookiedict, authorgenreslist, workgenreslist, authorlocationlist, workprovenancelist)

	return response


def fetchstoredimage(figurename) -> FlaskResponse:
	"""

	smeantic vector graphs are stored in the DB after generation

	now we fetch them for display in the page

	:param figurename:
	:return:
	"""

	graphbytes = fetchvectorgraph(figurename)

	response = make_response(graphbytes)
	response.headers.set('Content-Type', 'image/png')
	response.headers.set('Content-Disposition', 'attachment', filename='hipparchia_graph_{f}.png'.format(f=figurename))

	return response


"""

	JSON ROUTES

"""


@hipparchia.route('/get/json/<fnc>')
@hipparchia.route('/get/json/<fnc>/<one>')
@hipparchia.route('/get/json/<fnc>/<one>/<two>')
@hipparchia.route('/get/json/<fnc>/<one>/<two>/<three>')
def infogetter(fnc: str, one=None, two=None, three=None) -> JSON_STR:
	"""

	dispatcher for "/get/json" requests

	"""

	one = depunct(one)
	two = depunct(two)
	three = depunct(three)

	knownfunctions = {'sessionvariables':
							{'fnc': getsessionvariables, 'param': None},
						'worksof':
							{'fnc': findtheworksof, 'param': [one]},
						'workstructure':
							{'fnc': findworkstructure, 'param': [one, two, three]},
						'samplecitation':
							{'fnc': sampleworkcitation, 'param': [one, two]},
						'authorinfo':
							{'fnc': getauthinfo, 'param': [one]},
						'searchlistcontents':
							{'fnc': getsearchlistcontents, 'param': None},
						'genrelistcontents':
							{'fnc': getgenrelistcontents, 'param': None},
						'vectorranges':
							{'fnc': returnvectorsettingsranges, 'param': None},
						'helpdata':
							{'fnc': loadhelpdata, 'param': None},
						}

	if fnc not in knownfunctions:
		return json.dumps(str())

	f = knownfunctions[fnc]['fnc']
	p = knownfunctions[fnc]['param']

	if p:
		j = f(*p)
	else:
		j = f()

	if hipparchia.config['JSONDEBUGMODE']:
		print('/get/json/{f}\n\t{j}'.format(f=fnc, j=j))

	return j


def getsessionvariables() -> JSON_STR:
	"""
	a simple fetch and report: the JS wants to know what Python knows

	:return:
	"""

	returndict = {k: session[k] for k in session.keys() if k != 'csrf_token'}

	for k in returndict.keys():
		if isinstance(returndict[k], bool):
			if returndict[k]:
				returndict[k] = 'yes'
			else:
				returndict[k] = 'no'

	# print('rd', returndict)
	returndict = json.dumps(returndict)

	return returndict


def findtheworksof(authoruid) -> JSON_STR:
	"""
	fill the hint box with constantly updated values

	for "/getworksof/gr0026" the return list looks like:

		[{"value": "In Timarchum (w001)"}, {"value": "De falsa legatione (w002)"}, {"value": "In Ctesiphontem (w003)"},
		{"value": "Epistulae [Sp.] (w004)"}]

	it will be sorted by work number unless told otherwise

	:return:
	"""

	hintlist = list()

	try:
		myauthor = authordict[authoruid]
	except KeyError:
		myauthor = None

	if myauthor:
		worklist = myauthor.listofworks
		for work in worklist:
			hintlist.append('{t} ({id})'.format(t=work.title, id=work.universalid[-4:]))
		if not hintlist:
			hintlist.append('somehow failed to find any works: try picking the author again')
	else:
		hintlist.append('author was not properly loaded: try again')

	if hipparchia.config['SORTWORKSBYNUMBER']:
		try:
			sorter = {re.search(r'\(.*?\)$', h).group(0): h for h in hintlist}
		except IndexError:
			sorter = False
		if sorter:
			hintlist = [sorter[x] for x in sorted(sorter.keys())]
	else:
		# we are sorting by name...
		hintlist = sorted(hintlist)

	hintlist = [{'value': h} for h in hintlist]

	hintlist = json.dumps(hintlist)

	return hintlist


def findworkstructure(author, work, passage=None) -> JSON_STR:
	"""
	request detailed info about how a work works
	this is fed back to the js boxes : who should be active, what are the autocomplete values, etc?

	sample input:
		'/getstructure/gr0008w001/-1'
		'/getstructure/gr0008w001/13|22'

	:return:
	"""

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	po = StructureInputParsingObject(author, work, passage)
	wo = po.workobject

	ws = dict()
	if wo:
		lowandhigh = findvalidlevelvalues(wo, po.getcitationtuple(), dbcursor)
		# example: (4, 3, 'Book', '1', '7', ['1', '2', '3', '4', '5', '6', '7'])
		ws['totallevels'] = lowandhigh.levelsavailable
		ws['level'] = lowandhigh.currentlevel
		ws['label'] = lowandhigh.levellabel
		ws['low'] = lowandhigh.low
		ws['high'] = lowandhigh.high
		ws['range'] = lowandhigh.valuerange
	else:
		# (2, 0, 'verse', '1', '100')
		ws['totallevels'] = 1
		ws['level'] = 0
		ws['label'] = 'Error: repick the work'
		ws['low'] = 'Error:'
		ws['high'] = 'again'
		ws['range'] = ['error', 'select', 'the', 'work', 'again']

	# print('ws = ', ws)
	# example: {'totallevels': 5, 'level': 2, 'label': 'par', 'low': '1', 'high': '10', 'range': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']}

	results = json.dumps(ws)

	dbconnection.connectioncleanup()

	return results


def sampleworkcitation(authorid: str, workid: str) -> JSON_STR:
	"""

	called by loadsamplecitation() in autocomplete.js

	we are using the maual input style on the web page
	so we need some hint on how to do things: check the end line for a sample citation
	"Cic., In Verr" ==> 2.5.189.7

	:param authorid:
	:param workid:
	:return:
	"""
	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	returnvals = dict()
	returnvals['firstline'] = str()
	returnvals['lastline'] = str()

	authorid = depunct(authorid)
	workid = depunct(workid)

	try:
		ao = authordict[authorid]
		wo = workdict[authorid+'w'+workid]
	except KeyError:
		returnvals['firstline'] = 'no such author/work combination'
		return json.dumps(returnvals)

	toplevel = wo.availablelevels - 1
	firstlineindex = returnfirstorlastlinenumber(wo.universalid, dbcursor, disallowt=True, disallowlevel=toplevel)
	flo = dblineintolineobject(grabonelinefromwork(authorid, firstlineindex, dbcursor))

	lastlineidx = returnfirstorlastlinenumber(wo.universalid, dbcursor, findlastline=True)
	llo = dblineintolineobject(grabonelinefromwork(authorid, lastlineidx, dbcursor))

	returnvals['firstline'] = flo.prolixlocus()
	returnvals['lastline'] = llo.prolixlocus()

	results = json.dumps(returnvals)

	dbconnection.connectioncleanup()

	return results


def getauthinfo(authorid: str) -> JSON_STR:
	"""

	show local info about the author one is considering in the selection box

	:return:
	"""

	authorid = depunct(authorid)

	theauthor = authordict[authorid]

	authinfo = list()
	authinfo.append(formatauthinfo(theauthor))

	if len(theauthor.listofworks) > 1:
		authinfo.append('<br /><br /><span class="italic">work numbers:</span><br />')
	else:
		authinfo.append('<br /><span class="italic">work:</span><br />')

	sortedworks = {work.universalid: work for work in theauthor.listofworks}

	keys = sortedworks.keys()
	keys = sorted(keys)

	for work in keys:
		authinfo.append(woformatworkinfo(sortedworks[work]))

	authinfo = json.dumps('\n'.join(authinfo))

	return authinfo


def getsearchlistcontents() -> JSON_STR:
	"""
	return a formatted list of what a search would look like if executed with the current selections

	:return:
	"""
	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	searchlist = compilesearchlist(listmapper, session)
	searchlist = sortsearchlist(searchlist, authordict)

	searchlistinfo = list()

	cap = hipparchia.config['SEARCHLISTPREVIEWCAP']*2

	if len(searchlist) > 1:
		searchlistinfo.append('<br /><h3>Proposing to search the following {ww} works:</h3>'.format(ww=len(searchlist)))
		searchlistinfo.append('(Results will be arranged according to {so})<br /><br />'.format(so=session['sortorder']))
	else:
		searchlistinfo.append('<br /><h3>Proposing to search the following work:</h3>')

	count = 0
	wordstotal = 0
	# print('searchlist', searchlist)
	for worksel in searchlist:
		wo = workdict[worksel[:10]]
		au = formatname(wo, authordict[worksel[0:6]])
		count += 1
		searchlistinfo.append('\n[{ct}]&nbsp;'.format(ct=count))
		if len(worksel) == 10:
			# 'lt0474w071' vs 'lt0474w071_AT_' vs 'lt0474w071_FROM_x_TO_y'
			try:
				wordstotal += workdict[worksel].wordcount
			except TypeError:
				# TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'
				pass
			searchlistinfo.append(formatauthorandworkinfo(au, wo))
		if '_FROM_' in worksel or '_AT_' in worksel:
			boundaries = findselectionboundaries(wo, worksel, dbcursor)
			# grabbundlesoflines wants: {'work1': (start,stop), 'work2': (start,stop), ...}
			bundle = {wo.universalid: boundaries}
			linesinspan = grabbundlesoflines(bundle, dbcursor)
			wordcount = sum([ln.wordcount() for ln in linesinspan])
			wordstotal += wordcount
			searchlistinfo.append(formatauthorandworkinfo(au, wo, countprovided=wordcount))

	if len(searchlistinfo) > cap:
		searchlistinfo = searchlistinfo[:cap+1]
		searchlistinfo.append('<br />[list longer than user-defined cap]<br />')

	if wordstotal > 0:
		searchlistinfo.append('<br /><span class="emph">total words:</span> ' + format(wordstotal, ',d'))

	searchlistinfo = '\n'.join(searchlistinfo)
	searchlistinfo = json.dumps(searchlistinfo)

	dbconnection.connectioncleanup()

	return searchlistinfo


def getgenrelistcontents() -> JSON_STR:
	"""
	return a basic list of what you can pick
	:return:
	"""

	sessionmapper = {'greekcorpus': 'gr', 'inscriptioncorpus': 'in', 'papyruscorpus': 'dp', 'latincorpus': 'lt'}
	genres = str()
	glist = list()

	genres += '<h3>Author Categories</h3>'
	for sessionvar in ['greekcorpus', 'inscriptioncorpus', 'papyruscorpus', 'latincorpus']:
		if session[sessionvar]:
			for g in authorgenresdict[sessionmapper[sessionvar]]:
				glist.append(g)

	if len(glist) > 0:
		genres += ', '.join(glist)
	else:
		genres += '[no author genres in your currently selected database(s)]'

	glist = list()
	genres += '\n<h3>Work Categories</h3>'
	for sessionvar in ['greekcorpus', 'inscriptioncorpus', 'papyruscorpus', 'latincorpus']:
		if session[sessionvar]:
			for g in workgenresdict[sessionmapper[sessionvar]]:
				glist.append(g)

	if len(glist) > 0:
		genres += ', '.join(glist)
	else:
		genres += '[no work genres in your currently selected database(s)]'

	genres = json.dumps(genres)

	return genres


def returnvectorsettingsranges() -> JSON_STR:
	"""

	since vector settings names and ranges are subject to lots of tinkering, we will not
	hard-code them into the HTML/JS but instead generate them dynamically

	:return:
	"""

	scriptholder="""
	<script>
		{js}
	</script>
	"""

	spinnertamplate = """
	◦( '#$elementid' ).spinner({
		min: $min,
		max: $max,
		value: $val,
		step: $step,
		stop: function( event, ui ) {
			let result = ◦('#$elementid').spinner('value');
			setoptions('$elementid', String(result));
			},
		spin: function( event, ui ) {
			let result = ◦('#$elementid').spinner('value');
			setoptions('$elementid', String(result));
			}
		});
	◦( '#$elementid' ).val($val);
	"""

	t = Template(spinnertamplate)

	rangedata = list()

	for k in vectorranges.keys():
		r = list(vectorranges[k])
		m = r[0]
		x = r[-1]
		s = max(int((x-m)/15), 1)
		thisjs = t.substitute(elementid=k,
								min=m,
								max=x,
								step=s,
								val=session[k])
		thisjs = re.sub(r'◦', '$', thisjs)
		rangedata.append(thisjs)

	js = scriptholder.format(js='\n'.join(rangedata))
	jsinjection = json.dumps(js)

	return jsinjection


def loadhelpdata() -> JSON_STR:
	"""

	do not load the help html until someone clicks on the '?' button

	then send this stuff

	:return:
	"""

	if not hipparchia.config['EXTERNALWSGI']:
		currentpath = path.dirname(argv[0])
	else:
		# path.dirname(argv[0]) = /home/hipparchia/hipparchia_venv/bin
		currentpath = path.abspath(hipparchia.config['HARDCODEDPATH'])

	helppath = currentpath + '/server/helpfiles/'
	divmapper = {'Interface': 'helpinterface.html',
				 'Browsing': 'helpbrowsing.html',
				 'Dictionaries': 'helpdictionaries.html',
				 'MakingSearchLists': 'helpsearchlists.html',
				 'BasicSyntax': 'helpbasicsyntax.html',
				 'RegexSearching': 'helpregex.html',
				 'SpeedSearching': 'helpspeed.html',
				 'LemmaSearching': 'helplemmata.html',
				 'VectorSearching': 'helpvectors.html',
				 'Oddities': 'helpoddities.html',
				 'Extending': 'helpextending.html',
				 'IncludedMaterials': 'includedmaterials.html',
				 'Openness': 'helpopenness.html'}

	helpdict = dict()
	helpdict['helpcategories'] = list(divmapper.keys())

	for d in divmapper:
		helpfilepath = helppath + divmapper[d]
		helpcontents = ''
		if path.isfile(helpfilepath):
			with open(helpfilepath, encoding='utf8') as f:
				helpcontents = f.read()
		helpdict[d] = helpcontents

	helpdict = json.dumps(helpdict)

	return helpdict
