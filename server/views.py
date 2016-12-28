# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import json
import time
import re
from flask import render_template, redirect, request, url_for, session

from server import hipparchia
from server.hipparchiaclasses import ProgressPoll
from server.dbsupport.dbfunctions import setconnection, makeanemptyauthor, makeanemptywork, versionchecking
from server.dbsupport.citationfunctions import findvalidlevelvalues, finddblinefromlocus, finddblinefromincompletelocus
from server.lexica.lexicaformatting import parsemorphologyentry, entrysummary, dbquickfixes
from server.lexica.lexicalookups import browserdictionarylookup, searchdictionary
from server.searching.searchformatting import formatauthinfo, formatauthorandworkinfo, woformatworkinfo, mpresultformatter
from server.searching.searchfunctions import flagexclusions, compileauthorandworklist, calculatewholeauthorsearches
from server.searching.searchdispatching import searchdispatcher, dispatchshortphrasesearch
from server.searching.betacodetounicode import replacegreekbetacode
from server.textsandconcordnaces.concordancemaker import buildconcordancefromwork
from server.textsandconcordnaces.textandconcordancehelperfunctions import tcparserequest, tcfindstartandstop, conctohtmltable, \
	concordancesorter
from server.textsandconcordnaces.textbuilder import buildtext
from server.listsandsession.sessionfunctions import modifysessionvar, modifysessionselections, parsejscookie, \
	sessionvariables, sessionselectionsashtml, rationalizeselections, justgreek, justlatin, reducetosessionselections, returnactivedbs
from server.formatting_helper_functions import removegravity, stripaccents, bcedating, htmlifysearchfinds
from server.listsandsession.listmanagement import dropdupes, polytonicsort, sortauthorandworklists, sortresultslist, \
	tidyuplist
from server.browsing.browserfunctions import getandformatbrowsercontext

# ready some sets of objects that will be generally available: a few seconds spent here will save you the same over and over again later as you constantly regenerate author and work info
# this will give you listmapper{}, authordict{}, etc.
from server.loadglobaldicts import *

# empty dict in which to store progress polls
# note that more than one poll can be running
poll = {}


@hipparchia.route('/', methods=['GET', 'POST'])
def frontpage():
	"""
	the front page
	it used to do stuff
	now it just loads the JS which then calls all of the routes below
	
	:return:
	"""

	expectedsqltemplateversion = 12272016

	sessionvariables()

	# check to see which dbs we actually own
	activelists = []
	for list in listmapper:
		if len(listmapper[list]['a']) > 0:
			activelists.append(list)

	versionchecking(activelists, expectedsqltemplateversion)

	page = render_template('search.html',activelists=activelists)
	
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

	authors = []
	
	keys = list(authordict.keys())
	keys.sort()
	for k in keys:
		authors.append(authordict[k])
	return render_template('lister.html', found=authors, numberfound=len(authors))
	

