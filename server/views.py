# -*- coding: utf-8 -*-
import json
import time
import re
from flask import render_template, redirect, request, url_for, session

from server import hipparchia
from server.dbsupport.dbfunctions import dbauthorandworkmaker, setconnection, perseusidmismatch
from server.dbsupport.citationfunctions import findvalidlevelvalues, finddblinefromlocus, finddblinefromincompletelocus
from server.lexica.lexicaformatting import parsemorphologyentry, entrysummary, dbquickfixes
from server.lexica.lexicalookups import browserdictionarylookup, searchdictionary
from server.searching.searchformatting import formattedcittationincontext, formatauthinfo, formatworkinfo, formatauthorandworkinfo
from server.searching.searchfunctions import compileauthorandworklist, phrasesearch, withinxlines, \
	withinxwords, partialwordsearch, concsearch, flagexclusions, simplesearchworkwithexclusion, searchdispatcher
from server.searching.betacodetounicode import replacegreekbetacode
from server.textsandconcordnaces.concordancemaker import buildconcordance
from server.textsandconcordnaces.textbuilder import buildfulltext
from server.sessionhelpers.sessionfunctions import modifysessionvar, modifysessionselections, parsejscookie, \
	sessionvariables, setsessionvarviadb, sessionselectionsashtml, rationalizeselections
from server.formatting_helper_functions import removegravity, stripaccents, tidyuplist, polytonicsort, sortauthorandworklists, \
	dropdupes, bcedating
from server.browsing.browserfunctions import getandformatbrowsercontext

# all you need is read-only access
# it is a terrible idea to connect with a user who can write
dbconnection = setconnection('autocommit')
cursor = dbconnection.cursor()


@hipparchia.route('/', methods=['GET', 'POST'])
def search():
	sessionvariables(cursor)
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
		authorandworklist = compileauthorandworklist(cursor)
		
		# mark works that have passage exclusions associated with them: gr0001x001 instead of gr0001w001 if you are skipping part of w001
		authorandworklist = flagexclusions(authorandworklist)
		authorandworklist = sortauthorandworklists(authorandworklist, cursor)
		
		# worklist is sorted, and you need to be able to retain that ordering even though mp execution is coming
		# so we slap on an index value
		indexedworklist = []
		index = -1
		for w in authorandworklist:
			index += 1
			indexedworklist.append((index, w))
		del authorandworklist
		
		if len(proximate) < 1 and re.search(phrasefinder, seeking) is None:
			# a simple search
			thesearch = seeking
			htmlsearch = '<span class="emph">' + seeking + '</span>'
			hits = searchdispatcher('simple', seeking, proximate, indexedworklist)
		elif re.search(phrasefinder, seeking) is not None:
			# a phrase search
			thesearch = seeking
			htmlsearch = '<span class="emph">' + seeking + '</span>'
			hits = searchdispatcher('phrase', seeking, proximate, indexedworklist)
		else:
			# proximity search
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
			hits = searchdispatcher('proximity', seeking, proximate, indexedworklist)
		
		allfound = []
		hitcount = 0
		for hit in hits:
			if hitcount < int(session['maxresults']):
				hitcount += 1
				wkid = hit[0]
				result = hit[1]
				# print('item=', hit,'\n\tid:',wkid,'\n\tresult:',result)
				if '_AT_' in wkid:
					citwithcontext = formattedcittationincontext(result, wkid[0:10], linesofcontext, seeking, cursor)
				else:
					citwithcontext = formattedcittationincontext(result, wkid, linesofcontext, seeking, cursor)
				# add the hit count to line zero which contains the metadata for the lines
				citwithcontext[0]['hitnumber'] = hitcount
				allfound.append(citwithcontext)
			else:
				pass
		
		searchtime = time.time() - starttime
		searchtime = round(searchtime, 2)
		resultcount = len(allfound)
		
		if resultcount < int(session['maxresults']):
			hitmax = 'false'
		else:
			hitmax = 'true'
		
		page = render_template('search.html', title=thesearch, found=allfound,
		                       resultcount=resultcount, scope=str(len(indexedworklist)),
		                       searchtime=str(searchtime), lookedfor=seeking, proximate=proximate,
		                       thesearch=thesearch,
		                       htmlsearch=htmlsearch, hitmax=hitmax, lang=session['corpora'],
		                       sortedby=session['sortorder'],
		                       dmin=dmin, dmax=dmax)
	
	else:
		page = render_template('search.html', title=seeking, found=[], resultcount=0, searchtime='0', scope=0,
		                       hitmax=0, lang=session['corpora'], sortedby=session['sortorder'],
		                       dmin=dmin, dmax=dmax)
	
	return page


