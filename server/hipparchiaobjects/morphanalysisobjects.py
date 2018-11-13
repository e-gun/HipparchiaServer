# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List

from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.dbsupport.lexicaldbfunctions import grablemmataobjectfor, lookformorphologymatches

"""

IN PROGRESS

select * from latin_lemmata where dictonary_entry='laudo';

then, from that set you want to grab:
	first-person singular present active indicative
	present active infinitive
	first-person singular perfect active indicative
	perfect passive participle


select * from latin_morphology where latin_morphology.observed_form='laudo';
	<analysis>pres ind act 1st sg</analysis>

select * from latin_morphology where latin_morphology.observed_form='laudare';
	<analysis>pres inf act</analysis>

select * from latin_morphology where latin_morphology.observed_form='laudaui';
	<analysis>perf ind act 1st sg</analysis>

select * from latin_morphology where latin_morphology.observed_form='laudatus';
	<analysis>perf part pass masc nom sg</analysis>


select * from greek_lemmata where greek_lemmata.dictionary_entry='παιδεύω';

then, from that set you want to grab:
	[a] first-person singular present active indicative
	[b] first-person singular future active indicative
	[c] first-person singular aorist active indicative
	[d] first-person singular perfect active indicative
	[e] first-person singular perfect middle/passive
	[f] first-person singular aorist passive indicative

if you iterate through the set, you are looking for:
	[a] [select * from greek_morphology where greek_morphology.observed_form='παιδεύω';]
		<analysis>pres ind act 1st sg (epic)</analysis>
	[b] [select * from greek_morphology where greek_morphology.observed_form='παιδεύϲω';]
		<analysis>fut ind act 1st sg</analysis>
	[c] [select * from greek_morphology where greek_morphology.observed_form='ἐπαίδευϲα';]
		<analysis>aor ind act 1st sg</analysis>
	[d] [select * from greek_morphology where greek_morphology.observed_form='πεπαίδευκα';]
		<analysis>perf ind act 1st sg</analysis>
	[e] [select * from greek_morphology where greek_morphology.observed_form='πεπαίδευμαι';]
		<analysis>perf ind mp 1st sg</analysis>
	[f] [select * from greek_morphology where greek_morphology.observed_form='ἐπαιδεύθην';]
		<analysis>aor ind pass 1st sg</analysis>

	[if a forms never occurs, what do we do?][how to look for future indicatives of a form...]
	[select * from greek_morphology where greek_morphology.xrefs='83362071' and possible_dictionary_forms ~ '<analysis>fut ind act';]
	[but if you just grabbed all of the xrefs='83362071' you could sift them quickly

"""


class BaseFormMorphology(object):
	"""

	this only works for words that are dictionary headwords

	select * from greek_morphology where greek_morphology.xrefs='83362071'

	POS is tricky via the database:

		hipparchiaDB=# select pos from latin_dictionary where entry_name='brevis';
		     pos
		-------------
		 adv. ‖ adj.
		(1 row)

		hipparchiaDB=# select pos from latin_dictionary where entry_name='laudo';
		     pos
		--------------
		 v. a. ‖ adv.
		(1 row)

	"""
	def __init__(self, headword: str, language: str):
		assert language in ['greek', 'latin'], 'BaseFormMorphology() only knows words that are "greek_morphology" or "latin_morphology"'
		self.headword = headword
		self.language = language
		self.lemmata = grablemmataobjectfor(headword, '{lg}_lemmata'.format(lg=self.language), dbcursor=None)
		self.dictionaryentry = self.lemmata.dictionaryentry
		self.formlist = self.lemmata.formlist
		c = ConnectionObject()
		self.dbmorphobjects = [lookformorphologymatches(f, c.curs) for f in self.formlist]
		c.connectioncleanup()
		self.morphpossibilities = self._getmorphpossibilities()
		self.analyses = self._getalanlyses()
		self.missingparts = {'will_be_None_or_an_accurate_list_later'}
		self.principleparts = None

	def getprincipleparts(self):
		if not self.principleparts:
			self._determineprincipleparts()
		return self.principleparts

	def _getmorphpossibilities(self) -> list:
		pos = list()
		for m in self.dbmorphobjects:
			if m:
				pos.extend(m.getpossible())
		return pos

	def _getalanlyses(self) -> list:
		available = list()
		for m in self.morphpossibilities:
			mylanguage = str()
			if m.amgreek():
				mylanguage = 'greek'
			if m.amlatin():
				mylanguage = 'latin'
			analysislist = m.getanalysislist()
			available.extend([MorphAnalysis(m.observed, mylanguage, a) for a in analysislist])
		return available

	def _determineprincipleparts(self):
		if self.principleparts and not self.missingparts:
			return self.principleparts

		pplen = int()
		if self.language == 'greek':
			pplen = 6
		elif self.language == 'latin':
			pplen = 4

		verbforms = [a for a in self.analyses if a.partofspeech == 'verb']
		pp = [(f.analysis.whichprinciplepart(), f.word) for f in verbforms if f.analysis.isaprinciplepart()]
		pp = list(set(pp))
		pp.sort()
		self.principleparts = pp

		allpresent = {p[0]: p[1] for p in pp}
		self.missingparts = set(range(1, pplen + 1)) - set(allpresent.keys())
		# print('self.missingparts', self.missingparts)

		for p in self.missingparts:
			self.supplementmissing(p)

		self.principleparts = sorted(self.principleparts)
		return

	def supplementmissing(self, parttosupplement):

		alternates = [
			('tense', 'mood', 'voice', 'person'),
			('tense', 'mood', 'voice', 'number'),
			('tense', 'mood', 'voice')
			]

		verbforms = [a for a in self.analyses if a.partofspeech == 'verb']

		for a in alternates:
			for v in verbforms:
				if v.analysis.nearestmatchforaprinciplepart(a, parttosupplement):
					print('nextbest for pp {p} is {v}'.format(p=parttosupplement, v=v.word))
					self.principleparts.append((parttosupplement, '[{w}]'.format(w=v.word)))
					self.missingparts = self.missingparts - {parttosupplement}
					return
		self.principleparts.append((parttosupplement, '[no forms in use]'))
		self.missingparts = self.missingparts - {parttosupplement}
		return


