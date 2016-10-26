# -*- coding: utf-8 -*-

import re
from multiprocessing import Process, Manager

import psycopg2
from flask import session

from server import hipparchia
from server import pollingdata
from server.dbsupport.dbfunctions import setconnection, dblineintolineobject, makeablankline
from server.formatting_helper_functions import tidyuplist, dropdupes, prunedict, foundindict
from server.hipparchiaclasses import MPCounter
from server.searching.searchformatting import aggregatelines, cleansearchterm, prunebydate, removespuria, \
	sortandunpackresults, lookoutsideoftheline


def compileauthorandworklist(authordict, workdict):
	"""
	master author dict + session selctions into a list of dbs to search
	:param authors:
	:return:
	"""
	searchlist = session['auselections'] + session['agnselections'] + session['wkgnselections'] + session[
		'psgselections'] + session['wkselections']
	exclusionlist = session['auexclusions'] + session['wkexclusions'] + session['agnexclusions'] + session[
		'wkgnexclusions'] + session['psgexclusions']
	
	# trim by language
	if session['corpora'] == 'G':
		ad = prunedict(authordict, 'universalid', 'gr')
		wd = prunedict(workdict, 'universalid', 'gr')
	elif session['corpora'] == 'L':
		ad = prunedict(authordict, 'universalid', 'lt')
		wd = prunedict(workdict, 'universalid', 'lt')
	else:
		ad = authordict
		wd = workdict
	
	# build the inclusion list
	if len(searchlist) > 0:
		# build lists up from specific items (passages) to more general classes (works, then authors)
		
		authorandworklist = []
		for g in session['wkgnselections']:
			authorandworklist += foundindict(wd, 'workgenre', g)
		
		authorlist = []
		for g in session['agnselections']:
			authorlist = foundindict(ad, 'genres', g)
		for a in authorlist:
			for w in ad[a].listofworks:
				authorandworklist.append(w.universalid)
		del authorlist
		
		# a tricky spot: when/how to apply prunebydate()
		# if you want to be able to seek 5th BCE oratory and Plutarch, then you need to let auselections take precedence
		# accordingly we will do classes and genres first, then trim by date, then add in individual choices
		authorandworklist = prunebydate(authorandworklist, ad)
		
		# now we look at things explicitly chosen:
		# the passage checks are superfluous if rationalizeselections() got things right
		
		passages = session['psgselections']
		works = session['wkselections']
		works = tidyuplist(works)
		works = dropdupes(works, passages)
		
		for w in works:
			authorandworklist.append(w)
		
		authors = []
		for a in session['auselections']:
			authors.append(a)
		
		tocheck = works + passages
		authors = dropdupes(authors, tocheck)
		for a in authors:
			for w in ad[a].listofworks:
				authorandworklist.append(w.universalid)
		del authors
		del works
		
		if len(session['psgselections']) > 0:
			authorandworklist = dropdupes(authorandworklist, session['psgselections'])
			authorandworklist = session['psgselections'] + authorandworklist
		
		authorandworklist = list(set(authorandworklist))
		
		if session['spuria'] == 'N':
			authorandworklist = removespuria(authorandworklist, wd)
	
	else:
		# you picked nothing and want everything. well, maybe everything...
		authorandworklist = wd.keys()
		
		if session['latestdate'] != '1500' or session['earliestdate'] != '-850':
			authorandworklist = prunebydate(authorandworklist, ad)
		
		if session['spuria'] == 'N':
			authorandworklist = removespuria(authorandworklist, wd)
	
	# build the exclusion list
	# note that we are not handling excluded individual passages yet
	excludedworks = []
	
	if len(exclusionlist) > 0:
		excludedworks = []
		excludedauthors = []
		
		for g in session['agnexclusions']:
			excludedauthors += foundindict(ad, 'genres', g)
		
		for a in session['auexclusions']:
			excludedauthors.append(a)
		
		excludedauthors = tidyuplist(excludedauthors)
		
		for a in excludedauthors:
			for w in ad[a].listofworks:
				excludedworks.append(w.universalid)
		del excludedauthors
		
		for g in session['wkgnexclusions']:
			excludedworks += foundindict(wd, 'workgenre', g)
		
		excludedworks += session['wkexclusions']
		excludedworks = list(set(excludedworks))
	
	authorandworklist = list(set(authorandworklist) - set(excludedworks))
	
	del ad
	del wd
	
	return authorandworklist


