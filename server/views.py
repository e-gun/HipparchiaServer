# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import asyncio
import errno
import json
import locale
import re
import socket
import time
from urllib.request import urlopen

import websockets
from flask import render_template, redirect, request, url_for, session, send_file

from server.browsing.browserfunctions import getandformatbrowsercontext
from server.calculatewordweights import findtemporalweights, findccorporaweights, findgeneraweights
from server.dbsupport.citationfunctions import findvalidlevelvalues, finddblinefromlocus, finddblinefromincompletelocus,\
	perseusdelabeler
from server.dbsupport.dbfunctions import setconnection, makeanemptyauthor, makeanemptywork, versionchecking, \
	perseusidmismatch, returnfirstlinenumber
from server.formatting_helper_functions import removegravity, stripaccents, bcedating
from server.hipparchiaclasses import ProgressPoll, SearchObject
from server.lexica.lexicaformatting import entrysummary, dbquickfixes
from server.lexica.lexicalookups import browserdictionarylookup, searchdictionary, lexicalmatchesintohtml, \
	lookformorphologymatches, getobservedwordprevalencedata, grablemmataobjectfor
from server.listsandsession.listmanagement import dropdupes, polytonicsort, sortauthorandworklists, sortresultslist,\
	tidyuplist, calculatewholeauthorsearches, compileauthorandworklist, flagexclusions, buildhintlist
from server.listsandsession.sessionfunctions import modifysessionvar, modifysessionselections, parsejscookie, \
	sessionvariables, sessionselectionsashtml, rationalizeselections, justlatin, justtlg, reducetosessionselections, returnactivedbs
from server.loadglobaldicts import *
from server.searching.betacodetounicode import replacegreekbetacode
from server.searching.searchdispatching import searchdispatcher
from server.searching.searchformatting import formatauthinfo, formatauthorandworkinfo, woformatworkinfo, mpresultformatter, \
	nocontextresultformatter, htmlifysearchfinds, nocontexthtmlifysearchfinds
from server.searching.searchfunctions import cleaninitialquery
from server.textsandindices.indexmaker import buildindextowork
from server.textsandindices.textandindiceshelperfunctions import tcparserequest, textsegmentfindstartandstop, \
	wordindextohtmltable, indexdictsorter
from server.textsandindices.textbuilder import buildtext

# activate when you need to be shown new weight values upon startup and are willing to wait for the weights
# these number need to be given to dbHeadwordObject, but they only change between major shifts in the data

if hipparchia.config['CALCULATEWORDWEIGHTS'] == 'yes':
	if hipparchia.config['COLLAPSEDGENRECOUNTS'] == 'yes':
		c = True
	else:
		c = False
	print('greek wordweights', findtemporalweights('G'))
	print('corpus weights', findccorporaweights())
	print('greek genre weights:',findgeneraweights('G', c))
	print('latin genre weights:',findgeneraweights('L', c))

# empty dict in which to store progress polls
# note that more than one poll can be running
poll = {}


