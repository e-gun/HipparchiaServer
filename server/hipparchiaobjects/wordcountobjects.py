# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re

from server import hipparchia
from server.hipparchiaobjects.morphologyobjects import MorphPossibilityObject


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
		elif hipparchia.config['FALLBACKTODOUBLESTRIKES'] == 'yes':
			self.tlabel = '𝕋'
			self.glabel = '𝔾'
			self.llabel = '𝕃'
			self.dlabel = '𝔻'
			self.ilabel = '𝕀'
			self.clabel = 'ℂ'
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
		except KeyError:
			return 0

	def getlabel(self, element):
		ldict = {
			'total': self.tlabel, 'gr': self.glabel, 'lt': self.llabel, 'dp': self.dlabel, 'in': self.ilabel, 'ch': self.clabel
			}
		try:
			return ldict[element]
		except KeyError:
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

	hipparchiaDB=# select count(entry_name) from dictionary_headword_wordcounts;;
	 count
	--------
	 152692
	(1 row)

	"""

	greekworderaweights = {'early': 7.75, 'middle': 1.92, 'late': 1}
	corporaweights = {'gr': 1.0, 'lt': 10.68, 'in': 27.77, 'dp': 26.76, 'ch': 124.85}

	greekgenreweights = {'acta': 85.38, 'alchem': 72.13,
						'anthol': 17.68, 'apocalyp': 117.69, 'apocryph': 89.77,
						'apol': 7.0, 'astrol': 20.68, 'astron': 44.72, 'biogr':
						6.39, 'bucol': 416.66, 'caten': 5.21, 'chronogr': 4.55,
						'comic': 29.61, 'comm': 1.0, 'concil': 16.75, 'coq':
						532.74, 'dialog': 7.1, 'docu': 2.66, 'doxogr': 130.84,
						'eccl': 7.57, 'eleg': 188.08, 'encom': 13.17, 'epic':
						19.36, 'epigr': 10.87, 'epist': 4.7, 'evangel': 118.66,
						'exeget': 1.24, 'fab': 140.87, 'geogr': 10.74, 'gnom':
						88.54, 'gramm': 8.65, 'hagiogr': 22.83, 'hexametr':
						110.78, 'hist': 1.44, 'homilet': 6.87, 'hymn': 48.18,
						'hypoth': 12.95, 'iamb': 122.22, 'ignotum': 122914.2,
						'invectiv': 238.54, 'inscr': 1.91, 'jurisprud': 51.42,
						'lexicogr': 4.14, 'liturg': 531.5, 'lyr': 213.43,
						'magica': 85.38, 'math': 9.91, 'mech': 103.44, 'med':
						2.25, 'metrolog': 276.78, 'mim': 2183.94, 'mus': 96.32,
						'myth': 201.78, 'narrfict': 14.62, 'nathist': 9.67,
						'onir': 145.15, 'orac': 240.47, 'orat': 6.67, 'paradox':
						267.32, 'parod': 831.51, 'paroem': 65.58, 'perieg':
						220.38, 'phil': 3.69, 'physiognom': 628.77, 'poem': 62.82,
						'polyhist': 24.91, 'prophet': 95.51, 'pseudepigr': 611.65,
						'rhet': 8.67, 'satura': 291.58, 'satyr': 96.78, 'schol':
						5.56, 'tact': 52.01, 'test': 66.53, 'theol': 6.28, 'trag':
						35.8, 'allrelig': 0.58, 'allrhet': 2.9}

	latingenreweights = {'agric': 5.27, 'astron': 17.15, 'biogr':
						9.87, 'bucol': 40.42, 'comic': 4.22, 'comm': 2.25, 'coq':
						60.0, 'dialog': 1132.94, 'docu': 6.19, 'eleg': 8.35,
						'encom': 404.84, 'epic': 2.37, 'epigr': 669.7, 'epist':
						2.06, 'fab': 25.41, 'gnom': 147.29, 'gramm': 5.75,
						'hexametr': 20.07, 'hist': 1.0, 'hypoth': 763.05,
						'ignotum': 586.93, 'inscr': 1.3, 'jurisprud': 1.11,
						'lexicogr': 27.68, 'lyr': 24.77, 'med': 7.26, 'mim':
						1046.32, 'narrfict': 11.69, 'nathist': 1.94, 'orat': 1.81,
						'parod': 339.44, 'phil': 2.3, 'poem': 14.35, 'polyhist':
						4.75, 'rhet': 2.71, 'satura': 23.01, 'tact': 37.6, 'trag':
						13.3, 'allrelig': 0, 'allrhet': 1.08}

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
		elif hipparchia.config['FALLBACKTODOUBLESTRIKES'] == 'yes':
			self.qlabel = '𝕢'
			self.elabel = '𝕖'
			self.mlabel = '𝕞'
			self.latelabel = '𝕝'
			self.unklabel = '𝕦'
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
		elements = {'early': self.early, 'middle': self.middle, 'late': self.late,
		            'unk': self.t - (self.early + self.middle + self.late)
		            }
		try:
			return elements[element]
		except KeyError:
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
			except KeyError:
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
			except KeyError:
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


	hipparchiaDB=# select * from greek_morphology where observed_form='καταμείναντεϲ';
	observed_form |  xrefs   | prefixrefs |                                                                       possible_dictionary_forms
	---------------+----------+------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------
	καταμείναντεϲ | 58645029 |            | <possibility_1>καταμένω<xref_value>58645029</xref_value><xref_kind>9</xref_kind><transl>stay</transl><analysis>aor part act masc nom/voc pl</analysis></possibility_1>+
	           |          |            |
	(1 row)


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
		thepossible = re.findall(possiblefinder, self.possibleforms)
		return len(thepossible)

	def getpossible(self):
		possiblefinder = re.compile(r'(<possibility_(\d{1,2})>)(.*?)<xref_value>(.*?)</xref_value><xref_kind>(.*?)</xref_kind>(.*?)</possibility_\d{1,2}>')
		thepossible = re.findall(possiblefinder, self.possibleforms)
		listofpossibilitiesobjects = [MorphPossibilityObject(p, self.prefixcount) for p in thepossible]
		return listofpossibilitiesobjects