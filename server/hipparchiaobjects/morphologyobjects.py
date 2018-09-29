# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re

from flask import session

from server import hipparchia
from server.formatting.wordformatting import gkattemptelision, latattemptelision, minimumgreek


class MorphPossibilityObject(object):
	"""

	the embedded morphological possibilities

	"""

	def __init__(self, observedform, findalltuple, prefixcount):
		self.observed = observedform
		self.number = findalltuple[1]
		self.entry = findalltuple[2]
		self.xref = findalltuple[3]
		self.xkind = findalltuple[4]
		self.transandanal = findalltuple[5]
		self.prefixcount = prefixcount

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

	def amgreek(self):
		if re.search(minimumgreek, self.entry):
			return True
		else:
			return False

	def amlatin(self):
		minimumlatin = re.compile(r'[a-z]')
		if re.search(minimumlatin, self.entry):
			return True
		else:
			return False

	def getbaseform(self):
		if hipparchia.config['SUPPRESSWARNINGS'] == 'no':
			warn = True
		else:
			warn = False

		if self.amgreek():
			return self._getgreekbaseform()
		elif self.amlatin():
			return self._getlatinbaseform()
		else:
			if warn:
				print('MorphPossibilityObject failed to determine its own language', self.entry)
			return None

	def _getgreekbaseform(self):
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
		if hipparchia.config['SUPPRESSWARNINGS'] == 'no':
			warn = True
		else:
			warn = False

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
						print('abandoning efforts to parse', self.entry)
					baseform = segments[-1]
		else:
			if warn:
				print('MorphPossibilityObject.getbaseform() is confused', self.entry, segments)

		# not sure this ever happens with the greek data
		baseform = re.sub(r'^\s', '', baseform)

		return baseform

	def _getlatinbaseform(self):
		baseform = ''
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
	
	def formatconsolidatedgrammarentry(self, entrycountnumber=0):
		"""
		example: {'count': 1, 'form': 'ἀϲήμου', 'word': 'ἄϲημοϲ', 'transl': 'without mark', 'anal': ['masc/fem/neut gen sg'], 'xref': 16808356, 'trials': 1}

		something like this will come back:

		<p class="obsv">(1)&nbsp;
		<span class="dictionaryform">ἀϲήμου</span> (from <span class="dictionaryform">ἄϲημοϲ</span>, without mark): &nbsp;
		<br /><span class="possibility">masc/fem/neut gen sg</span>&nbsp;
		
		:return: 
		"""

		obsvstring = '<p class="obsv">({ct})&nbsp;'
		dfstring = '<span class="dictionaryform">{df}</span>'
		xdfstring = '<span class="dictionaryform">{df}</span> (from {wt}){x}: &nbsp;'
		posstring = '<br /><span class="possibility">{pos}</span>&nbsp;'
		ctposstring = '<br />[{ct}]&nbsp;<span class="possibility">{a}</span>'

		if session['debugparse'] == 'yes':
			xrefinfo = '<code>[{x}]</code>'.format(x=self.xref)
		else:
			xrefinfo = ''

		analysislist = self.getanalysislist()
		
		outputlist = list()
		outputlist.append(obsvstring.format(ct=str(entrycountnumber)))
		wordandtranslation = dfstring.format(df=self.observed)
		if len(self.gettranslation()) > 1:
			wordandtranslation = ', '.join([wordandtranslation, self.gettranslation()])

		outputlist.append(xdfstring.format(df=self.observed, wt=wordandtranslation, x=xrefinfo))
		if len(analysislist) == 1:
			outputlist.append(posstring.format(pos=analysislist[0]))
		else:
			count = 0
			for a in analysislist:
				count += 1
				outputlist.append(ctposstring.format(ct=chr(count + 96), a=a))
			outputlist.append('&nbsp;')

		analysisstring = '\n'.join(outputlist)

		# print('analysisstring\n', analysisstring)

		return analysisstring
	


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

	def __init__(self, dictionaryentry, xref, derivativeforms):
		self.dictionaryentry = dictionaryentry
		self.xref = xref
		self.formlist = derivativeforms