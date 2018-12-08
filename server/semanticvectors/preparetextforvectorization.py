# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from multiprocessing import Manager, Process

from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.semanticvectors.vectorhelpers import findsentences
from server.threading.mpthreadcount import setthreadcount


def vectorprepdispatcher(searchobject):
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

	connections = {i: ConnectionObject(readonlyconnection=False) for i in range(workers)}

	jobs = [Process(target=targetfunction, args=(foundsentences, listofitemstosearch, so, connections[i]))
			for i in range(workers)]

	for j in jobs:
		j.start()
	for j in jobs:
		j.join()

	for c in connections:
		connections[c].connectioncleanup()

	fs = list(foundsentences)
	return fs


def breaktextsintosentences(foundsentences, searchlist, searchobject, dbconnection):
	"""

	break a text into sentences that contain the term we are looking for

	that is, findsentences() both chunks and searches

	:param foundsentences:
	:param searchlist:
	:param activepoll:
	:param searchobject:
	:return:
	"""

	so = searchobject
	activepoll = so.poll

	dbcursor = dbconnection.cursor()

	commitcount = 0
	while searchlist:
		commitcount += 1
		try:
			authortable = searchlist.pop()
		except IndexError:
			authortable = None

		if authortable:
			foundsentences += findsentences(authortable, so, dbcursor)

			dbconnection.checkneedtocommit(commitcount)

		try:
			activepoll.remain(len(searchlist))
		except TypeError:
			pass

	return foundsentences
