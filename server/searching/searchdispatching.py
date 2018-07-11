# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from multiprocessing import Manager, Process
from multiprocessing.managers import ListProxy
from typing import List

from server import hipparchia
from server.threading.mpthreadcount import setthreadcount
from server.dbsupport.dblinefunctions import dblineintolineobject
from server.formatting.wordformatting import wordlistintoregex
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.dbtextobjects import dbWorkLine
from server.hipparchiaobjects.searchobjects import SearchObject
from server.searching.phrasesearching import phrasesearch, subqueryphrasesearch
from server.searching.proximitysearching import withinxlines, withinxwords
from server.searching.searchfunctions import findleastcommonterm, findleastcommontermcount, \
	massagesearchtermsforwhitespace
from server.searching.substringsearching import substringsearch


def searchdispatcher(searchobject: SearchObject) -> List[dbWorkLine]:
	"""

	assign the search to multiprocessing workers
		searchobject:
			<server.hipparchiaclasses.SearchObject object at 0x1102c15f8>
		activepoll:
			<server.hipparchiaclasses.ProgressPoll object at 0x1102c15f8>

	:param searchobject:
	:param activepoll:
	:return:
	"""

	so = searchobject
	activepoll = so.poll

	# recompose 'searchingfor' (if it exists)
	# note that 'proximate' does not need as many checks
	if so.seeking:
		searchingfor = massagesearchtermsforwhitespace(so.seeking)
	else:
		searchingfor = ''

	# lunate sigmas / UV / JI issues
	unomdifiedskg = searchingfor
	unmodifiedprx = so.proximate

	activepoll.statusis('Loading the the dispatcher...')

	manager = Manager()
	foundlineobjects = manager.list()
	searchlist = manager.list(so.indexrestrictions.keys())

	workers = setthreadcount()
	
	activepoll.allworkis(len(so.searchlist))
	activepoll.remain(len(so.indexrestrictions.keys()))
	activepoll.sethits(0)

	# be careful about getting mp aware args into the function

	targetfunction = None
	argumentuple = None

	if so.searchtype == 'simple':
		activepoll.statusis('Executing a simple word search...')
		targetfunction = workonsimplesearch
		argumentuple = (foundlineobjects, searchlist, so)
	elif so.searchtype == 'simplelemma':
		activepoll.statusis('Executing a lemmatized word search for the {n} known forms of {w}...'.format(n=len(so.lemma.formlist), w=so.lemma.dictionaryentry))
		chunksize = hipparchia.config['LEMMACHUNKSIZE']
		terms = so.lemma.formlist
		chunked = [terms[i:i + chunksize] for i in range(0, len(terms), chunksize)]
		chunked = [wordlistintoregex(c) for c in chunked]
		searchtuples = manager.list()
		masterlist = so.indexrestrictions.keys()
		for c in chunked:
			for item in masterlist:
				searchtuples.append((c, item))
		activepoll.allworkis(len(searchtuples))
		targetfunction = workonsimplelemmasearch
		argumentuple = (foundlineobjects, searchtuples, so)
	elif so.searchtype == 'phrase':
		activepoll.statusis('Executing a phrase search.')
		so.leastcommon = findleastcommonterm(so.termone, so.accented)
		lccount = findleastcommontermcount(so.termone, so.accented)

		# print('least common word in phrase:', lccount, ':', so.leastcommon, so.termone)
		# longestterm = max([len(t) for t in so.termone.split(' ') if t])
		# need to figure out when it will be faster to go to subqueryphrasesearch() and when not to
		# logic + trial and error
		#   e.g., any phrase involving λιποταξίου (e.g., γράψομαι λιποταξίου) can be very fast because that form appears 36x:
		#   you can find it in 1s but if you go through subqueryphrasesearch() you will spend about 17s per full TLG search
		# lccount = -1 if you are unaccented
		#   'if 0 < lccount < 500 or longestterm > 5' got burned badly with 'ἐξ ἀρχῆϲ πρῶτον'
		#   'or (lccount == -1 and longestterm > 6)' would take 1m to find διαφοραϲ ιδεαν via workonphrasesearch()
		#   but the same can be found in 16.45s via subqueryphrasesearch()
		# it looks like unaccented searches are very regularly faster via subqueryphrasesearch()
		#   when is this not true? being wrong about sqs() means spending an extra 10s; being wrong about phs() means an extra 40s...
		if 0 < lccount < 500:
			# print('workonphrasesearch()', searchingfor)
			targetfunction = workonphrasesearch
			argumentuple = (foundlineobjects, searchlist, so)
		else:
			targetfunction = subqueryphrasesearch
			argumentuple = (foundlineobjects, so.termone, searchlist, so)
			# print('subqueryphrasesearch()', searchingfor)
	elif so.searchtype == 'proximity':
		activepoll.statusis('Executing a proximity search...')
		if so.lemma or so.proximatelemma:
			pass
		elif so.accented or re.search(r'^[a-z]', so.termone) and so.near:
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
		targetfunction = workonproximitysearch
		argumentuple = (foundlineobjects, searchlist, so)
	else:
		# impossible, but...
		workers = 0

	# you need to give each job its own connection if you use a connection pool
	# otherwise there will be problems with threading
	# note that we are not yet taking care of connection types: 'autocommit', etc

	oneconnectionperworker = {i: ConnectionObject() for i in range(workers)}
	argumentswithconnections = [tuple(list(argumentuple) + [oneconnectionperworker[i]]) for i in range(workers)]
	jobs = [Process(target=targetfunction, args=argumentswithconnections[i]) for i in range(workers)]

	for j in jobs:
		j.start()
	for j in jobs:
		j.join()

	# generator needs to turn into a list
	foundlineobjects = list(foundlineobjects)

	for c in oneconnectionperworker:
		oneconnectionperworker[c].connectioncleanup()

	return foundlineobjects


