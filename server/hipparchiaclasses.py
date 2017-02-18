# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


import re
from multiprocessing import Value, Array
from server.formatting_helper_functions import attemptelision

class dbAuthor(object):
	"""
	Created out of the DB info, not the IDT or the AUTHTAB
	Initialized straight out of a DB read
	
		
	CREATE TABLE public.authors
	(
    universalid character(6) COLLATE pg_catalog."default",
    language character varying(10) COLLATE pg_catalog."default",
    idxname character varying(128) COLLATE pg_catalog."default",
    akaname character varying(128) COLLATE pg_catalog."default",
    shortname character varying(128) COLLATE pg_catalog."default",
    cleanname character varying(128) COLLATE pg_catalog."default",
    genres character varying(512) COLLATE pg_catalog."default",
    recorded_date character varying(64) COLLATE pg_catalog."default",
    converted_date character varying(8) COLLATE pg_catalog."default",
    location character varying(128) COLLATE pg_catalog."default"
	)
	
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
	
	CREATE TABLE public.works
	(
    universalid character(10) COLLATE pg_catalog."default",
    title character varying(512) COLLATE pg_catalog."default",
    language character varying(10) COLLATE pg_catalog."default",
    publication_info text COLLATE pg_catalog."default",
    levellabels_00 character varying(64) COLLATE pg_catalog."default",
    levellabels_01 character varying(64) COLLATE pg_catalog."default",
    levellabels_02 character varying(64) COLLATE pg_catalog."default",
    levellabels_03 character varying(64) COLLATE pg_catalog."default",
    levellabels_04 character varying(64) COLLATE pg_catalog."default",
    levellabels_05 character varying(64) COLLATE pg_catalog."default",
    workgenre character varying(32) COLLATE pg_catalog."default",
    transmission character varying(32) COLLATE pg_catalog."default",
    worktype character varying(32) COLLATE pg_catalog."default",
    provenance character varying(64) COLLATE pg_catalog."default",
    recorded_date character varying(64) COLLATE pg_catalog."default",
    converted_date character varying(8) COLLATE pg_catalog."default",
    wordcount integer,
    firstline integer,
    lastline integer,
    authentic boolean
	)
	
	
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
	
	CREATE TABLE public.in0207
	(
    index integer NOT NULL DEFAULT nextval('in0207'::regclass),
    wkuniversalid character varying(10) COLLATE pg_catalog."default",
    level_05_value character varying(64) COLLATE pg_catalog."default",
    level_04_value character varying(64) COLLATE pg_catalog."default",
    level_03_value character varying(64) COLLATE pg_catalog."default",
    level_02_value character varying(64) COLLATE pg_catalog."default",
    level_01_value character varying(64) COLLATE pg_catalog."default",
    level_00_value character varying(64) COLLATE pg_catalog."default",
    marked_up_line text COLLATE pg_catalog."default",
    accented_line text COLLATE pg_catalog."default",
    stripped_line text COLLATE pg_catalog."default",
    hyphenated_words character varying(128) COLLATE pg_catalog."default",
    annotations character varying(256) COLLATE pg_catalog."default"
	)
	
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


class dbWordCountObject(object):
	"""
	an object that corresponds to a db line

	CREATE TABLE public."wordcounts_ϲ"
	(
    entry_name character varying(64) COLLATE pg_catalog."default",
    total_count integer,
    gr_count integer,
    lt_count integer,
    dp_count integer,
    in_count integer,
    ch_count integer
	)

	"""

	def __init__(self, entryname, totalcount, greekcount, latincount, docpapcount, inscriptioncount, christiancount):
		self.entryname = entryname
		self.t = totalcount
		self.g = greekcount
		self.l = latincount
		self.d = docpapcount
		self.i = inscriptioncount
		self.c = christiancount
		self.tlabel = 'Ⓣ'
		self.glabel = 'Ⓖ'
		self.llabel = 'Ⓛ'
		self.dlabel = 'Ⓓ'
		self.ilabel = 'Ⓘ'
		self.clabel = 'Ⓒ'

	def getelement(self, element):
		cdict = {
			'total': self.t, 'gr': self.g, 'lt': self.l, 'dp': self.d, 'in': self.i, 'ch': self.c
			}
		try:
			return cdict[element]
		except:
			return 0

	def getlabel(self, element):
		ldict = {
			'total': self.tlabel, 'gr': self.glabel, 'lt': self.llabel, 'dp': self.dlabel, 'in': self.ilabel, 'ch': self.clabel
			}
		try:
			return ldict[element]
		except:
			return ''



class dbHeadwordObject(dbWordCountObject):
	"""
	an extended wordcount object

	CREATE TABLE public.dictionary_headword_wordcounts
	(
    entry_name character varying(64) COLLATE pg_catalog."default",
    total_count integer,
    gr_count integer,
    lt_count integer,
    dp_count integer,
    in_count integer,
    ch_count integer,
    frequency_classification character varying(64) COLLATE pg_catalog."default",
    early_occurrences integer,
    middle_occurrences integer,
    late_occurrences integer
	)

	"""

	greekworderaweights = {'early': 7.883171009462467, 'middle': 1.9249406986576483, 'late': 1}
	corporaweights =  {'gr': 1.0, 'lt': 11.371559943504066, 'in': 28.130258550554572, 'dp': 27.492143340147255, 'ch': 129.8977636244065}

	# into one dict so we can pass it to __init__
	wts = {'gkera': greekworderaweights, 'corp': corporaweights}

	def __init__(self, entryname, totalcount, greekcount, latincount, docpapcount, inscriptioncount, christiancount,
	             frqclass, early, middle, late, weights=wts):

		# see note in lexicallookups.py for deriving these weight numbers
		self.frqclass = frqclass
		self.early = early
		self.middle = middle
		self.late = late
		try:
			self.wtdgkearly = self.early * weights['gkera']['early']
			self.wtdgkmiddle = self.middle * weights['gkera']['middle']
			self.wtdgklate = self.late * weights['gkera']['late']
			# use our weighted values to determine its relative time balance
			self.predomera = max(self.wtdgkearly, self.wtdgkmiddle, self.wtdgklate)
		except:
			# no date info is available for this (Latin) word
			self.wtdgkearly, self.wtdgkmiddle, self.wtdgklate, self.predomera = -1, -1, -1, -1
		self.qlabel = 'ⓠ'
		self.elabel = 'ⓔ'
		self.mlabel = 'ⓜ'
		self.latelabel = 'ⓛ'
		self.unklabel = 'ⓤ'
		super().__init__(entryname, totalcount, greekcount, latincount, docpapcount, inscriptioncount, christiancount)
		# can't do this until self.g, etc exist owing to a call to super()
		self.wtdgr = self.g * weights['corp']['gr']
		self.wtdlt = self.l * weights['corp']['lt']
		self.wtdin = self.i * weights['corp']['in']
		self.wtddp = self.d * weights['corp']['dp']
		self.wtdch = self.c * weights['corp']['ch']
		self.predomcorp = max(self.wtdgr, self.wtdlt, self.wtdin, self.wtddp, self.wtdch)

	def gettime(self, element):
		elements = {'early': self.early, 'middle': self.middle, 'late': self.late ,
		            'unk': self.t - (self.early + self.middle + self.late)
		            }
		try:
			return elements[element]
		except:
			return 0

	def getweightedtime(self, element):
		elements = {'early': (self.wtdgkearly/self.predomera)*100, 'middle': (self.wtdgkmiddle/self.predomera)*100, 'late': (self.wtdgklate/self.predomera)*100
		            }
		if self.predomera != -1:
			try:
				return elements[element]
			except:
				return 0
		else:
			return None

	def getweightedcorpora(self, element):
		elements = {'gr': (self.wtdgr/self.predomcorp)*100, 'lt': (self.wtdlt/self.predomcorp)*100, 'in': (self.wtdin/self.predomcorp)*100,
		            'dp': (self.wtddp / self.predomcorp) * 100, 'ch': (self.wtdch/self.predomcorp)*100,
		            }
		try:
			return elements[element]
		except:
			return 0

	def gettimelabel(self, element):
		elements = {'early': self.elabel, 'middle': self.mlabel, 'late': self.latelabel, 'unk': self.unklabel,
		            'frq': self.frqclass
		            }
		try:
			return elements[element]
		except:
			return 0


class dbMorphologyObject(object):
	"""

	an object that corresponds to a db line

	CREATE TABLE public.greek_morphology
	(
    observed_form character varying(64) COLLATE pg_catalog."default",
    xrefs character varying(128) COLLATE pg_catalog."default",
    prefixrefs character varying(128) COLLATE pg_catalog."default",
    possible_dictionary_forms text COLLATE pg_catalog."default"
	)

	"""

	def __init__(self, observed, xrefs, prefixrefs, possibleforms):
		self.observed = observed
		self.xrefs = xrefs.split(', ')
		self.prefixrefs = [x for x in prefixrefs.split(', ') if x]
		self.possibleforms = possibleforms
		self.prefixcount = len(self.prefixrefs)
		self.xrefcount = len(self.xrefs)

	def countpossible(self):
		possiblefinder = re.compile(r'(<possibility_(\d{1,2})>)(.*?)<xref_value>(.*?)</xref_value><xref_kind>(.*?)</xref_kind>(.*?)</possibility_\d{1,2}>')
		thepossible = re.findall(possiblefinder,self.possibleforms)
		return len(thepossible)

	def getpossible(self):
		possiblefinder = re.compile(r'(<possibility_(\d{1,2})>)(.*?)<xref_value>(.*?)</xref_value><xref_kind>(.*?)</xref_kind>(.*?)</possibility_\d{1,2}>')
		thepossible = re.findall(possiblefinder,self.possibleforms)
		listofpossibilitiesobjects = [MorphPossibilityObject(p, self.prefixcount) for p in thepossible]
		return listofpossibilitiesobjects


class MorphPossibilityObject(object):
	"""

	the embedded morphological possibilities

	"""

	def __init__(self, findalltuple, prefixcount):
		self.number = findalltuple[1]
		self.entry = findalltuple[2]
		self.xref = findalltuple[3]
		self.xkind = findalltuple[4]
		self.transandanal = findalltuple[5]
		self.prefixcount = prefixcount

	def gettranslation(self):
		transfinder = re.compile(r'<transl>(.*?)</transl>')
		trans = re.findall(transfinder, self.transandanal)
		return ('; ').join(trans)

	def getanalysislist(self):
		analysisfinder = re.compile(r'<analysis>(.*?)</analysis>')
		analysislist = re.findall(analysisfinder, self.transandanal)
		return analysislist

	def getbaseform(self):
		"""
		the tricky bit:

		some are quite easy: 'ἐπώνυμοϲ'
		others are compounds with a ', ' separation

		there is a HUGE PROBLEM in the original data here:
		   [a] 'ὑπό, ἐκ-ἀράω²': what comes before the comma is a prefix to the verb
		   [b] 'ἠχούϲαϲ, ἠχέω': what comes before the comma is an observed form of the verb
		when you .split() what do you have at wordandform[0]?

		you have to look at the full db entry for the word:
		the number of items in prefixrefs corresponds to the number of prefix checks you will need to make to recompose the verb

		:return:
		"""

		# need an aspiration check; incl εκ -⟩ εξ

		baseform = ''
		segments = self.entry.split(', ')

		if len(segments) == 1 and '-' not in segments[-1]:
			# [a] the simplest case where what you see is what you should seek: 'ἐπώνυμοϲ'
			baseform = segments[-1]
		elif len(segments) == 2 and '-' not in segments[-1] and self.prefixcount == 0:
			# [b] a compound case, but it does not involve prefixes just morphology: 'ἠχούϲαϲ, ἠχέω'
			baseform = segments[-1]
		elif len(segments) == 1 and '-' in segments[-1]:
			# [c] the simplest version of a prefix: ἐκ-ϲύρω
			baseform = attemptelision(segments[-1])
		elif len(segments) == 2 and '-' in segments[-1] and self.prefixcount == 1:
			# [d] more info, but we do not need it: ἐκϲύρωμεν, ἐκ-ϲύρω
			baseform = attemptelision(segments[-1])
		elif len(segments) > 1 and '-' in segments[-1] and self.prefixcount > 1:
			# [e] all bets are off: ὑπό,κατά,ἐκ-λάω
			# print('segments',segments)
			for i in range(self.prefixcount-2,-1, -1):
				print('i=',i)
				baseform = attemptelision(segments[-1])
				baseform = segments[i]+'-'+baseform
				# print('getbaseform() baseform',baseform)
		else:
			print('getbaseform() is confused',self.entry, segments)

		return baseform

# currenly unused in HServer; used in HBuilder

class dbLemmaObject(object):
	"""
	an object that corresponds to a db line

	CREATE TABLE public.greek_lemmata
	(
    dictionary_entry character varying(64) COLLATE pg_catalog."default",
    xref_number integer,
    derivative_forms text COLLATE pg_catalog."default"
	)

	"""

	def __init__(self, dictionaryentry, xref, derivativeforms):
		self.dictionaryentry = dictionaryentry
		self.xref = xref
		self.formandidentificationlist = [f for f in derivativeforms.split('\t') if f]
		self.formlist = [f.split(' ')[0] for f in self.formandidentificationlist]
		self.formlist = [re.sub(r'\'','',f) for f in self.formlist]

	def getformdict(self):
		fd = {}
		for f in self.formandidentificationlist:
			key = f.split(' ')[0]
			body = f[len(key)+1:]
			fd[key] = body
		return fd
