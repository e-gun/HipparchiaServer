# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List

from server.hipparchiaobjects.morphologyobjects import MorphPossibilityObject


class dbAuthor(object):
	"""
	Created out of the DB info, not the IDT or the AUTHTAB
	Initialized straight out of a DB read


	CREATE TABLE public.authors (
	    universalid character(6) COLLATE pg_catalog."default",
	    language character varying(10) COLLATE pg_catalog."default",
	    idxname character varying(128) COLLATE pg_catalog."default",
	    akaname character varying(128) COLLATE pg_catalog."default",
	    shortname character varying(128) COLLATE pg_catalog."default",
	    cleanname character varying(128) COLLATE pg_catalog."default",
	    genres character varying(512) COLLATE pg_catalog."default",
	    recorded_date character varying(64) COLLATE pg_catalog."default",
	    converted_date integer,
	    location character varying(128) COLLATE pg_catalog."default"
	)

	slotting is supposed to be about speed of creation and access + RAM:

		https://stackoverflow.com/questions/472000/usage-of-slots
		https://towardsdatascience.com/understand-slots-in-python-e3081ef5196d

	slotted vs unslotted
	timeit.timeit(lambda: dbAuthor('self', 'universalid', 'language', 'idxname', 'akaname', 'shortname', 'cleanname', 'genres', 'recorded_date', ''), number=10000)
	0.009311130999776651

	timeit.timeit(lambda: dbAuthor('self', 'universalid', 'language', 'idxname', 'akaname', 'shortname', 'cleanname', 'genres', 'recorded_date', ''), number=10000)
	0.0074952109998775995

	vectors and dbLemmaObject are probably where you get the scale that would yield a real difference

	"""

	__slots__ = ('universalid', 'language', 'idxname', 'akaname', 'shortname', 'cleanname',
	            'genres', 'recorded_date', 'converted_date', 'location', 'authornumber',
	            'listofworks', 'name', 'id')

	def __init__(self, universalid, language, idxname, akaname, shortname, cleanname, genres, recorded_date, converted_date, location):

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
		self.listofworks = list()
		self.name = akaname
		self.id = universalid

	def earlier(self, other):
		return self.converted_date < other

	def later(self, other):
		return self.converted_date > other

	def atorearlier(self, other):
		return self.converted_date <= other

	def atorlater(self, other):
		return self.converted_date >= other

	def datefallsbetween(self, minimum, maximum):
		return minimum <= self.converted_date <= maximum

	def floruitis(self, other):
		return self.converted_date == other

	def floruitisnot(self, other):
		return self.converted_date != other

	def addwork(self, work):
		self.listofworks.append(work)

	def listworkids(self):
		return [w.universalid for w in self.listofworks]

	def grabfirstworkobject(self):
		# end up here if there was a workdict[workid] failure and we are hoping to find some workobject via an authorid
		return self.listofworks[0]

	def countwordsinworks(self):
		return sum([w.wordcount for w in self.listofworks if w.wordcount])


