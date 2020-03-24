# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server import hipparchia
from server.formatting.miscformatting import consolewarning
from server.formatting.wordformatting import gkattemptelision, latattemptelision, minimumgreek


class MorphPossibilityObject(object):
	"""

	the embedded morphological possibilities

	"""
	tenses = {'pres', 'aor', 'fut', 'perf', 'imperf', 'plup', 'futperf'}
	genders = {'masc', 'fem', 'neut', 'masc/neut', 'masc/fem'}

	def __init__(self, observedform, findalltuple, prefixcount):
		# print('findalltuple', findalltuple)
		self.observed = observedform
		self.number = findalltuple[1]
		self.entry = findalltuple[2]
		self.xref = findalltuple[3]
		self.xkind = findalltuple[4]
		self.transandanal = findalltuple[5]
		self.prefixcount = prefixcount
		self.rewritten = False

	def gettranslation(self):
		transfinder = re.compile(r'<transl>(.*?)</transl>')
		trans = re.findall(transfinder, self.transandanal)
		return '; '.join(trans)

	def getanalysislist(self):
		analysisfinder = re.compile(r'<analysis>(.*?)</analysis>')
		analysislist = re.findall(analysisfinder, self.transandanal)
		return analysislist

	def getxreflist(self):
		xreffinder = re.compile(r'<xref_value>(.*?)</xref_value')
		xreflist = re.findall(xreffinder, self.transandanal)
		return xreflist

	def amgreek(self) -> bool:
		if re.search(minimumgreek, self.entry):
			return True
		else:
			return False

	def amlatin(self) -> bool:
		minimumlatin = re.compile(r'[a-z]')
		if re.search(minimumlatin, self.entry):
			return True
		else:
			return False

	def canbeanadverb(self) -> bool:
		analysislist = self.getanalysislist()
		test = [a for a in analysislist if 'adverb' in a]
		if not test:
			return False
		else:
			return True

	def _gettokens(self) -> set:
		flatten = lambda l: [item for sublist in l for item in sublist]
		tokens = flatten([a.split(' ') for a in self.getanalysislist()])
		tokens = flatten([t.split('/') for t in tokens])
		tokens = set(tokens)
		return tokens

	def isconjugatedverb(self, bagging='lemmatized') -> bool:
		tokens = self._gettokens()
		# thumbprints = {'pres', 'ind', 'act', 'pass', 'mid', '1st', '2nd', '3rd'}
		if bagging == 'unlemmatized':
			thumbprints = {'1st', '2nd', '3rd'}
		else:
			thumbprints = {'1st'}
		if not tokens & thumbprints:
			return False
		else:
			return True

	def isnounoradjective(self, bagging='lemmatized') -> bool:
		# incredibilis ['masc/fem nom/voc sg']}
		tokens = self._gettokens()
		# thumbprints = {'nom', 'sg', 'masc', 'fem', 'neut', 'pl', 'voc', 'dat', 'gen'}
		if bagging == 'unlemmatized':
			thumbprints = {'masc', 'fem', 'neut'}
		else:
			thumbprints = {'nom'}
		disqualification = {'part', 'pass', 'act'}
		if not tokens & thumbprints:
			return False
		elif tokens & disqualification:
			return False
		else:
			return True

	def language(self) -> str:
		if self.amgreek():
			return 'greek'
		if self.amlatin():
			return 'latin'
		return 'unknown'

	def getbaseform(self):
		if not hipparchia.config['SUPPRESSWARNINGS']:
			warn = True
		else:
			warn = False

		if self.amgreek():
			return self._getgreekbaseform()
		elif self.amlatin():
			return self._getlatinbaseform()
		else:
			if warn:
				consolewarning('MorphPossibilityObject failed to determine its own language: {e}'.format(e=self.entry))
			return None

	def _getgreekbaseform(self) -> str:
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
		if not hipparchia.config['SUPPRESSWARNINGS']:
			warn = True
		else:
			warn = False

		# need an aspiration check; incl εκ -⟩ εξ

		baseform = str()
		segments = self.entry.split(', ')

		if len(segments) == 1 and '-' not in segments[-1]:
			# [a] the simplest case where what you see is what you should seek: 'ἐπώνυμοϲ'
			baseform = segments[-1]
		elif len(segments) == 2 and '-' not in segments[-1] and self.prefixcount == 0:
			# [b] a compound case, but it does not involve prefixes just morphology: 'ἠχούϲαϲ, ἠχέω'
			baseform = segments[-1]
		elif len(segments) == 1 and '-' in segments[-1]:
			# [c] the simplest version of a prefix: ἐκ-ϲύρω
			baseform = gkattemptelision(segments[-1])
		elif len(segments) == 2 and '-' in segments[-1] and self.prefixcount == 1:
			# [d] more info, but we do not need it: ἐκϲύρωμεν, ἐκ-ϲύρω
			baseform = gkattemptelision(segments[-1])
		elif len(segments) > 1 and '-' in segments[-1] and self.prefixcount > 1:
			# [e] all bets are off: ὑπό,κατά,ἐκ-λάω
			# print('segments',segments)
			for i in range(self.prefixcount - 2, -1, -1):
				baseform = gkattemptelision(segments[-1])
				try:
					baseform = segments[i] + '-' + baseform
				except IndexError:
					if warn:
						consolewarning('abandoning efforts to parse {e}'.format(e=self.entry))
					baseform = segments[-1]
		else:
			if warn:
				consolewarning('MorphPossibilityObject.getbaseform() is confused: {e} - {s}'.format(e=self.entry, s=segments))

		# not sure this ever happens with the greek data
		baseform = re.sub(r'^\s', '', baseform)

		return baseform

	def _getlatinbaseform(self):
		segments = self.entry.split(', ')

		if len(segments) == 1 and '-' not in segments[-1]:
			# [a] the simplest case where what you see is what you should seek: 'ἐπώνυμοϲ'
			baseform = segments[-1]
		elif len(segments) == 2 and '-' not in segments[-1] and self.prefixcount == 0:
			# [b] a compound case, but it does not involve prefixes just morphology: 'ἠχούϲαϲ, ἠχέω'
			baseform = segments[-1]
		else:
			# MorphPossibilityObject.getlatinbaseform() needs work praevortēmur, prae-verto
			# PREF+DASH+STEM is the issue; a number of elisions and phonic shifts to worry about
			#print('MorphPossibilityObject.getlatinbaseform() needs work',self.entry)
			baseform = latattemptelision(self.entry)

		# some latin words will erroneously yield ' concupio' as the base form: bad data
		baseform = re.sub(r'^\s', '', baseform)

		return baseform