@hipparchia.route('/concordance', methods=['GET'])
def concordance():
	"""
	build a concordance
	modes:
		0 - of this work
		1 - of words unique to this work in this author
		2 - of this author
	:return:
	"""
	starttime = time.time()
	try:
		work = re.sub('[\W]+', '', request.args.get('work', ''))
	except:
		work = ''
	
	try:
		mode = int(re.sub('[^\d]', '', request.args.get('mode', '')))
	except:
		mode = 0
	
	if mode > 2:
		mode = 0
	
	if work == '' or len(work) != 15:
		print('failed to pick a text for the concordance builder:', work, str(len(work)))
		work = 'lt0022w012_conc'
	
	author = dbauthorandworkmaker(work[0:6], cursor)
	authorname = author.shortname
	
	allworks = []
	for w in author.listofworks:
		allworks.append(w.universalid[6:10] + ' ==> ' + w.title)
		if w.universalid == work[0:10]:
			thework = w
	allworks.sort()
	
	if mode != 2:
		title = thework.title
	else:
		title = author.shortname
	ws = thework.structure
	structure = []
	for s in range(5, -1, -1):
		if s in ws:
			structure.append(ws[s])
	structure = ', '.join(structure)
	
	output = buildconcordance(work, mode, cursor)
	
	count = len(output)
	url = '/concordance?work=' + work
	
	linesevery = 10
	simpletexturl = '/simpletext?work=' + thework.universalid + '&linesevery=' + str(linesevery) + '&mode=0'
	
	buildtime = time.time() - starttime
	buildtime = round(buildtime, 2)
	
	page = render_template('concordance_maker.html', results=output, mode=mode, author=authorname, title=title,
	                       structure=structure, count=count, allworks=allworks, url=url, simpletexturl=simpletexturl,
	                       time=buildtime)
	
	return page


#
# unadorned views for quickly peeking at the data
#

@hipparchia.route('/simpletext', methods=['GET', 'POST'])
def workdump():
	try:
		work = re.sub('[\W]+', '', request.args.get('work', ''))
	except:
		work = ''
	
	try:
		linesevery = int(re.sub('[^\d]', '', request.args.get('linesevery', '')))
	except:
		linesevery = 10
	
	try:
		# hook for future possibility of PDF output
		# super slow, but maybe it can solve the problem with too much HTML spat at a browser?
		mode = int(re.sub('[^\d]', '', request.args.get('mode', '')))
	except:
		mode = 0
		
	if len(work) == 10:
		author = dbauthorandworkmaker(work[0:6], cursor)
		authorname = author.shortname
		
		for w in author.listofworks:
			if w.universalid == work:
				thework = w
				title = thework.title
		
		ws = thework.structure
		levelcount = len(ws)
		higherlevels=list(ws)
		higherlevels.remove(0)
		
		structure = []
		for s in range(5, -1, -1):
			if s in ws:
				structure.append(ws[s])
		structure = ', '.join(structure)
		
		output = buildfulltext(work, levelcount, higherlevels, linesevery, cursor)
	else:
		output = []

	try:
		page = render_template('workdumper.html',results=output, author=authorname, title=title,
		                       structure=structure)
	except:
		page = render_template('workdumper.html')
	
	return page


@hipparchia.route('/authors')
def authorlist():
	authors = loadallauthors(cursor)
	return render_template('lister.html', found=authors, numberfound=len(authors))


#
# helpers & routes you should not browse directly
#

