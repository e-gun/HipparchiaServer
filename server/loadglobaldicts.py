# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from server.dbsupport.dbfunctions import loadallauthorsasobjects, loadallworksasobjects, loadallworksintoallauthors, \
	findchronologicalweights, findcorpusweight
from server.listsandsession.listmanagement import dictitemstartswith
from server.listsandsession.sessiondicts import buildaugenresdict, buildworkgenresdict, buildauthorlocationdict, \
	buildworkprovenancedict

"""
this stuff gets loaded up front so you have access to all author and work info all the time
otherwise you'll hit the DB too often and ask the same question over and over again: a serious source of lag
"""

authordict = loadallauthorsasobjects()
workdict = loadallworksasobjects()
authordict = loadallworksintoallauthors(authordict, workdict)

authorgenresdict = buildaugenresdict(authordict)
authorlocationdict = buildauthorlocationdict(authordict)
workgenresdict = buildworkgenresdict(workdict)
workprovenancedict = buildworkprovenancedict(workdict)

print('building specialized sublists')
tlgauthors = dictitemstartswith(authordict, 'universalid', 'gr')
tlgworks = dictitemstartswith(workdict, 'universalid', 'gr')
latauthors = dictitemstartswith(authordict, 'universalid', 'lt')
latworks = dictitemstartswith(workdict, 'universalid', 'lt')
insauthors = dictitemstartswith(authordict, 'universalid', 'in')
insworks = dictitemstartswith(workdict, 'universalid', 'in')
ddpauthors = dictitemstartswith(authordict, 'universalid', 'dp')
ddpworks = dictitemstartswith(workdict, 'universalid', 'dp')
chrauthors = dictitemstartswith(authordict, 'universalid', 'ch')
chrworks = dictitemstartswith(workdict, 'universalid', 'ch')

listmapper = {
	'gr': {'a': tlgauthors, 'w': tlgworks},
	'lt': {'a': latauthors, 'w': latworks},
	'dp': {'a': insauthors, 'w': insworks},
	'in': {'a': ddpauthors, 'w': ddpworks},
	'ch': {'a': chrauthors, 'w': chrworks},
}


def findtemporalweights():
	"""
	figure out how many more words are 'late' than 'early', etc.
	you only need to run this once every major recalibration of the data
	the results are something like:
		greekwordweights = {'early': 7.883171009462467, 'middle': 1.9249406986576483, 'late': 1}
	"""

	greekwordcounts = { 'early': findchronologicalweights('early'),
						'middle': findchronologicalweights('middle'),
						'late': findchronologicalweights('late') }

	greekwordweights = {'early': greekwordcounts['late']/greekwordcounts['early'],
						'middle': greekwordcounts['late']/greekwordcounts['middle'],
						'late': 1}

	print('greekwordweights',greekwordweights)

	return


def findccorporaweights():
	"""
	figure out how many more words are 'gr' than 'lt', etc.
	you only need to run this once every major recalibration of the data
	the results are something like:
		corpus weights {'gr': 1.0, 'lt': 11.371559943504066, 'in': 28.130258550554572, 'dp': 27.492143340147255, 'ch': 129.8977636244065}

	:return:
	"""

	corpora = ['gr', 'lt', 'in', 'dp', 'ch']

	counts = {corpus: findcorpusweight(corpus+'_count') for corpus in corpora}

	max = counts['gr']

	weights = {corpus: max/counts[corpus] for corpus in counts}

	print('corpus weights',weights)

	return