def workonsimplesearch(foundlineobjects: ListProxy, searchlist: ListProxy, searchobject: SearchObject, dbconnection) -> ListProxy:
	"""
	
	a multiprocessor aware function that hands off bits of a simple search to multiple searchers
	you need to pick the right style of search for each work you search, though

	searchlist: ['gr0461', 'gr0489', 'gr0468', ...]

	substringsearch() called herein needs ability to CREATE TEMPORARY TABLE
	
	:param foundlineobjects: 
	:param searchlist: 
	:param searchobject: 
	:param dbconnection: 
	:return: 
	"""

	so = searchobject
	activepoll = so.poll

	# TESTING: probe the marked up data; good for finding rare/missing markup like 'hmu_scholium'
	# so.usecolumn = 'marked_up_line'

	dbconnection.setreadonly(False)
	dbcursor = dbconnection.cursor()

	commitcount = 0

	while searchlist and activepoll.gethits() <= so.cap:
		commitcount += 1
		dbconnection.checkneedtocommit(commitcount)
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		# that's not supposed to happen with the pool, but somehow it does

		try:
			authortable = searchlist.pop()
		except IndexError:
			authortable = None
			searchlist = None
			
		if authortable:
			foundlines = substringsearch(so.termone, authortable, so, dbcursor)
			lineobjects = [dblineintolineobject(f) for f in foundlines]
			foundlineobjects.extend(lineobjects)

			if lineobjects:
				# print(authortable, len(lineobjects))
				numberoffinds = len(lineobjects)
				activepoll.addhits(numberoffinds)

		try:
			activepoll.remain(len(searchlist))
		except TypeError:
			pass

	return foundlineobjects


