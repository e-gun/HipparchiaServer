# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from multiprocessing import Manager, Process

from flask import session

from server import hipparchia
from server.dbsupport.dbfunctions import dblineintolineobject, setconnection
from server.hipparchiaclasses import MPCounter
from server.searching.proximitysearching import withinxlines, withinxwords
from server.searching.phrasesearching import shortphrasesearch, phrasesearch
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion, findleastcommonterm
from server.lexica.lexicalookups import findcountsviawordcountstable


def searchdispatcher(searchtype, seeking, proximate, authorandworklist, authorswheredict, activepoll):
	"""
	assign the search to multiprocessing workers
	sample paramaters:
		searchtype:
			'simple'
		seeking:
			'rex'
		proximate:
			''
		authorandworklist:
			['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']
		authorswheredict: [every author that needs to have a where-clause built because you asked for an '_AT_']
			{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}
		activepoll:
			 <server.hipparchiaclasses.ProgressPoll object at 0x1102c15f8>

	:param seeking:
	:param indexedauthorandworklist:
	:return:
	"""

	if seeking[0] == ' ':
		# otherwise you will miss words that start lines because they do not have a leading whitespace
		seeking = r'(^|\s)' + seeking[1:]
	elif seeking[0:1] == '\s':
		seeking = r'(^|\s)' + seeking[2:]

	if seeking[-1] == ' ':
		# otherwise you will miss words that end lines because they do not have a trailing whitespace
		seeking = seeking[:-1] + r'(\s|$)'
	elif seeking[-2:] == '\s':
		seeking = seeking[:-2] + r'(\s|$)'

	activepoll.statusis('Loading the the dispatcher...')
	# we no longer receive the full authordict but instead a pre-pruned dict: authorswheredict{}

	count = MPCounter()
	manager = Manager()
	foundlineobjects = manager.list()
	whereclauseinfo = manager.dict(authorswheredict)
	searching = manager.list(authorandworklist)

	# if you don't autocommit you will soon see: "Error: current transaction is aborted, commands ignored until end of transaction block"
	# alternately you can commit every N transactions; the small db sizes for INS and DDP works means there can be some real pounding
	# of the server: the commitcount had to drop from 600 to 400 (with 4 workers) in order to avoid 'could not execute SELECT *...' errors

	commitcount = MPCounter()

	workers = hipparchia.config['WORKERS']

	activepoll.allworkis(len(authorandworklist))
	activepoll.remain(len(authorandworklist))
	activepoll.sethits(0)

	# a class and/or decorator would be nice, but you have a lot of trouble getting the (mp aware) args into the function
	# the must be a way, but this also works
	if searchtype == 'simple':
		activepoll.statusis('Executing a simple word search...')
		jobs = [Process(target=workonsimplesearch, args=(count, foundlineobjects, seeking, searching, commitcount, whereclauseinfo, activepoll)) for i in range(workers)]
	elif searchtype == 'phrase':
		if session['accentsmatter'] == 'no':
			criterion = 'longest'
		else:
			criterion = 'least common'
		activepoll.statusis('Executing a phrase search. Checking the '+criterion+' term first...<br />Progress meter only measures this first pass')
		leastcommon = findleastcommonterm(seeking)
		jobs = [Process(target=workonphrasesearch, args=(foundlineobjects, leastcommon, seeking, searching, commitcount, whereclauseinfo, activepoll)) for i in range(workers)]
	elif searchtype == 'proximity':
		activepoll.statusis('Executing a proximity search...')
		if session['accentsmatter'] == 'yes' and session['nearornot'] == 'T':
			# choose the faster option
			leastcommon = findleastcommonterm(seeking+' '+proximate)
			if leastcommon != seeking:
				proximate = seeking
				seeking = leastcommon
				print('seeking','proximate',seeking,proximate)
		jobs = [Process(target=workonproximitysearch, args=(count, foundlineobjects, seeking, proximate, searching, commitcount, whereclauseinfo, activepoll)) for i in range(workers)]
	else:
		# impossible, but...
		jobs = []

	for j in jobs: j.start()
	for j in jobs: j.join()


	return foundlineobjects