def flagexclusions(authorandworklist):
	"""
	some works whould only be searched partially
	this flags those items on the authorandworklist by changing their workname format
	gr0001w001 becomes gr0001x001 if session['wkexclusions'] mentions gr0001w001
	:param authorandworklist:
	:return:
	"""
	modifiedauthorandworklist = []
	for w in authorandworklist:
		if len(session['psgexclusions']) > 0:
			for x in session['psgexclusions']:
				if '_AT_' not in w and w in x:
					w = re.sub('w', 'x', w)
					modifiedauthorandworklist.append(w)
				else:
					modifiedauthorandworklist.append(w)
		else:
			modifiedauthorandworklist.append(w)
	
	# if you apply 3 restrictions you will now have 3 copies of gr0001x001
	modifiedauthorandworklist = tidyuplist(modifiedauthorandworklist)
	
	return modifiedauthorandworklist


def whereclauses(uidwithatsign, operand, authors):
	"""
	in order to restrict a search to a portion of a work, you will need a where clause
	this builds it out of something like 'gr0003w001_AT_3|12' (Thuc., Bk 3, Ch 12)
	note the clash with concsearching: it is possible to search the whole conc and then toss the bad lines, but...

	:param uidwithatsign:
	:param operand: this should be either '=' or '!='
	:return: a tuple consisting of the SQL string and the value to be passed via %s
	"""
	
	whereclausetuples = []
	
	a = uidwithatsign[:6]
	locus = uidwithatsign[14:].split('|')
	
	ao = authors[a]
	for w in ao.listofworks:
		if w.universalid == uidwithatsign[0:10]:
			wk = w
	
	wklvls = list(wk.structure.keys())
	wklvls.reverse()
	
	index = -1
	for l in locus:
		index += 1
		lvstr = 'level_0' + str(wklvls[index]) + '_value' + operand + '%s '
		whereclausetuples.append((lvstr, l))
	
	return whereclausetuples


def concsearch(seeking, cursor, workdbname):
	"""
	search for a word by looking it up in the concordance to that work
	returns the lines from the work that contain the word
	:param seeking:
	:param cursor:
	:param workdbname:
	:return: db lines that match the search criterion
	"""
	
	concdbname = workdbname + '_conc'
	seeking = cleansearchterm(seeking)
	mylimit = 'LIMIT ' + str(session['maxresults'])
	if session['accentsmatter'] == 'Y':
		ccolumn = 'word'
	else:
		ccolumn = 'stripped_word'
	
	searchsyntax = ['=', 'LIKE', 'SIMILAR TO', '~*']
	
	# whitespace = whole word and that can be done more quickly
	if seeking[0] == ' ' and seeking[-1] == ' ':
		seeking = seeking[1:-1]
		mysyntax = searchsyntax[0]
	else:
		if seeking[0] == ' ':
			seeking = '^' + seeking[1:]
		if seeking[-1] == ' ':
			seeking = seeking[0:-1] + '$'
		mysyntax = searchsyntax[3]
	
	found = []
	
	query = 'SELECT loci FROM ' + concdbname + ' WHERE ' + ccolumn + ' ' + mysyntax + ' %s ' + mylimit
	data = (seeking,)
	
	try:
		cursor.execute(query, data)
		found = cursor.fetchall()
	except psycopg2.DatabaseError as e:
		print('could not execute', query)
		print('Error:', e)
	
	hits = []
	for find in found:
		hits += find[0].split(' ')
	
	concfinds = []
	for hit in hits:
		query = 'SELECT * FROM ' + workdbname + ' WHERE index = %s'
		data = (hit,)
		try:
			cursor.execute(query, data)
			found = cursor.fetchone()
			concfinds.append(found)
		except psycopg2.DatabaseError as e:
			print('could not execute', query)
			print('Error:', e)
	
	return concfinds


