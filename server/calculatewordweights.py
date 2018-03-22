# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server.hipparchiaobjects.connectionobject import ConnectionObject


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


def workobjectgeneraweights(language, iscollapsed, workobjects):
	"""

	compare the results...

	greek genre weights: {'alchem': 72.13, 'anthol': 17.68, 'astrol': 20.68, 'astron': 44.72, 'biogr': 6.39, 'bucol': 416.66, 'chronogr': 4.55, 'comic': 29.61, 'comm': 1.0, 'coq': 532.74, 'dialog': 7.1, 'docu': 2.56, 'doxogr': 130.84, 'eleg': 188.08, 'encom': 13.17, 'epic': 19.36, 'epigr': 10.87, 'epist': 4.7, 'fab': 140.87, 'geogr': 10.74, 'gnom': 88.54, 'gramm': 8.65, 'hexametr': 110.78, 'hist': 1.44, 'hymn': 48.18, 'hypoth': 12.95, 'iamb': 122.22, 'ignotum': 122914.2, 'invectiv': 238.54, 'inscr': 1.67, 'jurisprud': 51.42, 'lexicogr': 4.14, 'lyr': 213.43, 'magica': 85.38, 'math': 9.91, 'mech': 103.44, 'med': 2.25, 'metrolog': 276.78, 'mim': 2183.94, 'mus': 96.32, 'myth': 201.78, 'narrfict': 14.62, 'nathist': 9.67, 'onir': 145.15, 'orac': 240.47, 'orat': 6.67, 'paradox': 267.32, 'parod': 831.51, 'paroem': 65.58, 'perieg': 220.38, 'phil': 3.69, 'physiognom': 628.77, 'poem': 62.82, 'polyhist': 24.91, 'rhet': 8.67, 'satura': 291.58, 'satyr': 96.78, 'schol': 5.56, 'tact': 52.01, 'test': 66.53, 'trag': 35.8, 'allrelig': 0.58, 'allrhet': 2.9}


	:param language:
	:param iscollapsed:
	:param workobjects:
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

	counts = {g: findgenreweightfromworkobject(g, language, workobjects) for g in knownworkgenres}
	counts = {re.sub(r'[\.\s]', '', g.lower()): counts[g] for g in counts}
	counts = {g: counts[g] for g in counts if counts[g] > 0}

	maximum = max(counts.values())
	weights = {g: round(maximum / counts[g], 2) for g in counts }

	if iscollapsed:
		relig = ['acta', 'apocalyp', 'apocryph', 'apol', 'caten', 'concil', 'eccl', 'evangel', 'exeget', 'hagiogr',
		          'homilet', 'liturg', 'prophet', 'pseudepigr', 'theol']
		relig = [r for r in relig if r in counts]

		allrhet = ['encom', 'invectiv', 'orat', 'rhet']
		allrhet = [r for r in allrhet if r in counts]

		weights = {weights[w]: w for w in weights if w not in relig}
		relcount = sum([counts[g] for g in relig])
		try:
			relwt = round(maximum / relcount, 2)
		except ZeroDivisionError:
			relwt = 0

		weights = {weights[w]: w for w in weights if w not in allrhet}
		rhetcount = sum([counts[g] for g in allrhet])
		try:
			rhetwt = round(maximum / rhetcount, 2)
		except ZeroDivisionError:
			rhetwt = 0

		weights['allrelig'] = relwt
		weights['allrhet'] = rhetwt

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
		relwt = round(maximum / relcount, 2)

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
	# 	print(g[0], '\t', g[1])

	return weights


def findchronologicalweights(era, language):
	"""

	an initial call to dictionary_headword_wordcounts to figure out the relative weight of the different eras

	how many words are 'early' / 'middle' / 'late'

	:param era:
	:param language:
	:return:
	"""

	dbconnection = ConnectionObject('autocommit')
	cursor = dbconnection.cursor()

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

	cursor.execute(q, d)
	thesum = cursor.fetchall()
	thesum = thesum[0][0]

	return thesum


def findgenreweightfromworkobject(genre, language, workdict):
	"""

	how many words belong to any given corpus?

	use work.wordcount + work.workgenre

	:param genre:
	:param language:
	:param workdict:
	:return:
	"""

	wordlist = [workdict[w].wordcount for w in workdict if workdict[w].workgenre == genre and (workdict[w].language==language or workdict[w].language==None)]
	totalwords = sum(wordlist)

	# w = "{:,}".format(totalwords)
	# print('{g}\t{t}'.format(g=genre, t=w))

	return totalwords


def findcorpusweight(corpus, language):
	"""

	how many words belong to any given corpus?

	there is an interesting problem here:

	find the total number of words in a corpus:

		hipparchiaDB=# select sum("iamb") FROM dictionary_headword_wordcounts where "iamb" > 0;

		sum = 112412

	compare with the total words in the corpus as reported by "/getsearchlistcontents"

		total words: 89,502

	the issue is homonymns: this turns 89k words into 112k counts.

	the size of any given genre is accordingly distorted

	the question is whether or not this distortion is uniform between genres.

	this function is less accurate than if you use "work.wordcount" & "work.workgenre"

	:param corpus:
	:param language:
	:return:
	"""

	dbconnection = ConnectionObject('autocommit')
	cursor = dbconnection.cursor()

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
		cursor.execute(q)
	else:
		cursor.execute(q+w, d)
	thesum = cursor.fetchall()
	thesum = thesum[0][0]

	# w = "{:,}".format(thesum)
	# print('{c}\t{n}'.format(c=corpus, n=w))

	return thesum

"""
greek wordweights {'early': 7.75, 'middle': 1.92, 'late': 1}
corpus weights {'gr': 1.0, 'lt': 10.68, 'in': 27.77, 'dp': 26.76, 'ch': 124.85}
greek genre weights: {'acta': 85.38, 'alchem': 72.13, 'anthol': 17.68, 'apocalyp': 117.69, 'apocryph': 89.77, 'apol': 7.0, 'astrol': 20.68, 'astron': 44.72, 'biogr': 6.39, 'bucol': 416.66, 'caten': 5.21, 'chronogr': 4.55, 'comic': 29.61, 'comm': 1.0, 'concil': 16.75, 'coq': 532.74, 'dialog': 7.1, 'docu': 2.66, 'doxogr': 130.84, 'eccl': 7.57, 'eleg': 188.08, 'encom': 13.17, 'epic': 19.36, 'epigr': 10.87, 'epist': 4.7, 'evangel': 118.66, 'exeget': 1.24, 'fab': 140.87, 'geogr': 10.74, 'gnom': 88.54, 'gramm': 8.65, 'hagiogr': 22.83, 'hexametr': 110.78, 'hist': 1.44, 'homilet': 6.87, 'hymn': 48.18, 'hypoth': 12.95, 'iamb': 122.22, 'ignotum': 122914.2, 'invectiv': 238.54, 'inscr': 1.91, 'jurisprud': 51.42, 'lexicogr': 4.14, 'liturg': 531.5, 'lyr': 213.43, 'magica': 85.38, 'math': 9.91, 'mech': 103.44, 'med': 2.25, 'metrolog': 276.78, 'mim': 2183.94, 'mus': 96.32, 'myth': 201.78, 'narrfict': 14.62, 'nathist': 9.67, 'onir': 145.15, 'orac': 240.47, 'orat': 6.67, 'paradox': 267.32, 'parod': 831.51, 'paroem': 65.58, 'perieg': 220.38, 'phil': 3.69, 'physiognom': 628.77, 'poem': 62.82, 'polyhist': 24.91, 'prophet': 95.51, 'pseudepigr': 611.65, 'rhet': 8.67, 'satura': 291.58, 'satyr': 96.78, 'schol': 5.56, 'tact': 52.01, 'test': 66.53, 'theol': 6.28, 'trag': 35.8}
latin genre weights: {'agric': 5.27, 'astron': 17.15, 'biogr': 9.87, 'bucol': 40.42, 'comic': 4.22, 'comm': 2.25, 'coq': 60.0, 'dialog': 1132.94, 'docu': 6.19, 'eleg': 8.35, 'encom': 404.84, 'epic': 2.37, 'epigr': 669.7, 'epist': 2.06, 'fab': 25.41, 'gnom': 147.29, 'gramm': 5.75, 'hexametr': 20.07, 'hist': 1.0, 'hypoth': 763.05, 'ignotum': 586.93, 'inscr': 1.3, 'jurisprud': 1.11, 'lexicogr': 27.68, 'lyr': 24.77, 'med': 7.26, 'mim': 1046.32, 'narrfict': 11.69, 'nathist': 1.94, 'orat': 1.81, 'parod': 339.44, 'phil': 2.3, 'poem': 14.35, 'polyhist': 4.75, 'rhet': 2.71, 'satura': 23.01, 'tact': 37.6, 'trag': 13.3}