@hipparchia.route('/')
def frontpage():
	"""
	the front page
	it used to do stuff
	now it just loads the JS which then calls all of the routes below

	:return:
	"""

	expectedsqltemplateversion = 2182017
	stylesheet = hipparchia.config['CSSSTYLESHEET']

	sessionvariables()

	# check to see which dbs we actually own
	activelists = [l for l in listmapper if len(listmapper[l]['a']) > 0]

	versionchecking(activelists, expectedsqltemplateversion)

	# check to see which dbs we search by default
	activecorpora = [c for c in ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus'] if session[c] == 'yes']

	page = render_template('search.html',activelists=activelists, activecorpora=activecorpora,
						   accents=session['accentsmatter'], onehit=session['onehit'], css=stylesheet)

	return page


#
# unadorned views for quickly peeking at the data
#


@hipparchia.route('/authors')
def authorlist():
	"""
	a simple dump of the authors available in the db

	:return:
	"""

	keys = list(authordict.keys())
	keys.sort()

	authors = [authordict[k] for k in keys]

	return render_template('authorlister.html', found=authors, numberfound=len(authors))

#
# helpers & routes you should not browse directly
#
@hipparchia.route('/executesearch/<timestamp>', methods=['GET'])
def executesearch(timestamp):
	"""
	the interface to all of the other search functions
	tell me what you are looking for and i'll try to find it

	the results are returned in a json bundle that will be used to update the html on the page

	:return:
	"""
	sessionvariables()
	# need to sanitize input at least a bit: remove digits and punctuation
	# dispatcher will do searchtermcharactersubstitutions() and massagesearchtermsforwhitespace() to take care of lunate sigma, etc.
	try:
		seeking = cleaninitialquery(request.args.get('seeking', ''))
	except:
		seeking = ''

	try:
		proximate = cleaninitialquery(request.args.get('proximate', ''))
	except:
		proximate = ''

	try:
		ts = str(int(timestamp))
	except:
		ts = str(int(time.time()))

	if len(seeking) < 1 and len(proximate) > 0:
		seeking = proximate
		proximate = ''

	dmin, dmax = bcedating()

	if hipparchia.config['TLGASSUMESBETACODE'] == 'yes':
		if justtlg() and re.search('[a-zA-Z]', seeking):
			# searching greek, but not typing in unicode greek: autoconvert
			# papyri, inscriptions, and christian texts all contain multiple languages
			seeking = seeking.upper()
			seeking = replacegreekbetacode(seeking)

		if justtlg() and re.search('[a-zA-Z]', proximate):
			proximate = proximate.upper()
			proximate = replacegreekbetacode(proximate)

	phrasefinder = re.compile('[^\s]\s[^\s]')

	poll[ts] = ProgressPoll(ts)
	poll[ts].activate()
	poll[ts].statusis('Preparing to search')

	# a search can take 30s or more and the user might alter the session while the search is running by toggling accentsmatter, etc
	# that can be a problem, so freeze the values now and rely on this instead of some moving target
	frozensession = session.copy()

	if len(seeking) > 0:
		s = SearchObject(ts, seeking, proximate, frozensession)
		starttime = time.time()
		poll[ts].statusis('Compiling the list of works to search')
		authorandworklist = compileauthorandworklist(listmapper, frozensession)
		if authorandworklist == []:
			return redirect(url_for('frontpage'))

		# mark works that have passage exclusions associated with them: gr0001x001 instead of gr0001w001 if you are skipping part of w001
		poll[ts].statusis('Marking exclusions from the list of works to search')
		authorandworklist = flagexclusions(authorandworklist)
		workssearched = len(authorandworklist)

		poll[ts].statusis('Calculating full authors to search')
		s.authorandworklist = calculatewholeauthorsearches(authorandworklist, authordict)

		# assemble a subset of authordict that will be relevant to our actual search and send it to searchdispatcher()
		# it turns out that we only need to pass authors that are part of psgselections or psgexclusions
		# whereclauses() is selectively invoked and it needs to check the information in the listed authors and works
		# once upon a time all authors were sent through searchdispatcher(), but loading them into the manager produced
		# a massive slowdown (as 200k objects got pickled into a mpshareable dict)
		authorswheredict = {}

		for w in s.psgselections:
			authorswheredict[w[0:6]] = authordict[w[0:6]]
		for w in s.psgexclusions:
			authorswheredict[w[0:6]] = authordict[w[0:6]]
		s.authorswhere = authorswheredict

		if len(proximate) < 1 and re.search(phrasefinder, seeking) is None:
			s.searchtype = 'simple'
			thesearch = seeking
			htmlsearch = '<span class="sought">»{skg}«</span>'.format(skg=seeking)
		elif re.search(phrasefinder, seeking):
			s.searchtype = 'phrase'
			thesearch = seeking
			htmlsearch = '<span class="sought">»{skg}«</span>'.format(skg=seeking)
		else:
			s.searchtype = 'proximity'
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=s.seeking, ns=s.nearstr, sp=s.proximity, sc=s.scope, pr=s.proximate)
			htmlsearch = '<span class="sought">»{skg}«</span>{ns} within {sp} {sc} of <span class="sought">»{pr}«</span>'.format(
				skg=seeking, ns=s.nearstr, sp=s.proximity, sc=s.scope, pr=proximate)

		hits = searchdispatcher(s, poll[ts])
		poll[ts].statusis('Putting the results in context')

		# hits [<server.hipparchiaclasses.dbWorkLine object at 0x10d952da0>, <server.hipparchiaclasses.dbWorkLine object at 0x10d952c50>, ... ]
		hitdict = sortresultslist(hits, authordict, workdict)
		if s.context > 0:
			allfound = mpresultformatter(hitdict, authordict, workdict, seeking, proximate, s.searchtype, poll[ts])
		else:
			allfound = nocontextresultformatter(hitdict, authordict, workdict, seeking, proximate, s.searchtype, poll[ts])

		searchtime = time.time() - starttime
		searchtime = round(searchtime, 2)
		if len(allfound) > s.cap:
			allfound = allfound[0:s.cap]

		poll[ts].statusis('Converting results to HTML')
		if s.context > 0:
			htmlandjs = htmlifysearchfinds(allfound)
		else:
			htmlandjs = nocontexthtmlifysearchfinds(allfound)
		# print('htmlandjs',htmlandjs)
		finds = htmlandjs['hits']
		findsjs = htmlandjs['hitsjs']

		resultcount = len(allfound)

		if resultcount < s.cap:
			hitmax = 'false'
		else:
			hitmax = 'true'

		# prepare the output

		sortorderdecoder = {
			'universalid': 'ID', 'shortname': 'name', 'genres': 'author genre', 'converted_date': 'date', 'location': 'location'
		}
		try:
			locale.setlocale(locale.LC_ALL, 'en_US')
		except locale.Error:
			pass
		resultcount = locale.format('%d', resultcount, grouping=True)
		workssearched = locale.format('%d', workssearched, grouping=True)

		output = {}
		output['title'] = thesearch
		output['found'] = finds
		output['js'] = findsjs
		output['resultcount'] = resultcount
		output['scope'] = workssearched
		output['searchtime'] = str(searchtime)
		output['proximate'] = proximate
		output['thesearch'] = thesearch
		output['htmlsearch'] = htmlsearch
		output['hitmax'] = hitmax
		output['onehit'] = frozensession['onehit']
		output['sortby'] = sortorderdecoder[frozensession['sortorder']]
		output['dmin'] = dmin
		output['dmax'] = dmax
		if justlatin() == False:
			output['icandodates'] = 'yes'
		else:
			output['icandodates'] = 'no'
		poll[ts].deactivate()

	else:
		output = {}
		output['title'] = '(empty query)'
		output['found'] = ''
		output['resultcount'] = 0
		output['scope'] = 0
		output['searchtime'] = '0.00'
		output['proximate'] = proximate
		output['thesearch'] = ''
		output['htmlsearch'] = '<span class="emph">nothing</span> (search not executed)'
		output['hitmax'] = 0
		output['dmin'] = dmin
		output['dmax'] = dmax
		if justlatin() is False:
			output['icandodates'] = 'yes'
		else:
			output['icandodates'] = 'no'
		output['sortby'] = frozensession['sortorder']
		output['onehit'] = frozensession['onehit']

	output = json.dumps(output)

	del poll[ts]

	return output


