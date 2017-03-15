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
from server.lexica.lexicalookups import findcountsviawordcountstable
from server.searching.phrasesearching import phrasesearch, subqueryphrasesearch
from server.searching.proximitysearching import withinxlines, withinxwords
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion, findleastcommonterm, \
	massagesearchtermsforwhitespace, searchtermcharactersubstitutions, findleastcommontermcount


def searchdispatcher(searchtype, searchingfor, proximate, authorandworklist, authorswheredict, activepoll):
	"""
	assign the search to multiprocessing workers
	sample paramaters:
		searchtype:
			'simple'
		searchingfor:
			'rex'
		proximate:
			''
		authorandworklist:
			['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']
		authorswheredict: [every author that needs to have a where-clause built because you asked for an '_AT_']
			{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}
		activepoll:
			 <server.hipparchiaclasses.ProgressPoll object at 0x1102c15f8>

	:param searchingfor:
	:param indexedauthorandworklist:
	:return:
	"""

	# recompose 'searchingfor'
	# note that 'proximate' does not need as many checks
	searchingfor = massagesearchtermsforwhitespace(searchingfor)

	# lunate sigmas / UV / JI issues
	unomdifiedskg = searchingfor
	unmodifiedprx = proximate
	searchingfor = searchtermcharactersubstitutions(searchingfor)
	proximate = searchtermcharactersubstitutions(proximate)

	activepoll.statusis('Loading the the dispatcher...')
	# we no longer receive the full authordict but instead a pre-pruned dict: authorswheredict{}

	count = MPCounter()
	manager = Manager()
	foundlineobjects = manager.list()
	whereclauseinfo = manager.dict(authorswheredict)
	searchlist = manager.list(authorandworklist)

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
		jobs = [Process(target=workonsimplesearch, args=(count, foundlineobjects, searchingfor, searchlist, commitcount, whereclauseinfo, activepoll)) for i in range(workers)]
	elif searchtype == 'phrase':
		activepoll.statusis('Executing a phrase search.')
		leastcommon = findleastcommonterm(searchingfor)
		lccount = findleastcommontermcount(searchingfor)
		longestterm = max([len(t) for t in searchingfor.split(' ') if t])
		# need to figure out when it will be faster to go to subqueryphrasesearch() and when not to
		# logic + trial and error
		#   e.g., any phrase involving λιποταξίου can be very fast because that form appears 36x: you can find it in 1s
		#   but if you go through subqueryphrasesearch() you will spend about 17s per full TLG search
		# lccount = -1 if you are unaccented
		#   'if 0 < lccount < 500 or longestterm > 5' got burned badly with 'ἐξ ἀρχῆϲ πρῶτον'
		#   'or (lccount == -1 and longestterm > 6)' would take 1m to find διαφοραϲ ιδεαν via workonphrasesearch()
		#   but the same can be found in 16.45s via subqueryphrasesearch()
		# it looks like unaccented searches are very regularly faster via subqueryphrasesearch()
		#   when is this not true? being wrong about sqs() means spending an extra 10s; being wrong about phs() means an extra 40s...
		if 0 < lccount < 500:
			# print('workonphrasesearch()',searchingfor)
			jobs = [Process(target=workonphrasesearch, args=(foundlineobjects, leastcommon, searchingfor, searchlist, commitcount, whereclauseinfo, activepoll)) for i in range(workers)]
		else:
			# print('subqueryphrasesearch()',searchingfor)
			jobs = [Process(target=subqueryphrasesearch, args=(foundlineobjects, searchingfor, searchlist, count, commitcount, whereclauseinfo, activepoll)) for i in range(workers)]
	elif searchtype == 'proximity':
		activepoll.statusis('Executing a proximity search...')
		termone = searchingfor
		termtwo = proximate
		if (session['accentsmatter'] == 'yes'  or re.search(r'^[a-z]',termone)) and session['nearornot'] == 'T':
			# choose the necessarily faster option
			leastcommon = findleastcommonterm(unomdifiedskg+' '+unmodifiedprx)
			if leastcommon != unomdifiedskg:
				termone = proximate
				termtwo = searchingfor
		elif len(termtwo) > len(termone) and session['nearornot'] == 'T':
			# look for the longest word first since that is probably the quicker route
			# but you can't swap searchingfor and proximate this way in a 'is not near' search without yielding the wrong focus
			tmp = termtwo
			termtwo = termone
			termone = tmp
		jobs = [Process(target=workonproximitysearch, args=(count, foundlineobjects, termone, termtwo, searchlist, commitcount, whereclauseinfo, activepoll)) for i in range(workers)]
	else:
		# impossible, but...
		jobs = []

	for j in jobs: j.start()
	for j in jobs: j.join()

	return foundlineobjects