@hipparchia.route('/clear')
def clearsession():
	# Clear the session
    session.clear()
	# Redirect the user to the main page
    return redirect(url_for('search'))


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
	
	htmlbundles = sessionselectionsashtml(cursor)
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
def dbofferauthorhints():

	# jquery sends: ImmutableMultiDict([('term', 'hero')])
	# the 'q' is from the GET: xmlhttp.open("GET", "/gethint?q="+str, true);
	# will return to the browser something like:  {"q": "ab"}
	# z = request.args.get('term')
	# print(z)
	# but we need '[' for spuria
	# strippedquery = re.sub('[\W_]+','',request.args.get('term', ''))
	strippedquery = re.sub(r'[!@#$|%()*\'\"]','',request.args.get('term', ''))
	# this returns what you typed: 'qaz', etc
	# print('len of avail',len(''.join(session['availableauthors'])))

	if session['corpora'] == 'B':
		query = 'SELECT language,cleanname,universalid from authors ORDER BY universalid ASC'
		cursor.execute(query)
	elif session['corpora'] == 'L':
		query = 'SELECT language,cleanname,universalid from authors WHERE universalid LIKE %s ORDER BY universalid ASC'
		data = ('lt%',)
		cursor.execute(query,data)
	elif session['corpora'] == 'G':
		query = 'SELECT language,cleanname,universalid from authors WHERE universalid LIKE %s ORDER BY universalid ASC'
		data = ('gr%',)
		cursor.execute(query,data)

	result = cursor.fetchall()
	authorlist = []
	for r in result:
		if r[0] == 'L':
			authorlist.append(r[1]+' ['+r[2]+']')
		else:
			authorlist.append(r[1] + ' ['+r[2]+']')

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
	# tell me the author, i'll return all the works to populate the hint box
	strippedquery = re.sub('[\W_]+', '', request.args.get('auth', ''))
	hint = []
	query = 'SELECT * FROM works WHERE universalid LIKE %s ORDER BY universalid ASC'
	# query = 'SELECT * FROM works'
	data = (strippedquery+'%',)
	cursor.execute(query, data)
	worklist = cursor.fetchall()

	for work in worklist:
		hint.append({'value':work[1]+' ('+work[0][-4:]+')'})
	if hint == []:
		hint.append({'value': 'somehow failed to find any works'})

	hint = json.dumps(hint)

	return hint


@hipparchia.route('/getgenrehint', methods=['GET'])
def genrelist():
	try:
		session['genres']
	except:
		session['genres'] = setsessionvarviadb('genres', 'authors', cursor)

	# the evil big cookie problem
	availablegenres = session['genres']

	strippedquery = re.sub('[\W_]+', '', request.args.get('term', ''))

	hint = []
	if session['corpora'] != 'L':
		if strippedquery != '':
			query = strippedquery.lower()
			qlen = len(query)
			for genre in availablegenres:
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
	try:
		session['workgenres']
	except:
		setsessionvarviadb('workgenre', 'works', cursor)

	# the evil big cookie problem
	availablegenres = session['workgenres']

	strippedquery = re.sub('[\W_]+', '', request.args.get('term', ''))

	hint = []
	if session['corpora'] != 'L':
		if strippedquery != '':
			query = strippedquery.lower()
			qlen = len(query)
			for genre in availablegenres:
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
	# auth + work + chunks of a citation
	passage = request.args.get('locus', '')[14:].split('|')
	safepassage = []
	for level in passage:
		safepassage.append(re.sub('[!@#$%^&*()=]+', '',level))
	safepassage = tuple(safepassage[:5])
	workdb = re.sub('[\W_|]+', '', request.args.get('locus', ''))[:10]
	ao = dbauthorandworkmaker(workdb[:6], cursor)
	structure = {}
	for work in ao.listofworks:
		if work.universalid == workdb:
			structure = work.structure
	lowandhigh = findvalidlevelvalues(workdb, structure, safepassage, cursor)
	# this should be a (level, label, low, high) [int, int, str, str]
	# results = [{'totallevels':lowandhigh[0]},{'level':lowandhigh[1]},{'label': lowandhigh[2]}, {'low': lowandhigh[3]}, {'high': lowandhigh[4]}, {'range': lowandhigh[5]}]
	results = [{'totallevels': lowandhigh[0]}, {'level': lowandhigh[1]}, {'label': lowandhigh[2]},
	           {'low': lowandhigh[3]}, {'high': lowandhigh[4]}, {'rng': lowandhigh[5]}]

	results = json.dumps(results)
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
def getauthinfo():
	"""
	show local info about the author one is considering in the selection box
	:return:
	"""
	
	authorid = re.sub('[\W_]+', '', request.args.get('au', ''))
	
	query = 'SELECT cleanname, universalid, genres, floruit, location, language FROM authors WHERE universalid=%s'
	data = (authorid,)
	cursor.execute(query, data)
	a = cursor.fetchone()
	
	query = 'SELECT universalid, title, workgenre, wordcount, publication_info FROM works WHERE universalid LIKE %s'
	data = (authorid+'%',)
	cursor.execute(query, data)
	w = cursor.fetchall()
	w.sort()
	
	authinfo = ''
	authinfo += formatauthinfo(a)
	
	if len(w) > 1:
		authinfo +='<br /><br /><span class="italic">work numbers:</span><br />\n'
	else:
		authinfo +='<br /><span class="italic">work:</span><br />\n'
	
	for work in w:
		authinfo += formatworkinfo(work)
		
	authinfo = json.dumps(authinfo)

	return authinfo


