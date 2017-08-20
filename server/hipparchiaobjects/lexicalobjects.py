# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re

from server import hipparchia
from server.formatting.wordformatting import gkattemptelision, latattemptelision


class dbWordCountObject(object):
	"""
	an object that corresponds to a db line

	CREATE TABLE public."wordcounts_ϲ" (
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
		if hipparchia.config['AVOIDCIRCLEDLETTERS'] != 'yes':
			self.tlabel = 'Ⓣ'
			self.glabel = 'Ⓖ'
			self.llabel = 'Ⓛ'
			self.dlabel = 'Ⓓ'
			self.ilabel = 'Ⓘ'
			self.clabel = 'Ⓒ'
		else:
			self.tlabel = 'T'
			self.glabel = 'G'
			self.llabel = 'L'
			self.dlabel = 'D'
			self.ilabel = 'I'
			self.clabel = 'C'

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

	CREATE TABLE public.dictionary_headword_wordcounts (
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

	greekworderaweights = {'early': 7.75, 'middle': 1.92, 'late': 1}
	corporaweights = {'gr': 1.0, 'lt': 10.68, 'in': 27.78, 'dp': 26.76, 'ch': 124.47}

	greekgenreweights = {'acta': 89.53, 'agric': 101839.74, 'alchem': 80.12, 'anthol':
						18.42, 'apocalyp': 128.74, 'apocryph': 100.53, 'apol': 7.24,
						'astrol': 21.11, 'astron': 47.88, 'biogr': 6.68, 'bucol':
						443.3, 'caten': 5.35, 'chronogr': 5.01, 'comic': 31.81, 'comm':
						1.0, 'concil': 18.02, 'coq': 607.89, 'dialog': 7.28, 'docu':
						4.21, 'doxogr': 144.06, 'eccl': 7.92, 'eleg': 223.49, 'encom':
						13.85, 'epic': 20.51, 'epigr': 11.91, 'epist': 4.87, 'evangel':
						127.36, 'exeget': 1.29, 'fab': 144.51, 'geogr': 11.62, 'gnom':
						95.76, 'gramm': 9.94, 'hagiogr': 24.3, 'hexametr': 120.27,
						'hist': 1.54, 'homilet': 7.25, 'hymn': 50.27, 'hypoth': 14.37,
						'iamb': 138.75, 'ignotum': 779074.0, 'invectiv': 247.63,
						'inscr': 4.07, 'jurisprud': 54.78, 'lexicogr': 4.65, 'liturg':
						589.76, 'lyr': 492.59, 'magica': 104.47, 'math': 11.42, 'mech':
						105.95, 'med': 2.33, 'metrolog': 326.55, 'mim': 2518.42, 'mus':
						101.89, 'myth': 203.19, 'narrfict': 16.0, 'nathist': 9.8,
						'onir': 140.35, 'orac': 270.33, 'orat': 6.71, 'paradox':
						270.91, 'parod': 853.78, 'paroem': 68.18, 'perieg': 239.39,
						'phil': 3.74, 'physiognom': 658.34, 'poem': 64.07, 'polyhist':
						25.7, 'prophet': 107.99, 'pseudepigr': 675.17, 'rhet': 8.74,
						'satura': 290.06, 'satyr': 133.99, 'schol': 6.15, 'tact': 54.5,
						'test': 83.53, 'theol': 6.48, 'trag': 36.02, 'allrelig': 0.6, 'allrhet': 2.94}

	latingenreweights = {'acta': 3364.04, 'agric': 5.21, 'alchem': 646.99, 'anthol':
						538.25, 'apocalyp': 14022.73, 'apocryph': 16050.11, 'apol':
						469.9, 'astrol': 5203.75, 'astron': 16.36, 'biogr': 9.64,
						'bucol': 38.45, 'caten': 350.38, 'chronogr': 429.17, 'comic':
						4.71, 'comm': 2.24, 'concil': 1383.34, 'coq': 62.11, 'dialog':
						70.63, 'docu': 9.74, 'doxogr': 236.24, 'eccl': 5203.75, 'eleg':
						7.69, 'encom': 267.18, 'epic': 2.25, 'epigr': 109.53, 'epist':
						2.06, 'exeget': 189.28, 'fab': 29.13, 'geogr': 234.04, 'gnom':
						81.28, 'gramm': 4.9, 'hagiogr': 14479.99, 'hexametr': 18.42,
						'hist': 1.0, 'homilet': 5947.14, 'hymn': 6831.58, 'hypoth':
						78.77, 'iamb': 16862.77, 'ignotum': 643.56, 'inscr': 1.93,
						'jurisprud': 1.1, 'lexicogr': 22.35, 'liturg': 222026.5, 'lyr':
						23.95, 'magica': 20814.98, 'math': 762.54, 'mech': 444053.0,
						'med': 7.28, 'metrolog': 23371.21, 'mim': 1066.58, 'mus':
						721.65, 'myth': 20814.98, 'narrfict': 11.78, 'nathist': 1.93,
						'orac': 1332159.0, 'orat': 1.79, 'paradox': 17300.77, 'parod':
						331.96, 'paroem': 66607.95, 'perieg': 83259.94, 'phil': 2.17,
						'poem': 13.66, 'polyhist': 4.88, 'pseudepigr': 266431.8,
						'rhet': 2.7, 'satyr': 363.38, 'schol': 34.3, 'tact': 37.58,
						'test': 69.97, 'theol': 4915.72, 'trag': 13.23, 'allrelig': 82.92, 'allrhet': 1.07}

	# into one dict so we can pass it to __init__
	wts = {'gkera': greekworderaweights, 'corp': corporaweights, 'gkgenre': greekgenreweights, 'ltgenre': latingenreweights}

	def __init__(self, entryname, totalcount, greekcount, latincount, docpapcount, inscriptioncount, christiancount,
	             frqclass, early, middle, late, acta, agric, alchem, anthol, apocalyp, apocryph, apol, astrol, astron, biogr, bucol,
	             caten, chronogr, comic, comm, concil, coq, dialog, docu, doxogr, eccl, eleg, encom, epic, epigr, epist, evangel,
	             exeget, fab, geogr, gnom, gramm, hagiogr, hexametr, hist, homilet, hymn, hypoth, iamb, ignotum,
	             invectiv, inscr, jurisprud, lexicogr, liturg, lyr, magica, math, mech, med, metrolog, mim, mus, myth, narrfict,
	             nathist, onir, orac, orat, paradox, parod, paroem, perieg, phil, physiognom, poem, polyhist, prophet,
	             pseudepigr, rhet, satura, satyr, schol, tact, test, theol, trag, weights=wts):

		# see note in lexicallookups.py for deriving these weight numbers
		self.entry = entryname
		self.frqclass = frqclass
		self.early = early
		self.middle = middle
		self.late = late
		self.acta = acta
		self.agric = agric
		self.alchem = alchem
		self.anthol = anthol
		self.apocalyp = apocalyp
		self.apocryph = apocryph
		self.apol = apol
		self.astrol = astrol
		self.astron = astron
		self.biogr = biogr
		self.bucol = bucol
		self.caten = caten
		self.chronogr = chronogr
		self.comic = comic
		self.comm = comm
		self.concil = concil
		self.coq = coq
		self.dialog = dialog
		self.docu = docu
		self.doxogr = doxogr
		self.eccl = eccl
		self.eleg = eleg
		self.encom = encom
		self.epic = epic
		self.epigr = epigr
		self.epist = epist
		self.evangel = evangel
		self.exeget = exeget
		self.fab = fab
		self.geogr = geogr
		self.gnom = gnom
		self.gramm = gramm
		self.hagiogr = hagiogr
		self.hexametr = hexametr
		self.hist = hist
		self.homilet = homilet
		self.hymn = hymn
		self.hypoth = hypoth
		self.iamb = iamb
		self.ignotum = ignotum
		self.inscr = inscr
		self.invectiv = invectiv
		self.jurisprud = jurisprud
		self.lexicogr = lexicogr
		self.liturg = liturg
		self.lyr = lyr
		self.magica = magica
		self.math = math
		self.mech = mech
		self.med = med
		self.metrolog = metrolog
		self.mim = mim
		self.mus = mus
		self.myth = myth
		self.narrfict = narrfict
		self.nathist = nathist
		self.onir = onir
		self.orac = orac
		self.orat = orat
		self.paradox = paradox
		self.parod = parod
		self.paroem = paroem
		self.perieg = perieg
		self.phil = phil
		self.physiognom = physiognom
		self.poem = poem
		self.polyhist = polyhist
		self.prophet = prophet
		self.pseudepigr = pseudepigr
		self.rhet = rhet
		self.satura = satura
		self.satyr = satyr
		self.schol = schol
		self.tact = tact
		self.test = test
		self.theol = theol
		self.trag = trag
		if re.search(r'^[^a-z]', self.entry):
			self.language = 'G'
		else:
			self.language = 'L'
		try:
			self.wtdgkearly = self.early * weights['gkera']['early']
			self.wtdgkmiddle = self.middle * weights['gkera']['middle']
			self.wtdgklate = self.late * weights['gkera']['late']
			# use our weighted values to determine its relative time balance
			self.predomera = max(self.wtdgkearly, self.wtdgkmiddle, self.wtdgklate)
		except:
			# no date info is available for this (Latin) word
			self.wtdgkearly, self.wtdgkmiddle, self.wtdgklate, self.predomera = -1, -1, -1, -1
		if hipparchia.config['AVOIDCIRCLEDLETTERS'] != 'yes':
			self.qlabel = 'ⓠ'
			self.elabel = 'ⓔ'
			self.mlabel = 'ⓜ'
			self.latelabel = 'ⓛ'
			self.unklabel = 'ⓤ'
		else:
			self.qlabel = 'q'
			self.elabel = 'e'
			self.mlabel = 'm'
			self.latelabel = 'l'
			self.unklabel = 'u'
		super().__init__(entryname, totalcount, greekcount, latincount, docpapcount, inscriptioncount, christiancount)
		# can't do this until self.g, etc exist owing to a call to super()
		self.wtdgr = self.g * weights['corp']['gr']
		self.wtdlt = self.l * weights['corp']['lt']
		self.wtdin = self.i * weights['corp']['in']
		self.wtddp = self.d * weights['corp']['dp']
		self.wtdch = self.c * weights['corp']['ch']
		self.predomcorp = max(self.wtdgr, self.wtdlt, self.wtdin, self.wtddp, self.wtdch)
		self.allrelig = None
		self.allrhet = None

	def gettime(self, element):
		elements = {'early': self.early, 'middle': self.middle, 'late': self.late ,
		            'unk': self.t - (self.early + self.middle + self.late)
		            }
		try:
			return elements[element]
		except:
			return 0

	def amlatin(self):
		minimumlatin = re.compile(r'[a-z]')
		if re.search(minimumlatin, self.entry):
			return True
		else:
			return False

	def getweightedtime(self, element):
		"""
		it would be nice to be able to turn this off some day

		:param element:
		:return:
		"""
		if self.amlatin() is False:
			return self.weightedtime(element)
		else:
			return None

	def weightedtime(self, element):
		try:
			elements = {'early': (self.wtdgkearly/self.predomera)*100,
						'middle': (self.wtdgkmiddle/self.predomera)*100,
						'late': (self.wtdgklate/self.predomera)*100}
		except ZeroDivisionError:
			# there was no self.predomera value
			return None
		if self.predomera != -1:
			try:
				return elements[element]
			except:
				return 0
		else:
			return None

	def getweightedcorpora(self, element):
		if self.predomcorp != 0:
			elements = {'gr': (self.wtdgr/self.predomcorp)*100,
						'lt': (self.wtdlt/self.predomcorp)*100,
						'in': (self.wtdin/self.predomcorp)*100,
						'dp': (self.wtddp / self.predomcorp) * 100,
						'ch': (self.wtdch/self.predomcorp)*100}
			try:
				return elements[element]
			except:
				return 0
		else:
			return 0

	def gettimelabel(self, element):
		elements = {'early': self.elabel,
					'middle': self.mlabel,
					'late': self.latelabel,
					'unk': self.unklabel,
					'frq': self.frqclass}
		try:
			return elements[element]
		except:
			return 0

	def sortgenresbyweight(self, gwt={'G': greekgenreweights, 'L': latingenreweights}):
		"""

		who is most likely to use this word? apply weight to counts by genre

		return a list of tuples:
			[('comic', 100.0), ('invectiv', 36.68718065621115), ('satura', 28.579618924301734), ('rhet', 15.163212890806758) ...]

		:param gwt:
		:return:
		"""

		mygenres = gwt[self.language]

		if hipparchia.config['EXCLUDEMINORGENRECOUNTS'] == 'yes':
			return self.genresebyweightlessminorgenres(500, mygenres)

		genretuplelist = [(key, getattr(self, key) * mygenres[key]) for key in mygenres]
		genretuplelist.sort(key=lambda x: x[1], reverse=True)
		norming = genretuplelist[0][1] / 100
		genretuplelist = [(g[0], g[1]/norming) for g in genretuplelist]

		return genretuplelist


	def genresebyweightlessminorgenres(self, maxmodifier, gwt={'G': greekgenreweights, 'L': latingenreweights}):
		"""

		same as sortgenresbyweight() but use maxmodifier to suppress genres that have so few words that any results
		spike the frequency outcomes

		i'm not sure you wuld ever want to exclude lyric, though

		basically 'maxmodifier' should be 500 since lyr has a modifier of 493

			14832896 	 comm
			...
			45437 	 metrolog
			34808 	 bucol
			32677 	 lyr
			25393 	 coq
			24994 	 liturg
			22845 	 physiognom
			22708 	 pseudepigr
			18023 	 parod
			6205 	 mim
			20 	 ignotum

		:param maxmodifier:
		:param gwt:
		:return:
		"""

		try:
			mygenres = gwt[self.language]
		except KeyError:
			# we got here by passing only one language to gwt and not a dict of two languages
			mygenres = gwt

		mygenres = {g: mygenres[g] for g in mygenres if mygenres[g] < maxmodifier}

		genretuplelist = [(key, getattr(self, key) * mygenres[key]) for key in mygenres]
		genretuplelist.sort(key=lambda x: x[1], reverse=True)
		norming = genretuplelist[0][1] / 100
		try:
			genretuplelist = [(g[0], g[1]/norming) for g in genretuplelist]
		except ZeroDivisionError:
			genretuplelist = None

		return genretuplelist

	def collapsedgenreweights(self, gwt={'G': greekgenreweights, 'L': latingenreweights}):
		"""
		modify the definition of genres, then make a call to sortgenresbyweight(); pass it a modified version of gwt
		:param gwt:
		:return:
		"""

		religwt = gwt[self.language]['allrelig']
		rhtgwt = gwt[self.language]['allrhet']

		mygenres = gwt[self.language]

		relig = ['acta', 'apocalyp', 'apocryph', 'apol', 'caten', 'concil', 'eccl', 'evangel', 'exeget', 'hagiogr',
	         'homilet', 'liturg', 'prophet', 'pseudepigr', 'theol']
		self.allrelig = sum([getattr(self, key) for key in mygenres if key in relig])
		mygenres = {g: mygenres[g] for g in mygenres if g not in relig}
		mygenres['allrelig'] = religwt

		allrhet = ['encom', 'invectiv', 'orat', 'rhet']
		self.allrhet = sum([getattr(self, key) for key in mygenres if key in allrhet])
		mygenres = {g: mygenres[g] for g in mygenres if g not in allrhet}
		mygenres['allrhet'] = rhtgwt

		return self.sortgenresbyweight({'G': mygenres, 'L': mygenres})


class dbMorphologyObject(object):
	"""

	an object that corresponds to a db line

	CREATE TABLE public.greek_morphology (
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

	def getxreflist(self):
		xreffinder = re.compile(r'<xref_value>(.*?)</xref_value')
		xreflist = re.findall(xreffinder, self.transandanal)
		return xreflist

	def amgreek(self):
		minimumgreek = re.compile('[α-ωἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]')
		if re.search(minimumgreek,self.entry):
			return True
		else:
			return False

	def amlatin(self):
		minimumlatin = re.compile(r'[a-z]')
		if re.search(minimumlatin,self.entry):
			return True
		else:
			return False

	def getbaseform(self):
		if self.amgreek():
			return self.getgreekbaseform()
		elif self.amlatin():
			return self.getlatinbaseform()
		else:
			print('MorphPossibilityObject failed to determine its own language',self.entry)
			return None

	def getgreekbaseform(self):
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
			baseform = gkattemptelision(segments[-1])
		elif len(segments) == 2 and '-' in segments[-1] and self.prefixcount == 1:
			# [d] more info, but we do not need it: ἐκϲύρωμεν, ἐκ-ϲύρω
			baseform = gkattemptelision(segments[-1])
		elif len(segments) > 1 and '-' in segments[-1] and self.prefixcount > 1:
			# [e] all bets are off: ὑπό,κατά,ἐκ-λάω
			# print('segments',segments)
			for i in range(self.prefixcount - 2, -1, -1):
				baseform = gkattemptelision(segments[-1])
				baseform = segments[i] + '-' + baseform
		else:
			print('MorphPossibilityObject.getbaseform() is confused', self.entry, segments)

		# not sure this ever happens with the greek data
		baseform = re.sub(r'^\s', '', baseform)

		return baseform

	def getlatinbaseform(self):
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


class dbDictionaryEntry(object):
	"""
	an object that corresponds to a db line

	CREATE TABLE greek_dictionary (
		entry_name character varying(64),
		metrical_entry character varying(64),
		unaccented_entry character varying(64),
		id_number integer,
		entry_type character varying(8),
		entry_options "char",
		entry_body text
	);

	CREATE TABLE latin_dictionary (
		entry_name character varying(64),
		metrical_entry character varying(64),
		id_number integer,
		entry_type character varying(8),
		entry_key character varying(64),
		entry_options "char",
		entry_body text
	);

	Latin only: entry_key
	Greek only: unaccented_entry

	"""

	def __init__(self, entry_name, metrical_entry, id_number, entry_type, entry_options, translations, entry_body):
		self.entry = entry_name
		self.metricalentry = metrical_entry
		self.id = id_number
		self.type = entry_type
		self.options = entry_options
		self.translations = translations.split(' ‖ ')
		self.body = entry_body
		self.nextentryid = -1
		self.preventryid = -1
		self.nextentry = '(none)'
		self.preventry = '(none)'


class dbGreekWord(dbDictionaryEntry):
	"""

	an object that corresponds to a db line

	differs from Latin in self.language and unaccented_entry

	"""

	def __init__(self, entry_name, metrical_entry, id_number, entry_type, entry_options, translations, entry_body, unaccented_entry):
		self.language = 'Greek'
		self.unaccented_entry = unaccented_entry
		super().__init__(entry_name, metrical_entry, id_number, entry_type, entry_options, translations, entry_body)
		self.entry_key = None

	def isgreek(self):
		return True

	def islatin(self):
		return False


class dbLatinWord(dbDictionaryEntry):
	"""

	an object that corresponds to a db line

	differs from Greek in self.language and unaccented_entry

	"""

	def __init__(self, entry_name, metrical_entry, id_number, entry_type, entry_options, translations, entry_body,
	             entry_key):
		self.language = 'Latin'
		self.unaccented_entry = None
		super().__init__(entry_name, metrical_entry, id_number, entry_type, entry_options, translations, entry_body)
		self.entry_key = entry_key

	def isgreek(self):
		return False

	def islatin(self):
		return True


class dbLemmaObject(object):
	"""
	an object that corresponds to a db line

	CREATE TABLE public.greek_lemmata (
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
		self.formlist = [re.sub(r'\'', '', f) for f in self.formlist]

	def getformdict(self):
		fd = dict()
		for f in self.formandidentificationlist:
			key = f.split(' ')[0]
			body = f[len(key)+1:]
			fd[key] = body

		return fd