def partialwordsearch(seeking, cursor, workdbname, authors):
	"""
	actually one of the most basic search types: look for a string/substring
	this is brute force: you wade through the full text of the work
	:param seeking:
	:param cursor:
	:param workdbname:
	:param authors:
	:return:
	"""
	
	mylimit = 'LIMIT ' + str(session['maxresults'])
	if session['accentsmatter'] == 'Y':
		columna = 'marked_up_line'
	else:
		columna = 'stripped_line'
	columnb = 'hyphenated_words'
	
	seeking = cleansearchterm(seeking)
	hyphsearch = seeking
	
	mysyntax = '~*'
	if seeking[0] == ' ':
		# otherwise you will miss words that start lines because they do not have a leading whitespace
		seeking = r'(^|\s)' + seeking[1:]
	elif seeking[0:1] == '\s':
		seeking = r'(^|\s)' + seeking[2:]
	
	found = []
	
	if '_AT_' not in workdbname:
		query = 'SELECT * FROM ' + workdbname + ' WHERE (' + columna + ' ' + mysyntax + ' %s) OR (' + columnb + ' ' + mysyntax + ' %s) ' + mylimit
		data = (seeking, hyphsearch)
	else:
		qw = ''
		db = workdbname[0:10]
		d = [seeking, hyphsearch]
		w = whereclauses(workdbname, '=', authors)
		for i in range(0, len(w)):
			qw += 'AND (' + w[i][0] + ') '
			d.append(w[i][1])
		
		query = 'SELECT * FROM ' + db + ' WHERE (' + columna + ' ' + mysyntax + ' %s OR ' + columnb + ' ' + mysyntax + ' %s) ' + qw + ' ORDER BY index ASC '+ mylimit
		data = tuple(d)
	
	try:
		cursor.execute(query, data)
		found = cursor.fetchall()
	except:
		print('could not execute', query, data)
	
	return found


def searchdispatcher(searchtype, seeking, proximate, indexedauthorandworklist, authordict):
	"""
	assign the search to multiprocessing workers
	:param seeking:
	:param indexedauthorandworklist:
	:return:
	"""
	
	pollingdata.pdpoolofwork.value = len(indexedauthorandworklist)
	pollingdata.pdremaining.value = len(indexedauthorandworklist)
	pollingdata.pdhits.val.value = 0
	
	count = MPCounter()
	manager = Manager()
	hits = manager.dict()
	authors = manager.dict(authordict)
	searching = manager.list(indexedauthorandworklist)
	
	# if you don't autocommit you will soon see: "Error: current transaction is aborted, commands ignored until end of transaction block"
	# alternately you can commit every N transactions
	commitcount = MPCounter()
	
	workers = hipparchia.config['WORKERS']
	
	# a class and/or decorator would be nice, but you have a lot of trouble getting the (mp aware) args into the function
	# the must be a way, but this also works
	if searchtype == 'simple':
		pollingdata.pdstatusmessage = 'Executing a simple word search...'
		jobs = [Process(target=workonsimplesearch, args=(count, hits, seeking, searching, commitcount, authors)) for i in range(workers)]
	elif searchtype == 'phrase':
		pollingdata.pdstatusmessage = 'Executing a phrase search. Checking longest term first...'
		jobs = [Process(target=workonphrasesearch, args=(hits, seeking, searching, commitcount, authors)) for i in range(workers)]
	elif searchtype == 'proximity':
		pollingdata.pdstatusmessage = 'Executing a proximity search...'
		jobs = [Process(target=workonproximitysearch, args=(count, hits, seeking, proximate, searching, commitcount, authors)) for i in range(workers)]
	else:
		# impossible, but...
		jobs = []
		
	for j in jobs: j.start()
	for j in jobs: j.join()
	
	# what comes back is a dict: {sortedawindex: (wkid, [(result1), (result2), ...])}
	# you need to sort by index and then unpack the results into a list
	# this will restore the old order from sortauthorandworklists()
	hits = sortandunpackresults(hits)
	lineobjects = []
	for h in hits:
		# hit= ('gr0199w012', (842, '-1', '-1', '-1', '-1', '5', '41', 'Πυθῶνί τ’ ἐν ἀγαθέᾳ· ', 'πυθωνι τ εν αγαθεα ', '', ''))
		lineobjects.append(dblineintolineobject(h[0],h[1]))
	
	return lineobjects


