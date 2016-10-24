# -*- coding: utf-8 -*-
import json
import time
import re
from flask import render_template, redirect, request, url_for, session

from server import hipparchia
from server import pollingdata
from server.dbsupport.dbfunctions import setconnection, makeanemptyauthor, makeanemptywork
from server.dbsupport.citationfunctions import findvalidlevelvalues, finddblinefromlocus, finddblinefromincompletelocus
from server.lexica.lexicaformatting import parsemorphologyentry, entrysummary, dbquickfixes
from server.lexica.lexicalookups import browserdictionarylookup, searchdictionary
from server.searching.searchformatting import formattedcittationincontext, aoformatauthinfo, formatauthorandworkinfo, \
	woformatworkinfo
from server.searching.searchfunctions import flagexclusions, searchdispatcher, compileauthorandworklist, dispatchshortphrasesearch
from server.searching.betacodetounicode import replacegreekbetacode
from server.textsandconcordnaces.concordancemaker import buildconcordancefromwork
from server.textsandconcordnaces.textandconcordancehelperfunctions import tcparserequest, tcfindstartandstop, conctohtmltable, \
	concordancesorter
from server.textsandconcordnaces.textbuilder import buildtext
from server.sessionhelpers.sessionfunctions import modifysessionvar, modifysessionselections, parsejscookie, \
	sessionvariables, sessionselectionsashtml, rationalizeselections, buildauthordict, buildworkdict, \
	buildaugenreslist, buildworkgenreslist
from server.formatting_helper_functions import removegravity, stripaccents, tidyuplist, polytonicsort, \
	dropdupes, bcedating, aosortauthorandworklists, prunedict, htmlifysearchfinds
from server.browsing.browserfunctions import getandformatbrowsercontext

# all you need is read-only access
# it is a terrible idea to connect with a user who can write
# autocommit will save your bacon if there is a problem looking something up: subseqent requests will get blocked
dbconnection = setconnection('autocommit')
cursor = dbconnection.cursor()

# ready some sets of objects that will be generally available: two seconds spent here will save you 2s over and over again later as you constantly regenerate author and work info

authordict = buildauthordict(cursor)
workdict = buildworkdict(authordict)
authorgenreslist = buildaugenreslist(authordict)
workgenreslist = buildworkgenreslist(workdict)

pollingdata.initializeglobals()


@hipparchia.route('/', methods=['GET', 'POST'])
def frontpate():
	"""
	the front page
	it used to do stuff
	now it just loads the JS which then calls all of the routes below
	
	:return:
	"""
	sessionvariables()
	
	seeking = ''
	proximate = ''

	dmin, dmax = bcedating()
	
	page = render_template('search.html', title=seeking, found=[], resultcount=0, searchtime='0', scope=0,
		                       hitmax=0, lang=session['corpora'], sortedby=session['sortorder'],
		                       dmin=dmin, dmax=dmax)
	
	return page


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
	starttime = time.time()
	pollingdata.pdactive = True
	
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
			startline = wo.starts
			endline = wo.ends
		else:
			# partial work
			startandstop = tcfindstartandstop(ao, wo, psg, cur)
			startline = startandstop['startline']
			endline = startandstop['endline']

		cdict = {wo.universalid: (startline, endline)}
		unsortedoutput = buildconcordancefromwork(cdict, cur)
		allworks = []
		
	elif ao.universalid != 'gr0000' and wo.universalid == 'gr0000w000':
		# whole author
		cdict = {}
		for wkid in ao.listworkids():
			cdict[wkid] = (workdict[wkid].starts, workdict[wkid].ends)
		unsortedoutput = buildconcordancefromwork(cdict, cur)
			
		allworks = []
		for w in ao.listofworks:
			allworks.append(w.universalid[6:10] + ' ==> ' + w.title)
		allworks.sort()
		
	else:
		# we do not have a valid selection
		unsortedoutput = []
		allworks = []
	
	# get ready to send stuff to the page
	pollingdata.pdstatusmessage = 'Preparing the concordance HTML'
	output = concordancesorter(unsortedoutput)
	count = len(output)
	output = conctohtmltable(output)
	
	buildtime = time.time() - starttime
	buildtime = round(buildtime, 2)
	pollingdata.pdactive = False
	
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
	
	return results