gr_count	102549980
lt_count	9599518
in_count	3692171
dp_count	3832371
ch_count	821412

	nb: there is a difference between the following two 'identical' items
	
		dp_count=3832371 
		Docu.=4,108,146
		
	the real issue is that dp_count is a count of headword matches (i.e., parseable words). Docu is a count of all words (and
	parts of words...)

GREEK
Comm.	10,939,364
Exeget.	8,846,704
Hist.	7,622,971
Inscr.	5,736,904
Med.	4,863,957
Docu.	4,108,146
Phil.	2,960,832
Lexicogr.	2,645,407
Chronogr.	2,403,380
Epist.	2,325,234
Caten.	2,101,547
Schol.	1,968,642
Theol.	1,742,265
Biogr.	1,712,397
Orat.	1,640,409
Homilet.	1,593,483
Apol.	1,562,718
Dialog.	1,540,843
Eccl.	1,445,473
Gramm.	1,265,294
Rhet.	1,261,290
Nat. Hist.	1,130,914
Math.	1,103,492
Geogr.	1,018,141
Epigr.	1,006,589
Hypoth.	844,452
Encom.	830,935
Narr. Fict.	748,164
Concil.	653,271
Anthol.	618,917
Epic.	564,955
Astrol.	528,929
Hagiogr.	479,241
Polyhist.	439,216
Comic.	369,416
Trag.	305,584
Astron.	244,611
Hymn.	227,033
Jurisprud.	212,761
Tact.	210,323
Poem.	174,143
Paroem.	166,820
Test.	164,425
Alchem.	151,659
Magica	128,128
Acta	128,126
Gnom.	123,554
Apocryph.	121,854
Prophet.	114,531
Mus.	113,577
Satyr.	113,029
Mech.	105,758
Hexametr.	98,752
Apocalyp.	92,952
Evangel.	92,189
Iamb.	89,502
Doxogr.	83,611
Fab.	77,654
Onir.	75,365
Eleg.	58,163
Myth.	54,213
Lyr.	51,255
Perieg.	49,638
Invectiv.	45,859
Orac.	45,491
Paradox.	40,923
Metrolog.	39,523
Satura	37,517
Bucol.	26,255
Liturg.	20,582
Coq.	20,534
Pseudepigr.	17,885
Physiognom.	17,398
Parod.	13,156
Mim.	5,009
Ignotum	89
Agric.	0