@hipparchia.route('/getsearchlistcontents')
def getsearchlistcontents():
	
	authorandworklist = compileauthorandworklist(cursor)
	authorandworklist = sortauthorandworklists(authorandworklist, cursor)
	
	searchlistinfo = '<br /><h3>Proposing to search the following works:</h3>'
	memory = ['','']
	count = 0
	wordstotal = 0
	for work in authorandworklist:
		count +=1
		if work[0:6] == memory[0]:
			a = memory[1]
		else:
			query = 'SELECT shortname FROM authors WHERE universalid = %s'
			data = (work[0:6],)
			cursor.execute(query, data)
			a = cursor.fetchone()
		query = 'SELECT universalid, title, workgenre, wordcount, publication_info FROM works WHERE universalid = %s'
		data = (work,)
		cursor.execute(query, data)
		w = cursor.fetchone()
		try:
			wordstotal += w[3]
		except:
			# TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'
			pass
		searchlistinfo += '\n['+str(count)+']&nbsp;'+formatauthorandworkinfo(a[0], w)
		memory[0] = work[0:6]
		memory[1] = a
	
	if wordstotal > 0:
		searchlistinfo += '<br /><span class="emph">total words:</span> '+format(wordstotal, ',d')

	searchlistinfo = json.dumps(searchlistinfo)
	
	return searchlistinfo


@hipparchia.route('/getgenrelistcontents')
def getgenrelistcontents():
	try:
		wg = session['workgenres']
	except:
		setsessionvarviadb('workgenre', 'works', cursor)
	
	try:
		ag = session['genres']
	except:
		setavalablegenrelist(cursor)
	
	genrelists = ''
	
	genrelists += '<h3>Author Categories</h3>'
	for g in ag:
		genrelists += g + ', '
	genrelists = genrelists[:-2]
	
	genrelists += '<h3>Work Categories</h3>'
	for g in wg:
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
	
	workdb = re.sub('[\W_|]+', '', request.args.get('locus', ''))[:10]
	ao = dbauthorandworkmaker(workdb[:6], cursor)
	workid = workdb[7:]
	
	ctx = int(session['browsercontext'])
	numbersevery = 5
	passage = request.args.get('locus', '')[10:]

	if passage[0:4] == '_LN_':
		# you were sent here either by the hit list or a forward/back button in the passage browser
		passage = re.sub('[\D]', '', passage[4:])
	elif passage[0:4] == '_AT_':
		# you were sent here by the citation builder autofill boxes
		passage = request.args.get('locus', '')[14:].split('|')
		safepassage = []
		for level in passage:
			safepassage.append(re.sub('[\W_|]+', '',level))
		safepassage = tuple(safepassage[:5])
		passage = finddblinefromlocus(workdb, safepassage, cursor)
	elif passage[0:4] == '_PE_':
		# a nasty kludge: should build the fixes into the db
		if 'gr0006' in workdb:
			remapper = dbquickfixes([workdb])
			workdb = remapper[workdb]
			workid = workdb[7:]
		citation = passage[4:].split(':')
		citation.reverse()
		passage = finddblinefromincompletelocus(workdb, citation, cursor)

	# first line is info; remaining lines are html
	try:
		browserdata = getandformatbrowsercontext(ao, int(workid), int(passage), ctx, numbersevery, cursor)
	except:
		# perseus lexical data had a bad author number?
		workdb = perseusidmismatch(workdb, cursor)
		workid = workdb[7:]
		browserdata = getandformatbrowsercontext(ao, int(workid), int(passage), ctx, numbersevery, cursor)
	if passage == -9999:
		browserdata.append('could not find a Perseus reference in the Hipparchia DB: '+request.args.get('locus', ''))

	
	browserdata = json.dumps(browserdata)
	
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
	cursor.execute(query, data)

	analysis = cursor.fetchone()
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
			returnarray.append({'value': browserdictionarylookup(entry, dict, cursor)})

	except:
		returnarray = [{'value': '[not found]'}, {'entries': '[not found]'} ]

	returnarray = [{'observed':word}] + returnarray
	
	if len(entriestocheck) > 0:
		returnarray[0]['trylookingunder'] = entriestocheck[0]
	
	returnarray = json.dumps(returnarray)

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

	newselections = json.dumps(sessionselectionsashtml(cursor))
	
	return newselections