@hipparchia.route('/text', methods=['GET'])
def textmaker():
	"""
	build a text
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
#
# unadorned views for quickly peeking at the data
#


@hipparchia.route('/authors')
def authorlist():

	authors = []
	
	keys = list(authordict.keys())
	keys.sort()
	for k in keys:
		authors.append(authordict[k])
	return render_template('lister.html', found=authors, numberfound=len(authors))

#
# helpers & routes you should not browse directly
#

@hipparchia.route('/clear')
def clearsession():
	# Clear the session
    session.clear()
	# Redirect the user to the main page
    return redirect(url_for('frontpate'))


@hipparchia.route('/makeselection', methods=['GET'])
def selectionmade():
	"""
	once a choice is made, parse and register it inside session['selections']
	then return the human readable version of the same for display on the page

	this is also called without arguments to return the searchlist contents by
	skipping ahead to sessionselectionsashtml()
	
	sample input: '/makeselection?auth=gr0008&work=001&locus=3|4|23'

	:return:
	"""
	
	try:
		genre = re.sub('[\W_]+', '', request.args.get('genre', ''))
	except:
		genre = ''

	try:
		# need periods (for now): just remove some obvious problem cases
		wkgenre = re.sub('[\[\]\'\\&\*\%\^_]+', '', request.args.get('wkgenre', ''))
	except:
		wkgenre = ''

	try:
		workid = re.sub('[\W_]+', '', request.args.get('work', ''))
	except:
		workid = ''

	try:
		uid = re.sub('[\W_]+', '', request.args.get('auth', ''))
	except:
		uid = ''

	try:
		locus = re.sub('[!@#$%^&*()=]+', '', request.args.get('locus', ''))
	except:
		locus = ''
		
	try:
		exclude = re.sub('[^tf]', '', request.args.get('exclude', ''))
	except:
		exclude = ''

	
	if exclude != 't':
		suffix = 'selections'
		other = 'exclusions'
	else:
		suffix = 'exclusions'
		other = 'selections'
					
	if (uid != '') and (workid != '') and (locus != ''):
		# a specific passage
		session['psg'+suffix].append(uid+'w'+workid+'_AT_'+locus)
		session['psg'+suffix] = tidyuplist(session['psg'+suffix])
		rationalizeselections(uid+'w'+workid+'_AT_'+locus, suffix)
	elif (uid != '') and (workid != ''):
		# a specific work
		session['wk'+suffix].append(uid+'w'+workid)
		session['wk'+suffix] = tidyuplist(session['wk'+suffix])
		rationalizeselections(uid+'w'+workid, suffix)
	elif (uid != '') and (workid == ''):
		# a specific author
		session['au'+suffix].append(uid)
		session['au'+suffix] = tidyuplist(session['au'+suffix])
		rationalizeselections(uid, suffix)
	elif genre != '':
		# add to the +/- genre list and then subtract from the -/+ list
		session['agn'+suffix].append(genre)
		session['agn'+suffix] = tidyuplist(session['agn'+suffix])
		session['agn'+other] = dropdupes(session['agn' + other], session['agn' + suffix])
	elif wkgenre != '':
		# add to the +/- genre list and then subtract from the -/+ list
		session['wkgn'+suffix].append(wkgenre)
		session['wkgn'+suffix] = tidyuplist(session['wkgn'+suffix])
		session['wkgn' + other] = dropdupes(session['wkgn' + other], session['wkgn' + suffix])
	
	# get three bundles to put in the table cells
	# stored in a dict with three keys: timeexclusions, selections, exclusions, numberofselections
	
	htmlbundles = sessionselectionsashtml(authordict, workdict)
	htmlbundles = json.dumps(htmlbundles)
	
	return htmlbundles


@hipparchia.route('/setsessionvariable', methods=['GET'])
def setsessionvariable():
	param = re.search(r'(.*?)=.*?', request.query_string.decode('utf-8'))
	param = param.group(1)
	val = request.args.get(param)
	# need to accept '-' because of the date spinner
	val = re.sub('[!@#$%^&*()\[\]=;`+\\\'\"]+', '', val)
	
	success = modifysessionvar(param, val)
	
	result = json.dumps([{param: val}])
	
	return result


@hipparchia.route('/getauthorhint', methods=['GET'])
def aoofferauthorhints():
	"""
	fill the hint box with constantly updated values
	:return:
	"""
	global authordict

	strippedquery = re.sub(r'[!@#$|%()*\'\"]','',request.args.get('term', ''))

	if session['corpora'] == 'G':
		ad = prunedict(authordict, 'universalid', 'gr')
	elif session['corpora'] == 'L':
		ad = prunedict(authordict, 'universalid', 'lt')
	else:
		ad = authordict

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
def woofferworkhints():
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
def aogenrelist():

	strippedquery = re.sub('[\W_]+', '', request.args.get('term', ''))

	hint = []
	if session['corpora'] != 'L':
		if strippedquery != '':
			query = strippedquery.lower()
			qlen = len(query)
			for genre in authorgenreslist:
				hintgenre = genre.lower()
				if query == hintgenre[0:qlen]:
					# jquery will gobble up label and value
					# another tag can be used for holding other info
					# pass that to 'ui.item.OTHERTAG' to be evaluated
					hint.append({'value': genre})
	else:
		hint = ['(genre unsupported on the Latin data)']

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getworkgenrehint', methods=['GET'])
def wkgenrelist():
	# this needs a lot of refactoring: genres should be removed from the session and put into a global
	# the evil big cookie problem

	strippedquery = re.sub('[\W_]+', '', request.args.get('term', ''))

	hint = []
	if session['corpora'] != 'L':
		if strippedquery != '':
			query = strippedquery.lower()
			qlen = len(query)
			for genre in workgenreslist:
				hintgenre = genre.lower()
				if query == hintgenre[0:qlen]:
					# jquery will gobble up label and value
					# another tag can be used for holding other info
					# pass that to 'ui.item.OTHERTAG' to be evaluated
					hint.append({'value': genre})
	else:
		hint = ['(genre unsupported on the Latin data)']

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
	workdb = re.sub('[\W_|]+', '', request.args.get('locus', ''))[:10]
	# ao = dbauthorandworkmaker(workdb[:6], cursor)
	ao = authordict[workdb[:6]]
	structure = {}
	for work in ao.listofworks:
		if work.universalid == workdb:
			structure = work.structure
	lowandhigh = findvalidlevelvalues(workdb, structure, safepassage, cur)
	results = [{'totallevels': lowandhigh[0]}, {'level': lowandhigh[1]}, {'label': lowandhigh[2]},
	           {'low': lowandhigh[3]}, {'high': lowandhigh[4]}, {'rng': lowandhigh[5]}]

	results = json.dumps(results)
	
	cur.close()
	del dbc
	
	return results


@hipparchia.route('/getsessionvariables')
def getsessionvariables():
	returndict = {}
	for k in session.keys():
		if k != 'genres' and k != 'workgenres' and k != 'csrf_token':
			# print(k, session[k])
			returndict[k] = session[k]
	returndict = json.dumps(returndict)
	
	return returndict


@hipparchia.route('/getauthorinfo', methods=['GET'])
def aogetauthinfo():
	"""
	show local info about the author one is considering in the selection box
	:return:
	"""
	dbc = setconnection('autocommit')
	cur = dbc.cursor()
	
	authorid = re.sub('[\W_]+', '', request.args.get('au', ''))
	
	theauthor = authordict[authorid]
	
	authinfo = ''
	authinfo += aoformatauthinfo(theauthor)
	
	if len(theauthor.listofworks) > 1:
		authinfo +='<br /><br /><span class="italic">work numbers:</span><br />\n'
	else:
		authinfo +='<br /><span class="italic">work:</span><br />\n'
	
	for work in theauthor.listofworks:
		authinfo += woformatworkinfo(work)
		
	authinfo = json.dumps(authinfo)
	
	cur.close()
	del dbc
	
	return authinfo


@hipparchia.route('/getsearchlistcontents')
def aogetsearchlistcontents():

	authorandworklist = compileauthorandworklist(authordict, workdict)
	authorandworklist = aosortauthorandworklists(authorandworklist, authordict)
	
	searchlistinfo = '<br /><h3>Proposing to search the following works:</h3>\n'
	searchlistinfo += '(Results will be arranged according to '+session['sortorder']+')<br /><br />\n'
	
	count = 0
	wordstotal = 0
	for work in authorandworklist:
		count += 1
		w = workdict[work]
		a = authordict[work[0:6]].shortname
		
		try:
			wordstotal += workdict[work].wordcount
		except:
			# TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'
			pass
		searchlistinfo += '\n[' + str(count) + ']&nbsp;' + formatauthorandworkinfo(a, w)
	
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

	genrelists = ''
	
	genrelists += '<h3>Author Categories</h3>'
	for g in authorgenreslist:
		genrelists += g + ', '
	genrelists = genrelists[:-2]
	
	genrelists += '<h3>Work Categories</h3>'
	for g in workgenreslist:
		genrelists += g + ', '
	genrelists = genrelists[:-2]
	
	genrelists = json.dumps(genrelists)
	
	return genrelists


@hipparchia.route('/browseto', methods=['GET'])
def grabtextforbrowsing():
	"""
	you want to browse something
	there are two standard ways to get results here: tell me a line or tell me a citation
		sample input: '/browseto?locus=gr0059w030_LN_48203'
		sample input: '/browseto?locus=gr0008w001_AT_23|3|3'
	alternately you can sent me a perseus ref from a dictionary entry ('_PE_') and I will *try* to convert it into a '_LN_'
	
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

	# first line is info; remaining lines are html

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


