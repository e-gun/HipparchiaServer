# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from multiprocessing import Manager, Process

from server import hipparchia
from server.dbsupport.dbfunctions import dblineintolineobject, setconnection
from server.hipparchiaclasses import MPCounter
from server.lexica.lexicalookups import findcountsviawordcountstable
from server.searching.phrasesearching import phrasesearch, subqueryphrasesearch
from server.searching.proximitysearching import withinxlines, withinxwords
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion, findleastcommonterm, \
	massagesearchtermsforwhitespace, findleastcommontermcount


def searchdispatcher(searchobject, activepoll):
	"""
	assign the search to multiprocessing workers
		searchobject:
			<server.hipparchiaclasses.SearchObject object at 0x1102c15f8>
		activepoll:
			<server.hipparchiaclasses.ProgressPoll object at 0x1102c15f8>

	:param searchingfor:
	:param indexedauthorandworklist:
	:return:
	"""
	so = searchobject

	# recompose 'searchingfor'
	# note that 'proximate' does not need as many checks
	searchingfor = massagesearchtermsforwhitespace(so.seeking)

	# lunate sigmas / UV / JI issues
	unomdifiedskg = searchingfor
	unmodifiedprx = so.proximate

	activepoll.statusis('Loading the the dispatcher...')

	count = MPCounter()
	manager = Manager()
	foundlineobjects = manager.list()
	searchlist = manager.list(so.authorandworklist)

	# if you don't autocommit you will soon see: "Error: current transaction is aborted, commands ignored until end of transaction block"
	# alternately you can commit every N transactions; multiple workers on small tables will lock you out of the DB;
	# you can go up to 32k without a commit? but every 1k is far safer and more or less cost free for our purposes

	commitcount = MPCounter()
	workers = hipparchia.config['WORKERS']
	activepoll.allworkis(len(so.authorandworklist))
	activepoll.remain(len(so.authorandworklist))
	activepoll.sethits(0)

	# be careful about getting mp aware args into the function

	if so.searchtype == 'simple':
		activepoll.statusis('Executing a simple word search...')
		jobs = [Process(target=workonsimplesearch, args=(count, foundlineobjects, searchlist, commitcount, activepoll, so))
		        for i in range(workers)]
	elif so.searchtype == 'phrase':
		activepoll.statusis('Executing a phrase search.')
		so.leastcommon = findleastcommonterm(so.termone, so.accented)
		lccount = findleastcommontermcount(so.termone, so.accented)
		longestterm = max([len(t) for t in so.termone.split(' ') if t])
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
			jobs = [Process(target=workonphrasesearch, args=(foundlineobjects, searchlist, commitcount, activepoll, so))
			        for i in range(workers)]
		else:
			# print('subqueryphrasesearch()',searchingfor)
			jobs = [Process(target=subqueryphrasesearch, args=(foundlineobjects, so.termone, searchlist, count, commitcount, activepoll, so))
			        for i in range(workers)]
	elif so.searchtype == 'proximity':
		activepoll.statusis('Executing a proximity search...')

		if so.accented or re.search(r'^[a-z]',so.termone) and so.near:
			# choose the necessarily faster option
			leastcommon = findleastcommonterm(unomdifiedskg+' '+unmodifiedprx, so.accented)
			if leastcommon != unomdifiedskg:
				tmp = so.termone
				so.termone = so.termtwo
				so.termtwo = tmp
		elif len(so.termtwo) > len(so.termone) and so.near:
			# look for the longest word first since that is probably the quicker route
			# but you can't swap searchingfor and proximate this way in a 'is not near' search without yielding the wrong focus
			tmp = so.termone
			so.termone = so.termtwo
			so.termtwo = tmp
		jobs = [Process(target=workonproximitysearch, args=(count, foundlineobjects, searchlist, activepoll, so))
		        for i in range(workers)]
	else:
		# impossible, but...
		jobs = []

	for j in jobs: j.start()
	for j in jobs: j.join()

	return foundlineobjects


def workonsimplesearch(count, foundlineobjects, searchlist, commitcount, activepoll, searchobject):
	"""
	a multiprocessors aware function that hands off bits of a simple search to multiple searchers
	you need to pick the right style of search for each work you search, though

	searchlist:
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
	so = searchobject

	while len(searchlist) > 0 and count.value <= so.cap:
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		# that's not supposed to happen with the pool, but somehow it does
		try:
			wkid = searchlist.pop()
			activepoll.remain(len(searchlist))
		except IndexError:
			wkid = 'gr0000w000'
			
		if wkid != 'gr0000w000':
			if 'x' in wkid:
				wkid = re.sub('x', 'w', wkid)
				foundlines = simplesearchworkwithexclusion(so.termone, wkid, so, curs)
			else:
				foundlines = substringsearch(so.termone, wkid, so, curs)

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


def workonphrasesearch(foundlineobjects, searchinginside, commitcount, activepoll, searchobject):
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

	so = searchobject

	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	if so.accented:
		# maxhits ('πολυτρόπωϲ', 506, 506, 0, 0, 0, 0)
		maxhits = findcountsviawordcountstable(so.leastcommon)

	try:
		maxhits = maxhits[1]
	except:
		maxhits = 9999

	while len(searchinginside) > 0 and len(foundlineobjects) < so.cap:
		try:
			wkid = searchinginside.pop()
			activepoll.remain(len(searchinginside))
		except:
			wkid = 'gr0000w000'
		commitcount.increment()
		if commitcount.value % 400 == 0:
			dbconnection.commit()

		if wkid != 'gr0000w000':
			foundlines = phrasesearch(maxhits, wkid, activepoll, so, curs)

			for f in foundlines:
				foundlineobjects.append(dblineintolineobject(f))

	dbconnection.commit()
	curs.close()
	del dbconnection

	return foundlineobjects


def workonproximitysearch(count, foundlineobjects, searchinginside, activepoll, searchobject):
	"""

	a multiprocessors aware function that hands off bits of a proximity search to multiple searchers
	note that exclusions are handled deeper down in withinxlines() and withinxwords()

	searchinginside:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']

	searchobject.authorswhere = whereclauseinfo: every author that needs to have a where-clause
	built because you asked for an '_AT_':
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}

	searchobject.termone:
		'rex'

	searchobject.termtwo:
		'patres'

	:param count:
	:param hits:
	:param searchingfor:
	:param proximate:
	:param searching:
	:return: a collection of hits
	"""

	so = searchobject

	while len(searchinginside) > 0 and count.value <= so.cap:

		try:
			wkid = searchinginside.pop()
			activepoll.remain(len(searchinginside))
		except:
			wkid = 'gr0000w000'

		if wkid != 'gr0000w000':
			if so.scope == 'lines':
				foundlines = withinxlines(wkid, so)
			else:
				foundlines = withinxwords(wkid, so)

			count.increment(len(foundlines))
			activepoll.addhits(len(foundlines))

			for f in foundlines:
				foundlineobjects.append(dblineintolineobject(f))

	return foundlineobjects