@hipparchia.route('/dictsearch', methods=['GET'])
def dictsearch():
	"""
	basic, functionsl place to look up greek dictionary entries
	needs to be merged with the main project page, though
	:return:
	"""
	seeking = re.sub(r'[!@#$|%()*\'\"]', '', request.args.get('term', ''))
	seeking = seeking.lower()
	seeking = re.sub('σ|ς', 'ϲ', seeking)
	seeking = re.sub('v', 'u', seeking)
	returnarray = []
	
	if re.search(r'[a-z]', seeking[0]) is not None:
		dict = 'latin'
		usecolumn = 'entry_name'
	else:
		dict = 'greek'
		usecolumn = 'unaccented_entry'
	
	seeking = stripaccents(seeking)
	query = 'SELECT entry_name FROM ' + dict + '_dictionary' + ' WHERE ' + usecolumn + ' ~* %s'
	if seeking[0] == ' ' and seeking[-1] != ' ':
		data = ('^' + seeking[1:] + '.*?',)
	elif seeking[0] == ' ' and seeking[-1] == ' ':
		data = ('^' + seeking[1:-1] + '$',)
	else:
		data = ('.*?' + seeking + '.*?',)
	cursor.execute(query, data)
	
	# note that the dictionary db has a problem with vowel lengths vs accents
	# SELECT * FROM greek_dictionary WHERE entry_name LIKE %s d ('μνᾱ/αϲθαι,μνάομαι',)
	found = cursor.fetchall()
	
	# the results should be given the polytonicsort() treatment
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
			{'value': browserdictionarylookup(entry[0], dict, cursor) + '<hr style="border: 1px solid;" />'})
	
	returnarray = json.dumps(returnarray)
	
	return returnarray


@hipparchia.route('/reverselookup', methods=['GET'])
def reverselexiconsearch():
	"""
	attempt to find all of the greek/latin dictionary entries that might go with the english search term
	:return:
	"""
	
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
	cursor.execute(query, data)
	
	matches = cursor.fetchall()
	entries = []
	
	# then go back and see if it is mentioned in the summary of senses
	for match in matches:
		m = match[0]
		definition = searchdictionary(cursor, dict + '_dictionary', 'entry_name', m, syntax='LIKE')
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
			{'value': browserdictionarylookup(entry, dict, cursor) + '<hr style="border: 1px solid;" />'})
	
	returnarray = json.dumps(returnarray)
	
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

	modifysessionselections(cookiedict, cursor)
	
	response = redirect(url_for('search'))
	return response


#
# testing
#


#
# slated for removal
#