class MorphAnalysis(object):
	def __init__(self, word, mylanguage, analysisstring):
		self.word = word
		assert mylanguage in ['greek', 'latin'], 'MorphAnalysis() only knows words that are "greek" or "latin"'
		self.language = mylanguage
		self.analysisstring = analysisstring
		self.analyssiscomponents = analysisstring.split(' ')
		self.analysis = None
		self.partofspeech = self.findpartofspeech()

	def findpartofspeech(self):
		pos = None
		tenses = ['pres', 'aor', 'fut', 'perf', 'imperf', 'plup', 'futperf', 'part']
		if self.analyssiscomponents[0] in tenses:
			pos = 'verb'
			self.analysis = VerbAnalysis(self.word, self.language, self.analyssiscomponents)
		return pos

class NounAnalysis(object):
	pass


class VerbAnalysis(object):
	gkprincipleparts = {('pres', 'ind', 'act', '1st', 'sg'): 1,
	                    ('fut', 'ind', 'act', '1st', 'sg'): 2,
	                    ('aor', 'ind', 'act', '1st', 'sg'): 3,
	                    ('perf', 'ind', 'act', '1st', 'sg'): 4,
	                    ('perf', 'ind', 'mp', '1st', 'sg'): 5,
	                    ('aor', 'ind', 'pass', '1st', 'sg'): 6
	                    }

	# note the inverted dict structures
	latprincipleparts = {1: ('pres', 'ind', 'act', '1st', 'sg'),
	                     2: ('pres', 'inf', 'act', None, None),
	                     3: ('perf', 'ind', 'act', '1st', 'sg'),
	                     4: ('perf', 'part', 'pass', 'masc', 'nom', 'sg')
	                     }

	elementmap = {'tense': 0,
	           'mood': 1,
	           'voice': 2,
	           'person': 3,
	           'number': 4,
	           'gender': 3,
	           'case': 4,
	           'pcpnumber': 5}

	def __init__(self, word, language, analyssiscomponents: List[str]):
		# this will need refactoring when you do latin participles (can catch them via the exra # of parts (maybe))
		self.word = word
		self.language = language
		self.dialects = list()
		self.case = None
		self.gender = None
		self.person = None
		self.tense = analyssiscomponents[0]
		self.mood = analyssiscomponents[1]
		self.voice = analyssiscomponents[2]
		if self.language == 'greek':
			try:
				self.person = analyssiscomponents[3]
			except IndexError:
				self.person = None
			try:
				self.number = analyssiscomponents[4]
			except IndexError:
				self.number = None
			try:
				dialects = ' '.join(analyssiscomponents[5:])
				dialects = re.sub(r'[()]', '', dialects)
				self.dialects = [x for x in dialects.split(' ') if x]
			except IndexError:
				pass
			if not self.dialects:
				self.dialects = ['attic']

		if self.language == 'latin' and len(analyssiscomponents) == 6:
			# participle
			# print(word, len(analyssiscomponents), 'analyssiscomponents', analyssiscomponents)
			self.gender = analyssiscomponents[3]
			self.case = analyssiscomponents[4]
			self.number = analyssiscomponents[5]

		if self.language == 'latin' and len(analyssiscomponents) < 6:
			# not a participle...
			try:
				self.person = analyssiscomponents[3]
			except IndexError:
				self.person = None
			try:
				self.number = analyssiscomponents[4]
			except IndexError:
				self.number = None

		self.ppts = dict()
		if self.language == 'greek':
			self.ppts = VerbAnalysis.gkprincipleparts
		elif self.language == 'latin':
			self.ppts = VerbAnalysis.latprincipleparts

		self.pptuple = (self.tense, self.mood, self.voice, self.person, self.number)
		self.baseformdisqualifiers = ["'", 'κἀ']  # incomplete at the moment
		# also need to toss the second of:
		# [(1, 'subicio'), (1, 'subicioque')

	def isaprinciplepart(self) -> bool:
		if self.language == 'greek':
			return self._isagreekprinciplepart()
		if self.language == 'latin':
			return self._isalatinprinciplepart()

	def _isalatinprinciplepart(self) -> bool:
		if self.case:
			tomatch = [self.ppts[4]]
		elif not self.person:
			tomatch = [self.ppts[2]]
		else:
			tomatch = [self.ppts[1], self.ppts[3]]

		if self.pptuple not in tomatch:
			return False

		dq = [re.search(d, self.word) for d in self.baseformdisqualifiers]
		if any(dq):
			return False

		return True

	def _isagreekprinciplepart(self) -> bool:
		if self.pptuple not in self.ppts:
			return False

		if not (self.dialects == ['attic'] or self.dialects == ['parad_form']):
			return False

		dq = [re.search(d, self.word) for d in self.baseformdisqualifiers]
		if any(dq):
			return False

		return True

	def whichprinciplepart(self) -> int:
		part = None

		if self.language == 'greek':
			try:
				part = self.ppts[self.pptuple]
			except KeyError:
				part = None

		if self.language == 'latin':
			test = [p for p in self.ppts if self.ppts[p] == self.pptuple]
			try:
				part = test[0]
			except IndexError:
				part = None

		return part

	def nearestmatchforaprinciplepart(self, acceptableelements: list, acceptablepart: int):
		if self.language == 'greek':
			return self._nearestmatchforagreekprinciplepart(acceptableelements, acceptablepart)
		if self.language == 'latin':
			return self._nearestmatchforalatinprinciplepart(acceptableelements, acceptablepart)

	def _nearestmatchforalatinprinciplepart(self, acceptableelements: list, acceptablepart: int):
		acceptabletuple = tuple([getattr(self, e) for e in acceptableelements])

		if 'case' in acceptableelements and 'number' in acceptableelements:
			acceptableelements = [e.replace('number', 'pcpnumber') for e in acceptableelements]

		positions = [VerbAnalysis.elementmap[e] for e in VerbAnalysis.elementmap if e in acceptableelements]
		positions = sorted(positions)
		usingppts = [self.ppts[p] for p in self.ppts.keys() if p is acceptablepart]
		try:
			usingppts = usingppts[0]
		except IndexError:
			return False

		newusing = list()
		for p in positions:
			newusing.append(usingppts[p])

		newusing = tuple(newusing)

		if acceptabletuple == newusing:
			return True
		else:
			return False

	def _nearestmatchforagreekprinciplepart(self, acceptableelements: list, acceptablepart: int):
		if not (self.dialects == ['attic'] or self.dialects == ['parad_form']):
			return False

		acceptabletuple = tuple([getattr(self, e) for e in acceptableelements])
		positions = [VerbAnalysis.elementmap[e] for e in VerbAnalysis.elementmap if e in acceptableelements]
		positions = sorted(positions)

		usingppts = [p for p in self.ppts.keys() if self.ppts[p] is acceptablepart]
		usingppts = usingppts[0]

		newusing = list()
		for p in positions:
			newusing.append(usingppts[p])

		newusing = tuple(newusing)

		if acceptabletuple == newusing:
			return True
		else:
			return False




class AdjAnalysis(object):
	pass


class AdvAnalysis(object):
	pass


class IndeclAnalysis(object):
	pass