def dispatchshortphrasesearch(searchphrase, indexedauthorandworklist, authorswheredict, activepoll):
	"""
	brute force a search for something horrid like και δη και
	a set of short words should send you here, otherwise you will look up all the words that look like και and then...

	sample paramaters:
	searchtype:
		'simple'
	seeking:
		'te tu me'
	proximate:
		''
	authorandworklist:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']
	authorswheredict: [every author that needs to have a where-clause built because you asked for an '_AT_']
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}
	activepoll:
		 <server.hipparchiaclasses.ProgressPoll object at 0x1102c15f8>

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
	foundlineobjects = manager.list()
	workstosearch = manager.list(indexedauthorandworklist)
	# if you don't autocommit you will see: "Error: current transaction is aborted, commands ignored until end of transaction block"
	# alternately you can commit every N transactions
	commitcount = MPCounter()

	workers = hipparchia.config['WORKERS']

	jobs = [Process(target=shortphrasesearch, args=(count, foundlineobjects, searchphrase, workstosearch, authorswheredict, activepoll)) for i in range(workers)]

	for j in jobs: j.start()
	for j in jobs: j.join()


	return foundlineobjects


def workonsimplesearch(count, foundlineobjects, seeking, searchinginside, commitcount, whereclauseinfo, activepoll):
	"""
	a multiprocessors aware function that hands off bits of a simple search to multiple searchers
	you need to pick the right style of search for each work you search, though

	searchinginside:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']

	whereclauseinfo: [every author that needs to have a where-clause built because you asked for an '_AT_']
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}

	seeking:
		'rex'

	:param count:
	:param hits:
	:param seeking:
	:param searching:
	:return: a collection of lineobjects
		[<server.hipparchiaclasses.dbWorkLine object at 0x114401828>, <server.hipparchiaclasses.dbWorkLine object at 0x1144017b8>,...]
	"""

	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	while len(searchinginside) > 0 and count.value <= int(session['maxresults']):
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		# that's not supposed to happen with the pool, but somehow it does
		try:
			wkid = searchinginside.pop()
			activepoll.remain(len(searchinginside))
		except:
			wkid = 'gr0000w000'
			
		if wkid != 'gr0000w000':
			if 'x' in wkid:
				wkid = re.sub('x', 'w', wkid)
				foundlines = simplesearchworkwithexclusion(seeking, wkid, whereclauseinfo, curs)
			else:
				foundlines = substringsearch(seeking, curs, wkid, whereclauseinfo)

			count.increment(len(foundlines))
			activepoll.addhits(len(foundlines))

			for f in foundlines:
				foundlineobjects.append(dblineintolineobject(f))

		commitcount.increment()
		if commitcount.value % 400 == 0:
			dbconnection.commit()
	
	dbconnection.commit()
	curs.close()
	del dbconnection

	return foundlineobjects


def workonphrasesearch(foundlineobjects, leastcommon, seeking, searchinginside, commitcount, whereclauseinfo, activepoll):
	"""
	a multiprocessors aware function that hands off bits of a phrase search to multiple searchers
	you need to pick temporarily reassign max hits so that you do not stop searching after one item in the phrase hits the limit

	searchinginside:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']

	whereclauseinfo: [every author that needs to have a where-clause built because you asked for an '_AT_']
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}

	seeking:
		'Romulus rex'

	:param hits:
	:param seeking:
	:param searching:
	:return:
	"""

	if session['accentsmatter'] == 'no':
		maxhits = 25000
	else:
		maxhits = findcountsviawordcountstable(leastcommon)
	# maxhits ('πολυτρόπωϲ', 506, 506, 0, 0, 0, 0)

	tmp = session['maxresults']
	session['maxresults'] = maxhits[1]

	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	while len(searchinginside) > 0:
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		try:
			wkid = searchinginside.pop()
			activepoll.remain(len(searchinginside))
		except:
			wkid = 'gr0001w001'
		commitcount.increment()
		if commitcount.value % 400 == 0:
			dbconnection.commit()

		foundlines = phrasesearch(leastcommon, seeking, curs, wkid, whereclauseinfo, activepoll)

		for f in foundlines:
			foundlineobjects.append(dblineintolineobject(f))

	session['maxresults'] = tmp
	dbconnection.commit()
	curs.close()
	del dbconnection

	return foundlineobjects


def workonproximitysearch(count, foundlineobjects, seeking, proximate, searchinginside, commitcount, whereclauseinfo, activepoll):
	"""
	a multiprocessors aware function that hands off bits of a proximity search to multiple searchers
	note that exclusions are handled deeper down in withinxlines() and withinxwords()

	searchinginside:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']

	whereclauseinfo: [every author that needs to have a where-clause built because you asked for an '_AT_']
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}

	seeking:
		'rex'

	proximate:
		'patres'

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

	while len(searchinginside) > 0 and count.value <= int(session['maxresults']):
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		# not supposed to happen, but it does...

		try:
			wkid = searchinginside.pop()
			activepoll.remain(len(searchinginside))
		except:
			wkid = 'gr0001w001'

		if wkid != 'gr0000w000':
			if session['searchscope'] == 'L':
				foundlines = withinxlines(int(session['proximity']), seeking, proximate, curs, wkid, whereclauseinfo)
			else:
				foundlines = withinxwords(int(session['proximity']), seeking, proximate, curs, wkid, whereclauseinfo)

			count.increment(len(foundlines))
			activepoll.addhits(len(foundlines))

			for f in foundlines:
				foundlineobjects.append(dblineintolineobject(f))

			commitcount.increment()
			if commitcount.value % 400 == 0:
				dbconnection.commit()

	dbconnection.commit()
	curs.close()
	del dbconnection

	return foundlineobjects
