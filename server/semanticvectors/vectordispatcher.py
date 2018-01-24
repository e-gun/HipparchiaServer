# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from multiprocessing import Manager, Process

from server import hipparchia
from server.dbsupport.dbfunctions import setconnection, setthreadcount
from server.hipparchiaobjects.helperobjects import MPCounter
from server.semanticvectors.vectorhelpers import findsentences
from server.textsandindices.indexmaker import mpmorphology


def vectordispatching(searchobject, activepoll):
	"""

	assign the vectorization to multiprocessing workers
		searchobject:
			<server.hipparchiaclasses.SearchObject object at 0x1102c15f8>
		activepoll:
			<server.hipparchiaclasses.ProgressPoll object at 0x1102c15f8>


	:param searchobject:
	:param activepoll:
	:return:
	"""

	so = searchobject

	manager = Manager()
	foundsentences = manager.list()
	searchlist = manager.list(so.indexrestrictions.keys())

	workers = setthreadcount()

	targetfunction = breaktextsintosentences
	argumentuple = (foundsentences, searchlist, activepoll, so)

	jobs = [Process(target=targetfunction, args=argumentuple) for i in range(workers)]

	for j in jobs:
		j.start()
	for j in jobs:
		j.join()

	return list(foundsentences)


def findheadwords(wordlist, activepoll):
	"""

	return a dict of morpholog objects

	:param wordlist:
	:param activepoll:
	:return:
	"""

	manager = Manager()
	commitcount = MPCounter()
	terms = manager.list(wordlist)
	morphobjects = manager.dict()
	workers = setthreadcount()

	targetfunction = mpmorphology
	argumentuple = (terms, morphobjects, commitcount)

	jobs = [Process(target=targetfunction, args=argumentuple) for i in range(workers)]

	for j in jobs:
		j.start()
	for j in jobs:
		j.join()

	return morphobjects


def breaktextsintosentences(foundsentences, searchlist, activepoll, searchobject):
	"""

	break a text into sentences that contain the term we are looking for

	that is, findsentences() both chunks and searches

	:param foundsentences:
	:param searchlist:
	:param activepoll:
	:param searchobject:
	:return:
	"""

	commitcount = 0

	dbconnection = setconnection('not_autocommit', readonlyconnection=False)
	curs = dbconnection.cursor()
	so = searchobject

	while searchlist:
		commitcount += 1
		try:
			authortable = searchlist.pop()
		except IndexError:
			authortable = None

		if authortable:
			foundsentences += findsentences(authortable, so, curs)

			if commitcount % hipparchia.config['MPCOMMITCOUNT'] == 0:
				dbconnection.commit()

		try:
			activepoll.remain(len(searchlist))
		except TypeError:
			pass

	dbconnection.commit()
	curs.close()

	return foundsentences