def workonsimplelemmasearch(foundlineobjects: ListProxy, searchtuples: ListProxy, searchobject: SearchObject, dbconnection) -> ListProxy:
	"""
	
	a multiprocessor aware function that hands off bits of a simple search to multiple searchers
	you need to pick the right style of search for each work you search, though

	searchlist: ['gr0461', 'gr0489', 'gr0468', ...]

	lemmatized clivius:
		(^|\s)clivi(\s|$)|(^|\s)cliviam(\s|$)|(^|\s)clivique(\s|$)|(^|\s)cliviae(\s|$)|(^|\s)cliui(\s|$)

	searchtuples:
		[(lemmatizedchunk1, tabletosearch1), (lemmatizedchunk1, tabletosearch2), ...]

	these searches go very slowly of you seek "all 429 known forms of »εὑρίϲκω«"; so they have been broken up
	you will search N forms in all tables; then another N forms in all tables; ...
	
	:param foundlineobjects: 
	:param searchtuples: 
	:param searchobject: 
	:param dbconnection: 
	:return: 
	"""

	so = searchobject
	activepoll = so.poll

	# substringsearch will be creating a temp table
	dbconnection.setreadonly(False)
	dbcursor = dbconnection.cursor()

	commitcount = 0
	while searchtuples and activepoll.gethits() <= so.cap:
		commitcount += 1
		dbconnection.checkneedtocommit(commitcount)
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		# that's not supposed to happen with the pool, but somehow it does

		try:
			searchingfor, authortable = searchtuples.pop()
		except IndexError:
			authortable = None
			searchingfor = None
			searchtuples = None

		if authortable:
			foundlines = substringsearch(searchingfor, authortable, so, dbcursor)
			lineobjects = [dblineintolineobject(f) for f in foundlines]
			foundlineobjects.extend(lineobjects)

			if lineobjects:
				numberoffinds = len(lineobjects)
				activepoll.addhits(numberoffinds)

		try:
			activepoll.remain(len(searchtuples))
		except TypeError:
			pass

	return foundlineobjects


def workonphrasesearch(foundlineobjects: ListProxy, searchinginside: ListProxy, searchobject: SearchObject, dbconnection) -> ListProxy:
	"""

	a multiprocessor aware function that hands off bits of a phrase search to multiple searchers
	you need to pick temporarily reassign max hits so that you do not stop searching after one item in the phrase
	hits the limit

	searchinginside:
		['lt0400', 'lt0022', ...]

	:param foundlineobjects:
	:param searchinginside:
	:param activepoll:
	:param searchobject:
	:return:
	"""

	so = searchobject
	activepoll = so.poll

	dbcursor = dbconnection.cursor()

	commitcount = 0
	while searchinginside and len(foundlineobjects) < so.cap:
		commitcount += 1
		dbconnection.checkneedtocommit(commitcount)

		try:
			wkid = searchinginside.pop()
		except IndexError:
			wkid = None
			searchinginside = None

		if wkid:
			foundlines = phrasesearch(wkid, so, dbcursor)
			foundlineobjects.extend([dblineintolineobject(ln) for ln in foundlines])
		try:
			activepoll.remain(len(searchinginside))
		except TypeError:
			pass

	return foundlineobjects


def workonproximitysearch(foundlineobjects: ListProxy, searchinginside: ListProxy, searchobject: SearchObject, dbconnection) -> ListProxy:
	"""

	a multiprocessor aware function that hands off bits of a proximity search to multiple searchers

	searchinginside:
		['lt0400', 'lt0022', ...]

	searchobject.termone:
		'rex'

	searchobject.termtwo:
		'patres'

	:param foundlineobjects:
	:param searchinginside:
	:param activepoll:
	:param searchobject:
	:return:
	"""

	so = searchobject
	activepoll = so.poll

	if so.scope == 'lines':
		searchfunction = withinxlines
	else:
		searchfunction = withinxwords

	while searchinginside and activepoll.gethits() <= so.cap:
		try:
			wkid = searchinginside.pop()
		except IndexError:
			wkid = None
			searchinginside = None

		if wkid:
			foundlines = searchfunction(wkid, so, dbconnection)

			if foundlines:
				activepoll.addhits(len(foundlines))

			foundlineobjects.extend([dblineintolineobject(ln) for ln in foundlines])

		try:
			activepoll.remain(len(searchinginside))
		except TypeError:
			pass

	return foundlineobjects
