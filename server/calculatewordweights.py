# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server.dbsupport.dbfunctions import setconnection


def findtemporalweights(language):
	"""
	figure out how many more words are 'late' than 'early', etc.
	you only need to run this once every major recalibration of the data
	the results are something like:
		greekwordweights = {'early': 7.883171009462467, 'middle': 1.9249406986576483, 'late': 1}

	these values get used by dbHeadwordObjects

	"""

	wordcounts = {'early': findchronologicalweights('early', language),
						'middle': findchronologicalweights('middle', language),
						'late': findchronologicalweights('late', language)}

	wordweights = {'early': round(wordcounts['late']/wordcounts['early'], 2),
						'middle': round(wordcounts['late']/wordcounts['middle'], 2),
						'late': 1}

	return wordweights


def findccorporaweights():
	"""
	figure out how many more words are 'gr' than 'lt', etc.
	you only need to run this once every major recalibration of the data
	the results are something like:
		corpus weights {'gr': 1.0, 'lt': 11.371559943504066, 'in': 28.130258550554572, 'dp': 27.492143340147255, 'ch': 129.8977636244065}

	counts {'gr': 98970519, 'lt': 9435706, 'in': 3540624, 'dp': 3606545, 'ch': 808509}

	:return:
	"""

	corpora = ['gr', 'lt', 'in', 'dp', 'ch']

	counts = {corpus: findcorpusweight(corpus+'_count', 'B') for corpus in corpora}

	maximum = max(counts.values())

	weights = {corpus: round(maximum/counts[corpus], 2) for corpus in counts}

	return weights


