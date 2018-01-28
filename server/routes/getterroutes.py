# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json

from flask import redirect, request, session, url_for

from server import hipparchia
from server.dbsupport.citationfunctions import findvalidlevelvalues
from server.dbsupport.dbfunctions import makeanemptyauthor, setconnection
from server.formatting.bibliographicformatting import formatauthinfo, formatauthorandworkinfo, formatname, \
	woformatworkinfo
from server.formatting.wordformatting import depunct
from server.listsandsession.listmanagement import compilesearchlist, sortsearchlist
from server.listsandsession.sessionfunctions import modifysessionselections, modifysessionvar, parsejscookie
from server.startup import authordict, authorgenresdict, authorlocationdict, listmapper, workdict, workgenresdict, \
	workprovenancedict


# getselections is in selectionroutes.py
# getauthorhint, etc. are in hintroutes.py

@hipparchia.route('/getsessionvariables')
def getsessionvariables():
	"""
	a simple fetch and report: the JS wants to know what Python knows

	:return:
	"""

	returndict = {k: session[k] for k in session.keys() if k != 'csrf_token'}

	# print('rd',returndict)
	returndict = json.dumps(returndict)

	return returndict


@hipparchia.route('/getcookie/<cookienum>')
def cookieintosession(cookienum):
	"""
	take a stored cookie and convert its values into the current session settings

	:return:
	"""

	cookienum = cookienum[0:2]

	thecookie = request.cookies.get('session' + cookienum)

	# comes back as a string that needs parsing
	cookiedict = parsejscookie(thecookie)

	for key, value in cookiedict.items():
		modifysessionvar(key, value)

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

	response = redirect(url_for('frontpage'))

	return response


@hipparchia.route('/getworksof/<authoruid>')
def findtheworksof(authoruid):
	"""
	fill the hint box with constantly updated values
	:return:
	"""

	strippedquery = depunct(authoruid)

	hint = list()

	try:
		myauthor = authordict[strippedquery]
	except KeyError:
		myauthor = None

	if myauthor:
		worklist = myauthor.listofworks
		for work in worklist:
			hint.append({'value': '{t} ({id})'.format(t=work.title, id=work.universalid[-4:])})
		if not hint:
			hint.append({'value': 'somehow failed to find any works: try picking the author again'})
	else:
		hint.append({'value': 'author was not properly loaded: try again'})

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getstructure/<locus>')
def workstructure(locus):
	"""
	request detailed info about how a work works
	this is fed back to the js boxes : who should be active, what are the autocomplete values, etc?

	sample input:
		'/getstructure/gr0008w001_AT_-1'
		'/getstructure/gr0008w001_AT_13|22'


	:return:
	"""
	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	workid = locus.split('_AT_')[0]
	workid = depunct(workid)

	try:
		passage = locus.split('_AT_')[1]
	except IndexError:
		passage = '-1'

	unsafepassage = passage.split('|')
	# this list will need to match the one in '/browse': '-' is absolutely necessry to catch '-1'
	allowed = ',;-'
	safepassage = [depunct(p, allowed) for p in unsafepassage]
	safepassage = tuple(safepassage[:5])

	try:
		ao = authordict[workid[:6]]
	except KeyError:
		ao = makeanemptyauthor('gr0000')

	# it is a list of works and not a dict, so we can't pull the structure from the key
	# should probably change that some day
	structure = dict()
	for work in ao.listofworks:
		if work.universalid == workid:
			structure = work.structure

	ws = dict()
	if structure:
		lowandhigh = findvalidlevelvalues(workid, structure, safepassage, cur)
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
	results = json.dumps(ws)

	cur.close()

	return results


@hipparchia.route('/getauthorinfo/<authorid>')
def getauthinfo(authorid):
	"""
	show local info about the author one is considering in the selection box
	:return:
	"""

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

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

	cur.close()

	return authinfo


@hipparchia.route('/getsearchlistcontents')
def getsearchlistcontents():
	"""
	return a formatted list of what a search would look like if executed with the current selections

	:return:
	"""

	searchlist = compilesearchlist(listmapper)
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
	for work in searchlist:
		work = work[:10]
		count += 1
		w = workdict[work]
		au = formatname(w, authordict[work[0:6]])

		try:
			wordstotal += workdict[work].wordcount
		except TypeError:
			# TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'
			pass
		searchlistinfo.append('\n[{ct}]&nbsp;'.format(ct=count))
		searchlistinfo.append(formatauthorandworkinfo(au, w))

	if len(searchlistinfo) > cap:
		searchlistinfo = searchlistinfo[:cap+1]
		searchlistinfo.append('<br />[list longer than user-defined cap]<br />')

	if wordstotal > 0:
		searchlistinfo.append('<br /><span class="emph">total words:</span> ' + format(wordstotal, ',d'))

	searchlistinfo = '\n'.join(searchlistinfo)
	searchlistinfo = json.dumps(searchlistinfo)

	return searchlistinfo


@hipparchia.route('/getgenrelistcontents')
def getgenrelistcontents():
	"""
	return a basic list of what you can pick
	:return:
	"""

	sessionmapper = {'greekcorpus': 'gr', 'inscriptioncorpus': 'in', 'papyruscorpus': 'dp', 'latincorpus': 'lt'}
	genres = str()
	glist = list()

	genres += '<h3>Author Categories</h3>'
	for sessionvar in ['greekcorpus', 'inscriptioncorpus', 'papyruscorpus', 'latincorpus']:
		if session[sessionvar] == 'yes':
			for g in authorgenresdict[sessionmapper[sessionvar]]:
				glist.append(g)

	if len(glist) > 0:
		genres += ', '.join(glist)
	else:
		genres += '[no author genres in your currently selected database(s)]'

	glist = list()
	genres += '\n<h3>Work Categories</h3>'
	for sessionvar in ['greekcorpus', 'inscriptioncorpus', 'papyruscorpus', 'latincorpus']:
		if session[sessionvar] == 'yes':
			for g in workgenresdict[sessionmapper[sessionvar]]:
				glist.append(g)

	if len(glist) > 0:
		genres += ', '.join(glist)
	else:
		genres += '[no work genres in your currently selected database(s)]'

	genres = json.dumps(genres)

	return genres