@hipparchia.route('/browse/<locus>')
def grabtextforbrowsing(locus):
	"""
	you want to browse something
	there are two standard ways to get results here: tell me a line or tell me a citation
		sample input: '/browseto/gr0059w030_LN_48203'
		sample input: '/browseto/gr0008w001_AT_23|3|3'
	alternately you can sent me a perseus ref from a dictionary entry ('_PE_') and I will *try* to convert it into a '_LN_'
	sample output: [could probably use retooling...]
		[{'forwardsandback': ['gr0199w010_LN_55', 'gr0199w010_LN_5']}, {'value': '<currentlyviewing><span class="author">Bacchylides</span>, <span class="work">Dithyrambi</span><br />Dithyramb 1, line 42<br /><span class="pubvolumename">Bacchylide. Dithyrambes, épinicies, fragments<br /></span><span class="pubpress">Les Belles Lettres , </span><span class="pubcity">Paris , </span><span class="pubyear">1993. </span><span class="pubeditor"> (Irigoin, J. )</span></currentlyviewing><br /><br />'}, {'value': '<table>\n'}, {'value': '<tr class="browser"><td class="browsedline"><observed id="[–⏑–––⏑–––⏑–]δ̣ουϲ">[–⏑–––⏑–––⏑–]δ̣ουϲ</observed> </td><td class="browsercite"></td></tr>\n'}, ...]

	:return:
	"""

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	workdb = re.sub('[\W_|]+', '', locus)[:10]

	try: ao = authordict[workdb[:6]]
	except: ao = makeanemptyauthor('gr0000')

	try:
		wo = workdict[workdb]
	except KeyError:
		if ao.universalid == 'gr0000':
			wo = makeanemptywork('gr0000w000')
		else:
			# you have only selected an author, but not a work: 'gr7000w_AT_1' will fail fecause we need 'wNNN'
			# so send line 1 of work 1
			wo = ao.listofworks[0]
			locus = wo.universalid + '_LN_' + str(wo.starts)

	ctx = int(session['browsercontext'])
	numbersevery = hipparchia.config['SHOWLINENUMBERSEVERY']

	resultmessage = 'success'

	passage = locus[10:]

	if passage[0:4] == '_LN_':
		# you were sent here either by the hit list or a forward/back button in the passage browser
		passage = re.sub('[\D]', '', passage[4:])
	elif passage[0:4] == '_AT_':
		# you were sent here by the citation builder autofill boxes
		p = locus[14:].split('|')
		cleanedp = [re.sub('[\W_|]+', '',level) for level in p]
		cleanedp = tuple(cleanedp[:5])
		if len(cleanedp) == wo.availablelevels:
			passage = finddblinefromlocus(wo.universalid, cleanedp, cur)
		else:
			p = finddblinefromincompletelocus(wo, cleanedp, cur)
			resultmessage = p['code']
			passage = p['line']
	elif passage[0:4] == '_PE_':
		# you came here via a perseus dictionary xref: all sorts of crazy ensues
		# nasty kludge with eur: should build the fixes into the db
		# euripides
		if 'gr0006' in workdb:
			remapper = dbquickfixes([workdb])
			workid = remapper[workdb]
			wo = workdict[workid]

		try:
			# dict does not always agree with our ids...
			# do an imperfect test for this by inviting the exception
			# you can still get a valid but wrong work, of course,
			# but if you ask for w001 and only w003 exists, this is supposed to take care of that
			returnfirstlinenumber(workdb, cur)
		except:
			# dict did not agree with our ids...: euripides, esp
			# what follows is a 'hope for the best' approach
			workid = perseusidmismatch(workdb, cur)
			wo = workdict[workid]
			# print('dictionary lookup id remap',workdb,workid,wo.title)

		citation = passage[4:].split(':')
		citation.reverse()

		# life=cal. or section=32
		needscleaning = [True for c in citation if len(c.split('=')) > 1]
		if True in needscleaning:
			citation = perseusdelabeler(citation, wo)

		# another problem 'J. ' in sallust <bibl id="lt0631w001_PE_J. 79:3" default="NO" valid="yes"><author>Sall.</author> J. 79, 3</bibl>
		# lt0631w002_PE_79:3 is what you need to send to finddblinefromincompletelocus()
		# note that the work number is wrong, so the next is only a partial fix and valid only if wNNN has been set right

		if ' ' in citation[-1]:
			citation[-1] = citation[-1].split(' ')[-1]

		p = finddblinefromincompletelocus(wo, citation, cur)
		resultmessage = p['code']
		passage = p['line']

	if passage:
		browserdata = getandformatbrowsercontext(ao, wo, int(passage), ctx, numbersevery, cur)
	else:
		browserdata = {}
		browserdata['browseforwards'] = wo.ends
		browserdata['browseback'] = wo.starts
		browserdata['currentlyviewing'] = '<p class="currentlyviewing">error in fetching the browser data for {ao}, {wo} </p><br /><br />'.format(ao=ao.shortname, wo=wo.title)
		try:
			browserdata['ouputtable'] = [passage, workdb, citation]
		except:
			browserdata['ouputtable'] = [passage, workdb]
		browserdata['authornumber'] = ao.universalid
		browserdata['workid'] = wo.universalid
		browserdata['authorboxcontents'] = ao.cleanname + ' [' + ao.universalid + ']'
		browserdata['workboxcontents'] = wo.title + ' (' + wo.universalid[-4:] + ')'

	if resultmessage != 'success':
		resultmessage = '<span class="small">({rc})</span>'.format(rc=resultmessage)
		browserdata['currentlyviewing'] = '{rc}<br />{bd}'.format(rc=resultmessage, bd=browserdata['currentlyviewing'])

	browserdata = json.dumps(browserdata)

	cur.close()

	return browserdata