def findgeneraweights(language, collapsed=False):
	"""
	figure out how many more words are 'acta' than 'lt', etc.
	you only need to run this once every major recalibration of the data

	collapsing will merge genres under a broader heading

	genre weights {'acta': 87.55620093264861, 'alchem': 78.54326714323537, 'anthol': 17.8794679395616, '
	apocalyp': 128.41778277996625, 'apocryph': 97.23301212717142, 'apol': 7.102795647023107, 'astrol': 21.041150611322553,
	'astron': 46.93895013987165, 'biogr': 6.445097663489068, 'bucol': 426.1346816823719, 'caten': 5.245064661177692,
	'chronogr': 4.9056486958086225, 'comic': 30.518666658436672, 'comm': 1.0, 'concil': 17.88966774892297,
	'coq': 584.1332650730516, 'dialog': 7.030764848109672, 'docu': 4.0174947644631365, 'doxogr': 135.39717574463035,
	'eccl': 7.753557158120775, 'eleg': 211.86522117952893, 'encom': 13.472325815856639, 'epic': 19.652909665939266,
	'epigr': 11.557230234605704, 'epist': 4.769424536422383, 'evangel': 121.05917111470218, 'exeget': 1.260416459541563,
	'fab': 139.24986856928277, 'geogr': 11.322683081733352, 'gnom': 89.32842715102169, 'gramm': 9.610482775779314,
	'hagiogr': 23.68254029077695, 'hexametr': 114.88572535047633, 'hist': 1.4930493650897185, 'homilet': 7.166827401602196,
	'hymn': 48.98481536032972, 'hypoth': 13.86901343526268, 'iamb': 133.82017646740405, 'ignotum': 741644.8,
	'inscr': 3.2385486274771806, 'invectiv': 240.7234249732221, 'jurisprud': 55.31793584670637, 'lexicogr': 4.566307354383092, 'liturg': 593.4582699847964,
	'lyr': 453.92465648621356, 'magica': 103.2435389680446, 'math': 11.522763307436131, 'mech': 103.9934377037572,
	'med': 2.2936207732090597, 'metrolog': 326.44972159253473, 'mim': 2390.4747784045126, 'mus': 100.36671696427968,
	'myth': 196.04673539518902, 'narrfict': 15.678848257746724, 'nathist': 9.544677162689208, 'onir': 138.95505217994116,
	'orac': 260.29017653458743, 'orat': 6.5498475018071485, 'paradox': 262.35268315115496, 'parod': 822.9981690062698,
	'paroem': 66.10584675173031, 'perieg': 234.11613554934735, 'phil': 3.6845141514355126, 'physiognom': 649.2841321952287,
	'poem': 62.03403468710923, 'polyhist': 25.119809783805206, 'prophet': 106.80983927645602, 'pseudepigr': 653.2013387352475,
	'rhet': 8.528024874203133, 'satura': 281.288325874232, 'satyr': 123.0404552354566, 'schol': 5.910570563534397,
	'tact': 52.98295446427296, 'test': 75.579710071081, 'theol': 6.434358928088063, 'trag': 34.57084123824751}

	if you 'collapse' you will get:
		'relig': 0.5892025697245473
		'allrhet': 2.870955148487275

	:return:
	"""

	knownworkgenres = [
		'Acta',
		'Agric.',
		'Alchem.',
		'Anthol.',
		'Apocalyp.',
		'Apocryph.',
		'Apol.',
		'Astrol.',
		'Astron.',
		'Biogr.',
		'Bucol.',
		'Caten.',
		'Chronogr.',
		'Comic.',
		'Comm.',
		'Concil.',
		'Coq.',
		'Dialog.',
		'Docu.',
		'Doxogr.',
		'Eccl.',
		'Eleg.',
		'Encom.',
		'Epic.',
		'Epigr.',
		'Epist.',
		'Evangel.',
		'Exeget.',
		'Fab.',
		'Geogr.',
		'Gnom.',
		'Gramm.',
		'Hagiogr.',
		'Hexametr.',
		'Hist.',
		'Homilet.',
		'Hymn.',
		'Hypoth.',
		'Iamb.',
		'Ignotum',
		'Invectiv.',
		'Inscr.',
		'Jurisprud.',
		'Lexicogr.',
		'Liturg.',
		'Lyr.',
		'Magica',
		'Math.',
		'Mech.',
		'Med.',
		'Metrolog.',
		'Mim.',
		'Mus.',
		'Myth.',
		'Narr. Fict.',
		'Nat. Hist.',
		'Onir.',
		'Orac.',
		'Orat.',
		'Paradox.',
		'Parod.',
		'Paroem.',
		'Perieg.',
		'Phil.',
		'Physiognom.',
		'Poem.',
		'Polyhist.',
		'Prophet.',
		'Pseudepigr.',
		'Rhet.',
		'Satura',
		'Satyr.',
		'Schol.',
		'Tact.',
		'Test.',
		'Theol.',
		'Trag.'
	]
	cleanedknownworkgenres = [g.lower() for g in knownworkgenres]
	cleanedknownworkgenres = [re.sub(r'[\.\s]','',g) for g in cleanedknownworkgenres]

	counts = {g: findcorpusweight(g, language) for g in cleanedknownworkgenres}
	counts = {g: counts[g] for g in counts if counts[g] > 0}

	maximum = max(counts.values())
	weights = {g: round(maximum / counts[g], 2) for g in counts}

	if collapsed:
		relig = ['acta', 'apocalyp', 'apocryph', 'apol', 'caten', 'concil', 'eccl', 'evangel', 'exeget', 'hagiogr',
		          'homilet', 'liturg', 'prophet', 'pseudepigr', 'theol']
		relig = [r for r in relig if r in counts]

		allrhet = ['encom', 'invectiv', 'orat', 'rhet']
		allrhet = [r for r in allrhet if r in counts]

		weights = {weights[w]: w for w in weights if w not in relig}
		relcount = sum([counts[g] for g in relig])
		relwt = round(maximum / relcount,2)

		weights = {weights[w]: w for w in weights if w not in allrhet}
		rhetcount = sum([counts[g] for g in allrhet])
		rhetwt = round(maximum / rhetcount, 2)

		weights['allrelig'] = relwt
		weights['allrhet'] = rhetwt

	# print the actual counts
	# gcounts = [(counts[g], g) for g in counts]
	# gcounts.sort(reverse=True)
	# print('wordcounts')
	# for g in gcounts:
	# 	print(g[0],'\t',g[1])

	return weights


def findchronologicalweights(era, language):
	"""

	an initial call to dictionary_headword_wordcounts to figure out the relative weight of the different eras

	how many words are 'early' / 'middle' / 'late'

	:param era:
	:param language:
	:return:
	"""

	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	eramap = {
		'early': 'early_occurrences',
		'middle': 'middle_occurrences',
		'late': 'late_occurrences'
	}

	try:
		theera = eramap[era]
	except KeyError:
		return -1

	q = 'SELECT SUM({e}) FROM dictionary_headword_wordcounts WHERE entry_name ~ %s'.format(e=theera)

	if language == 'G':
		d = ('^[^a-z]',)
	else:
		d = ('^[a-z]',)

	curs.execute(q, d)
	thesum = curs.fetchall()
	thesum = thesum[0][0]

	return thesum


