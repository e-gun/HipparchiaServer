# -*- coding: utf-8 -*-
from multiprocessing import Value


class dbAuthor(object):
	"""
	Created out of the DB info, not the IDT or the AUTHTAB
	Initialized straight out of a DB read
	"""

	def __init__(self, universalid, language, idxname, akaname, shortname, cleanname, genres, floruit, location):
		self.universalid = universalid
		self.language = language
		self.idxname = idxname
		self.akaname = akaname
		self.shortname = shortname
		self.cleanname = cleanname
		self.genres = genres
		self.floruit = floruit
		self.location = location
		self.authornumber = universalid[2:]
		self.listofworks = []
		self.name = akaname
		self.id = universalid

	def earlier(self, other):
		return float(self.floruit) < other
	
	def later(self, other):
		return float(self.floruit) > other
	
	def atorearlier(self, other):
		return float(self.floruit) <= other
	
	def atorlater(self, other):
		return float(self.floruit) >= other
	
	def floruitis(self, other):
		return float(self.floruit) == other
	
	def floruitisnot(self, other):
		return float(self.floruit) != other

	def addwork(self, work):
		self.listofworks.append(work)

class dbOpus(object):
	"""
	Created out of the DB info, not the IDT vel sim
	Initialized straight out of a DB read
	note the efforts to match a simple Opus, but the fit is potentially untidy
	it is always going to be importnat to know exactly what kind of object you are handling
	"""

	def __init__(self, universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05, workgenre, transmission, worktype, wordcount, authentic):
		self.universalid = universalid
		self.title = title
		self.language = language
		self.publication_info = publication_info
		self.levellabels_00 = levellabels_00
		self.levellabels_01 = levellabels_01
		self.levellabels_02 = levellabels_02
		self.levellabels_03 = levellabels_03
		self.levellabels_04 = levellabels_04
		self.levellabels_05 = levellabels_05
		self.workgenre = workgenre
		self.transmission = transmission
		self.worktype = worktype
		self.wordcount = wordcount
		self.authentic = authentic
		self.name = title
		self.worknumber = int(universalid[7:])
		self.structure = {}
		idx = -1
		for label in [levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05]:
			idx += 1
			if label != '':
				self.structure[idx] = label


class MPCounter(object):
	def __init__(self):
		self.val = Value('i', 0)
	
	def increment(self, n=1):
		with self.val.get_lock():
			self.val.value += n
	
	@property
	def value(self):
		return self.val.value