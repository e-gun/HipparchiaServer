# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""
import re
from multiprocessing import Manager, Process

from flask import session

from server import hipparchia
from server.dbsupport.dbfunctions import dblineintolineobject, setconnection
from server.hipparchiaclasses import MPCounter
from server.searching.proximitysearching import withinxlines, withinxwords
from server.searching.searchformatting import sortandunpackresults
from server.searching.phrasesearching import shortphrasesearch, phrasesearch
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion


def searchdispatcher(searchtype, seeking, proximate, indexedauthorandworklist, authorswheredict, activepoll):
	"""
	assign the search to multiprocessing workers
	:param seeking:
	:param indexedauthorandworklist:
	:return:
	"""

	activepoll.statusis('Loading the the dispatcher...')
	# several seconds might elapse before you actually execute: loading the full authordict into the manager is a killer
	# 	the complexity of the objects + their embedded objects x 190k...
	#
	# why are we passing authors anyway?
	# 	whereclauses() will use the author info
	#	whereclauses() also needs the embedded workobjects
	#	whereclauses() relevant any time you have an _AT_
	#
	# accordingly we no longer receive the full authordict but instead a pre-pruned dict: authorswheredict{}

	count = MPCounter()
	manager = Manager()
	hits = manager.dict()
	authors = manager.dict(authorswheredict)
	searching = manager.list(indexedauthorandworklist)
	
	# if you don't autocommit you will soon see: "Error: current transaction is aborted, commands ignored until end of transaction block"
	# alternately you can commit every N transactions; the small db sizes for INS and DDP works means there can be some real pounding
	# of the server: the commitcount had to drop from 600 to 400 (with 4 workers) in order to avoid 'could not execute SELECT *...' errors

	commitcount = MPCounter()
	
	workers = hipparchia.config['WORKERS']

	activepoll.allworkis(len(indexedauthorandworklist))
	activepoll.remain(len(indexedauthorandworklist))
	activepoll.sethits(0)

	# a class and/or decorator would be nice, but you have a lot of trouble getting the (mp aware) args into the function
	# the must be a way, but this also works
	if searchtype == 'simple':
		activepoll.statusis('Executing a simple word search...')
		jobs = [Process(target=workonsimplesearch, args=(count, hits, seeking, searching, commitcount, authors, activepoll)) for i in range(workers)]
	elif searchtype == 'phrase':
		activepoll.statusis('Executing a phrase search. Checking longest term first...<br />Progress meter only measures this first pass')
		jobs = [Process(target=workonphrasesearch, args=(hits, seeking, searching, commitcount, authors, activepoll)) for i in range(workers)]
	elif searchtype == 'proximity':
		activepoll.statusis('Executing a proximity search...')
		jobs = [Process(target=workonproximitysearch, args=(count, hits, seeking, proximate, searching, commitcount, authors, activepoll)) for i in range(workers)]
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


def dispatchshortphrasesearch(searchphrase, indexedauthorandworklist, authors, activepoll):
	"""
	brute force a search for something horrid like και δη και
	a set of short words should send you here, otherwise you will look up all the words that look like και and then...
	:param searchphrase:
	:param cursor:
	:param wkid:
	:return:
	"""
	
	activepoll.allworkis(len(indexedauthorandworklist))
	activepoll.remain(len(indexedauthorandworklist))
	activepoll.sethits(0)
	activepoll.statusis('Executing a short-phrase search...')
		
	count = MPCounter()
	manager = Manager()
	hits = manager.dict()
	workstosearch = manager.list(indexedauthorandworklist)
	# if you don't autocommit you will see: "Error: current transaction is aborted, commands ignored until end of transaction block"
	# alternately you can commit every N transactions
	commitcount = MPCounter()
	
	workers = hipparchia.config['WORKERS']
	
	jobs = [Process(target=shortphrasesearch, args=(count, hits, searchphrase, workstosearch, authors, activepoll)) for i in range(workers)]
	
	for j in jobs: j.start()
	for j in jobs: j.join()
			
	hits = sortandunpackresults(hits)
	# hits = [('gr0059w002', <server.hipparchiaclasses.dbWorkLine object at 0x10b0bb358>), ...]

	lineobjects = []
	for h in hits:
		lineobjects.append(h[1])
	
	return lineobjects


def workonsimplesearch(count, hits, seeking, searching, commitcount, authors, activepoll):
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
		# that's not supposed to happen with the pool, but somehow it does
		try:
			i = searching.pop()
			activepoll.remain(len(searching))
		except: i = (-1,'gr0000w000')
		commitcount.increment()
		if commitcount.value % 400 == 0:
			dbconnection.commit()
		wkid = i[1]
		index = i[0]
		if index != -1:
			if '_AT_' in wkid:
				hits[index] = (wkid, substringsearch(seeking, curs, wkid, authors))
			elif 'x' in wkid:
				wkid = re.sub('x', 'w', wkid)
				hits[index] = (wkid, simplesearchworkwithexclusion(seeking, wkid, authors, curs))
			else:
				# used to have more options, so this 'else' seems illogical/redundant right now
				hits[index] = (wkid, substringsearch(seeking, curs, wkid, authors))

			if len(hits[index][1]) == 0:
				del hits[index]
			else:
				count.increment(len(hits[index][1]))
				activepoll.addhits(len(hits[index][1]))

	dbconnection.commit()
	curs.close()
	del dbconnection

	return hits


def workonphrasesearch(hits, seeking, searching, commitcount, authors, activepoll):
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
			activepoll.remain(len(searching))
		except: i = (-1,'gr0001w001')
		commitcount.increment()
		if commitcount.value % 400 == 0:
			dbconnection.commit()
		wkid = i[1]
		index = i[0]
		hits[index] = (wkid, phrasesearch(seeking, curs, wkid, authors, activepoll))

	session['maxresults'] = tmp
	dbconnection.commit()
	curs.close()
	del dbconnection

	return hits


def workonproximitysearch(count, hits, seeking, proximate, searching, commitcount, authors, activepoll):
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
			activepoll.remain(len(searching))
		except: i = (-1,'gr0001w001')
		commitcount.increment()
		if commitcount.value % 400 == 0:
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
			activepoll.addhits(len(hits[index][1]))

	dbconnection.commit()
	curs.close()
	del dbconnection

	return hits