def workonsimplesearch(count, hits, seeking, searching, commitcount, authors):
	"""
	a multiprocessors aware function that hands off bits of a simple search to multiple searchers
	you need to pick the right style of search for each work you search, though
	:param count:
	:param hits:
	:param seeking:
	:param searching:
	:return: a collection of hits
	"""
	
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()
	
	while len(searching) > 0 and count.value <= int(session['maxresults']):
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		try:
			i = searching.pop()
			pollingdata.pdremaining.value = len(searching)
		except: i = (-1,'gr0000w000')
		commitcount.increment()
		if commitcount.value % 750 == 0:
			dbconnection.commit()
		wkid = i[1]
		index = i[0]
		if index != -1:
			if '_AT_' in wkid:
				hits[index] = (wkid, partialwordsearch(seeking, curs, wkid, authors))
			elif 'x' in wkid:
				wkid = re.sub('x', 'w', wkid)
				hits[index] = (wkid, simplesearchworkwithexclusion(seeking, wkid, authors, curs))
			else:
				hits[index] = (wkid, concsearch(seeking, curs, wkid))
			
			if len(hits[index][1]) == 0:
				del hits[index]
			else:
				count.increment(len(hits[index][1]))
				pollingdata.pdhits.increment(len(hits[index][1]))
				
	dbconnection.commit()
	curs.close()
	del dbconnection
	
	return hits


def workonphrasesearch(hits, seeking, searching, commitcount, authors):
	"""
	a multiprocessors aware function that hands off bits of a phrase search to multiple searchers
	you need to pick temporarily reassign max hits so that you do not stop searching after one item in the phrase hits the limit

	:param hits:
	:param seeking:
	:param searching:
	:return:
	"""
	tmp = session['maxresults']
	session['maxresults'] = 19999
	
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()
	
	while len(searching) > 0:
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		try:
			i = searching.pop()
			pollingdata.pdremaining.value = len(searching)
		except: i = (-1,'gr0001w001')
		commitcount.increment()
		if commitcount.value % 750 == 0:
			dbconnection.commit()
		wkid = i[1]
		index = i[0]
		hits[index] = (wkid, phrasesearch(seeking, curs, wkid, authors))
		
	session['maxresults'] = tmp
	dbconnection.commit()
	curs.close()
	del dbconnection
	
	return hits


def phrasesearch(searchphrase, cursor, wkid, authors):
	"""
	a whitespace might mean things are on a new line
	note how horrible something like και δη και is: you will search και first and then...

	:param searchphrase:
	:param cursor:
	:param authorobject:
	:param worknumber:
	:return: db lines that match the search criterion
	"""
	searchphrase = cleansearchterm(searchphrase)
	searchterms = searchphrase.split(' ')
	searchterms = [x for x in searchterms if x]
	
	longestterm = searchterms[0]
	for term in searchterms:
		if len(term) > len(longestterm):
			longestterm = term
	
	if 'x' not in wkid:
		# hits = partialwordsearch(longestterm, cursor, wkid, authors)
		hits = concsearch(longestterm, cursor, wkid)
	else:
		wkid = re.sub('x', 'w', wkid)
		hits = simplesearchworkwithexclusion(longestterm, wkid, authors, cursor)
	
	fullmatches = []
	for hit in hits:
		phraselen = len(searchphrase.split(' '))
		wordset = lookoutsideoftheline(hit[0], phraselen - 1, wkid, cursor)
		if session['accentsmatter'] == 'N':
			wordset = re.sub(r'[\.\?\!;:,·’]', r'', wordset)
		else:
			# the difference is in the apostrophe: δ vs δ’
			wordset = re.sub(r'[\.\?\!;:,·]', r'', wordset)
		
		if session['nearornot'] == 'T' and re.search(searchphrase, wordset) is not None:
			fullmatches.append(hit)
			pollingdata.pdhits.increment(1)
		elif session['nearornot'] == 'F' and re.search(searchphrase, wordset) is None:
			fullmatches.append(hit)
			pollingdata.pdhits.increment(1)
	
	return fullmatches