LATIN
Hist.	1,040,043
Jurisprud.	936,812
Inscr.	801,908
Orat.	573,366
Nat. Hist.	535,714
Epist.	505,214
Comm.	462,756
Phil.	452,337
Epic.	438,017
Rhet.	384,113
Comic.	246,612
Polyhist.	218,891
Agric.	197,449
Gramm.	181,030
Docu.	167,928
Med.	143,202
Eleg.	124,507
Biogr.	105,398
Narr. Fict.	88,986
Trag.	78,188
Poem.	72,498
Astron.	60,652
Hexametr.	51,826
Satura	45,194
Lyr.	41,989
Fab.	40,934
Lexicogr.	37,569
Tact.	27,663
Bucol.	25,732
Coq.	17,334
Gnom.	7,061
Parod.	3,064
Encom.	2,569
Ignotum	1,772
Epigr.	1,553
Hypoth.	1,363
Mim.	994
Dialog.	918
Acta	0
Alchem.	0
Anthol.	0
Apocalyp.	0
Apocryph.	0
Apol.	0
Astrol.	0
Caten.	0
Chronogr.	0
Concil.	0
Doxogr.	0
Eccl.	0
Evangel.	0
Exeget.	0
Geogr.	0
Hagiogr.	0
Homilet.	0
Hymn.	0
Iamb.	0
Invectiv.	0
Liturg.	0
Magica	0
Math.	0
Mech.	0
Metrolog.	0
Mus.	0
Myth.	0
Onir.	0
Orac.	0
Paradox.	0
Paroem.	0
Perieg.	0
Physiognom.	0
Prophet.	0
Pseudepigr.	0
Satyr.	0
Schol.	0
Test.	0
Theol.	0

"""
