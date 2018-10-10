# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import pickle
from multiprocessing import JoinableQueue
from multiprocessing.managers import ListProxy
from queue import Empty as QueueEmpty

from server.dbsupport.dblinefunctions import dblineintolineobject
from server.dbsupport.redisdbfunctions import establishredisconnection
from server.hipparchiaobjects.searchobjects import SearchObject


class GenericSearchFunctionObject(object):
	"""

	a class to hold repeated code for the searches

	the chief difference between most search types is the number and names of the parameters passed
	to self.searchfunction

	one also has the option of storing the searchlist either in shared memory or in a redis set
	the retrieval, parrsing, and ending checks for the two structures are different

	handling the matrix of possibilities for search_type and list_type combinations produces the
	somewhat tangled set of options below

	"""
	def __init__(self, foundlineobjects: ListProxy, listofplacestosearch, searchobject: SearchObject, dbconnection, searchfunction):
		self.commitcount = 0
		self.dbconnection = dbconnection
		self.dbcursor = self.dbconnection.cursor()
		self.so = searchobject
		self.foundlineobjects = foundlineobjects
		self.listofplacestosearch = listofplacestosearch
		self.searchfunction = searchfunction
		self.searchfunctionparameters = None
		self.activepoll = self.so.poll
		self.parameterswapper = self.simpleparamswapper
		self.remaindererror = NotImplementedError
		self.emptytest = None
		self.remainder = None

	def getnextfnc(self):
		raise NotImplementedError

	def getremain(self):
		return len(self.remainder)

	def listcleanup(self):
		pass

	def updatepollremaining(self):
		try:
			self.activepoll.remain(self.getremain())
		except self.remaindererror:
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

		:return:
		"""

		insertposition = self.searchfunctionparameters.index('parametertoswap')
		while self.emptytest and self.activepoll.gethits() <= self.so.cap:
			nextitem = self.getnextfnc()
			if nextitem:
				params = self.parameterswapper(nextitem, insertposition)
				foundlines = self.searchfunction(*tuple(params))
				lineobjects = [dblineintolineobject(f) for f in foundlines]
				self.foundlineobjects.extend(lineobjects)
				self.updatepollfinds(lineobjects)
				self.updatepollremaining()
			else:
				# listofplacestosearch has been exhausted
				break

		self.listcleanup()
		# empty return because foundlineobjects is a ListProxy:
		# ask for self.foundlineobjects as the search result instead
		return


class RedisSearchFunctionObject(GenericSearchFunctionObject):
	def __init__(self, foundlineobjects, listofplacestosearch: ListProxy, searchobject, dbconnection, searchfunction):
		super().__init__(foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)
		self.listofplacestosearch = True
		self.rc = establishredisconnection()
		redissearchid = '{id}_searchlist'.format(id=self.so.searchid)
		# lambda this because if you define as self.rc.spop(redissearchid) you will actually pop an item..,
		self.getnetxitem = lambda x: self.rc.spop(redissearchid)
		self.remainder = self.rc.smembers(redissearchid)
		self.emptyerror = AttributeError
		self.remaindererror = AttributeError
		self.emptytest = self.listofplacestosearch

	def getnextfnc(self):
		nextsearchlocation = self.trytogetnext()
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
	def __init__(self, foundlineobjects, listofplacestosearch: ListProxy, searchobject, dbconnection, searchfunction):
		super().__init__(foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)
		self.emptytest = self.listofplacestosearch
		self.getnetxitem = self.listofplacestosearch.pop
		self.remainder = self.listofplacestosearch
		self.emptyerror = IndexError
		self.remaindererror = TypeError

	def getnextfnc(self):
		self.commitcount += 1
		self.dbconnection.checkneedtocommit(self.commitcount)
		try:
			nextsearchlocation = self.getnetxitem(0)
		except self.emptyerror:
			nextsearchlocation = None
		return nextsearchlocation


class QueuedSearchFunctionObject(GenericSearchFunctionObject):
	def __init__(self, foundlineobjects, listofplacestosearch: JoinableQueue, searchobject, dbconnection, searchfunction):
		super().__init__(foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)
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


def returnsearchfncobject(foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction):
		if isinstance(listofplacestosearch, type(JoinableQueue())):
			# print('QueuedSearchFunctionObject')
			return QueuedSearchFunctionObject(foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)
		elif searchobject.redissearchlist:
			# print('RedisSearchFunctionObject')
			return RedisSearchFunctionObject(foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)
		else:
			# print('ManagedListSearchFunctionObject')
			return ManagedListSearchFunctionObject(foundlineobjects, listofplacestosearch, searchobject, dbconnection, searchfunction)