#
# helpers & routes you should not browse directly
#
@hipparchia.route('/executesearch', methods=['GET'])
def executesearch():
	"""
	the interface to all of the other search functions
	tell me what you are looking for and i'll try to find it
	
	the results are returned in a json bundle that will be used to update the html on the page
	
	:return:
	"""
	sessionvariables()
	# need to sanitize input at least a bit...
	try:
		seeking = re.sub(r'[\'"`!;&]', '', request.args.get('seeking', ''))
	except:
		seeking = ''
	
	try:
		proximate = re.sub(r'[\'"`!;&]', '', request.args.get('proximate', ''))
	except:
		proximate = ''
	
	try:
		ts = str(int(request.args.get('id', '')))
	except:
		ts = str(int(time.time()))
	
	if len(seeking) < 1 and len(proximate) > 0:
		seeking = proximate
		proximate = ''
	
	dmin, dmax = bcedating()
	
	if justgreek() and re.search('[a-zA-Z]', seeking) is not None:
		# searching greek, but not typing in unicode greek: autoconvert
		seeking = seeking.upper()
		seeking = replacegreekbetacode(seeking)
	
	if justgreek() and re.search('[a-zA-Z]', proximate) is not None:
		proximate = proximate.upper()
		proximate = replacegreekbetacode(proximate)
	
	phrasefinder = re.compile('[^\s]\s[^\s]')
	
	poll[ts] = ProgressPoll(ts)
	poll[ts].activate()
	poll[ts].statusis('Preparing to search')
	
	linesofcontext = int(session['linesofcontext'])
	searchtime = 0
	
	if len(seeking) > 0:
		seeking = seeking.lower()
		starttime = time.time()
		poll[ts].statusis('Compiling the list of works to search')
		
		authorandworklist = compileauthorandworklist(listmapper)
		# mark works that have passage exclusions associated with them: gr0001x001 instead of gr0001w001 if you are skipping part of w001
		poll[ts].statusis('Marking exclusions from the list of works to search')
		authorandworklist = flagexclusions(authorandworklist)
		workssearched = len(authorandworklist)
		poll[ts].statusis('Calculating full authors to search')
		authorandworklist = calculatewholeauthorsearches(authorandworklist, authordict)

		# worklist is unsorted, and the index is only semi-useful right now, but it is hard to rip it out
		# since it is also used to allow the manager to manage a dict and its keys

		indexedworklist = []
		index = -1
		for w in authorandworklist:
			index += 1
			indexedworklist.append((index, w))
		del authorandworklist

		# assemble a subset of authordict that will be relevant to our actual search and send it to searchdispatcher()
		# it turns out that we only need to pass authors that are part of psgselections or psgexclusions
		# whereclauses() is selectively invoked and it needs to check the information in those and only those authors and works
		# formerly all authors were sent through searchdispatcher(), but loading them into the manager produced
		# a massive slowdown (as 200k objects got pickled into a mpshareable dict)

		authorswheredict = {}

		for w in session['psgselections']:
			authorswheredict[w[0:6]] = authordict[w[0:6]]
		for w in session['psgexclusions']:
			authorswheredict[w[0:6]] = authordict[w[0:6]]

		if len(proximate) < 1 and re.search(phrasefinder, seeking) is None:
			searchtype = 'simple'
			thesearch = seeking
			htmlsearch = '<span class="emph">' + seeking + '</span>'
			hits = searchdispatcher('simple', seeking, proximate, indexedworklist, authorswheredict, poll[ts])
		elif re.search(phrasefinder, seeking) is not None:
			searchtype = 'phrase'
			thesearch = seeking
			htmlsearch = '<span class="emph">' + seeking + '</span>'
			terms = seeking.split(' ')
			if len(max(terms, key=len)) > 3:
				hits = searchdispatcher('phrase', seeking, proximate, indexedworklist, authorswheredict, poll[ts])
			else:
				# you are looking for a set of little words: και δη και, etc.
				#   16s to find και δη και via a std phrase search; 1.6s to do it this way
				# not immediately obvious what the best number for minimum max term len is:
				# consider what happens if you send a '4' this way:
				#   εἶναι τὸ κατὰ τὴν (Searched between 850 B.C.E. and 200 B.C.E.)
				# this takes 13.7s with a std phrase search; it takes 14.6s if sent to shortphrasesearch()
				#   οἷον κἀν τοῖϲ (Searched between 850 B.C.E. and 200 B.C.E.)
				#   5.57 std; 17.54s 'short'
				# so '3' looks like the right answer
				hits = dispatchshortphrasesearch(seeking, indexedworklist, authorswheredict, poll[ts])
		else:
			searchtype = 'proximity'
			if session['searchscope'] == 'W':
				scope = 'words'
			else:
				scope = 'lines'
			
			if session['nearornot'] == 'T':
				nearstr = ''
			else:
				nearstr = ' not'
			thesearch = seeking + nearstr + ' within ' + session['proximity'] + ' ' + scope + ' of ' + proximate
			htmlsearch = '<span class="emph">' + seeking + '</span>' + nearstr + ' within ' + session['proximity'] + ' ' \
			             + scope + ' of ' + '<span class="emph">' + proximate + '</span>'
			hits = searchdispatcher('proximity', seeking, proximate, indexedworklist, authorswheredict, poll[ts])
		
		poll[ts].statusis('Putting the results in context')

		# safe to send authordict and workdict to mpresultformatter() because only the objects relevant to hits
		# will get sent to the manager (thus avoiding the problem you see with loading them all into searchdispacher()

		hitdict = sortresultslist(hits, authordict, workdict)
		allfound = mpresultformatter(hitdict, authordict, workdict, seeking, proximate, searchtype, poll[ts])
		
		searchtime = time.time() - starttime
		searchtime = round(searchtime, 2)
		if len(allfound) > int(session['maxresults']):
			allfound = allfound[0:int(session['maxresults'])]
		
		poll[ts].statusis('Converting results to HTML')
		htmlandjs = htmlifysearchfinds(allfound)
		finds = htmlandjs['hits']
		findsjs = htmlandjs['hitsjs']
		
		resultcount = len(allfound)
		
		if resultcount < int(session['maxresults']):
			hitmax = 'false'
		else:
			hitmax = 'true'
		
		# prepare the output

		sortorderdecoder = {
			'universalid': 'ID', 'shortname': 'name', 'genres': 'author genre', 'converted_date': 'date', 'location': 'location'
		}

		output = {}
		output['title'] = thesearch
		output['found'] = finds
		output['js'] = findsjs
		output['resultcount'] = resultcount
		output['scope'] = str(workssearched)
		output['searchtime'] = str(searchtime)
		output['lookedfor'] = seeking
		output['proximate'] = proximate
		output['thesearch'] = thesearch
		output['htmlsearch'] = htmlsearch
		output['hitmax'] = hitmax
		output['sortby'] = sortorderdecoder[session['sortorder']]
		output['dmin'] = dmin
		output['dmax'] = dmax
		if justlatin() == False:
			output['icandodates'] = 'yes'
		else:
			output['icandodates'] = 'no'
		poll[ts].deactivate()
		
	else:
		output = {}
		output['title'] = seeking
		output['found'] = ''
		output['resultcount'] = 0
		output['scope'] = 0
		output['searchtime'] = '0.00'
		output['lookedfor'] = '[no search executed]'
		output['proximate'] = proximate
		output['thesearch'] = ''
		output['htmlsearch'] = ''
		output['hitmax'] = 0
		output['dmin'] = dmin
		output['dmax'] = dmax
		if justlatin() == False:
			output['icandodates'] = 'yes'
		else:
			output['icandodates'] = 'no'
		output['sortby'] = session['sortorder']
	
	output = json.dumps(output)
	
	del poll[ts]
	
	return output


