# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from multiprocessing import Manager, Process

from server import hipparchia
from server.dbsupport.dbfunctions import setthreadcount
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.semanticvectors.vectorhelpers import findsentences


def vectorprepdispatcher(searchobject, activepoll):
	"""

	assign the vector prep to multiprocessing workers
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
	listofitemstosearch = manager.list(so.indexrestrictions.keys())

	workers = setthreadcount()

	targetfunction = breaktextsintosentences
	argumentuple = (foundsentences, listofitemstosearch, activepoll, so)

	jobs = [Process(target=targetfunction, args=argumentuple) for i in range(workers)]

	for j in jobs:
		j.start()
	for j in jobs:
		j.join()

	return list(foundsentences)


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

	dbconnection = ConnectionObject('not_autocommit', readonlyconnection=False)
	cursor = dbconnection.cursor()
	so = searchobject

	while searchlist:
		commitcount += 1
		try:
			authortable = searchlist.pop()
		except IndexError:
			authortable = None

		if authortable:
			foundsentences += findsentences(authortable, so, cursor)

			if commitcount % hipparchia.config['MPCOMMITCOUNT'] == 0:
				dbconnection.commit()

		try:
			activepoll.remain(len(searchlist))
		except TypeError:
			pass

	dbconnection.connectioncleanup()

	return foundsentences