def workonproximitysearch(count, hits, seeking, proximate, searching, commitcount, authors):
	"""
	a multiprocessors aware function that hands off bits of a proximity search to multiple searchers
	note that exclusions are handled deeper down in withinxlines() and withinxwords()
	:param count:
	:param hits:
	:param seeking:
	:param proximate:
	:param searching:
	:return: a collection of hits
	"""
	
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()
	
	if len(proximate) > len(seeking) and session['nearornot'] != 'F' and ' ' not in seeking and ' ' not in proximate:
		# look for the longest word first since that is probably the quicker route
		# but you cant swap seeking and proximate this way in a 'is not near' search without yielding the wrong focus
		tmp = proximate
		proximate = seeking
		seeking = tmp
	
	while len(searching) > 0 and count.value <= int(session['maxresults']):
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		try:
			i = searching.pop()
			pollingdata.pdremaining.value = len(searching)
		except: i = (-1,'gr0001w001')
		commitcount.increment()
		if commitcount.value % 750 == 0:
			dbconnection.commit()
		wkid = i[1]
		index = i[0]
		if session['searchscope'] == 'L':
			hits[index] = (wkid, withinxlines(int(session['proximity']), seeking, proximate, curs, wkid, authors))
		else:
			hits[index] = (wkid, withinxwords(int(session['proximity']), seeking, proximate, curs, wkid, authors))
		
		if len(hits[index][1]) == 0:
			del hits[index]
		else:
			count.increment(len(hits[index][1]))
			pollingdata.pdhits.increment(len(hits[index][1]))
	
	dbconnection.commit()
	curs.close()
	del dbconnection
	
	return hits


def simplesearchworkwithexclusion(seeking, workdbname, authors, cursor):
	"""
	special issues arise if you want to search Iliad less books 1 and 24
	the standard search apparatus can't do this, but this can
	a modified version of partialwordsearch()

	possible to use finddblinefromincompletelocus() to get a set of line numbers to search the main db or the conc
	but is that at all faster? it likely means more queries in the end, not fewer

	problem: l2<>1 AND l1<>10 inside an SQL query will kill ALL 10s at l1, not just in the one segment
	so you cant just string together the where clauses as one giant collection of ANDs
	instead to search Hdt while dropping book 1 and 7.10 and 9.110 you do:

		SELECT * FROM gr0016w001 WHERE (stripped_line ~* 'δεινον' OR hyphenated_words ~* 'δεινον')
		AND (level_02_value<>'1' )
		AND (level_02_value<>'7' OR level_01_value<>'10' )
		AND (level_02_value<>'9'OR level_01_value<>'110' )
		LIMIT 250

	"""
	mylimit = ' LIMIT ' + str(session['maxresults'])
	if session['accentsmatter'] == 'Y':
		columna = 'marked_up_line'
	else:
		columna = 'stripped_line'
	columnb = 'hyphenated_words'
	
	seeking = cleansearchterm(seeking)
	hyphsearch = seeking
	db = workdbname[0:10]
	
	mysyntax = '~*'
	if seeking[0] == ' ':
		# otherwise you will miss words that start lines because they do not have a leading whitespace
		seeking = r'(^|\s)' + seeking[1:]
	elif seeking[0:1] == '\s':
		seeking = r'(^|\s)' + seeking[2:]
	
	restrictions = []
	for p in session['psgexclusions']:
		if workdbname in p:
			restrictions.append(whereclauses(p, '<>', authors))
	
	d = [seeking, hyphsearch]
	qw = 'AND ('
	for r in restrictions:
		for i in range(0, len(r)):
			qw += r[i][0] + 'OR '
			d.append(r[i][1])
		# drop the trailing ' OR'
		qw = qw[0:-4] + ') AND ('
	# drop the trailing ') AND ('
	qw = qw[0:-6]
	
	query = 'SELECT * FROM ' + db + ' WHERE (' + columna + ' ' + mysyntax + ' %s OR ' + columnb + ' ' + mysyntax + ' %s) ' + qw + ' ORDER BY index ASC '+mylimit
	data = tuple(d)
	cursor.execute(query, data)
	found = cursor.fetchall()
	
	return found