@hipparchia.route('/concordance', methods=['GET'])
def concordance():
	"""
	build a concordance
	modes should go away later
	modes:
		0 - of this work
		1 - of words unique to this work in this author
		2 - of this author
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
			poll[ts].statusis('Preparing a concordance to '+wo.title)
			startline = wo.starts
			endline = wo.ends
		else:
			# partial work
			poll[ts].statusis('Preparing a partial concordance to ' + wo.title)
			startandstop = tcfindstartandstop(ao, wo, psg, cur)
			startline = startandstop['startline']
			endline = startandstop['endline']

		cdict = {wo.universalid: (startline, endline)}
		unsortedoutput = buildconcordancefromwork(cdict, poll[ts], cur)
		allworks = []
		
	elif ao.universalid != 'gr0000' and wo.universalid == 'gr0000w000':
		poll[ts].statusis('Preparing a concordance to the works of '+ao.shortname)
		# whole author
		cdict = {}
		for wkid in ao.listworkids():
			cdict[wkid] = (workdict[wkid].starts, workdict[wkid].ends)
		unsortedoutput = buildconcordancefromwork(cdict, poll[ts], cur)
			
		allworks = []
		for w in ao.listofworks:
			allworks.append(w.universalid[6:10] + ' ==> ' + w.title)
		allworks.sort()
		
	else:
		# we do not have a valid selection
		unsortedoutput = []
		allworks = []
	
	# get ready to send stuff to the page
	poll[ts].statusis('Sorting the concordance items')
	output = concordancesorter(unsortedoutput)
	count = len(output)

	poll[ts].statusis('Preparing the concordance HTML')
	output = conctohtmltable(output)
	
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


@hipparchia.route('/text', methods=['GET'])
def textmaker():
	"""
	build a text suitable for display
	:return:
	"""
	dbc = setconnection('autocommit')
	cur = dbc.cursor()
	
	try:
		linesevery = int(re.sub('[^\d]', '', request.args.get('linesevery', '')))
	except:
		linesevery = 10
	
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
			startandstop = tcfindstartandstop(ao, wo, psg, cur)
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


@hipparchia.route('/progress', methods=['GET'])
def progressreport():
	"""
	allow js to poll the progress of a long operation
	this code is itself in progress and will remain so for a while

	note that if you run through uWSGI the GET sent to '/executesearch' will block/lock the IO
	this will prevent anything GET being sent to '/progress' until after jsexecutesearch() finishes
	not quite the async dreamland you had imagined

	searches will work, but the progress statements will be broken
	
	also multiple clients will confuse hipparchia

	something like gevent needs to be integrated so you can handle async requests, I guess.
	websockets: but that's plenty of extra imports for what is generally a one-user model

	New in Python 3.6: PEP 525: Asynchronous Generator
	This probably makes a websockets poll a lot easier to write

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