@hipparchia.route('/indexto', methods=['GET'])
def completeindex():
	"""
	build a complete index to a an author, work, or segment of a work

	:return:
	"""

	try:
		ts = str(int(request.args.get('id', '')))
	except:
		ts = str(int(time.time()))

	starttime = time.time()

	poll[ts] = ProgressPoll(ts)
	poll[ts].activate()

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	req = tcparserequest(request, authordict, workdict)
	ao = req['authorobject']
	wo = req['workobject']
	psg = req['passagelist']

	if ao.universalid != 'gr0000' and wo.universalid != 'gr0000w000':
		# we have both an author and a work, maybe we also have a subset of the work
		if psg == ['']:
			# whole work
			poll[ts].statusis('Preparing an index to '+wo.title)
			startline = wo.starts
			endline = wo.ends
		else:
			# partial work
			poll[ts].statusis('Preparing a partial index to ' + wo.title)
			startandstop = textsegmentfindstartandstop(ao, wo, psg, cur)
			startline = startandstop['startline']
			endline = startandstop['endline']

		cdict = {wo.universalid: (startline, endline)}
		unsortedoutput = buildindextowork(cdict, poll[ts], cur)
		allworks = []

	elif ao.universalid != 'gr0000' and wo.universalid == 'gr0000w000':
		poll[ts].statusis('Preparing an index to the works of '+ao.shortname)
		# whole author
		cdict = {}
		for wkid in ao.listworkids():
			cdict[wkid] = (workdict[wkid].starts, workdict[wkid].ends)
		unsortedoutput = buildindextowork(cdict, poll[ts], cur)

		allworks = []
		for w in ao.listofworks:
			allworks.append(w.universalid[6:10] + ' ⇒ ' + w.title)
		allworks.sort()

	else:
		# we do not have a valid selection
		unsortedoutput = []
		allworks = []

	# get ready to send stuff to the page
	poll[ts].statusis('Sorting the index items')
	output = indexdictsorter(unsortedoutput)
	count = len(output)
	locale.setlocale(locale.LC_ALL, 'en_US')
	count = locale.format("%d", count, grouping=True)

	poll[ts].statusis('Preparing the index HTML')
	output = wordindextohtmltable(output)

	buildtime = time.time() - starttime
	buildtime = round(buildtime, 2)
	poll[ts].deactivate()

	results = {}
	results['authorname'] = ao.shortname
	results['title'] = wo.title
	results['structure'] = wo.citation()
	results['worksegment'] = '.'.join(psg)
	results['elapsed'] = buildtime
	results['wordsfound'] = count
	results['lines'] = output
	results['keytoworks'] = allworks

	results = json.dumps(results)

	cur.close()
	del dbc
	del poll[ts]

	return results


@hipparchia.route('/textof', methods=['GET'])
def textmaker():
	"""
	build a text suitable for display
	:return:
	"""
	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	linesevery = hipparchia.config['SHOWLINENUMBERSEVERY']

	req = tcparserequest(request, authordict, workdict)
	ao = req['authorobject']
	wo = req['workobject']
	psg = req['passagelist']

	if ao.universalid != 'gr0000' and wo.universalid == 'gr0000w000':
		# default to first work
		wo = ao.listofworks[0]

	if ao.universalid != 'gr0000' and wo.universalid != 'gr0000w000':
		# we have both an author and a work, maybe we also have a subset of the work
		if psg == ['']:
			# whole work
			startline = wo.starts
			endline = wo.ends
		else:
			startandstop = textsegmentfindstartandstop(ao, wo, psg, cur)
			startline = startandstop['startline']
			endline = startandstop['endline']

		output = buildtext(wo.universalid, startline, endline, linesevery, cur)
	else:
		output = []

	results = {}
	results['authorname'] = ao.shortname
	results['title'] = wo.title
	results['structure'] = wo.citation()
	results['worksegment'] = '.'.join(psg)
	results['lines'] = output

	results = json.dumps(results)

	cur.close()
	del dbc

	return results


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
	# session.clear()
	for key, value in cookiedict.items():
		modifysessionvar(key, value)


	# you need a master list out of authorgenresdict = { 'gk': gklist, 'lt': ltlist, 'in': inlist, 'dp': dplist }

	authorgenreslist = []
	for db in authorgenresdict:
		authorgenreslist += authorgenresdict[db]
	authorgenreslist = list(set(authorgenreslist))

	workgenreslist = []
	for db in workgenresdict:
		workgenreslist += workgenresdict[db]
	workgenreslist = list(set(workgenreslist))

	authorlocationlist = []
	for db in authorlocationdict:
		authorlocationlist += authorlocationdict[db]
	authorlocationlist = list(set(authorlocationlist))

	workprovenancelist = []
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

	strippedquery = re.sub('[\W_]+', '', authoruid)

	hint = []

	try:
		myauthor = authordict[strippedquery]
	except:
		myauthor = None

	if myauthor:
		worklist = myauthor.listofworks
		for work in worklist:
			hint.append({'value':work.title+' ('+work.universalid[-4:]+')'})
		if hint == []:
			hint.append({'value': 'somehow failed to find any works: try picking the author again'})
	else:
		hint.append({'value': 'author was not properly loaded: try again'})

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getauthorhint', methods=['GET'])
def offerauthorhints():
	"""
	fill the hint box with constantly updated values
	:return:
	"""

	strippedquery = re.sub(r'[!@#$|%()*\'\"]','',request.args.get('term', ''))

	ad = reducetosessionselections(listmapper, 'a')

	authorlist = ['{nm} [{id}]'.format(nm=ad[a].cleanname, id=ad[a].universalid) for a in ad]

	authorlist.sort()

	hint = []

	if strippedquery:
		hint = buildhintlist(strippedquery, authorlist)

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getgenrehint', methods=['GET'])
def augenrelist():
	"""
	populate the author genres autocomplete box with constantly updated values
	:return:
	"""

	strippedquery = re.sub('[\W_]+', '', request.args.get('term', ''))

	activedbs = returnactivedbs()
	activegenres = []
	for key in activedbs:
		activegenres += authorgenresdict[key]

	activegenres = list(set(activegenres))
	activegenres.sort()

	hint = []

	if len(activegenres) > 0:
		if strippedquery:
			hint = buildhintlist(strippedquery, activegenres)
	else:
		hint = ['(no author genre data available inside of your active database(s))']

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getworkgenrehint', methods=['GET'])
def wkgenrelist():
	"""
	populate the work genres autocomplete box with constantly updated values
	:return:
	"""

	strippedquery = re.sub('[\W_]+', '', request.args.get('term', ''))

	activedbs = returnactivedbs()
	activegenres = []
	for key in activedbs:
		activegenres += workgenresdict[key]

	activegenres = list(set(activegenres))
	activegenres.sort()

	hint = []

	if len(activegenres) > 0:
		if strippedquery:
			hint = buildhintlist(strippedquery, activegenres)
	else:
		hint = ['(no work genre data available inside of your active database(s))']

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getaulocationhint', methods=['GET'])
def offeraulocationhints():
	"""
	fill the hint box with constantly updated values

	:return:
	"""

	strippedquery = re.sub(r'[!@#$|%()*\'\"]', '', request.args.get('term', ''))

	activedbs = returnactivedbs()
	activelocations = []

	for key in activedbs:
		activelocations += authorlocationdict[key]

	activelocations = list(set(activelocations))
	activelocations.sort()

	hint = []

	if len(activelocations) > 0:
		if strippedquery:
			hint = buildhintlist(strippedquery, activelocations)
		else:
			hint = ['(no author location data available inside of your active database(s))']

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getwkprovenancehint', methods=['GET'])
def offerprovenancehints():
	"""
	fill the hint box with constantly updated values
	TODO: these should be pruned so as to exclude locations that are meaningless relative to the currently active DBs
		e.g., if you have only Latin active, location is meaningless; and many TLG places do not match INS locations

	:return:
	"""

	strippedquery = re.sub(r'[!@#$|%()*\'\"]', '', request.args.get('term', ''))

	activedbs = returnactivedbs()
	activelocations = []

	for key in activedbs:
		activelocations += workprovenancedict[key]

	activelocations = list(set(activelocations))
	activelocations.sort()

	hint = []

	if len(activelocations) > 0:
		if strippedquery:
			hint = buildhintlist(strippedquery, activelocations)
		else:
			hint = ['(no work provenance data available inside of your active database(s))']

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
	workid = re.sub('[\W_|]+', '', workid)

	try:
		passage = locus.split('_AT_')[1]
	except IndexError:
		passage = '-1'

	unsafepassage = passage.split('|')
	safepassage = [re.sub('[!@#$%^&*()=]+', '',p) for p in unsafepassage]
	safepassage = tuple(safepassage[:5])

	try:
		ao = authordict[workid[:6]]
	except:
		ao = makeanemptyauthor('gr0000')

	# it is a list of works and not a dict, so we can't pull the structure from the key
	# should probably change that some day
	structure = {}
	for work in ao.listofworks:
		if work.universalid == workid:
			structure = work.structure

	ws = {}
	if structure != {}:
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
	del dbc

	return results


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


