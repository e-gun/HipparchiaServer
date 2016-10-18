# -*- coding: utf-8 -*-
import re
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

	def __init__(self, universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05, workgenre, transmission, worktype, wordcount, firstline, lastline, authentic):
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
		self.starts = firstline
		self.ends = lastline
		self.authentic = authentic
		self.name = title
		try:
			self.length = lastline - firstline
		except:
			self.length = -1
		self.worknumber = int(universalid[7:])
		self.structure = {}
		idx = -1
		for label in [levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05]:
			idx += 1
			if label != '':
				self.structure[idx] = label
		
		availablelevels = 1
		for level in [self.levellabels_01, self.levellabels_02, self.levellabels_03, self.levellabels_04, self.levellabels_05]:
			if level != '' and level is not None:
				availablelevels += 1
		self.availablelevels = availablelevels
		
	def citation(self):
		cit = []
		levels = [self.levellabels_00, self.levellabels_01, self.levellabels_02, self.levellabels_03, self.levellabels_04, self.levellabels_05]
		for l in range(0,self.availablelevels):
			cit.append(levels[l])
		cit.reverse()
		cit = ', '.join(cit)
		
		return cit
	
			

class dbWorkLine(object):
	"""
	an object that corresponds to a db line
	"""
	
	def __init__(self, wkuinversalid, index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, stripped_line, hyphenated_words, annotations):
		self.wkuinversalid = wkuinversalid
		self.index = index
		self.l5 = level_05_value
		self.l4 = level_04_value
		self.l3 = level_03_value
		self.l2 = level_02_value
		self.l1 = level_01_value
		self.l0 = level_00_value
		self.contents = re.sub(r'\s$', '', marked_up_line)
		self.strippedcontents = re.sub(r'\s$', '', stripped_line)
		self.annotations = annotations
		self.universalid = wkuinversalid+'_LN_'+str(index)

		if self.contents is None:
			self.contents = ''
			self.strippedcontents = ''
		
		hyph = hyphenated_words.split(' ')
		if len(hyph) != 2:
			self.hyphenated = {'accented': '', 'stripped': ''}
		else:
			self.hyphenated = {'accented': hyph[0], 'stripped': hyph[1]}
	
	def locus(self):
		"""
		call me to get a formatted citation
		:param self:
		:return:
		"""
		loc = []
		for lvl in [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5]:
			if str(lvl) != '-1':
				loc.append(lvl)
		loc.reverse()
		citation = '.'.join(loc)
		return citation
	
	
	def locustuple(self):
		"""
		call me to get a citation tuple in 0-to-5 order
		:return:
		"""
		cit = []
		for lvl in [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5]:
			if str(lvl) != '-1':
				cit.append(lvl)
		citationtuple = tuple(cit)
	
		return citationtuple
	
	
	def samelevelas(self, other):
		"""
		are two loci at the same level or have we shifted books, sections, etc?
		the two loci have to be from the same work
		:param self:
		:param other:
		:return:
		"""
		if self.wkuinversalid == other.wkuinversalid and self.l5 == other.l5 and self.l4 == other.l4 and self.l3 == other.l3 and self.l2 == other.l2 and self.l1 == other.l1:
			return True
		else:
			return False
	
	
	def equivalentlevelas(self, other):
		"""
		are two loci at the same level or have we shifted books, sections, etc?
		the two loci do not have to be from the same work
		:param self:
		:param other:
		:return:
		"""
		if self.l5 == other.l5 and self.l4 == other.l4 and self.l3 == other.l3 and self.l2 == other.l2 and self.l1 == other.l1:
			return True
		else:
			return False
	
	
	def toplevel(self):
		top = 0
		for lvl in [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5]:
			if str(lvl) != '-1':
				top += 1
			else:
				return top
			
		# should not need this, but...
		return top
	
	
	def unformattedline(self):
		"""
		remove markup from contents
		:return:
		"""

		unformatted = re.sub(r'(\<.*?\>)',r'',self.contents)
		
		return unformatted


	def lastword(self, version):
		"""
		return the last word of the line:
			lineobject.lastword('contents')
		"""
		lastword = ''
		if version in ['contents', 'strippedcontents']:
			line = getattr(self, version)
			line = line.split(' ')
			lastword = line[-1]
		
		return lastword


class MPCounter(object):
	def __init__(self):
		self.val = Value('i', 0)
	
	def increment(self, n=1):
		with self.val.get_lock():
			self.val.value += n
	
	@property
	def value(self):
		return self.val.value