@hipparchia.route('/getcookie', methods=['GET'])
def cookieintosession():
	"""
	take a stored cookie and convert its values into the current session settings
	
	:return:
	"""
	cookienum = request.args.get('cookie', '')
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


@hipparchia.route('/getauthorhint', methods=['GET'])
def offerauthorhints():
	"""
	fill the hint box with constantly updated values
	:return:
	"""
	global authordict

	strippedquery = re.sub(r'[!@#$|%()*\'\"]','',request.args.get('term', ''))

	ad = reducetosessionselections(listmapper, 'a')

	authorlist = []
	for a in ad:
		authorlist.append(ad[a].cleanname+' ['+ad[a].universalid+']')
		
	authorlist.sort()
	
	hint = []

	if strippedquery != '':
		query = strippedquery.lower()
		qlen = len(query)
		for author in authorlist:
			if query == author.lower()[0:qlen]:
				# jquery will gobble up label and value
				# another tag can be used for holding other info
				# pass that to 'ui.item.OTHERTAG' to be evaluated
				hint.append({'value':author})
	hint = json.dumps(hint)
	return hint


@hipparchia.route('/getworkhint', methods=['GET'])
def offerworkhints():
	"""
	fill the hint box with constantly updated values
	:return:
	"""
	# global authordict
	
	strippedquery = re.sub('[\W_]+', '', request.args.get('auth', ''))
	
	hint = []
	
	try:
		myauthor = authordict[strippedquery]
	except:
		myauthor = None
	
	if myauthor is not None:
		worklist = myauthor.listofworks
		for work in worklist:
			hint.append({'value':work.title+' ('+work.universalid[-4:]+')'})
		if hint == []:
			hint.append({'value': 'somehow failed to find any works: try picking the author again'})
	else:
		hint.append({'value': 'author was not properly loaded: try again'})
	
	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getgenrehint', methods=['GET'])