@hipparchia.route('/getauthorinfo/<authorid>')
def getauthinfo(authorid):
	"""
	show local info about the author one is considering in the selection box
	:return:
	"""

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	authorid = re.sub('[\W_]+', '', authorid)

	theauthor = authordict[authorid]

	authinfo = ''
	authinfo += formatauthinfo(theauthor)

	if len(theauthor.listofworks) > 1:
		authinfo +='<br /><br /><span class="italic">work numbers:</span><br />\n'
	else:
		authinfo +='<br /><span class="italic">work:</span><br />\n'

	sortedworks = {work.universalid: work for work in theauthor.listofworks}

	keys = sortedworks.keys()
	keys = sorted(keys)

	for work in keys:
		authinfo += woformatworkinfo(sortedworks[work])

	authinfo = json.dumps(authinfo)

	cur.close()
	del dbc

	return authinfo


@hipparchia.route('/getsearchlistcontents')
def getsearchlistcontents():
	"""
	return a formatted list of what a search would look like if executed with the current selections

	:return:
	"""

	authorandworklist = compileauthorandworklist(listmapper)
	authorandworklist = sortauthorandworklists(authorandworklist, authordict)

	if len(authorandworklist) > 1:
		searchlistinfo = '<br /><h3>Proposing to search the following {ww} works:</h3>\n'.format(ww=len(authorandworklist))
		searchlistinfo += '(Results will be arranged according to {so})<br /><br />\n'.format(so=session['sortorder'])
	else:
		searchlistinfo = '<br /><h3>Proposing to search the following work:</h3>\n'

	count = 0
	wordstotal = 0
	for work in authorandworklist:
		work = work[:10]
		count += 1
		w = workdict[work]

		if w.universalid[0:2] not in ['in', 'dp', 'ch']:
			a = authordict[work[0:6]].shortname
		else:
			a = authordict[work[0:6]].idxname

		try:
			wordstotal += workdict[work].wordcount
		except:
			# TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'
			pass
		searchlistinfo += '\n[{ct}]&nbsp;'.format(ct=count)

		if w.converted_date:
			if int(w.converted_date) < 2000:
				if int(w.converted_date) < 1:
					searchlistinfo += '(<span class="date">{dt} BCE</span>)&nbsp;'.format(dt=w.converted_date[1:])
				else:
					searchlistinfo += '(<span class="date">{dt} CE</span>)&nbsp;'.format(dt=w.converted_date)

		searchlistinfo += formatauthorandworkinfo(a, w)

	if wordstotal > 0:
		searchlistinfo += '<br /><span class="emph">total words:</span> ' + format(wordstotal, ',d')

	searchlistinfo = json.dumps(searchlistinfo)

	return searchlistinfo


@hipparchia.route('/getgenrelistcontents')
def getgenrelistcontents():
	"""
	return a basic list of what you can pick
	:return:
	"""

	sessionmapper = { 'greekcorpus': 'gr', 'inscriptioncorpus': 'in', 'papyruscorpus': 'dp', 'latincorpus': 'lt'}
	genres = ''
	glist = []

	genres += '<h3>Author Categories</h3>'
	for sessionvar in ['greekcorpus', 'inscriptioncorpus', 'papyruscorpus', 'latincorpus']:
		if session[sessionvar] == 'yes':
			for g in authorgenresdict[sessionmapper[sessionvar]]:
				glist.append(g)

	if len(glist) > 0:
		genres += ', '.join(glist)
	else:
		genres += '[no author genres in your currently selected database(s)]'

	glist = []
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