def findcorpusweight(corpus, language):
	"""


	:param corpus:
	:param language:
	:return:
	"""

	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	q = 'SELECT SUM({c}) FROM dictionary_headword_wordcounts'.format(c=corpus)

	w = ' WHERE entry_name ~ %s'

	# uh oh:  "~ '[^a-z]'" will grab Greek in PostgreSQL
	# worse still, [abcde...z] will also grab Greek
	# you have to give the range less 'w' if you are going to stop some sort of internal autoconversion to 'a-z'

	# contrast python's understanding of the same:
	# >>> x = ['βαλλ', 'ball']
	# >>> print([z for z in x if re.search(r'^[^a-z]', z)])
	# ['βαλλ']
	# >>> print([z for z in x if re.search(r'[^a-z]', z)])
	# ['βαλλ']

	if language == 'G':
		d = ('^[^abcdefghijklmnopqrstuvxyz]',)
	elif language == 'L':
		d = ('^[abcdefghijklmnopqrstuvxyz]',)
	else:
		d = ('',)

	if language == 'B':
		curs.execute(q)
	else:
		curs.execute(q+w, d)
	thesum = curs.fetchall()
	thesum = thesum[0][0]

	return thesum

"""
greek wordweights {'early': 7.72, 'middle': 1.92, 'late': 1}
corpus weights {'gr': 1.0, 'lt': 11.37, 'in': 28.13, 'dp': 27.49, 'ch': 129.89}
greek genre weights: {'agric': 16513.67, 'alchem': 79.21, 'anthol': 17.91, 'astrol': 21.02, 'astron': 47.08, 'biogr': 6.47, 'bucol': 425.46, 'chronogr': 4.9, 'comic': 30.51, 'comm': 1.0, 'coq': 598.04, 'dialog': 7.08, 'docu': 4.16, 'doxogr': 141.89, 'eleg': 212.14, 'encom': 13.47, 'epic': 19.64, 'epigr': 11.63, 'epist': 4.76, 'fab': 139.05, 'geogr': 11.35, 'gnom': 92.62, 'gramm': 9.86, 'hexametr': 115.44, 'hist': 1.5, 'hymn': 48.94, 'hypoth': 14.04, 'iamb': 133.7, 'ignotum': 477831.0, 'invectiv': 240.4, 'inscr': 3.72, 'jurisprud': 55.15, 'lexicogr': 4.58, 'lyr': 455.88, 'magica': 103.13, 'math': 11.52, 'mech': 103.85, 'med': 2.29, 'metrolog': 326.41, 'mim': 2387.23, 'mus': 101.38, 'myth': 195.94, 'narrfict': 15.67, 'nathist': 9.67, 'onir': 138.77, 'orac': 259.94, 'orat': 6.54, 'paradox': 262.33, 'parod': 823.62, 'paroem': 66.02, 'perieg': 233.86, 'phil': 3.7, 'physiognom': 648.4, 'poem': 61.97, 'polyhist': 24.98, 'rhet': 8.51, 'satura': 280.91, 'satyr': 126.45, 'schol': 5.99, 'tact': 52.95, 'test': 82.78, 'trag': 34.51, 0.59: 'relig', 'allrhet': 2.87}
latin genre weights: {'agric': 5.06, 'alchem': 631.89, 'anthol': 491.2, 'astrol': 5027.98, 'astron': 16.17, 'biogr': 9.35, 'bucol': 37.89, 'chronogr': 411.78, 'comic': 4.58, 'epic': 2.19, 'coq': 61.11, 'dialog': 72.9, 'docu': 9.18, 'doxogr': 227.13, 'eleg': 9.83, 'encom': 267.29, 'epigr': 102.17, 'epist': 1.98, 'fab': 81.09, 'geogr': 223.57, 'gnom': 78.87, 'gramm': 4.84, 'hexametr': 17.92, 'hist': 1.0, 'hymn': 7607.27, 'hypoth': 81.21, 'iamb': 21300.35, 'ignotum': 421.56, 'inscr': 1.96, 'jurisprud': 17.48, 'lexicogr': 21.1, 'lyr': 23.5, 'magica': 33471.97, 'math': 722.71, 'mech': 390506.33, 'med': 7.13, 'metrolog': 20919.98, 'mim': 1026.75, 'mus': 700.67, 'myth': 19525.32, 'narrfict': 11.33, 'nathist': 2.15, 'orac': 1171519.0, 'orat': 1.74, 'paradox': 16500.27, 'parod': 322.29, 'perieg': 73219.94, 'phil': 2.1, 'poem': 14.58, 'polyhist': 4.73, 'rhet': 2.61, 'satyr': 343.45, 'schol': 31.69, 'tact': 36.35, 'test': 67.67, 'trag': 12.86, 80.16: 'relig', 'allrhet': 1.04}

	greek wordcounts
	14812761 	 comm
	11761783 	 exeget
	9898136 	 hist
	6467218 	 med
	3998526 	 phil
	3980896 	 inscr
	3564399 	 docu
	3232465 	 lexicogr
	3109863 	 epist
	3020791 	 chronogr
	2824515 	 caten
	2472581 	 schol
	2305015 	 theol
	2289647 	 biogr
	2266016 	 orat
	2093642 	 dialog
	2085748 	 apol
	2069472 	 homilet
	1912832 	 eccl
	1740151 	 rhet
	1531167 	 nathist
	1501598 	 gramm
	1304776 	 geogr
	1285648 	 math
	1273736 	 epigr
	1099734 	 encom
	1055074 	 hypoth
	945378 	 narrfict
	828300 	 concil
	827220 	 anthol
	754061 	 epic
	704714 	 astrol
	626240 	 hagiogr
	592998 	 polyhist
	485518 	 comic
	429197 	 trag
	314597 	 astron
	302652 	 hymn
	279766 	 tact
	268606 	 jurisprud
	239035 	 poem
	224365 	 paroem
	186996 	 alchem
	178943 	 test
	169027 	 acta
	159922 	 gnom
	152470 	 apocryph
	146115 	 mus
	143634 	 magica
	142630 	 mech
	138872 	 prophet
	128315 	 hexametr
	122526 	 evangel
	117142 	 satyr
	115421 	 apocalyp
	110787 	 iamb
	106746 	 onir
	106530 	 fab
	104393 	 doxogr
	75600 	 myth
	69827 	 eleg
	63341 	 perieg
	61618 	 invectiv
	56985 	 orac
	56467 	 paradox
	52732 	 satura
	45381 	 metrolog
	34816 	 bucol
	32493 	 lyr
	24989 	 liturg
	24769 	 coq
	22845 	 physiognom
	22703 	 pseudepigr
	17985 	 parod
	6205 	 mim
	31 	 ignotum


	wordcounts
	1215991 	 hist
	1098321 	 jurisprud
	671410 	 orat
	626013 	 nathist
	599210 	 inscr
	590187 	 epist
	556759 	 phil
	534959 	 comm
	534933 	 epic
	448876 	 rhet
	255728 	 comic
	247930 	 polyhist
	243498 	 gramm
	232422 	 agric
	164327 	 med
	156727 	 eleg
	127677 	 docu
	125299 	 biogr
	103420 	 narrfict
	91130 	 trag
	87412 	 poem
	74244 	 astron
	65390 	 hexametr
	55533 	 lexicogr
	49860 	 lyr
	41281 	 fab
	36973 	 schol
	32229 	 tact
	30920 	 bucol
	19316 	 coq
	17312 	 test
	17108 	 dialog
	16010 	 hypoth
	14853 	 gnom
	11466 	 epigr
	6467 	 exeget
	5240 	 geogr
	5158 	 doxogr
	4383 	 encom
	3635 	 parod
	3457 	 caten
	3411 	 satyr
	2845 	 chronogr
	2570 	 apol
	2385 	 anthol
	1854 	 ignotum
	1854 	 alchem
	1672 	 mus
	1621 	 math
	1141 	 mim
	832 	 concil
	383 	 acta
	249 	 theol
	233 	 astrol
	212 	 eccl
	188 	 homilet
	154 	 hymn
	84 	 apocalyp
	82 	 hagiogr
	80 	 apocryph
	71 	 paradox
	60 	 myth
	56 	 metrolog
	55 	 iamb
	35 	 magica
	16 	 perieg
	16 	 paroem
	5 	 pseudepigr
	5 	 liturg
	3 	 mech
	1 	 orac


"""