@hipparchia.route('/clearselections', methods=['GET'])
def clearselections():
	"""
	a selection gets thrown into the trash
	:return:
	"""
	category = request.args.get('cat', '')
	selectiontypes = ['auselections', 'wkselections', 'psgselections', 'agnselections', 'wkgnselections',
	                  'auexclusions', 'wkexclusions', 'psgexclusions', 'agnexclusions', 'wkgnexclusions']
	if category not in selectiontypes:
		category = ''
	
	item = request.args.get('id', '')
	item = int(item)
	
	try:
		session[category].pop(item)
	except:
		print('failed to pop',category,str(item))
		pass
	
	session.modified = True

	newselections = json.dumps(sessionselectionsashtml(authordict, workdict))
	
	return newselections


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
	if session['corpora'] == 'L':
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
	

@hipparchia.route('/getcookie', methods=['GET'])
def cookieintosession():

	cookienum = request.args.get('cookie', '')
	cookienum = cookienum[0:2]
	
	thecookie = request.cookies.get('session'+cookienum)
	# comes back as a string that needs parsing
	cookiedict = parsejscookie(thecookie)
	# session.clear()
	for key,value in cookiedict.items():
		modifysessionvar(key,value)

	modifysessionselections(cookiedict, authorgenreslist, workgenreslist)
	
	response = redirect(url_for('search'))
	return response


