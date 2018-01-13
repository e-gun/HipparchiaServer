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
from server.dbsupport.dbfunctions import dblineintolineobject, setconnection, setthreadcount
from server.formatting.wordformatting import wordlistintoregex
from server.hipparchiaobjects.helperobjects import MPCounter
from server.searching.phrasesearching import phrasesearch, subqueryphrasesearch
from server.searching.proximitysearching import withinxlines, withinxwords
from server.searching.searchfunctions import findleastcommonterm, findleastcommontermcount, \
	massagesearchtermsforwhitespace, substringsearch


def searchdispatcher(searchobject, activepoll):
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

	count = MPCounter()
	manager = Manager()
	foundlineobjects = manager.list()
	searchlist = manager.list(so.indexrestrictions.keys())

	commitcount = MPCounter()
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
		argumentuple = (count, foundlineobjects, searchlist, commitcount, activepoll, so)
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
		argumentuple = (count, foundlineobjects, searchtuples, commitcount, activepoll, so)
	elif so.searchtype == 'phrase':
		activepoll.statusis('Executing a phrase search.')
		so.leastcommon = findleastcommonterm(so.termone, so.accented)
		lccount = findleastcommontermcount(so.termone, so.accented)
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
			argumentuple = (foundlineobjects, searchlist, commitcount, activepoll, so)
		else:
			targetfunction = subqueryphrasesearch
			argumentuple = (foundlineobjects, so.termone, searchlist, count, commitcount, activepoll, so)
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
		argumentuple = (count, foundlineobjects, searchlist, activepoll, so)
	else:
		# impossible, but...
		workers = 0

	jobs = [Process(target=targetfunction, args=argumentuple) for i in range(workers)]

	for j in jobs:
		j.start()
	for j in jobs:
		j.join()

	return foundlineobjects


def workonsimplesearch(count, foundlineobjects, searchlist, commitcount, activepoll, searchobject):
	"""

	a multiprocessor aware function that hands off bits of a simple search to multiple searchers
	you need to pick the right style of search for each work you search, though

	searchlist: ['gr0461', 'gr0489', 'gr0468', ...]


	:param count:
	:param foundlineobjects:
	:param searchlist:
	:param commitcount:
	:param activepoll:
	:param searchobject:
	:return:
	"""

	# print('workonsimplesearch() - searchlist', searchlist)

	# substringsearch() needs ability to CREATE TEMPORARY TABLE
	dbconnection = setconnection('not_autocommit', readonlyconnection=False)
	curs = dbconnection.cursor()
	so = searchobject

	# print('workonsimplesearch() - so.termone', so.termone)

	while searchlist and count.value <= so.cap:

		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		# that's not supposed to happen with the pool, but somehow it does

		try:
			authortable = searchlist.pop()
		except IndexError:
			authortable = None
			searchlist = None
			
		if authortable:
			foundlines = substringsearch(so.termone, authortable, so, curs)
			lineobjects = [dblineintolineobject(f) for f in foundlines]
			foundlineobjects += lineobjects

			numberoffinds = len(lineobjects)
			count.increment(numberoffinds)
			activepoll.addhits(numberoffinds)

		commitcount.increment()
		if commitcount.value % hipparchia.config['MPCOMMITCOUNT'] == 0:
			dbconnection.commit()
		try:
			activepoll.remain(len(searchlist))
		except TypeError:
			pass

	dbconnection.commit()
	curs.close()

	return foundlineobjects


def workonsimplelemmasearch(count, foundlineobjects, searchtuples, commitcount, activepoll, searchobject):
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

	:param count:
	:param foundlineobjects:
	:param searchtuples:
	:param commitcount:
	:param activepoll:
	:param searchobject:
	:return:
	"""

	so = searchobject

	# print('workonsimplesearch() - searchlist', searchlist)

	# substringsearch() needs ability to CREATE TEMPORARY TABLE
	dbconnection = setconnection('not_autocommit', readonlyconnection=False)
	curs = dbconnection.cursor()

	while searchtuples and count.value <= so.cap:

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
			foundlines = substringsearch(searchingfor, authortable, so, curs)
			lineobjects = [dblineintolineobject(f) for f in foundlines]
			foundlineobjects += lineobjects

			numberoffinds = len(lineobjects)
			count.increment(numberoffinds)
			activepoll.addhits(numberoffinds)

		commitcount.increment()
		if commitcount.value % hipparchia.config['MPCOMMITCOUNT'] == 0:
			dbconnection.commit()
		try:
			activepoll.remain(len(searchtuples))
		except TypeError:
			pass

	dbconnection.commit()
	curs.close()

	return foundlineobjects


def workonphrasesearch(foundlineobjects, searchinginside, commitcount, activepoll, searchobject):
	"""

	a multiprocessor aware function that hands off bits of a phrase search to multiple searchers
	you need to pick temporarily reassign max hits so that you do not stop searching after one item in the phrase
	hits the limit

	searchinginside:
		['lt0400', 'lt0022', ...]

	:param foundlineobjects:
	:param searchinginside:
	:param commitcount:
	:param activepoll:
	:param searchobject:
	:return:
	"""

	so = searchobject

	dbconnection = setconnection('autocommit', readonlyconnection=False)
	curs = dbconnection.cursor()

	while searchinginside and len(foundlineobjects) < so.cap:
		try:
			wkid = searchinginside.pop()
		except IndexError:
			wkid = None
			searchinginside = None

		commitcount.increment()
		if commitcount.value % hipparchia.config['MPCOMMITCOUNT'] == 0:
			dbconnection.commit()

		if wkid:
			foundlines = phrasesearch(wkid, activepoll, so, curs)
			for f in foundlines:
				foundlineobjects.append(dblineintolineobject(f))
		try:
			activepoll.remain(len(searchinginside))
		except TypeError:
			pass

	dbconnection.commit()
	curs.close()

	return foundlineobjects


def workonproximitysearch(count, foundlineobjects, searchinginside, activepoll, searchobject):
	"""

	a multiprocessor aware function that hands off bits of a proximity search to multiple searchers

	searchinginside:
		['lt0400', 'lt0022', ...]

	searchobject.termone:
		'rex'

	searchobject.termtwo:
		'patres'

	:param count:
	:param foundlineobjects:
	:param searchinginside:
	:param activepoll:
	:param searchobject:
	:return:
	"""

	so = searchobject

	while searchinginside and count.value <= so.cap:
		try:
			wkid = searchinginside.pop()
		except IndexError:
			wkid = None
			searchinginside = None

		if wkid:
			if so.scope == 'lines':
				foundlines = withinxlines(wkid, so)
			else:
				foundlines = withinxwords(wkid, so)

			count.increment(len(foundlines))
			activepoll.addhits(len(foundlines))

			for f in foundlines:
				foundlineobjects.append(dblineintolineobject(f))
		try:
			activepoll.remain(len(searchinginside))
		except TypeError:
			pass

	return foundlineobjects