def augenrelist():
	"""
	populate the author genres autocomplete box with constantly updated values
	:return:
	"""

	strippedquery = re.sub('[\W_]+', '', request.args.get('term', ''))

	hint = []

	activedbs = returnactivedbs()
	activegenres = []
	for key in activedbs:
		activegenres += authorgenresdict[key]

	activegenres = list(set(activegenres))

	if len(activegenres) > 0:
		if strippedquery != '':
			query = strippedquery.lower()
			qlen = len(query)
			for genre in activegenres:
				hintgenre = genre.lower()
				if query == hintgenre[0:qlen]:
					# jquery will gobble up label and value
					# another tag can be used for holding other info
					# pass that to 'ui.item.OTHERTAG' to be evaluated
					hint.append({'value': genre})
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

	hint = []

	activedbs = returnactivedbs()
	activegenres = []
	for key in activedbs:
		activegenres += workgenresdict[key]

	activegenres = list(set(activegenres))

	if len(activegenres) > 0:
		if strippedquery != '':
			query = strippedquery.lower()
			qlen = len(query)
			for genre in activegenres:
				hintgenre = genre.lower()
				if query == hintgenre[0:qlen]:
					# jquery will gobble up label and value
					# another tag can be used for holding other info
					# pass that to 'ui.item.OTHERTAG' to be evaluated
					hint.append({'value': genre})
	else:
		hint = ['(no work genre data available inside of your active database(s))']

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getaulocationhint', methods=['GET'])
def offeraulocationhints():
	"""
	fill the hint box with constantly updated values
	TODO: these should be pruned so as to exclude locations that are meaningless relative to the currently active DBs
		e.g., if you have only Latin active, location is meaningless; and many TLG places do not match INS locations

	:return:
	"""

	strippedquery = re.sub(r'[!@#$|%()*\'\"]', '', request.args.get('term', ''))

	hint = []

	activedbs = returnactivedbs()
	activelocations = []

	for key in activedbs:
		activelocations += authorlocationdict[key]

	activelocations = list(set(activelocations))

	if len(activelocations) > 0:
		if strippedquery != '':
			query = strippedquery.lower()
			qlen = len(query)
			for location in activelocations:
				if query == location.lower()[0:qlen]:
					hint.append({'value': location})
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

	hint = []

	activedbs = returnactivedbs()
	activelocations = []

	for key in activedbs:
		activelocations += workprovenancedict[key]

	activelocations = list(set(activelocations))

	if len(activelocations) > 0:
		if strippedquery != '':
			query = strippedquery.lower()
			qlen = len(query)
			for location in activelocations:
				if query == location.lower()[0:qlen]:
					hint.append({'value': location})
		else:
			hint = ['(no work provenance data available inside of your active database(s))']

	hint = json.dumps(hint)
	return hint


