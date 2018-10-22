# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import pickle
import re
from multiprocessing import Manager, Process
from multiprocessing.managers import ListProxy
from typing import List

from server import hipparchia
from server.dbsupport.dblinefunctions import dblineintolineobject
from server.dbsupport.miscdbfunctions import icanpickleconnections
from server.dbsupport.redisdbfunctions import buildredissearchlist, loadredisresults
from server.formatting.wordformatting import wordlistintoregex
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.dbtextobjects import dbWorkLine
from server.hipparchiaobjects.searchfunctionobjects import returnsearchfncobject
from server.hipparchiaobjects.searchobjects import SearchObject
from server.searching.phrasesearching import phrasesearch, subqueryphrasesearch
from server.searching.proximitysearching import withinxlines, withinxwords
from server.searching.searchfunctions import findleastcommonterm, findleastcommontermcount, loadsearchqueue, \
	massagesearchtermsforwhitespace
from server.searching.substringsearching import substringsearch
from server.threading.mpthreadcount import setthreadcount


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
	founddblineobjects = manager.list()

	workers = setthreadcount()

	if so.redisresultlist and so.redissearchlist:
		listofplacestosearch = None
		buildredissearchlist(list(so.indexrestrictions.keys()), so.searchid)
	else:
		listofplacestosearch = manager.list(so.indexrestrictions.keys())

	activepoll.allworkis(len(so.searchlist))
	activepoll.remain(len(so.indexrestrictions.keys()))
	activepoll.sethits(0)

	# be careful about getting mp aware args into the function

	targetfunction = None
	argumentuple = None

	if so.searchtype == 'simple':
		activepoll.statusis('Executing a simple word search...')
		targetfunction = workonsimplesearch
		argumentuple = (founddblineobjects, listofplacestosearch, so)
	elif so.searchtype == 'simplelemma':
		activepoll.statusis('Executing a lemmatized word search for the {n} known forms of {w}...'.format(n=len(so.lemma.formlist), w=so.lemma.dictionaryentry))
		# don't search for every form at once (100+?)
		# instead build a list of tuples: [(ORed_regex_forms_part_01, authortable1), ...]
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
		if so.usequeue:
			searchtuples = loadsearchqueue([t for t in searchtuples], workers)
		if so.redissearchlist:
			ptuples = [pickle.dumps(s) for s in searchtuples]
			buildredissearchlist(ptuples, so.searchid)
		targetfunction = workonsimplelemmasearch
		argumentuple = (founddblineobjects, searchtuples, so)
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
			argumentuple = (founddblineobjects, listofplacestosearch, so)
		else:
			# print('subqueryphrasesearch()', searchingfor)
			targetfunction = subqueryphrasesearch
			argumentuple = (founddblineobjects, so.termone, listofplacestosearch, so)
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
		argumentuple = (founddblineobjects, listofplacestosearch, so)
	else:
		# impossible, but...
		workers = 0


	# non-parallel multiprocessing implementation across platforms: widows can't pickle a connection;
	# everone else needs to pickle the connection
	if icanpickleconnections():
		# you need to give each job its own connection if you use a connection pool
		# otherwise there will be problems with threading
		# note that we are not yet taking care of connection types: 'autocommit', etc

		oneconnectionperworker = {i: ConnectionObject() for i in range(workers)}
	else:
		# will grab a connection later once inside of 'sfo'
		oneconnectionperworker = {i: None for i in range(workers)}

	# note that the following (when fully implemented...) does not produce speedups
	# operedisconnectionperworker = {i: establishredisconnection() for i in range(workers)}

	argumentswithconnections = [tuple([i] + list(argumentuple) + [oneconnectionperworker[i]]) for i in range(workers)]
	jobs = [Process(target=targetfunction, args=argumentswithconnections[i]) for i in range(workers)]

	for j in jobs:
		j.start()

	for j in jobs:
		j.join()

	if so.redisresultlist:
		foundlineobjects = loadredisresults(so.searchid)
	else:
		# foundlineobjects = [dblineintolineobject(item) for item in founddblineobjects]
		foundlineobjects = list(founddblineobjects)

	for c in oneconnectionperworker:
		oneconnectionperworker[c].connectioncleanup()

	return foundlineobjects


