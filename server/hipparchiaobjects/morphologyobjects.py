# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server import hipparchia
from server.formatting.miscformatting import consolewarning
from server.formatting.wordformatting import gkattemptelision, latattemptelision, minimumgreek
from server.listsandsession.genericlistfunctions import flattenlistoflists


class MorphPossibilityObject(object):
	"""

	generate an object to deal with the morphological possibilities embedded inside of dbMorphologyObject.possibleforms

	possibilitydict is JSON from teh database:
		{
				'headword': 'WORD',
				'scansion': 'SCAN',
				'xref_value': 'VAL',
				'xref_kind': 'KIND',
				'transl': 'TRANS',
				'analysis': 'ANAL'
		}

	old:

	findalltuple ('<possibility_1>', '1', 'fīliīs, filia', '30273503', '9', '<transl>a daughter; female offspring</transl><analysis>fem abl pl</analysis>')
	findalltuple ('<possibility_2>', '2', 'fīliīs, filia', '30273503', '9', '<transl>a daughter; female offspring</transl><analysis>fem dat pl</analysis>')
	findalltuple ('<possibility_3>', '3', 'fīliīs, filius', '30284765', '9', '<transl>a son; a son of mother earth</transl><analysis>masc abl pl</analysis>')
	findalltuple ('<possibility_4>', '4', 'fīliīs, filius', '30284765', '9', '<transl>a son; a son of mother earth</transl><analysis>masc dat pl</analysis>')

	"""
	tenses = {'pres', 'aor', 'fut', 'perf', 'imperf', 'plup', 'futperf'}
	genders = {'masc', 'fem', 'neut', 'masc/neut', 'masc/fem'}

	def __init__(self, observedform, possibilitynumber, possibilitydict, prefixcount):
		# print('possibilitydict', possibilitydict)
		# print('findalltuple', findalltuple)
		self.observed = observedform
		self.number = possibilitynumber
		self.entry = possibilitydict['headword']
		self.xref = possibilitydict['xref_value']
		self.xkind = possibilitydict['xref_kind']
		self.transl = possibilitydict['transl']
		self.anal = possibilitydict['analysis']
		self.prefixcount = prefixcount
		self.rewritten = False

	def gettranslation(self):
		trans = self.transl
		try:
			trans = trans.split('; ')
		except IndexError:
			pass
		# print('trans=', trans)
		# flag the level labels in 'A. Useful; B. Neutr. absol; C. ...'
		levelhighlighter = re.compile(r'^(.{1,3}\.)\s')
		levelbracket = lambda x: '<span class="transtree">{item}</span> '.format(item=x.group(1))
		trans = [re.sub(levelhighlighter, levelbracket, t) for t in trans]
		t = '; '.join(trans)
		return t

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
		if 'adverb' in self.anal:
			return False
		else:
			return True

	def _gettokens(self) -> set:
		tokens = self.anal.split(' ')
		tokens = flattenlistoflists([t.split('/') for t in tokens])
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
		baseform = re.sub(r'^\s', str(), baseform)

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
		baseform = re.sub(r'^\s', str(), baseform)

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