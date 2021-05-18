# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import pickle
from multiprocessing import JoinableQueue
from multiprocessing.managers import ListProxy
from queue import Empty as QueueEmpty

from server.dbsupport.dblinefunctions import dblineintolineobject
from server.dbsupport.redisdbfunctions import establishredisconnection
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.searchobjects import SearchObject


class GenericSearchFunctionObject(object):
	"""

	a class to hold repeated code for the searches

	the chief difference between most search types is the number and names of the parameters passed
	to self.searchfunction

	one also has the option of storing the searchlist either in shared memory or in a redis set
	the retrieval, parsing, and ending checks for the two structures are different

	handling the matrix of possibilities for search_type and list_type combinations produces the
	somewhat tangled set of options below

	"""
	def __init__(self, workerid, foundlineobjects: ListProxy, listofplacestosearch, searchobject: SearchObject, dbconnection, searchfunction):
		self.workerid = workerid
		self.commitcount = 0
		if dbconnection:
			self.dbconnection = dbconnection
			self.needconnectioncleanup = False
		else:
			# you are running Windows and can't pickle your connections
			self.dbconnection = ConnectionObject()
			self.needconnectioncleanup = True
		self.dbcursor = self.dbconnection.cursor()
		self.so = searchobject
		self.foundlineobjects = foundlineobjects
		self.listofplacestosearch = listofplacestosearch
		self.searchfunction = searchfunction
		self.searchfunctionparameters = None
		self.activepoll = self.so.poll
		self.parameterswapper = self.simpleparamswapper
		self.emptytest = self.listofplacestosearch
		try:
			self.getnetxitem = self.listofplacestosearch.pop
		except AttributeError:
			# this should get implemented momentarily after this GenericObject has been initialized
			self.getnetxitem = NotImplementedError
		self.remainder = self.listofplacestosearch
		self.emptyerror = IndexError
		self.remaindererror = TypeError

	def authorsamongthefinds(self) -> set:
		authorset = {f.authorid for f in self.foundlineobjects}
		return authorset

	def getnextfnc(self):
		self.commitcount += 1
		self.dbconnection.checkneedtocommit(self.commitcount)
		try:
			nextsearchlocation = self.getnetxitem(0)
		except self.emptyerror:
			nextsearchlocation = None
		return nextsearchlocation

	def getremain(self):
		return len(self.remainder)

	def listcleanup(self):
		pass

	def addnewfindstolistoffinds(self, newfinds: list):
		self.foundlineobjects.extend(newfinds)
		# nf = ', '.join([f.universalid for f in newfinds])
		# print('{c} {u}\tadded\t{ln}'.format(c=self.workerid, u=self.dbconnection.uniquename, ln=nf))

	def updatepollremaining(self):
		try:
			self.activepoll.remain(self.getremain())
		except self.remaindererror:
			self.activepoll.setnotes('Number remaining unavailable: % complete will be inaccurate')
			pass

	def updatepollfinds(self, lines: list):
		if lines:
			numberoffinds = len(lines)
			self.activepoll.addhits(numberoffinds)
		return

	def simpleparamswapper(self, texttoinsert: str, insertposition: int) -> list:
		"""

		the various searchfunctions have different interfaces

		this lets you get the right collection of paramaters into the various functions

		:param texttoinsert:
		:param insertposition:
		:return:
		"""
		parameters = self.searchfunctionparameters
		parameters[insertposition] = texttoinsert
		return parameters

	def tupleparamswapper(self, tupletoinsert: tuple, insertposition: int) -> list:
		"""

		somewhat brittle, but...

		this handles the non-standard case of a tuple that needs swapping instead of an individual name
		(i.e., it works with the lemmatized search)

		:param tupletoinsert:
		:param insertposition:
		:return:
		"""
		if self.so.redissearchlist:
			tupletoinsert = pickle.loads(tupletoinsert)

		parameters = self.searchfunctionparameters
		head = parameters[:insertposition]
		tail = parameters[insertposition+1:]
		newparams = head + list(tupletoinsert) + tail
		return newparams

	def iteratethroughsearchlist(self):
		"""

		this is the simple core of the whole thing; the rest is about feeding it properly

		if you do not pickle the lineobjects here and now you will need to generate line objects at the other end
			foundlineobjects = [dblineintolineobject(item) for item in founddblineobjects]

		you will also need to use lo.decompose() in phrasesearching.py to feed the findslist

		:return:
		"""

		insertposition = self.searchfunctionparameters.index('parametertoswap')
		while self.emptytest and self.activepoll.gethits() <= self.so.cap:
			srchfunct = self.searchfunction
			nextitem = self.getnextfnc()
			if self.so.session['onehit']:
				# simplelemma chunk might have already searched and found in an author
				if self.so.lemma or self.so.proximatelemma:
					# nextitem looks like '(chunk, item)'
					if nextitem[1] in self.authorsamongthefinds():
						srchfunct = None

			if nextitem and srchfunct:
				params = self.parameterswapper(nextitem, insertposition)
				foundlines = srchfunct(*tuple(params))
				lineobjects = [dblineintolineobject(f) for f in foundlines]
				self.addnewfindstolistoffinds(lineobjects)
				self.updatepollfinds(lineobjects)
				self.updatepollremaining()
			elif not srchfunct:
				pass
			else:
				# listofplacestosearch has been exhausted
				break

		self.listcleanup()

		if self.needconnectioncleanup:
			self.dbconnection.connectioncleanup()

		# empty return because foundlineobjects is a ListProxy:
		# ask for self.foundlineobjects as the search result instead
		# print('{i} finished'.format(i=self.workerid))
		return