@hipparchia.route('/getstructure', methods=['GET'])
def workstructure():
	"""
	request detailed info about how a work works
	this is fed back to the js boxes : who should be active, what are the autocomplete values, etc?

	sample input: '/getstructure?locus=gr0008w001_AT_-1'; '/getstructure?locus=gr0008w001_AT_13|22'
	:return:
	"""
	dbc = setconnection('autocommit')
	cur = dbc.cursor()
	
	passage = request.args.get('locus', '')[14:].split('|')
	safepassage = []
	for level in passage:
		safepassage.append(re.sub('[!@#$%^&*()=]+', '',level))
	safepassage = tuple(safepassage[:5])
	workid = re.sub('[\W_|]+', '', request.args.get('locus', ''))[:10]

	try:
		ao = authordict[workid[:6]]
	except:
		ao = makeanemptyauthor('gr0000')
		
	structure = {}
	for work in ao.listofworks:
		if work.universalid == workid:
			structure = work.structure
	
	ws = {}
	if structure != {}:
		lowandhigh = findvalidlevelvalues(workid, structure, safepassage, cur)
		# example: (4, 3, 'Book', '1', '7', ['1', '2', '3', '4', '5', '6', '7'])
		ws['totallevels'] = lowandhigh[0]
		ws['level'] = lowandhigh[1]
		ws['label'] = lowandhigh[2]
		ws['low'] = lowandhigh[3]
		ws['high'] = lowandhigh[4]
		ws['range'] = lowandhigh[5]
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
	a simple fetch and report: JS wants to know what Python knows
	
	:return:
	"""
	returndict = {}
	for k in session.keys():
		if k != 'csrf_token':
			returndict[k] = session[k]

	# print('rd',returndict)
	returndict = json.dumps(returndict)

	return returndict


@hipparchia.route('/getauthorinfo', methods=['GET'])
def getauthinfo():
	"""
	show local info about the author one is considering in the selection box
	:return:
	"""
	
	dbc = setconnection('autocommit')
	cur = dbc.cursor()
	
	authorid = re.sub('[\W_]+', '', request.args.get('au', ''))
	
	theauthor = authordict[authorid]
	
	authinfo = ''
	authinfo += formatauthinfo(theauthor)
	
	if len(theauthor.listofworks) > 1:
		authinfo +='<br /><br /><span class="italic">work numbers:</span><br />\n'
	else:
		authinfo +='<br /><span class="italic">work:</span><br />\n'

	sortedworks = {}
	for work in theauthor.listofworks:
		sortedworks[work.universalid] = work

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
	
	searchlistinfo = '<br /><h3>Proposing to search the following works:</h3>\n'
	searchlistinfo += '(Results will be arranged according to '+session['sortorder']+')<br /><br />\n'
	
	count = 0
	wordstotal = 0
	for work in authorandworklist:
		work = work[:10]
		count += 1
		w = workdict[work]
		a = authordict[work[0:6]].shortname
		
		try:
			wordstotal += workdict[work].wordcount
		except:
			# TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'
			pass
		searchlistinfo += '\n[' + str(count) + ']&nbsp;'

		if int(w.converted_date) < 2000:
			if int(w.converted_date) < 1:
				searchlistinfo += '('+w.converted_date[1:]+ ' BCE)&nbsp;'
			else:
				searchlistinfo += '(' + w.converted_date + ' CE)&nbsp;'

		searchlistinfo += formatauthorandworkinfo(a, w)

	if wordstotal > 0:
		searchlistinfo += '<br /><span class="emph">total words:</span> ' + format(wordstotal, ',d')
	
	searchlistinfo = json.dumps(searchlistinfo)
	
	return searchlistinfo


@hipparchia.route('/browseto', methods=['GET'])
def grabtextforbrowsing():
	"""
	you want to browse something
	there are two standard ways to get results here: tell me a line or tell me a citation
		sample input: '/browseto?locus=gr0059w030_LN_48203'
		sample input: '/browseto?locus=gr0008w001_AT_23|3|3'
	alternately you can sent me a perseus ref from a dictionary entry ('_PE_') and I will *try* to convert it into a '_LN_'
	sample output: [could probably use retooling...]
		[{'forwardsandback': ['gr0199w010_LN_55', 'gr0199w010_LN_5']}, {'value': '<currentlyviewing><span class="author">Bacchylides</span>, <span class="work">Dithyrambi</span><br />Dithyramb 1, line 42<br /><span class="pubvolumename">Bacchylide. Dithyrambes, épinicies, fragments<br /></span><span class="pubpress">Les Belles Lettres , </span><span class="pubcity">Paris , </span><span class="pubyear">1993. </span><span class="pubeditor"> (Irigoin, J. )</span></currentlyviewing><br /><br />'}, {'value': '<table>\n'}, {'value': '<tr class="browser"><td class="browsedline"><observed id="[–⏑–––⏑–––⏑–]δ̣ουϲ">[–⏑–––⏑–––⏑–]δ̣ουϲ</observed> </td><td class="browsercite"></td></tr>\n'}, ...]
		
	:return:
	"""
	
	dbc = setconnection('autocommit')
	cur = dbc.cursor()
	
	workdb = re.sub('[\W_|]+', '', request.args.get('locus', ''))[:10]
	
	try: ao = authordict[workdb[:6]]
	except: ao = makeanemptyauthor('gr0000')
	
	try:
		wo = workdict[workdb]
		bokenwkref = False
	except:
		bokenwkref = True
		if ao.universalid == 'gr0000':
			wo = makeanemptywork('gr0000w000')
		else:
			wo = ao.listofworks[0]
	
	ctx = int(session['browsercontext'])
	numbersevery = 10
	
	if bokenwkref == True:
		passage = '_LN_'+str(wo.starts)
	else:
		passage = request.args.get('locus', '')[10:]

	if passage[0:4] == '_LN_':
		# you were sent here either by the hit list or a forward/back button in the passage browser
		passage = re.sub('[\D]', '', passage[4:])
	elif passage[0:4] == '_AT_':
		# you were sent here by the citation builder autofill boxes
		p = request.args.get('locus', '')[14:].split('|')
		cleanedp = []
		for level in p:
			cleanedp.append(re.sub('[\W_|]+', '',level))
		cleanedp = tuple(cleanedp[:5])
		if len(cleanedp) == wo.availablelevels:
			passage = finddblinefromlocus(wo.universalid, cleanedp, cur)
		elif p[0] == '-1': # cleanedp will strip the '-'
			passage = wo.starts
		else:
			passage = finddblinefromincompletelocus(wo.universalid, cleanedp, cur)
	elif passage[0:4] == '_PE_':
		# you came here via a perseus dictionary xref: all sorts of crazy ensues
		# a nasty kludge: should build the fixes into the db
		if 'gr0006' in workdb:
			remapper = dbquickfixes([workdb])
			workdb = remapper[workdb]
		citation = passage[4:].split(':')
		citation.reverse()
		passage = finddblinefromincompletelocus(workdb, citation, cur)

	try:
		browserdata = getandformatbrowsercontext(ao, wo, int(passage), ctx, numbersevery, cur)
	except:
		browserdata = [{'forwardsandback': [0,0]}]
		browserdata.append({'value': 'error in fetching the data to browse for '+ao.shortname+', '+wo.universalid +'<br /><br />'})
	if passage == -9999:
		browserdata = [{'forwardsandback': [0, 0]}]
		browserdata.append({'value': 'could not find a Perseus locus in the Hipparchia DB:<br />'+request.args.get('locus', '')+'<br /><br />'})
		try:
			browserdata.append({'value': 'author: '+ao.shortname})
		except:
			pass
		try:
			w = workdict[workdb]
			browserdata.append({'value': '<br />work: '+w.title})
			browserdata.append({'value': '<br /><br />Hipparchia citation structure: ' + w.citation()})
			passage = request.args.get('locus', '')[10:]
			pe = passage[4:].split(':')
			pe = ', '.join(pe)
			browserdata.append({'value': '<br />Perseus citation structure: ' + pe})
			browserdata.append({'value': '<br /><br />'})
		except:
			pass
	
	browserdata = json.dumps(browserdata)
	
	cur.close()
	del dbc
	
	return browserdata


@hipparchia.route('/observed', methods=['GET'])
def findbyform():
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
	
	word = request.args.get('word', '')
	word = re.sub('[\W_|]+', '',word)
	word = removegravity(word)
	# python seems to know how to do this with greek...
	word = word.lower()
	
	if re.search(r'[a-z]', word[0]) is not None:
		word = stripaccents(word)
		dict = 'latin'
	else:
		dict = 'greek'

	query = 'SELECT possible_dictionary_forms FROM ' + dict + '_morphology WHERE observed_form LIKE %s'
	data = (word,)
	cur.execute(query, data)

	analysis = cur.fetchone()
	possible = re.compile(r'(<possibility_(\d{1,2})>)(.*?)<xref_value>(.*?)</xref_value>(.*?)</possibility_\d{1,2}>')
	# 1 = #, 2 = word, 4 = body, 3 = xref

	returnarray = []
	entriestocheck = []
	try:
		matches = re.findall(possible, analysis[0])
		for m in matches:
			returnarray.append({'value': parsemorphologyentry(m)})
			entriestocheck.append(m[2])

		unsiftedentries = []
		for e in entriestocheck:
			# print('entry:',entry)
			# entry: χώρᾱϲ,χώρα
			e = e.split(',')
			e = e[-1]
			e = re.sub(r'#(\d{1,})',r' (\1)',e)
			unsiftedentries.append(e)
		siftedentries = tidyuplist(unsiftedentries)

		for entry in siftedentries:
			returnarray.append({'value': browserdictionarylookup(entry, dict, cur)})

	except:
		returnarray = [{'value': '[not found]'}, {'entries': '[not found]'} ]

	returnarray = [{'observed':word}] + returnarray
	
	if len(entriestocheck) > 0:
		returnarray[0]['trylookingunder'] = entriestocheck[0]
	
	returnarray = json.dumps(returnarray)

	cur.close()
	del dbc

	return returnarray


@hipparchia.route('/dictsearch', methods=['GET'])
def dictsearch():
	"""
	look up words
	return dictionary entries
	json packing
	:return:
	"""
	
	dbc = setconnection('autocommit')
	cur = dbc.cursor()
	
	seeking = re.sub(r'[!@#$|%()*\'\"]', '', request.args.get('term', ''))
	seeking = seeking.lower()
	seeking = re.sub('σ|ς', 'ϲ', seeking)
	seeking = re.sub('v', 'u', seeking)
	returnarray = []
	
	if re.search(r'[a-z]', seeking) is not None:
		dict = 'latin'
		usecolumn = 'entry_name'
	else:
		dict = 'greek'
		usecolumn = 'unaccented_entry'
	
	seeking = stripaccents(seeking)
	query = 'SELECT entry_name FROM ' + dict + '_dictionary' + ' WHERE ' + usecolumn + ' ~* %s'
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
	if len(found) > 0:
		sortedfinds = []
		finddict = {}
		for f in found:
			finddict[f[0]] = f
		keys = finddict.keys()
		keys = polytonicsort(keys)
		
		for k in keys:
			sortedfinds.append(finddict[k])
		
		for entry in sortedfinds:
			returnarray.append(
				{'value': browserdictionarylookup(entry[0], dict, cur) + '<hr style="border: 1px solid;" />'})
	else:
		returnarray.append({'value':'[nothing found]'})
	
	returnarray = json.dumps(returnarray)
	
	cur.close()
	del dbc
	
	return returnarray


@hipparchia.route('/reverselookup', methods=['GET'])
def reverselexiconsearch():
	"""
	attempt to find all of the greek/latin dictionary entries that might go with the english search term
	:return:
	"""
	
	dbc = setconnection('autocommit')
	cur = dbc.cursor()
	
	returnarray = []
	seeking = re.sub(r'[!@#$|%()*\'\"]', '', request.args.get('word', ''))
	if justlatin():
		dict = 'latin'
		translationlabel = 'hi'
	else:
		dict = 'greek'
		translationlabel = 'tr'
	
	usecolumn = 'entry_body'
	
	# first see if your term is mentioned at all
	query = 'SELECT entry_name FROM ' + dict + '_dictionary' + ' WHERE ' + usecolumn + ' LIKE %s'
	data = ('%' + seeking + '%',)
	cur.execute(query, data)
	
	matches = cur.fetchall()
	entries = []
	
	# then go back and see if it is mentioned in the summary of senses
	for match in matches:
		m = match[0]
		definition = searchdictionary(cur, dict + '_dictionary', 'entry_name', m, syntax='LIKE')
		# returns (metrical_entry, entry_body, entry_type)
		definition = definition[1]
		a, s, q = entrysummary(definition, dict, translationlabel)
		del a
		del q
		
		for sense in s:
			if re.search(r'^'+seeking,sense) is not None:
				entries.append(m)
				
	entries = list(set(entries))
	entries = polytonicsort(entries)
	
	# in which case we should retrieve and format this entry
	for entry in entries:
		returnarray.append(
			{'value': browserdictionarylookup(entry, dict, cur) + '<hr style="border: 1px solid;" />'})
	
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
		[{"spuria": "N"}]
		etc.
		
	:return:
	"""
	
	param = re.search(r'(.*?)=.*?', request.query_string.decode('utf-8'))
	param = param.group(1)
	val = request.args.get(param)
	# need to accept '-' because of the date spinner
	val = re.sub('[!@#$%^&*()\[\]=;`+\\\'\"]+', '', val)
	
	success = modifysessionvar(param, val)
	
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
		genre = re.sub('[\W_]+', '', request.args.get('genre', ''))
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

	# get three bundles to put in the table cells
	# stored in a dict with three keys: timeexclusions, selections, exclusions, numberofselections

	htmlbundles = sessionselectionsashtml(authordict, workdict)
	htmlbundles = json.dumps(htmlbundles)
	
	return htmlbundles


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
	
	newselections = json.dumps(sessionselectionsashtml(authordict, workdict))
	
	return newselections


@hipparchia.route('/clear')
def clearsession():
	"""
	clear the session
	this will reset all settings and reload the front page
	:return:
	"""
	
	session.clear()
	return redirect(url_for('frontpage'))
	