def workonsimplesearch(workerid: int, foundlineobjects: ListProxy, listofplacestosearch: ListProxy, searchobject: SearchObject, dbconnection) -> ListProxy:
	"""

	the simplest version: look for a term in some places

	substringsearch() called herein needs ability to CREATE TEMPORARY TABLE

	:param foundlineobjects:
	:param listofplacestosearch:
	:param searchobject:
	:param dbconnection:
	:return:
	"""

	# TESTING: probe the marked up data; good for finding rare/missing markup like 'hmu_scholium'
	# searchobject.usecolumn = 'marked_up_line'

	sfo = returnsearchfncobject(workerid, foundlineobjects, listofplacestosearch, searchobject, dbconnection, substringsearch)
	sfo.searchfunctionparameters = [sfo.so.termone, 'parametertoswap', sfo.so, sfo.dbcursor]
	sfo.dbconnection.setreadonly(False)
	sfo.iteratethroughsearchlist()

	return sfo.foundlineobjects


def workonproximitysearch(workerid: int, foundlineobjects: ListProxy, listofplacestosearch: ListProxy, searchobject: SearchObject, dbconnection) -> ListProxy:
	"""

	look for A near/not near B

	a multiprocessor aware function that hands off bits of a proximity search to multiple searchers

	searchinginside:
		['lt0400', 'lt0022', ...]

	searchobject.termone:
		'rex'

	searchobject.termtwo:
		'patres'

	:param foundlineobjects:
	:param listofplacestosearch:
	:param activepoll:
	:param searchobject:
	:return:
	"""

	if searchobject.scope == 'lines':
		fnc = withinxlines
	else:
		fnc = withinxwords

	sfo = returnsearchfncobject(workerid, foundlineobjects, listofplacestosearch, searchobject, dbconnection, fnc)
	sfo.searchfunctionparameters = ['parametertoswap', sfo.so, sfo.dbconnection]
	sfo.iteratethroughsearchlist()

	return sfo.foundlineobjects


def workonphrasesearch(workerid: int, foundlineobjects: ListProxy, listofplacestosearch: ListProxy, searchobject: SearchObject, dbconnection) -> ListProxy:
	"""

	a multiprocessor aware function that hands off bits of a phrase search to multiple searchers
	you need to pick temporarily reassign max hits so that you do not stop searching after one item in the phrase
	hits the limit

	searchinginside:
		['lt0400', 'lt0022', ...]

	:param foundlineobjects:
	:param listofplacestosearch:
	:param activepoll:
	:param searchobject:
	:return:
	"""

	sfo = returnsearchfncobject(workerid, foundlineobjects, listofplacestosearch, searchobject, dbconnection, phrasesearch)
	sfo.searchfunctionparameters = ['parametertoswap', sfo.so, sfo.dbcursor]
	sfo.iteratethroughsearchlist()

	return sfo.foundlineobjects


def workonsimplelemmasearch(workerid: int, foundlineobjects: ListProxy, searchtuples: ListProxy, searchobject: SearchObject, dbconnection) -> ListProxy:
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

	since we swap both the search term and the location and not just the location, we can's use the generic
	gsfo.iteratethroughsearchlist() which only swaps locations

	:param foundlineobjects:
	:param searchtuples:
	:param searchobject:
	:param dbconnection:
	:return:
	"""

	sfo = returnsearchfncobject(workerid, foundlineobjects, searchtuples, searchobject, dbconnection, substringsearch)
	sfo.dbconnection.setreadonly(False)
	sfo.parameterswapper = sfo.tupleparamswapper
	sfo.searchfunctionparameters = ['parametertoswap', sfo.so, sfo.dbcursor]
	sfo.iteratethroughsearchlist()

	return sfo.foundlineobjects