def dispatchshortphrasesearch(searchphrase, indexedauthorandworklist, authors):
	"""
	brute force a search for something horrid like και δη και
	a set of short words should send you here, otherwise you will look up all the words that look like και and then...
	:param searchphrase:
	:param cursor:
	:param wkid:
	:return:
	"""
	
	pollingdata.pdpoolofwork.value = len(indexedauthorandworklist)
	pollingdata.pdremaining.value = len(indexedauthorandworklist)
	pollingdata.pdhits.val.value = 0
	pollingdata.pdstatusmessage = 'Executing a short-phrase search...'
	
	
	count = MPCounter()
	manager = Manager()
	hits = manager.dict()
	workstosearch = manager.list(indexedauthorandworklist)
	# if you don't autocommit you will see: "Error: current transaction is aborted, commands ignored until end of transaction block"
	# alternately you can commit every N transactions
	commitcount = MPCounter()
	
	workers = hipparchia.config['WORKERS']
	
	jobs = [Process(target=shortphrasesearch, args=(count, hits, searchphrase, workstosearch, authors)) for i in range(workers)]
	
	for j in jobs: j.start()
	for j in jobs: j.join()
			
	hits = sortandunpackresults(hits)
	# hits = [('gr0059w002', <server.hipparchiaclasses.dbWorkLine object at 0x10b0bb358>), ...]

	lineobjects = []
	for h in hits:
		lineobjects.append(h[1])
	
	return lineobjects


def shortphrasesearch(count, hits, searchphrase, workstosearch, authors):
	"""
	mp aware search for runs of short words
	:return:
	"""
	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	
	while len(workstosearch) > 0 and count.value <= int(session['maxresults']):
		try:
			w = workstosearch.pop()
			pollingdata.pdremaining.value = len(workstosearch)
		except: w = (-1, 'gr0000w000')
		index = w[0]
		if index != -1:
			matchobjects = []
			wkid = w[1]
			# echeck for exclusions
			if re.search(r'x', wkid) is not None:
				wkid = re.sub(r'x', 'w', wkid)
				restrictions = []
				for p in session['psgexclusions']:
					if wkid in p:
						restrictions.append(whereclauses(p, '<>', authors))
			
				whr = ''
				data = []
				for r in restrictions:
					for i in range(0, len(r)):
						whr += r[i][0] + 'OR '
						data.append(r[i][1])
					# drop the trailing ' OR'
					whr = whr[0:-4] + ') AND ('
				# drop the trailing ') AND ('
				whr = whr[0:-6]
			
				query = 'SELECT * FROM ' + wkid + ' WHERE ('+ whr + ' ORDER BY index ASC'
				curs.execute(query, tuple(data))
			else:
				wkid = re.sub(r'x', 'w', wkid)
				query = 'SELECT * FROM ' + wkid + ' ORDER BY index'
				curs.execute(query)
				
			fulltext = curs.fetchall()
			
			previous = makeablankline(wkid, -1)
			lineobjects = []
			for dbline in fulltext:
				lineobjects.append(dblineintolineobject(wkid, dbline))
			lineobjects.append(makeablankline(wkid, -9999))
			del fulltext
			
			if session['accentsmatter'] == 'N':
				acc = 'stripped'
			else:
				acc = 'accented'
			
			searchphrase = cleansearchterm(searchphrase)
			searchterms = searchphrase.split(' ')
			searchterms = [x for x in searchterms if x]
			contextneeded = len(searchterms) - 1
			
			for i in range(0, len(lineobjects) - 1):
				if count.value <= int(session['maxresults']):
					if previous.hashyphenated == True and lineobjects[i].hashyphenated == True:
						core = lineobjects[i].allbutfirstandlastword(acc)
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[1:contextneeded + 1]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					elif previous.hashyphenated == False and lineobjects[i].hashyphenated == True:
						core = lineobjects[i].allbutlastword(acc)
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[0:contextneeded]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					elif previous.hashyphenated == True and lineobjects[i].hashyphenated == False:
						core = lineobjects[i].allbutfirstword(acc)
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[0:contextneeded]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					else:
						# previous.hashyphenated == False and lineobjects[i].hashyphenated == False
						if session['accentsmatter'] == 'N':
							core = lineobjects[i].stripped
						else:
							core = lineobjects[i].unformattedline()
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[0:contextneeded]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					
					try:
						prepend = previous.wordlist(acc)[-1 * contextneeded:]
					except:
						prepend = previous.wordlist(acc)
					
					prepend = ' '.join(prepend)
					supplement = ' '.join(supplement)
					searchzone = prepend + ' ' + core + ' ' + supplement
					searchzone = re.sub(r'\s\s', r' ', searchzone)
					
					if re.search(searchphrase, searchzone) is not None:
						count.increment(1)
						pollingdata.pdhits.val.value = count.value
						matchobjects.append(lineobjects[i])
					previous = lineobjects[i]
					
		# note that each work generates one set of matchobjects (but they are internally sorted)
			hits[index] = (wkid, matchobjects)
	
	curs.close()
	del dbconnection
	
	return hits


