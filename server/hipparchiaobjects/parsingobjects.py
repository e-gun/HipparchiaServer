# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server import hipparchia
from server.dbsupport.miscdbfunctions import returnfirstwork
from server.startup import authordict, workdict


class InputParsingObject(object):
	"""

	clean and prep the textmaker or indexmaker query info

	"""
	def __init__(self, authorid, workid=None, searchlocation=None, endpoint=None, delimiter=NotImplemented, objecttype=NotImplemented):
		self.authorid = authorid
		self.workid = workid
		self.searchlocation = searchlocation
		self.endpointlocation = endpoint

		self.delimiter = delimiter
		self.objecttype = objecttype
		self.needsreversal = True
		self.defaulthipparchiadelimeter = '|'

		assert self.delimiter in [None, '.', '|', ':']
		assert self.objecttype in ['text', 'index', 'browser', 'structure']
		assert self.needsreversal in [True, False]

		self.supplementalvalidcitationcharacters = '_|'
		# tempting to exclude ';<>-,.'
		self.totallyunaccepablenomatterwhat = str()
		self.maximuminputlength = hipparchia.config['MAXIMUMLOCUSLENGTH']

		self.authorobject = self._findauthorobject()
		self.workobject = self._findworkobject()
		self.passageaslist = self._findpassagelist(self.searchlocation)
		self.endpointlist = self._findpassagelist(self.endpointlocation)
		# print('self.delimiter', self.delimiter)
		# print('self.passageaslist', self.passageaslist)
		# print('self.endpointlist', self.endpointlist)

	def _findauthorobject(self):
		try:
			return authordict[self.authorid]
		except KeyError:
			return None

	def _findworkobject(self):
		if self.authorobject and self.workid:
			workdb = self.authorobject.universalid + 'w' + self.workid
		elif self.authorobject:
			workdb = returnfirstwork(self.authorobject.universalid)
		else:
			workdb = None

		try:
			return workdict[workdb]
		except KeyError:
			return None

	def _findpassagelist(self, thecitation: str):
		if not thecitation:
			return list()
		else:
			if self.delimiter:
				thecitation = re.sub(re.escape(self.delimiter), self.defaulthipparchiadelimeter, thecitation)
			thecitation = self.reducetovalidcitationcharacters(thecitation)
			citationlist = thecitation.split(self.defaulthipparchiadelimeter)
			if self.needsreversal:
				citationlist.reverse()
			# there are only five levels...
			citationlist = citationlist[:5]
			return citationlist

	def updatepassagelist(self):
		# if you update the supplemental chars you need to call this again to get the non-default values
		self.passageaslist = self._findpassagelist(self.searchlocation)

	def updateenpointlist(self):
		self.endpointlist = self._findpassagelist(self.endpointlocation)

	def hasauthorobject(self):
		if self.authorobject:
			return True
		else:
			return False

	def hasworkobject(self):
		if self.workobject:
			return True
		else:
			return False

	@staticmethod
	def citationcharacterset() -> set:
		"""

		determined via putting the following code into "/testroute"

		# looking for all of the unique chars required to generate all of the citations.

		dbconnection = ConnectionObject()
		cursor = dbconnection.cursor()
		flatten = lambda x: [item for sublist in x for item in sublist]

		authorlist = [a for a in authordict]

		charlist = list()

		count = 0
		for a in authorlist:
			count += 1
			q = 'select level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value from {t}'
			cursor.execute(q.format(t=a))
			f = cursor.fetchall()
			c = set(str().join(flatten(f)))
			charlist.append(c)

		charlist = flatten(charlist)
		charlist = set(charlist)
		charlist = list(charlist)
		charlist.sort()

		print(charlist)
		dbconnection.connectioncleanup()


		:return:

		"""

		# ooh, look at all of those dangerous injectable characters...; fortunately some of them are small variants
		# notice that '.' is a huge problem vis a vis raw citation input

		allusedchars = {' ', ',', '-', '.', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ';', '<', '>', '@',
		                'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R',
		                'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g',
		                'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y',
		                'z', '❨', '❩', '⟦', '⟧', '﹕', '﹖', '﹠', '﹡', '﹢', '﹦', '﹪', '＇', '／'}

		return allusedchars

	def reducetovalidcitationcharacters(self, text: str) -> str:
		"""

		take a string and purge it of any characters that could not potentially be found in a citation

		supplement should be a stinrg (which is a list...): '123!|abc"

		:param text:
		:return:
		"""

		text = text[:self.maximuminputlength]

		validchars = self.citationcharacterset() - set(self.totallyunaccepablenomatterwhat)
		validchars = validchars.union(set(self.supplementalvalidcitationcharacters))
		reduced = [x for x in text if x in validchars]
		restored = str().join(reduced)
		return restored


class TextmakerInputParsingObject(InputParsingObject):
	def __init__(self, authorid, workid=None, location=None, endpoint=None, delimiter='|', objecttype='text'):
		super().__init__(authorid, workid, location, endpoint, delimiter, objecttype)


class IndexmakerInputParsingObject(InputParsingObject):
	def __init__(self, authorid, workid=None, location=None, endpoint=None, delimiter='|', objecttype='index'):
		super().__init__(authorid, workid, location, endpoint, delimiter, objecttype)


class BrowserInputParsingObject(InputParsingObject):
	def __init__(self, authorid, workid=None, location=None, endpoint=None, delimiter='|', objecttype='browser'):
		super().__init__(authorid, workid, location, endpoint, delimiter, objecttype)
		self.supplementalvalidcitationcharacters = '_|,:'
		self.updatepassagelist()


class StructureInputParsingObject(InputParsingObject):
	def __init__(self, authorid, workid=None, location=None, endpoint=None, delimiter='|', objecttype='structure'):
		super().__init__(authorid, workid, location, endpoint, delimiter, objecttype)
		if not location:
			self.searchlocation = 'firstline'
		self.needsreversal = False
		self.updatepassagelist()
		self.citationtuple = tuple(self.passageaslist)