class dbOpus(object):
	"""
	Created out of the DB info, not the IDT vel sim
	Initialized straight out of a DB read
	note the efforts to match a simple Opus, but the fit is potentially untidy
	it is always going to be important to know exactly what kind of object you are handling

	CREATE TABLE public.works (
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
		converted_date integer,
		wordcount integer,
		firstline integer,
		lastline integer,
		authentic boolean
	)


	"""

	__slots__ = ('universalid', 'title', 'language', 'publication_info', 'levellabels_00', 'levellabels_01',
	            'levellabels_02', 'levellabels_03', 'levellabels_04', 'levellabels_05', 'workgenre',
	            'transmission', 'worktype', 'provenance', 'recorded_date', 'converted_date', 'wordcount',
	            'authentic', 'worknumber', 'authorid', 'starts', 'ends', 'name', 'length', 'structure', 'availablelevels')

	def __init__(self, universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02,
	             levellabels_03, levellabels_04, levellabels_05, workgenre, transmission, worktype, provenance,
	             recorded_date, converted_date, wordcount, firstline, lastline, authentic):
		self.universalid = universalid
		self.worknumber = universalid[7:]
		self.authorid = universalid[0:6]
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
		self.structure = dict()
		idx = -1
		for label in [levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05]:
			idx += 1
			if label:
				self.structure[idx] = label

		availablelevels = 1
		for level in [self.levellabels_01, self.levellabels_02, self.levellabels_03, self.levellabels_04, self.levellabels_05]:
			if level and level != '':
				availablelevels += 1
		self.availablelevels = availablelevels

	def citation(self):
		if self.universalid[0:2] not in ['in', 'dp', 'ch']:
			cit = list()
			levels = [self.levellabels_00, self.levellabels_01, self.levellabels_02, self.levellabels_03, self.levellabels_04, self.levellabels_05]
			for l in range(0, self.availablelevels):
				cit.append(levels[l])
			cit.reverse()
			cit = ', '.join(cit)
		else:
			cit = '(face,) line'

		return cit

	def earlier(self, other):
		return self.converted_date < other

	def later(self, other):
		return self.converted_date > other

	def datefallsbetween(self, minval, maxval):
		return minval <= self.converted_date <= maxval

	def bcedate(self):
		if self.converted_date:
			# converted_date is a float
			cds = str(self.converted_date)
			if self.converted_date < 1:
				return '{d} BCE'.format(d=cds[1:])
			elif self.converted_date < 1500:
				return '{d} CE'.format(d=cds)
			else:
				return 'date unknown'
		else:
			return 'date unknown'

	def isnotliterary(self):
		"""
		a check to see if you come from something other than 'gr' or 'lt'
		:return:
		"""

		if self.universalid[0:2] in ['in', 'dp', 'ch']:
			return True
		else:
			return False

	def isliterary(self):
		"""
		a check to see if you come from 'gr' or 'lt'
		:return:
		"""

		if self.universalid[0:2] in ['gr', 'lt']:
			return True
		else:
			return False

	def lines(self):
		return set(range(self.starts, self.ends + 1))


class dbMorphologyObject(object):
	"""

	an object that corresponds to a db line

	CREATE TABLE public.latin_morphology
	(
		observed_form             character varying(64),
		xrefs                     character varying(128),
		prefixrefs                character varying(128),
		possible_dictionary_forms jsonb,
		related_headwords         character varying(256)
	)
	WITH (
	  OIDS=FALSE
	);

	hipparchiaDB=# select count(observed_form) from greek_morphology;
	 count
	--------
	 911871
	(1 row)

	hipparchiaDB=# select count(observed_form) from latin_morphology;
	 count
	--------
	 270227
	(1 row)

	possible_dictionary_forms is going to be JSON:
		{'NUMBER': {
				'headword': 'WORD',
				'scansion': 'SCAN',
				'xref_value': 'VAL',
				'xref_kind': 'KIND',
				'transl': 'TRANS',
				'analysis': 'ANAL'
			},
		'NUMBER': {
				'headword': 'WORD',
				'scansion': 'SCAN',
				'xref_value': 'VAL',
				'xref_kind': 'KIND',
				'transl': 'TRANS',
				'analysis': 'ANAL'
			},
		...}

	"""

	__slots__ = ('observed', 'xrefs', 'prefixrefs', 'possibleforms', 'prefixcount', 'xrefcount', 'headwords', 'rewritten')

	def __init__(self, observed: str, xrefs, prefixrefs, possibleforms: dict, headwords: list):
		self.observed = observed
		self.xrefs = xrefs.split(', ')
		self.prefixrefs = [x for x in prefixrefs.split(', ') if x]
		self.possibleforms = possibleforms
		self.prefixcount = len(self.prefixrefs)
		self.xrefcount = len(self.xrefs)
		self.headwords = headwords
		self.rewritten = str()

	def countpossible(self) -> int:
		return len(self.possibleforms)

	def getpossible(self) -> List[MorphPossibilityObject]:
		po = [MorphPossibilityObject(self.observed, p, self.possibleforms[p], self.prefixcount) for p in self.possibleforms]
		return po


class dbLemmaObject(object):
	"""
	an object that corresponds to a db line

	CREATE TABLE public.greek_lemmata (
		dictionary_entry character varying(64) COLLATE pg_catalog."default",
		xref_number integer,
		derivative_forms text COLLATE pg_catalog."default"
	)

	hipparchiaDB=# select count(dictionary_entry) from greek_lemmata;
	 count
	--------
	 114098
	(1 row)

	hipparchiaDB=# select count(dictionary_entry) from latin_lemmata;
	 count
	-------
	 38662
	(1 row)

	"""

	__slots__ = ('dictionaryentry', 'xref', 'formlist')

	def __init__(self, dictionaryentry, xref, derivativeforms):
		self.dictionaryentry = dictionaryentry
		self.xref = xref
		self.formlist = derivativeforms