class RedisSearchFunctionObject(GenericSearchFunctionObject):
	""""

	use redis to store the results

	this is part of a long-term bug-hunt re. failures to exit from the searches; but it might make some sort of
	sense for other reasons

	using redis to store the searchlist seems only to slow you down and this slowdown itself is a "fix",
	but not a very interesting one

	"""
	def __init__(self, workerid, foundlineobjects, listofplacestosearch: ListProxy, searchobject, dbconnection, searchfunction):
		super().__init__(workerid, foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)
		self.rc = establishredisconnection()
		self.redissearchid = '{id}_searchlist'.format(id=self.so.searchid)
		self.redisfindsid = '{id}_findslist'.format(id=self.so.searchid)
		if searchobject.redissearchlist:
			self.listofplacestosearch = True
			# lambda this because if you define as self.rc.spop(redissearchid) you will actually pop an item..,
			self.getnetxitem = lambda x: self.rc.spop(self.redissearchid)
			self.getnextfnc = self.redisgetnextfnc
			self.getremain = self._redisgetremain
			self.emptyerror = AttributeError
			self.remaindererror = AttributeError
			self.emptytest = self.listofplacestosearch

	def __del__(self):
		self.rc.delete(self.redissearchid)

	def addnewfindstolistoffinds(self, newfinds: list):
		finds = [pickle.dumps(f) for f in newfinds]
		for f in finds:
			self.rc.rpush(self.redisfindsid, f)

	def _redisgetremain(self):
		return len(self.rc.smembers(self.redissearchid))

	def redisgetnextfnc(self):
		self.commitcount += 1
		self.dbconnection.checkneedtocommit(self.commitcount)
		try:
			nextsearchlocation = self.getnetxitem(0)
		except self.emptyerror:
			nextsearchlocation = None

		try:
			# redis sends bytes; we need strings
			nextsearchlocation = nextsearchlocation.decode()
		except AttributeError:
			# next = None...
			pass
		except UnicodeDecodeError:
			# next = None...
			pass
		return nextsearchlocation


class ManagedListSearchFunctionObject(GenericSearchFunctionObject):
	def __init__(self, workerid, foundlineobjects: ListProxy, listofplacestosearch: ListProxy, searchobject, dbconnection, searchfunction):
		super().__init__(workerid, foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)


class QueuedSearchFunctionObject(GenericSearchFunctionObject):
	"""

	DISABLED / UNREACHABLE

	for searchlists this is not really better or more interesting than the ListProxy that a ManagedListSearchFunctionObject has

	meanwhile implementing a Queue for results was not immediately fun or obvious or obviously going to help

	need the following in "dynamicsqlsearchdispatching.py" to turn this on:

		# experiment with JoinableQueue
		# https://docs.python.org/3.7/library/multiprocessing.html#multiprocessing.JoinableQueue
		# https://pymotw.com/2/multiprocessing/communication.html

		if so.usequeue:
			listofplacestosearch = loadsearchqueue(so.indexrestrictions.keys(), workers)

	"""
	def __init__(self, workerid, foundlineobjects, listofplacestosearch: ListProxy, searchobject, dbconnection, searchfunction):
		super().__init__(workerid, foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)
		self.getnetxitem = self.listofplacestosearch.get
		self.emptyerror = QueueEmpty
		self.remainder = None
		self.remaindererror = NotImplementedError
		self.emptytest = not self.listofplacestosearch.empty()

	def listcleanup(self):
		# flush the contents: necessary if you hit the cap and items are still in the queue
		# but if there are no items, then don't try to '.get()'

		if self.activepoll.gethits() >= self.so.cap:
			lastitem = False
			while not lastitem:
				lastitem = not(self.getnextfnc())

	def getnextfnc(self):
		self.commitcount += 1
		self.dbconnection.checkneedtocommit(self.commitcount)
		nextsearchlocation = self.getnetxitem()
		self.listofplacestosearch.task_done()
		return nextsearchlocation

	def getremain(self):
		return self.listofplacestosearch.qsize()


def returnsearchfncobject(workerid, foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction):
		if isinstance(listofplacestosearch, type(JoinableQueue())):
			return QueuedSearchFunctionObject(workerid, foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)
		elif searchobject.redisresultlist:
			return RedisSearchFunctionObject(workerid, foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)
		else:
			return ManagedListSearchFunctionObject(workerid, foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)
