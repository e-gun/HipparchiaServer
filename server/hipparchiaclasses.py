# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import re
from multiprocessing import Value, Array


class dbAuthor(object):
	"""
	Created out of the DB info, not the IDT or the AUTHTAB
	Initialized straight out of a DB read
	"""

	def __init__(self, universalid, language, idxname, akaname, shortname, cleanname, genres, recorded_date,
				 converted_date, location):

		self.universalid = universalid
		self.language = language
		self.idxname = idxname
		self.akaname = akaname
		self.shortname = shortname
		self.cleanname = cleanname
		self.genres = genres
		self.recorded_date = recorded_date
		self.converted_date = converted_date
		self.location = location
		self.authornumber = universalid[2:]
		self.listofworks = []
		self.name = akaname
		self.id = universalid

	def earlier(self, other):
		return float(self.converted_date) < other

	def later(self, other):
		return float(self.converted_date) > other

	def atorearlier(self, other):
		return float(self.converted_date) <= other

	def atorlater(self, other):
		return float(self.converted_date) >= other

	def floruitis(self, other):
		return float(self.converted_date) == other

	def floruitisnot(self, other):
		return float(self.converted_date) != other

	def addwork(self, work):
		self.listofworks.append(work)

	def listworkids(self):
		workids = []
		for w in self.listofworks:
			workids.append(w.universalid)

		return workids


class dbOpus(object):
	"""
	Created out of the DB info, not the IDT vel sim
	Initialized straight out of a DB read
	note the efforts to match a simple Opus, but the fit is potentially untidy
	it is always going to be important to know exactly what kind of object you are handling
	"""

	def __init__(self, universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02,
				 levellabels_03, levellabels_04, levellabels_05, workgenre, transmission, worktype, provenance,
				 recorded_date, converted_date, wordcount, firstline, lastline, authentic):
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
		self.provenance = provenance
		self.recorded_date = recorded_date
		self.converted_date = converted_date
		self.wordcount = wordcount
		self.starts = firstline
		self.ends = lastline
		self.authentic = authentic
		self.name = title
		try:
			self.length = lastline - firstline
		except:
			self.length = -1
		#self.worknumber = int(universalid[7:])
		# con't use int() any longer because ins and ddp numbers count via hex
		self.worknumber = universalid[7:]
		self.structure = {}
		idx = -1
		for label in [levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05]:
			idx += 1
			if label != '' and label != None:
				self.structure[idx] = label
		
		availablelevels = 1
		for level in [self.levellabels_01, self.levellabels_02, self.levellabels_03, self.levellabels_04, self.levellabels_05]:
			if level != '' and level is not None:
				availablelevels += 1
		self.availablelevels = availablelevels
		
	def citation(self):
		if self.universalid[0:2] not in ['in', 'dp', 'ch']:
			cit = []
			levels = [self.levellabels_00, self.levellabels_01, self.levellabels_02, self.levellabels_03,
					  self.levellabels_04, self.levellabels_05]
			for l in range(0,self.availablelevels):
				cit.append(levels[l])
			cit.reverse()
			cit = ', '.join(cit)
		else:
			cit = '(face,) line'
		
		return cit

	def earlier(self, other):
		return float(self.converted_date) < other

	def later(self, other):
		return float(self.converted_date) > other

			