@hipparchia.route('/progress', methods=['GET'])
def progressreport():
	"""
	allow js to poll the progress of a long operation
	this code is itself in progress and will remain so until the passing of globals between funcitons gets sorted
	:return:
	"""

	try:
		searchid = int(request.args.get('id', ''))
	except:
		searchid = -1
	
	if pollingdata.pdactive == False:
		time.sleep(.3)
	
	progress = {}
	progress['total'] = pollingdata.pdpoolofwork.value
	progress['remaining'] = pollingdata.pdremaining.value
	progress['hits'] = pollingdata.pdhits.value
	progress['message'] = pollingdata.pdstatusmessage
	progress['active'] = pollingdata.pdactive
	
	progress = json.dumps(progress)
	
	return progress


@hipparchia.route('/executesearch', methods=['GET'])
def jsexecutesearch():
	dbc = setconnection('autocommit')
	cur = dbc.cursor()
		
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
	
	if len(seeking) < 1 and len(proximate) > 0:
		seeking = proximate
		proximate = ''
	
	pollingdata.pdactive = True
	pollingdata.pdremaining.value = -1
	pollingdata.pdpoolofwork.value = -1
	
	linesofcontext = int(session['linesofcontext'])
	searchtime = 0
	
	dmin, dmax = bcedating()
	
	if session['corpora'] == 'G' and re.search('[a-zA-Z]', seeking) is not None:
		# searching greek, but not typing in unicode greek: autoconvert
		seeking = seeking.upper()
		seeking = replacegreekbetacode(seeking)
	
	if session['corpora'] == 'G' and re.search('[a-zA-Z]', proximate) is not None:
		proximate = proximate.upper()
		proximate = replacegreekbetacode(proximate)
	
	phrasefinder = re.compile('[^\s]\s[^\s]')
	
	if len(seeking) > 0:
		starttime = time.time()
		pollingdata.pdstatusmessage = 'Compiling the list of works to search'
		
		authorandworklist = compileauthorandworklist(authordict, workdict)
		# mark works that have passage exclusions associated with them: gr0001x001 instead of gr0001w001 if you are skipping part of w001
		authorandworklist = flagexclusions(authorandworklist)
		authorandworklist = aosortauthorandworklists(authorandworklist, authordict)
		
		# worklist is sorted, and you need to be able to retain that ordering even though mp execution is coming
		# so we slap on an index value
		indexedworklist = []
		index = -1
		for w in authorandworklist:
			index += 1
			indexedworklist.append((index, w))
		del authorandworklist
		
		if len(proximate) < 1 and re.search(phrasefinder, seeking) is None:
			searchtype = 'simple'
			thesearch = seeking
			htmlsearch = '<span class="emph">' + seeking + '</span>'
			hits = searchdispatcher('simple', seeking, proximate, indexedworklist, authordict)
		elif re.search(phrasefinder, seeking) is not None:
			searchtype = 'phrase'
			thesearch = seeking
			htmlsearch = '<span class="emph">' + seeking + '</span>'
			terms = seeking.split(' ')
			if len(max(terms, key=len)) > 3:
				hits = searchdispatcher('phrase', seeking, proximate, indexedworklist, authordict)
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
				hits = dispatchshortphrasesearch(seeking, indexedworklist)
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
			hits = searchdispatcher('proximity', seeking, proximate, indexedworklist, authordict)
		
		pollingdata.pdstatusmessage = 'Formatting the results'
		pollingdata.pdpoolofwork.value = -1
		
		allfound = []
		hitcount = 0
		
		for lineobject in hits:
			if hitcount < int(session['maxresults']):
				hitcount += 1
				# print('item=', hit,'\n\tid:',wkid,'\n\tresult:',result)
				authorobject = authordict[lineobject.wkuinversalid[0:6]]
				workobject = workdict[lineobject.wkuinversalid]
				citwithcontext = formattedcittationincontext(lineobject, workobject, authorobject, linesofcontext,
				                                             seeking, proximate, searchtype, cur)
				# add the hit count to line zero which contains the metadata for the lines
				citwithcontext[0]['hitnumber'] = hitcount
				allfound.append(citwithcontext)
			else:
				pass
		
		searchtime = time.time() - starttime
		searchtime = round(searchtime, 2)
		if len(allfound) > int(session['maxresults']):
			allfound = allfound[0:int(session['maxresults'])]
		
		htmlandjs = htmlifysearchfinds(allfound)
		finds = htmlandjs['hits']
		findsjs = htmlandjs['hitsjs']
		
		resultcount = len(allfound)
		
		if resultcount < int(session['maxresults']):
			hitmax = 'false'
		else:
			hitmax = 'true'
		
		# prepare the output
		
		output = {}
		output['title'] = thesearch
		output['found'] = finds
		output['js'] = findsjs
		output['resultcount'] = resultcount
		output['scope'] = str(len(indexedworklist))
		output['searchtime'] = str(searchtime)
		output['lookedfor'] = seeking
		output['proximate'] = proximate
		output['thesearch'] = thesearch
		output['htmlsearch'] = htmlsearch
		output['hitmax'] = hitmax
		output['lang'] = session['corpora']
		output['sortby'] = session['sortorder']
		output['dmin'] = dmin
		output['dmax'] = dmax
		
	else:
		output = {}
		output['title'] = seeking
		output['found'] = []
		output['resultcount'] = 0
		output['scope'] = 0
		output['searchtime'] = '0.00'
		output['lookedfor'] = seeking
		output['proximate'] = proximate
		output['thesearch'] = ''
		output['htmlsearch'] = ''
		output['hitmax'] = 0
		output['lang'] = session['corpora']
		output['sortby'] = session['sortorder']
		output['dmin'] = dmin
		output['dmax'] = dmax
				
	output = json.dumps(output)
	
	cur.close()
	del dbc
	
	pollingdata.pdhits.val.value = -1
	pollingdata.pdactive = False
	
	return output