def workonsimplesearch(count, foundlineobjects, searchingfor, searchinginside, commitcount, whereclauseinfo, activepoll):
	"""
	a multiprocessors aware function that hands off bits of a simple search to multiple searchers
	you need to pick the right style of search for each work you search, though

	searchinginside:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']

	whereclauseinfo: [every author that needs to have a where-clause built because you asked for an '_AT_']
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}

	searchingfor:
		'rex'

	:param count:
	:param hits:
	:param searchingfor:
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
				foundlines = simplesearchworkwithexclusion(searchingfor, wkid, whereclauseinfo, curs)
			else:
				foundlines = substringsearch(searchingfor, curs, wkid, whereclauseinfo)

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


def workonphrasesearch(foundlineobjects, leastcommon, searchingfor, searchinginside, commitcount, whereclauseinfo, activepoll):
	"""
	a multiprocessors aware function that hands off bits of a phrase search to multiple searchers
	you need to pick temporarily reassign max hits so that you do not stop searching after one item in the phrase hits the limit

	searchinginside:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']

	whereclauseinfo: [every author that needs to have a where-clause built because you asked for an '_AT_']
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}

	searchingfor:
		'Romulus rex'

	:param hits:
	:param searchingfor:
	:param searching:
	:return:
	"""

	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	if session['accentsmatter'] == 'yes':
		# maxhits ('πολυτρόπωϲ', 506, 506, 0, 0, 0, 0)
		maxhits = findcountsviawordcountstable(leastcommon)

	try:
		maxhits = maxhits[1]
	except:
		maxhits = 9999

	while len(searchinginside) > 0 and len(foundlineobjects) < int(session['maxresults']):
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		# notsupposedtohappen butitdoes
		try:
			wkid = searchinginside.pop()
			activepoll.remain(len(searchinginside))
		except:
			wkid = 'gr0001w001'
		commitcount.increment()
		if commitcount.value % 400 == 0:
			dbconnection.commit()

		foundlines = phrasesearch(leastcommon, searchingfor, maxhits, wkid, whereclauseinfo, activepoll, curs)

		for f in foundlines:
			foundlineobjects.append(dblineintolineobject(f))

	dbconnection.commit()
	curs.close()
	del dbconnection

	return foundlineobjects


def workonproximitysearch(count, foundlineobjects, searchingfor, proximate, searchinginside, commitcount, whereclauseinfo, activepoll):
	"""
	a multiprocessors aware function that hands off bits of a proximity search to multiple searchers
	note that exclusions are handled deeper down in withinxlines() and withinxwords()

	searchinginside:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']

	whereclauseinfo: [every author that needs to have a where-clause built because you asked for an '_AT_']
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}

	searchingfor:
		'rex'

	proximate:
		'patres'

	:param count:
	:param hits:
	:param searchingfor:
	:param proximate:
	:param searching:
	:return: a collection of hits
	"""

	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	while len(searchinginside) > 0 and count.value <= int(session['maxresults']):
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		# not supposed to happen, but it does...

		try:
			wkid = searchinginside.pop()
			activepoll.remain(len(searchinginside))
		except:
			wkid = 'gr0000w000'

		if wkid != 'gr0000w000':
			if session['searchscope'] == 'L':
				foundlines = withinxlines(int(session['proximity']), searchingfor, proximate, curs, wkid, whereclauseinfo)
			else:
				foundlines = withinxwords(int(session['proximity']), searchingfor, proximate, curs, wkid, whereclauseinfo)

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