"""

not easy to fingerprint via the lexicon

pos not stored in the greek dictionary...


hipparchiaDB=# select distinct pos from latin_dictionary;
              pos
-------------------------------
subst. ‖ adv. ‖ adj.
subst. ‖ v. n.
prep. ‖ adv. ‖ adj.
v. a. ‖ adv. ‖ prep.
p. a. ‖ adv. ‖ v. freq. a.
v. a. ‖ adv. ‖ subst.
adv. num.
subst.
subst. ‖ adj.
v. a. ‖ v. dep. ‖ adv.
adj. ‖ v. n.
v. dep. ‖ adj. ‖ adv.
v. dep. ‖ adj.
v. a. ‖ adv.
v. dep. ‖ adv.
pron. adj. ‖ adv.
adv. ‖ adj. ‖ v. n.
prep.
v. a. ‖ prep.
adv. ‖ prep. ‖ adj.
prep. ‖ partic.
v. a. ‖ adj. ‖ p. a. ‖ subst.
adj. ‖ adv. ‖ adj.
adv. ‖ adj.
v. a. ‖ subst.
prep. ‖ adj.
adj. ‖ partic.
v. a. ‖ adv. ‖ adj. ‖ p. a.
adv. ‖ adj. ‖ p. a.
v. dep. ‖ p. a. ‖ v. n.
subst. ‖ adj. ‖ adv. ‖ adj.
v. a. ‖ adv. ‖ p. a.
v. a. ‖ adv. ‖ adj.
v. freq. a.
adv. ‖ partic.
v. a. ‖ p. a. ‖ subst.
v. dep. ‖ p. a. ‖ adv.
v. a. ‖ p. a. ‖ v. n.

v. a. ‖ adv. ‖ p. a. ‖ subst.
p. a. ‖ v. dep. ‖ adv.
v. a. ‖ v. dep. ‖ p. a.
num. adj.
adv. ‖ prep. ‖ p. a. ‖ adj.
adv. ‖ v. n.
subst. ‖ num. adj.
v. a. ‖ adv. ‖ p. a. ‖ v. n.
v. a. ‖ adj. ‖ prep. ‖ p. a.
v. n.
v. a. ‖ v. dep.
subst. ‖ adj. ‖ adj.
v. a. ‖ adj.
v. dep. ‖ adj. ‖ p. a.
v. a. ‖ adj. ‖ p. a.
adj. ‖ num. adj.
adv. ‖ p. a. ‖ v. n.
subst. ‖ p. a. ‖ v. n.
p. a.
adv.
p. a. ‖ v. n.
v. dep. ‖ p. a.
adj.
v. dep. ‖ v. n.
adv. ‖ prep.
adj. ‖ adj.
partic.
subst. ‖ adv.
p. a. ‖ v. freq. a.
subst. ‖ adv. ‖ p. a. ‖ v. n.
v. dep.
v. a. ‖ v. n.
adv. ‖ p. a.
v. a.
v. a. ‖ p. a.
interj.
"""