@hipparchia.route('/parse/<observedword>')
def findbyform(observedword):
	"""
	this function sets of a chain of other functions
	find dictionary form
	find the other possible forms
	look up the dictionary form
	return a formatted set of info
	:return:
	"""

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	cleanedword = re.sub('[\W_|]+', '',observedword)
	# oddly 'ὕβˈριν' survives the '\W' check; should be ready to extend this list
	cleanedword = re.sub('[ˈ]+', '', cleanedword)
	cleanedword = removegravity(cleanedword)
	# python seems to know how to do this with greek...
	word = cleanedword.lower()

	if re.search(r'[a-z]', word[0]):
		cleanedword = stripaccents(word)
		usedictionary = 'latin'
	else:
		usedictionary = 'greek'

	cleanedword = cleanedword.lower()
	# a collection of HTML items that the JS will just dump out later; i.e. a sort of pseudo-page
	returnarray = []

	morphologyobject = lookformorphologymatches(cleanedword, usedictionary, cur)
	# print('findbyform() mm',morphologyobject.getpossible()[0].transandanal)
	# φέρεται --> morphologymatches [('<possibility_1>', '1', 'φέρω', '122883104', '<transl>fero</transl><analysis>pres ind mp 3rd sg</analysis>')]

	if morphologyobject:
		if hipparchia.config['SHOWGLOBALWORDCOUNTS'] == 'yes':
			returnarray.append(getobservedwordprevalencedata(cleanedword))
		returnarray += lexicalmatchesintohtml(cleanedword, morphologyobject, usedictionary, cur)
	else:
		returnarray = [{'value': '<br />[could not find a match for {cw} in the morphology table]'.format(cw=cleanedword)}, {'entries': '[not found]'}]

	returnarray = [r for r in returnarray if r]
	returnarray = [{'observed':cleanedword}] + returnarray
	returnarray = json.dumps(returnarray)

	cur.close()
	del dbc

	return returnarray


@hipparchia.route('/dictsearch/<searchterm>')
def dictsearch(searchterm):
	"""
	look up words
	return dictionary entries
	json packing
	:return:
	"""

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	seeking = re.sub(r'[!@#$|%()*\'\"\[\]]', '', searchterm)
	seeking = seeking.lower()
	seeking = re.sub('σ|ς', 'ϲ', seeking)
	seeking = re.sub('v', '(u|v|U|V)', seeking)

	if re.search(r'[a-z]', seeking):
		usedictionary = 'latin'
		usecolumn = 'entry_name'
	else:
		usedictionary = 'greek'
		usecolumn = 'unaccented_entry'

	seeking = stripaccents(seeking)
	query = 'SELECT entry_name FROM {d}_dictionary WHERE {c} ~* %s'.format(d=usedictionary,c=usecolumn)
	if seeking[0] == ' ' and seeking[-1] == ' ':
		data = ('^' + seeking[1:-1] + '$',)
	elif seeking[0] == ' ' and seeking[-1] != ' ':
		data = ('^' + seeking[1:] + '.*?',)
	else:
		data = ('.*?' + seeking + '.*?',)

	cur.execute(query, data)

	# note that the dictionary db has a problem with vowel lengths vs accents
	# SELECT * FROM greek_dictionary WHERE entry_name LIKE %s d ('μνᾱ/αϲθαι,μνάομαι',)
	try:
		found = cur.fetchall()
	except:
		found = []

	# the results should be given the polytonicsort() treatment
	returnarray = []

	if len(found) > 0:
		finddict = {f[0]:f for f in found}
		keys = finddict.keys()
		keys = polytonicsort(keys)

		sortedfinds = [finddict[k] for k in keys]

		if len(sortedfinds) == 1:
			# sending '0' to browserdictionarylookup() will hide the count number
			count = -1
		else:
			count = 0

		for entry in sortedfinds:
			count += 1
			returnarray.append({'value': browserdictionarylookup(count, entry[0], usedictionary, cur)})
	else:
		returnarray.append({'value':'[nothing found]'})

	returnarray = json.dumps(returnarray)

	cur.close()
	del dbc

	return returnarray


@hipparchia.route('/reverselookup/<searchterm>')
def reverselexiconsearch(searchterm):
	"""
	attempt to find all of the greek/latin dictionary entries that might go with the english search term
	:return:
	"""

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	returnarray = []
	seeking = re.sub(r'[!@#$|%()*\'\"]', '', searchterm)
	if justlatin():
		usedict = 'latin'
		translationlabel = 'hi'
	else:
		usedict = 'greek'
		translationlabel = 'tr'

	# first see if your term is mentioned at all
	query = 'SELECT entry_name FROM {d}_dictionary WHERE entry_body LIKE %s'.format(d=usedict)
	data = ('%' + seeking + '%',)
	cur.execute(query, data)

	matches = cur.fetchall()
	entries = []

	# then go back and see if it is mentioned in the summary of senses
	for match in matches:
		m = match[0]
		matchingobjectlist = searchdictionary(cur, usedict + '_dictionary', 'entry_name', m, syntax='LIKE')
		for o in matchingobjectlist:
			if o.entry:
				# AttributeError: 'list' object has no attribute 'entry'
				definition = o.body
				lemmaobject = grablemmataobjectfor(o.entry, usedict + '_lemmata', cur)
				summarydict = entrysummary(definition, usedict, translationlabel, lemmaobject)

				for sense in summarydict['senses']:
					if re.search(r'^'+seeking,sense):
						entries.append(m)

	entries = list(set(entries))
	entries = polytonicsort(entries)

	# in which case we should retrieve and format this entry
	if entries:
		count = 0
		for entry in entries:
			count += 1
			returnarray.append({'value': browserdictionarylookup(count, entry, usedict, cur)})
	else:
		returnarray.append({'value': '<br />[nothing found under "{skg}"]'.format(skg=seeking)})

	returnarray = json.dumps(returnarray)

	cur.close()
	del dbc

	return returnarray


@hipparchia.route('/setsessionvariable', methods=['GET'])
def setsessionvariable():
	"""
	accept a variable name and value: hand it off to the parser/setter
	returns:
		[{"latestdate": "1"}]
		[{"spuria": "no"}]
		etc.

	:return:
	"""

	param = re.search(r'(.*?)=.*?', request.query_string.decode('utf-8'))
	param = param.group(1)
	val = request.args.get(param)
	# need to accept '-' because of the date spinner
	val = re.sub('[!@#$%^&*()\[\]=;`+\\\'\"]+', '', val)

	modifysessionvar(param, val)

	result = json.dumps([{param: val}])

	return result