def withinxlines(distanceinlines, firstterm, secondterm, cursor, workdbname, authors):
	"""
	after finding x, look for y within n lines of x
	people who send phrases to both halves and/or a lot of regex will not always get what they want
	:param distanceinlines:
	:param additionalterm:
	:return:
	"""
	firstterm = cleansearchterm(firstterm)
	secondterm = re.compile(cleansearchterm(secondterm))
	
	# hits = partialwordsearch(longestterm, cursor, authorobject, worknumber)
	if '_AT_' not in workdbname and 'x' not in workdbname and ' ' not in firstterm:
		hits = concsearch(firstterm, cursor, workdbname)
	elif 'x' in workdbname:
		workdbname = re.sub('x', 'w', workdbname)
		hits = simplesearchworkwithexclusion(firstterm, workdbname, authors, cursor)
	else:
		hits = partialwordsearch(firstterm, cursor, workdbname, authors)
	
	fullmatches = []
	for hit in hits:
		wordset = aggregatelines(hit[0] - distanceinlines, hit[0] + distanceinlines, cursor, workdbname)
		if session['nearornot'] == 'T' and re.search(secondterm, wordset) is not None:
			fullmatches.append(hit)
		elif session['nearornot'] == 'F' and re.search(secondterm, wordset) is None:
			fullmatches.append(hit)
	
	return fullmatches


def withinxwords(distanceinwords, firstterm, secondterm, cursor, workdbname, authors):
	"""
	after finding x, look for y within n words of x
	:param distanceinlines:
	:param additionalterm:
	:return:
	"""
	distanceinwords += 1
	firstterm = cleansearchterm(firstterm)
	secondterm = cleansearchterm(secondterm)
	
	if '_AT_' not in workdbname and 'x' not in workdbname and ' ' not in firstterm:
		hits = concsearch(firstterm, cursor, workdbname)
	elif 'x' in workdbname:
		workdbname = re.sub('x', 'w', workdbname)
		hits = simplesearchworkwithexclusion(firstterm, workdbname, authors, cursor)
	else:
		hits = partialwordsearch(firstterm, cursor, workdbname, authors)
	
	fullmatches = []
	for hit in hits:
		linesrequired = 0
		wordlist = []
		while len(wordlist) < 2 * distanceinwords + 1:
			wordset = aggregatelines(hit[0] - linesrequired, hit[0] + linesrequired, cursor, workdbname)
			wordlist = wordset.split(' ')
			try:
				wordlist.remove('')
			except:
				pass
			linesrequired += 1
		
		# the word is near the middle...
		center = len(wordlist) // 2
		prior = ''
		next = ''
		if firstterm in wordlist[center]:
			startfrom = center
		else:
			distancefromcenter = 0
			while firstterm not in prior and firstterm not in next:
				distancefromcenter += 1
				try:
					next = wordlist[center + distancefromcenter]
					prior = wordlist[center - distancefromcenter]
				except:
					# print('failed to find next/prior:',authorobject.shortname,distancefromcenter,wordlist)
					# to avoid the infinite loop...
					firstterm = prior
			if firstterm in prior:
				startfrom = center - distancefromcenter
			else:
				startfrom = center + distancefromcenter
		
		searchszone = wordlist[startfrom - distanceinwords:startfrom + distanceinwords]
		searchszone = ' '.join(searchszone)
		
		if session['nearornot'] == 'T' and re.search(secondterm, searchszone) is not None:
			fullmatches.append(hit)
		elif session['nearornot'] == 'F' and re.search(secondterm, searchszone) is None:
			fullmatches.append(hit)
	
	return fullmatches