class dbWorkLine(object):
	"""
	an object that corresponds to a db line
	"""
	
	def __init__(self, wkuinversalid, index, level_05_value, level_04_value, level_03_value, level_02_value,
				 level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words,
				 annotations):

		self.wkuinversalid = wkuinversalid[:10]
		self.index = index
		self.l5 = level_05_value
		self.l4 = level_04_value
		self.l3 = level_03_value
		self.l2 = level_02_value
		self.l1 = level_01_value
		self.l0 = level_00_value
		self.accented = marked_up_line
		self.polytonic = accented_line
		self.stripped = stripped_line
		self.annotations = annotations
		self.universalid = self.wkuinversalid+'_LN_'+str(index)
		self.hyphenated = hyphenated_words
		if len(self.hyphenated) > 1:
			self.hashyphenated = True
		else:
			self.hashyphenated = False
		
		if self.accented is None:
			self.accented = ''
			self.stripped = ''
	
	def locus(self):
		"""
		call me to get a formatted citation: "3.2.1"
		:param self:
		:return:
		"""
		loc = []

		if self.wkuinversalid[0:2] not in ['in', 'dp', 'ch']:
			for lvl in [self.l0, self.l1, self.l2, self.l3, self.l4, self.l5]:
				if str(lvl) != '-1':
					loc.append(lvl)
			loc.reverse()
			citation = '.'.join(loc)
		else:
			# papyrus and inscriptions are wonky: usually they have just a recto, but sometimes they have something else
			# only mark the 'something else' version
			if self.l1 != 'recto':
				citation = self.l1 + ' ' + self.l0
			else:
				citation = self.l0
		
		return citation
	
	
	def shortlocus(self):
		"""
		try to get a short citation that drops the lvl0 info: "3.2"
		useful for tagging level shifts without constantly seeling 'line 1'
		:return:
		"""
		loc = []
		for lvl in [self.l1, self.l2, self.l3, self.l4, self.l5]:
			if str(lvl) != '-1' and (self.wkuinversalid[0:2] not in ['in','dp', 'ch'] and lvl != 'recto'):
				loc.append(lvl)
		loc.reverse()
		if loc == []:
			citation = self.locus()
		else:
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

		markup = re.compile(r'(\<.*?\>)')
		nbsp = re.compile(r'&nbsp;')
		
		unformatted = re.sub(markup, r'', self.accented)
		unformatted = re.sub(nbsp, r'', unformatted)
		
		return unformatted


	def showlinehtml(self):
		"""

		make HTML of marked up line visible

		:return:
		"""

		markup = re.compile(r'(\<)(.*?)(\>)')
		left = '<smallcode>&lt;'
		right = '&gt;</smallcode>'

		visiblehtml = re.sub(markup,left+r'\2'+right,self.accented)

		return visiblehtml

	def wordcount(self):
		"""
		return a wordcount
		"""
		
		line = self.stripped
		words = line.split(' ')
		
		return len(words)


	def wordlist(self, version):
		"""
		return a list of words in the line; will include the full version of a hyphenated last word
		:param version:
		:return:
		"""
		wordlist = []
		
		if version in ['polytonic', 'stripped']:
			line = getattr(self, version)
			# Non-breaking space needs to go
			line = re.sub(r'\xa0', ' ', line)
			wordlist = line.split(' ')
			wordlist = [w for w in wordlist if w]
		
		return wordlist
	

	def allbutlastword(self, version):
		"""
		return the line less its final word
		"""
		allbutlastword = ''
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			line = line.split(' ')
			allbutlast= line[:-1]
			allbutlastword = ' '.join(allbutlast)
		
		return allbutlastword
	
	
	def allbutfirstword(self, version):
		"""
		return the line less its first word
		"""
		allbutfirstword = ''
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			if version == 'accented':
				line = re.sub(r'(\<.*?\>)', r'', line)
			line = line.split(' ')
			allbutfirst = line[1:]
			allbutfirstword = ' '.join(allbutfirst)
		
		return allbutfirstword
	
	
	def allbutfirstandlastword(self, version):
		"""
		terun the line lest the first and last words (presumably both are hypenated)
		:param version:
		:return:
		"""
		allbutfirstandlastword = ''
		if version in ['accented', 'stripped']:
			line = getattr(self, version)
			if version == 'accented':
				line = re.sub(r'(\<.*?\>)', r'', line)
			line = line.split(' ')
			middle = line[1:-1]
			allbutfirstandlastword = ' '.join(middle)

		return allbutfirstandlastword


class MPCounter(object):
	"""
	a counter that is mp safe
	"""
	def __init__(self):
		self.val = Value('i', 0)
	
	def increment(self, n=1):
		with self.val.get_lock():
			self.val.value += n
	
	@property
	def value(self):
		return self.val.value
	
	
class ProgressPoll(object):
	"""
	
	a dictionary of Values that can be shared between processes
	the items and their methods build a polling package for progress reporting
	
	general scheme:
		create the object
		set up some shareable variables
		hand them to the search functions
		report on their fate
		delete when done
	
	locking checks mostly unimportant: not esp worried about race conditions; most of this is simple fyi
	"""
	def __init__(self, timestamp):
		self.pd = {}
		self.searchid = str(timestamp)
		self.socket = 0
		
		self.pd['active'] = Value('b', False)
		self.pd['remaining'] = Value('i', -1)
		self.pd['poolofwork'] = Value('i', -1)
		self.pd['statusmessage'] = Array('c', b'')
		self.pd['hits'] = MPCounter()
		self.pd['hits'].increment(-1)
		
	def getstatus(self):
		return self.pd['statusmessage'].decode('utf-8')
	
	
	def getremaining(self):
		return self.pd['remaining'].value
	
	
	def gethits(self):
		return self.pd['hits'].value
	
	
	def worktotal(self):
		return self.pd['poolofwork'].value
	
	
	def statusis(self, statusmessage):
		self.pd['statusmessage'] = bytes(statusmessage, encoding='UTF-8')
	
	
	def allworkis(self, amount):
		self.pd['poolofwork'].value = amount
	
	
	def remain(self, remaining):
		with self.pd['remaining'].get_lock():
			self.pd['remaining'].value = remaining
	
			
	def sethits(self, found):
		self.pd['hits'].val.value = found
		
		
	def addhits(self, hits):
		self.pd['hits'].increment(hits)


	def activate(self):
		self.pd['active'] = True

	
	def deactivate(self):
		self.pd['active'] = False
	

	def getactivity(self):
		return self.pd['active']


class FormattedSearchResult(object):
	def __init__(self, hitnumber, author, work, citationstring, clickurl, formattedlines):
		self.hitnumber = hitnumber
		self.author = author
		self.work = work
		self.citationstring = citationstring
		self.clickurl = clickurl
		self.formattedlines = formattedlines