@hipparchia.route('/makeselection', methods=['GET'])
def selectionmade():
	"""
	once a choice is made, parse and register it inside session['selections']
	then return the human readable version of the same for display on the page

	this is also called without arguments to return the searchlist contents by
	skipping ahead to sessionselectionsashtml()

	sample input:
		'/makeselection?auth=gr0008&work=001&locus=3|4|23'

	sample output (pre-json):
		{'numberofselections': 2, 'timeexclusions': '', 'exclusions': '<span class="picklabel">Works</span><br /><span class="wkexclusions" id="searchselection_02" listval="0">Bacchylides, <span class="pickedwork">Dithyrambi</span></span><br />', 'selections': '<span class="picklabel">Author categories</span><br /><span class="agnselections" id="searchselection_00" listval="0">Lyrici</span><br />\n<span class="picklabel">Authors</span><br /><span class="auselections" id="searchselection_01" listval="0">AG</span><br />\n'}

	:return:
	"""

	# lingering bug that should be handled: if you swap languages and leave lt on a gr list, you will have trouble compiling the searchlist

	# you clicked #pickauthor or #excludeauthor
	try:
		workid = re.sub('[\W_]+', '', request.args.get('work', ''))
	except:
		workid = ''

	try:
		uid = re.sub('[\W_]+', '', request.args.get('auth', ''))
	except:
		uid = ''

	try:
		locus = re.sub('[!@#$%^&*()=;]+', '', request.args.get('locus', ''))
	except:
		locus = ''

	try:
		exclude = re.sub('[^tf]', '', request.args.get('exclude', ''))
	except:
		exclude = ''

	# you clicked #pickgenre or #excludegenre
	try:
		auloc = re.sub('[!@#$%^&*=;]+', '', request.args.get('auloc', ''))
	except:
		auloc = ''

	try:
		wkprov = re.sub('[!@#$%^&*=;]+', '', request.args.get('wkprov', ''))
	except:
		wkprov = ''

	try:
		genre = re.sub('[!@#$%^&*=;]+', '', request.args.get('genre', ''))
	except:
		genre = ''

	try:
		# need periods (for now): just remove some obvious problem cases
		wkgenre = re.sub('[\[\]\'\\&\*\%\^_;]+', '', request.args.get('wkgenre', ''))
	except:
		wkgenre = ''

	if exclude != 't':
		suffix = 'selections'
		other = 'exclusions'
	else:
		suffix = 'exclusions'
		other = 'selections'

	if (uid != '') and (workid != '') and (locus != ''):
		# a specific passage
		session['psg' + suffix].append(uid + 'w' + workid + '_AT_' + locus)
		session['psg' + suffix] = tidyuplist(session['psg' + suffix])
		rationalizeselections(uid + 'w' + workid + '_AT_' + locus, suffix)
	elif (uid != '') and (workid != ''):
		# a specific work
		session['wk' + suffix].append(uid + 'w' + workid)
		session['wk' + suffix] = tidyuplist(session['wk' + suffix])
		rationalizeselections(uid + 'w' + workid, suffix)
	elif (uid != '') and (workid == ''):
		# a specific author
		session['au' + suffix].append(uid)
		session['au' + suffix] = tidyuplist(session['au' + suffix])
		rationalizeselections(uid, suffix)

	# if vs elif: allow multiple simultaneous settings
	if genre != '':
		# add to the +/- genre list and then subtract from the -/+ list
		session['agn' + suffix].append(genre)
		session['agn' + suffix] = tidyuplist(session['agn' + suffix])
		session['agn' + other] = dropdupes(session['agn' + other], session['agn' + suffix])
	if wkgenre != '':
		# add to the +/- genre list and then subtract from the -/+ list
		session['wkgn' + suffix].append(wkgenre)
		session['wkgn' + suffix] = tidyuplist(session['wkgn' + suffix])
		session['wkgn' + other] = dropdupes(session['wkgn' + other], session['wkgn' + suffix])
	if auloc != '':
		# add to the +/- locations list and then subtract from the -/+ list
		session['aloc' + suffix].append(auloc)
		session['aloc' + suffix] = tidyuplist(session['aloc' + suffix])
		session['aloc' + other] = dropdupes(session['aloc' + other], session['aloc' + suffix])
	if wkprov != '':
		# add to the +/- locations list and then subtract from the -/+ list
		session['wloc' + suffix].append(wkprov)
		session['wloc' + suffix] = tidyuplist(session['wloc' + suffix])
		session['wloc' + other] = dropdupes(session['wloc' + other], session['wloc' + suffix])

	# after the update to the data, you need to update the page html

	return getcurrentselections()


@hipparchia.route('/clearselections', methods=['GET'])
def clearselections():
	"""
	a selection gets thrown into the trash
	:return:
	"""
	category = request.args.get('cat', '')
	selectiontypes = ['auselections', 'wkselections', 'psgselections', 'agnselections', 'wkgnselections', 'alocselections', 'wlocselections',
					  'auexclusions', 'wkexclusions', 'psgexclusions', 'agnexclusions', 'wkgnexclusions', 'alocexclusions', 'wlocexclusions']
	if category not in selectiontypes:
		category = ''

	item = request.args.get('id', '')
	item = int(item)

	try:
		session[category].pop(item)
	except:
		print('failed to pop', category, str(item))
		pass

	session.modified = True

	return getcurrentselections()


@hipparchia.route('/getselections')
def getcurrentselections():
	"""

	send the html for what we have picked so that the relevant box can be populate

	get three bundles to put in the table cells

	stored in a dict with three keys: timeexclusions, selections, exclusions, numberofselections

	:return:
	"""

	htmlbundles = sessionselectionsashtml(authordict, workdict)
	htmlbundles = json.dumps(htmlbundles)

	return htmlbundles