@hipparchia.route('/singlethreadedsearch', methods=['GET', 'POST'])
def singlethreadedsearch():
	# about 1/3rd to 1/4 the speed of the multiprocessor version 
	sessionvariables(cursor)
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
	
	linesofcontext = int(session['linesofcontext'])
	searchtime = 0
	
	dmax = session['latestdate']
	dmin = session['earliestdate']
	if dmax[0] == '-':
		dmax = dmax[1:] + ' B.C.E.'
	else:
		dmax = dmax + ' C.E.'
	
	if dmin[0] == '-':
		dmin = dmin[1:] + ' B.C.E.'
	else:
		dmin = dmin + 'C.E.'
	
	if len(seeking) > 0:
		if session['corpora'] == 'G' and re.search('[a-zA-Z]', seeking) is not None:
			seeking = seeking.upper()
			seeking = replacegreekbetacode(seeking)
		starttime = time.time()
		authorandworklist = compileauthorandworklist(cursor)
		# mark works that have passage exclusions associated with them: gr0001x001 instead of gr0001w001 if you are skipping part of w001
		
		authorandworklist = flagexclusions(authorandworklist)
		authorandworklist = sortauthorandworklists(authorandworklist, cursor)
		
		allfound = []
		
		if len(proximate) < 1:
			# a simple search
			# but somebody still might try to execute a phrase search: ' non solum ' inside the simple search box
			hitcount = 0
			starttime = time.time()
			thesearch = seeking
			htmlsearch = '<span class="emph">' + seeking + '</span>'
			
			phrasefinder = re.compile('[^\s]\s[^\s]')
			for wkid in authorandworklist:
				if len(allfound) < int(session['maxresults']):
					if re.search(phrasefinder, seeking) is None:
						if '_AT_' in wkid:
							results = partialwordsearch(seeking, cursor, wkid)
						elif 'x' in wkid:
							wkid = re.sub('x', 'w', wkid)
							results = simplesearchworkwithexclusion(seeking, cursor, wkid)
						else:
							results = concsearch(seeking, cursor, wkid)
					else:
						tmp = session['maxresults']
						session['maxresults'] = 19999
						results = phrasesearch(seeking, cursor, wkid)
						session['maxresults'] = tmp
					for result in results:
						if len(allfound) < int(session['maxresults']):
							hitcount += 1
							if '_AT_' in wkid:
								citwithcontext = formattedcittationincontext(result, wkid[0:10], linesofcontext,
								                                             seeking, cursor)
							else:
								citwithcontext = formattedcittationincontext(result, wkid, linesofcontext, seeking,
								                                             cursor)
							# add the hit count to line zero which contains the metadata for the lines
							citwithcontext[0]['hitnumber'] = hitcount
							allfound.append(citwithcontext)
						else:
							pass
		else:
			# proximity search
			if session['corpora'] == 'G' and re.search('[a-zA-Z]', proximate) is not None:
				# searching greek, but not typing in unicode greek: autoconvert
				proximate = proximate.upper()
				proximate = replacegreekbetacode(proximate)
			
			hitcount = 0
			starttime = time.time()
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
			
			if len(proximate) > len(seeking) and session[
				'nearornot'] != 'F' and ' ' not in seeking and ' ' not in proximate:
				# look for the longest word first since that is probably the quicker route
				# but you cant swap seeking and proximate this way in a 'is not near' search without yielding the wrong focus
				tmp = proximate
				proximate = seeking
				seeking = tmp
			
			for wkid in authorandworklist:
				if len(allfound) < int(session['maxresults']):
					# unflagged: there are no exclusions to apply to this specific work
					if session['searchscope'] == 'L':
						results = withinxlines(int(session['proximity']), seeking, proximate, cursor, wkid)
					else:
						results = withinxwords(int(session['proximity']), seeking, proximate, cursor, wkid)
					for result in results:
						if len(allfound) < int(session['maxresults']):
							hitcount += 1
							citwithcontext = formattedcittationincontext(result, wkid, linesofcontext, seeking, cursor)
							# add the hit count to line zero which contains the metadata for the lines
							citwithcontext[0]['hitnumber'] = hitcount
							allfound.append(citwithcontext)
						else:
							pass
		
		searchtime = time.time() - starttime
		searchtime = round(searchtime, 2)
		resultcount = len(allfound)
		
		if resultcount < int(session['maxresults']):
			hitmax = 'false'
		else:
			hitmax = 'true'
		
		page = render_template('search.html', title=thesearch, found=allfound,
		                       resultcount=resultcount, scope=str(len(authorandworklist)),
		                       searchtime=str(searchtime), lookedfor=seeking, proximate=proximate,
		                       thesearch=thesearch,
		                       htmlsearch=htmlsearch, hitmax=hitmax, lang=session['corpora'],
		                       sortedby=session['sortorder'],
		                       dmin=dmin, dmax=dmax)
	
	else:
		page = render_template('search.html', title=seeking, found=[], resultcount=0, searchtime='0', scope=0,
		                       hitmax=0, lang=session['corpora'], sortedby=session['sortorder'],
		                       dmin=dmin, dmax=dmax)
	
	return page