def findgeneraweights():
	"""
	figure out how many more words are 'acta' than 'lt', etc.
	you only need to run this once every major recalibration of the data

	genre weights {'acta': 87.55620093264861, 'alchem': 78.54326714323537, 'anthol': 17.8794679395616, '
	apocalyp': 128.41778277996625, 'apocryph': 97.23301212717142, 'apol': 7.102795647023107, 'astrol': 21.041150611322553,
	'astron': 46.93895013987165, 'biogr': 6.445097663489068, 'bucol': 426.1346816823719, 'caten': 5.245064661177692,
	'chronogr': 4.9056486958086225, 'comic': 30.518666658436672, 'comm': 1.0, 'concil': 17.88966774892297,
	'coq': 584.1332650730516, 'dialog': 7.030764848109672, 'docu': 4.0174947644631365, 'doxogr': 135.39717574463035,
	'eccl': 7.753557158120775, 'eleg': 211.86522117952893, 'encom': 13.472325815856639, 'epic': 19.652909665939266,
	'epigr': 2.5296844770800417, 'epist': 4.769424536422383, 'evangel': 121.05917111470218, 'exeget': 1.260416459541563,
	'fab': 139.24986856928277, 'geogr': 11.322683081733352, 'gnom': 89.32842715102169, 'gramm': 9.610482775779314,
	'hagiogr': 23.68254029077695, 'hexametr': 114.88572535047633, 'hist': 1.4930493650897185, 'homilet': 7.166827401602196,
	'hymn': 48.98481536032972, 'hypoth': 13.86901343526268, 'iamb': 133.82017646740405, 'ignotum': 741644.8,
	'invectiv': 240.7234249732221, 'jurisprud': 55.31793584670637, 'lexicogr': 4.566307354383092, 'liturg': 593.4582699847964,
	'lyr': 453.92465648621356, 'magica': 103.2435389680446, 'math': 11.522763307436131, 'mech': 103.9934377037572,
	'med': 2.2936207732090597, 'metrolog': 326.44972159253473, 'mim': 2390.4747784045126, 'mus': 100.36671696427968,
	'myth': 196.04673539518902, 'narrfict': 15.678848257746724, 'nathist': 9.544677162689208, 'onir': 138.95505217994116,
	'orac': 260.29017653458743, 'orat': 6.5498475018071485, 'paradox': 262.35268315115496, 'parod': 822.9981690062698,
	'paroem': 66.10584675173031, 'perieg': 234.11613554934735, 'phil': 3.6845141514355126, 'physiognom': 649.2841321952287,
	'poem': 62.03403468710923, 'polyhist': 25.119809783805206, 'prophet': 106.80983927645602, 'pseudepigr': 653.2013387352475,
	'rhet': 8.528024874203133, 'satura': 281.288325874232, 'satyr': 123.0404552354566, 'schol': 5.910570563534397,
	'tact': 52.98295446427296, 'test': 75.579710071081, 'theol': 6.434358928088063, 'trag': 34.57084123824751}

	:return:
	"""

	knownworkgenres = [
		'Acta',
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

	counts = {g: findcorpusweight(g) for g in cleanedknownworkgenres}

	max = counts['comm']
	weights = {corpus: max / counts[corpus] for corpus in counts}
	print('genre weights', weights)
	return


# uncomment when you need to be shown new weight values upon startup and are willing to wait for the weights
# findtemporalweights()
# findccorporaweights()
# findgeneraweights()




"""
genre wordcounts

20	ignotum
6205	mim
18023	parod
22708	pseudepigr
22845	physiognom
24994	liturg
25393	coq
32677	lyr
34808	bucol
45437	metrolog
52732	satura
56538	paradox
56986	orac
61618	invectiv
63357	perieg
70011	eleg
75660	myth
106520	fab
106746	onir
109551	doxogr
110842	iamb
115505	apocalyp
120553	satyr
122526	evangel
129110	hexametr
138872	prophet
142633	mech
143669	magica
147787	mus
152550	apocryph
166049	gnom
169410	acta
188850	alchem
196255	test
224381	paroem
239109	poem
268139	jurisprud
279956	tact
302806	hymn
316004	astron
429058	trag}
486027	comic
590486	polyhist
626322	hagiogr
704947	astrol
754743	epic
801466	inscr
829132	concil
829605	anthol
946045	narrfict
1069499	hypoth
1100990	encom
1283430	epigr
1287269	math
1310016	geogr
1543408	gramm
1554049	nathist
1739312	rhet
1913044	eccl
2069660	homilet
2088318	apol
2109713	dialog
2264617	orat
2301423	biogr
2305264	theol
2509554	schol
2827972	caten
3023636	chronogr
3109997	epist
3248335	lexicogr
4025740	phil
6467022	med
9934632	hist
11768250	exeget
14832896	comm

"""