@hipparchia.route('/clear')
def clearsession():
	"""
	clear the session
	this will reset all settings and reload the front page
	:return:
	"""

	session.clear()
	return redirect(url_for('frontpage'))


async def wscheckpoll(websocket, path):
	"""

	note that this is a non-view in views.py: a pain to import it becuase it needs access to poll = {}

	a poll checker started by startwspolling(): the client sends the name of a poll and this will output
	the status of the poll continuously while the poll remains active

	:param websocket:
	:param path:
	:return:
	"""

	try:
		ts = await websocket.recv()
	except websockets.exceptions.ConnectionClosed:
		# you reloaded the page
		return

	while True:
		progress = {}
		try:
			progress['active'] = poll[ts].getactivity()
			progress['total'] = poll[ts].worktotal()
			progress['remaining'] = poll[ts].getremaining()
			progress['hits'] = poll[ts].gethits()
			progress['message'] = poll[ts].getstatus()
			progress['elapsed'] = poll[ts].getelapsed()
			if hipparchia.config['SUPPRESSLONGREQUESTMESSAGE'] == 'no':
				if poll[ts].getnotes():
					progress['extrainfo'] = poll[ts].getnotes()
			else:
				progress['extrainfo'] = ''
		except KeyError:
			# the poll is deleted when the query ends; you will always end up here
			progress['active'] = 'inactive'
			try:
				await websocket.send(json.dumps(progress))
			except websockets.exceptions.ConnectionClosed:
				# you reloaded the page in the middle of a search and both the poll and the socket vanished
				pass
			break
		await asyncio.sleep(.4)
		# print('progress',progress)
		try:
			await websocket.send(json.dumps(progress))
		except websockets.exceptions.ConnectionClosed:
			# websockets.exceptions.ConnectionClosed because you reloaded the page in the middle of a search
			pass

	return


@hipparchia.route('/startwspolling/<theport>', methods=['GET'])
def startwspolling(theport=hipparchia.config['PROGRESSPOLLDEFAULTPORT']):
	"""

	launch a websocket poll server

	tricky because loop.run_forever() will run forever: you can't start this when you launch HipparchiaServer without
	blocking execution of everything else; only a call via the URL mechanism will let you delagate this to an independent
	thread

	the poll is more or less eternal: the libary was coded that way, and it is kind of irritating

	startwspolling() will get called every time you reload the front page: it is at the top of documentready.js

	multiple servers on multiple ports is possible, but not yet implemented: a multi-client model is not a priority

	:param theport:
	:return:
	"""

	try:
		theport = int(theport)
	except:
		theport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	# min/max are a very good idea since you are theoretically giving anyone anywhere the power to open a ws socket: 64k+ of them would be sad
	if hipparchia.config['PROGRESSPOLLMINPORT'] < theport < hipparchia.config['PROGRESSPOLLMAXPORT']:
		theport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	# because we are not in the main thread we cannot ask for the default loop
	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	wspolling = websockets.serve(wscheckpoll, '127.0.0.1', port=theport, loop=loop)

	try:
		loop.run_until_complete(wspolling)
	except OSError:
		# print('websocket is already listening at',theport)
		pass

	try:
		loop.run_forever()
	finally:
		loop.run_until_complete(loop.shutdown_asyncgens())
		loop.close()

	# actually this function never returns
	print('wow: startwspolling() returned')
	return


@hipparchia.route('/confirm/<ts>')
def checkforactivesearch(ts):
	"""

	test the activity of a poll so you don't start conjuring a bunch of key errors if you use wscheckpoll() prematurely

	:param ts:
	:return:
	"""

	try:
		ts = str(int(ts))
	except:
		ts = str(int(time.time()))

	theport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	# sock.setblocking(0)
	result = sock.connect_ex(('127.0.0.1', theport))
	if result == 0:
		pass
	else:
		print('websocket probe failed:',errno.errorcode[result])
		# need to fire up the websocket
		try:
			r = urlopen('http://127.0.0.1:5000/startwspolling/default', data=None, timeout=.1)
		except socket.timeout:
			# socket.timeout: but our aim was to send the request, not to read the response and get blocked
			print('websocket at {p} was told to launch'.format(p=theport))

	sock.close()
	del sock

	try:
		if poll[ts].getactivity():
			return json.dumps(theport)
	except KeyError:
		time.sleep(.1)
		try:
			if poll[ts].getactivity():
				return json.dumps(theport)
			else:
				print('checkforactivesearch() reports that the websocket is still inactive: there is a serious problem?')
				return json.dumps('no')
		except:
			return json.dumps('no')


@hipparchia.route('/favicon.ico')
def sendfavicon():
	return send_file('static/images/hipparchia_favicon.ico')


@hipparchia.route('/apple-touch-icon-precomposed.png')
def appletouchticon():
	return send_file('static/images/hipparchia_apple-touch-icon-precomposed.png')


# old progress architecture: will be removed
@hipparchia.route('/progress', methods=['GET'])
def progressreport():
	"""
	allow js to poll the progress of a long operation
	this code is itself in progress and will remain so for a while

	note that if you run through uWSGI the GET sent to '/executesearch' will block/lock the IO
	this will prevent anything GET being sent to '/progress' until after jsexecutesearch() finishes
	not quite the async dreamland you had imagined

	searches will work, but the progress statements will be broken

	:return:
	"""

	try:
		ts = str(int(request.args.get('id', '')))
	except:
		ts = str(int(time.time()))

	progress = {}
	try:
		progress['active'] = poll[ts].getactivity()
		progress['total'] = poll[ts].worktotal()
		progress['remaining'] = poll[ts].getremaining()
		progress['hits'] = poll[ts].gethits()
		progress['message'] = poll[ts].getstatus()
	except:
		time.sleep(.1)
		try:
			progress['active'] = poll[ts].getactivity()
			progress['total'] = poll[ts].worktotal()
			progress['remaining'] = poll[ts].getremaining()
			progress['hits'] = poll[ts].gethits()
			progress['message'] = poll[ts].getstatus()
		except:
			progress = {'active': 0}

	progress = json.dumps(progress)

	return progress

