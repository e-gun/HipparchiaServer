# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re

from server import hipparchia
from server.helperfunctions import gkattemptelision, latattemptelision


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

	greekworderaweights = {'early': 7.72, 'middle': 1.92, 'late': 1}
	corporaweights =  {'gr': 1.0, 'lt': 11.37, 'in': 28.13, 'dp': 27.49, 'ch': 129.89}

	greekgenreweights = {'acta': 87.64, 'agric': 16513.67, 'alchem': 79.21, 'anthol': 17.91, 'apocalyp': 128.34,
	                     'apocryph': 97.15, 'apol': 7.1, 'astrol': 21.02, 'astron': 47.08, 'biogr': 6.47, 'bucol': 425.46,
	                     'caten': 5.24, 'chronogr': 4.9, 'comic': 30.51, 'comm': 1.0, 'concil': 17.88, 'coq': 598.04,
	                     'dialog': 7.08, 'docu': 4.16, 'doxogr': 141.89, 'eccl': 7.74, 'eleg': 211.32, 'encom': 13.47,
	                     'epic': 19.64, 'epigr': 11.63, 'epist': 4.76, 'evangel': 120.89, 'exeget': 1.26, 'fab': 138.18,
	                     'geogr': 11.35, 'gnom': 92.62, 'gramm': 9.86, 'hagiogr': 23.65, 'hexametr': 115.44, 'hist': 1.5,
	                     'homilet': 7.16, 'hymn': 48.94, 'hypoth': 14.04, 'iamb': 133.7, 'ignotum': 644033.22,
	                     'invectiv': 240.4, 'inscr': 3.72, 'jurisprud': 53.38, 'lexicogr': 4.58, 'liturg': 592.77,
	                     'lyr': 455.88, 'magica': 103.13, 'math': 11.52, 'mech': 103.85, 'med': 2.29, 'metrolog': 326.41,
	                     'mim': 2387.23, 'mus': 101.38, 'myth': 195.94, 'narrfict': 15.67, 'nathist': 9.67, 'onir': 138.77,
	                     'orac': 259.94, 'orat': 6.54, 'paradox': 262.33, 'parod': 823.62, 'paroem': 66.02, 'perieg': 233.86,
	                     'phil': 3.7, 'physiognom': 648.4, 'poem': 61.96, 'polyhist': 24.98, 'prophet': 106.66,
	                     'pseudepigr': 652.46, 'rhet': 8.51, 'satura': 280.91, 'satyr': 126.45, 'schol': 5.99, 'tact': 52.95,
	                     'test': 82.78, 'theol': 6.43, 'trag': 34.51, 'allrelig': 0.59, 'allrhet': 2.87}

	latingenreweights = {'acta': 3174.91, 'agric': 5.23, 'alchem': 655.87, 'anthol': 509.85, 'apocalyp': 14476.08,
	                     'apocryph': 15199.89, 'apol': 473.15, 'astrol': 5218.85, 'astron': 16.38, 'biogr': 9.7,
	                     'bucol': 39.33, 'caten': 351.75, 'chronogr': 427.41, 'comic': 4.76, 'comm': 2.27, 'concil': 1461.53,
	                     'coq': 62.95, 'dialog': 71.08, 'docu': 9.52, 'doxogr': 235.75, 'eccl': 5735.81, 'eleg': 7.76,
	                     'encom': 277.43, 'epic': 2.27, 'epigr': 106.05, 'epist': 2.06, 'exeget': 188.03, 'fab': 29.46,
	                     'geogr': 232.06, 'gnom': 81.87, 'gramm': 4.99, 'hagiogr': 14829.16, 'hexametr': 18.6, 'hist': 1.0,
	                     'homilet': 6468.04, 'hymn': 7896.05, 'hypoth': 75.95, 'iamb': 22108.93, 'ignotum': 655.87,
	                     'inscr': 2.03, 'jurisprud': 1.11, 'lexicogr': 21.9, 'liturg': 243198.2, 'lyr': 24.39, 'magica': 34742.6,
	                     'math': 750.15, 'mech': 405330.33, 'med': 7.4, 'metrolog': 21714.12, 'mim': 1065.72, 'mus': 727.27,
	                     'myth': 20266.52, 'narrfict': 11.76, 'nathist': 1.94, 'orac': 1215991.0, 'orat': 1.81, 'paradox': 17126.63,
	                     'parod': 334.52, 'paroem': 75999.44, 'perieg': 75999.44, 'phil': 2.18, 'poem': 13.91, 'polyhist': 4.9,
	                     'pseudepigr': 243198.2, 'rhet': 2.71, 'satyr': 356.49, 'schol': 32.89, 'tact': 37.73, 'test': 70.24,
	                     'theol': 4883.5, 'trag': 13.34, 'allrelig': 83.21, 'allrhet': 1.08}

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
		if re.search(r'^[^a-z]',self.entry):
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
		if re.search(minimumlatin,self.entry):
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
			elements = {'early': (self.wtdgkearly/self.predomera)*100, 'middle': (self.wtdgkmiddle/self.predomera)*100, 'late': (self.wtdgklate/self.predomera)*100
		            }
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
			elements = {'gr': (self.wtdgr/self.predomcorp)*100, 'lt': (self.wtdlt/self.predomcorp)*100, 'in': (self.wtdin/self.predomcorp)*100,
			            'dp': (self.wtddp / self.predomcorp) * 100, 'ch': (self.wtdch/self.predomcorp)*100,
			            }
			try:
				return elements[element]
			except:
				return 0
		else:
			return 0

	def gettimelabel(self, element):
		elements = {'early': self.elabel, 'middle': self.mlabel, 'late': self.latelabel, 'unk': self.unklabel,
		            'frq': self.frqclass
		            }
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

	CREATE TABLE public.greek_dictionary (
	    entry_name character varying(64) COLLATE pg_catalog."default",
	    metrical_entry character varying(64) COLLATE pg_catalog."default",
	    unaccented_entry character varying(64) COLLATE pg_catalog."default",
	    id_number character varying(8) COLLATE pg_catalog."default",
	    entry_type character varying(8) COLLATE pg_catalog."default",
	    entry_options "char",
	    entry_body text COLLATE pg_catalog."default"
	)

	CREATE TABLE public.latin_dictionary (
	    entry_name character varying(64) COLLATE pg_catalog."default",
	    metrical_entry character varying(64) COLLATE pg_catalog."default",
	    id_number character varying(8) COLLATE pg_catalog."default",
	    entry_type character varying(8) COLLATE pg_catalog."default",
	    entry_key character varying(64) COLLATE pg_catalog."default",
	    entry_options "char",
	    entry_body text COLLATE pg_catalog."default"
	)

	Latin only: entry_key
	Greek only: unaccented_entry

	"""

	def __init__(self, entry_name, metrical_entry, id_number, entry_type, entry_options, entry_body):
		self.entry = entry_name
		self.metricalentry = metrical_entry
		self.id = id_number
		self.type = entry_type
		self.options = entry_options
		self.body = entry_body


class dbGreekWord(dbDictionaryEntry):
	"""

	an object that corresponds to a db line

	differs from Latin in self.language and unaccented_entry

	"""

	def __init__(self, entry_name, metrical_entry, id_number, entry_type, entry_options, entry_body, unaccented_entry):
		self.language = 'Greek'
		self.unaccented_entry = unaccented_entry
		super().__init__(entry_name, metrical_entry, id_number, entry_type, entry_options, entry_body)
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

	def __init__(self, entry_name, metrical_entry, id_number, entry_type, entry_options, entry_body,
	             entry_key):
		self.language = 'Latin'
		self.unaccented_entry = None
		super().__init__(entry_name, metrical_entry, id_number, entry_type, entry_options, entry_body)
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
		self.formlist = [re.sub(r'\'','',f) for f in self.formlist]

	def getformdict(self):
		fd = {}
		for f in self.formandidentificationlist:
			key = f.split(' ')[0]
			body = f[len(key)+1:]
			fd[key] = body
		return fd