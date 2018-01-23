# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server.dbsupport.dbfunctions import resultiterator, setconnection
from server.formatting.wordformatting import acuteorgrav
from server.searching.searchfunctions import buildbetweenwhereextension


def mostcommonwords():
	"""

	fetch N most common Greek and Latin

	build an exclusion list from this and return it: wordstoskip

	but first prune the common word list of words you nevertheless are interested in

	:return: wordstoskip
	"""

	wordswecareabout = {
		'facio', 'possum', 'video', 'dico²', 'vaco', 'volo¹', 'habeo', 'do', 'vis',
		'ἔδω', 'δέω¹', 'δεῖ', 'δέομαι', 'ἔχω', 'λέγω¹'
	}

	dbconnection = setconnection('not_autocommit', readonlyconnection=False)
	cursor = dbconnection.cursor()

	lim = 50

	qtemplate = """
	SELECT entry_name,total_count FROM dictionary_headword_wordcounts 
		WHERE entry_name ~ '[{yesorno}a-zA-Z]' ORDER BY total_count DESC LIMIT {lim};
	"""

	counts = dict()

	# grab the raw data: a greek query and a latin query
	for yn in {'', '^'}:
		cursor.execute(qtemplate.format(yesorno=yn, lim=lim))
		tophits = resultiterator(cursor)
		tophits = {t[0]: t[1] for t in tophits}
		counts.update(tophits)

	# results = ['{wd} - {ct}'.format(wd=c, ct=counts[c]) for c in counts]
	#
	# for r in results:
	# 	print(r)

	"""
	qui¹ - 252258
	et - 227461
	in - 183991
	edo¹ - 159485
	is - 132687
	sum¹ - 118388
	hic - 100294
	non - 96510
	ab - 92200
	ut - 76251
	si - 68954
	ad - 68314
	cum - 67464
	a - 65642
	ex - 65447
	video - 59061
	eo¹ - 58429
	tu - 57950
	ego - 53963
	quis¹ - 52881
	dico² - 48947
	ille - 44237
	sed - 44146
	de - 42799
	neque - 41911
	facio - 41864
	possum - 41647
	atque - 40752
	vel - 39938
	sui - 39732
	res - 38768
	verus - 36390
	quam - 36164
	vaco - 34484
	volo¹ - 34173
	verum - 33960
	aut - 32020
	ipse - 31921
	huc - 31591
	habeo - 30683
	venio - 30506
	do - 30195
	omne - 29962
	ito - 28879
	magnus - 28258
	vis - 27077
	b - 25918
	alius² - 25430
	for - 25212
	idem - 24600
	ὁ - 11774357
	καί - 4507884
	τίϲ - 2470088
	ἔδω - 1975836
	δέ - 1956680
	εἰμί - 1871655
	δέω¹ - 1791349
	ἐν - 1772435
	δεῖ - 1760164
	δέομαι - 1758948
	εἰϲ - 1462703
	αὐτόϲ - 1370472
	οὐ - 1080583
	τιϲ - 1057788
	οὗτοϲ - 958661
	γάροϲ - 768756
	γάρον - 768664
	γάρ - 768318
	μένω - 664175
	ἐγώ - 637360
	μέν - 633860
	τῷ - 588950
	ζεύϲ - 523874
	ἡμόϲ - 523162
	κατά - 514164
	ἐπί - 509941
	ὡϲ - 494902
	διά - 471148
	πρόϲ - 445770
	ϲύ - 442052
	πᾶϲ - 441801
	προϲάμβ - 435408
	τε - 434017
	ἐκ - 430405
	ἕ - 426187
	ὅϲ - 423775
	ἀλλά - 422349
	γίγνομαι - 407624
	ὅϲτιϲ - 393943
	ἤ¹ - 391617
	ἤ² - 389621
	ἔχω - 389518
	λέγω¹ - 370838
	μή - 365352
	ὅτι¹ - 358520
	ὅτι² - 356884
	τῇ - 347564
	τήιοϲ - 328408
	ἀπό - 320122
	εἰ - 312686

	"""

	wordstoskip = counts.keys() - wordswecareabout

	dbconnection.commit()
	cursor.close()

	return wordstoskip


def cleansentence(sentence):
	"""

	if we are using the marked up line, then a lot of gunk needs to go

	:param sentence:
	:return:
	"""

	return sentence


def recursivesplit(tosplit, listofsplitlerms):
	"""

	split and keep splitting

	:param tosplit:
	:param splitterm:
	:return:
	"""


	while listofsplitlerms:
		cutter = listofsplitlerms.pop()
		split = [t.split(cutter) for t in tosplit]
		flattened = [item for sublist in split for item in sublist]
		tosplit = recursivesplit(flattened, listofsplitlerms)

	return tosplit


def findsentences(authortable, searchobject, cursor):
	"""



	:param authortable:
	:param searchobject:
	:param cursor:
	:return:
	"""

	so = searchobject

	r = so.indexrestrictions[authortable]
	whereextensions = ''

	if r['type'] == 'temptable':
		# make the table
		q = r['where']['tempquery']
		cursor.execute(q)
		# now you can work with it
		whereextensions = 'EXISTS (SELECT 1 FROM {tbl}_includelist incl WHERE incl.includeindex = {tbl}.index'.format(
			tbl=authortable)
		whr = 'WHERE {xtn} )'.format(xtn=whereextensions)
	elif r['type'] == 'between':
		whereextensions = buildbetweenwhereextension(authortable, so)
		# contains a trailing ' AND'
		whereextensions = whereextensions[:-4]
		whr = 'WHERE {xtn} '.format(xtn=whereextensions)
	elif r['type'] == 'unrestricted':
		whr = ''
	else:
		# should never see this
		print('error in substringsearch(): unknown whereclause type', r['type'])
		whr = ''

	# need to add to the whereclause something that skips titles

	query = 'SELECT {c} FROM {db} {whr}'.format(c=so.usecolumn, db=authortable, whr=whr)
	cursor.execute(query)
	results = resultiterator(cursor)

	wholetext = ' '.join([r[0] for r in results])

	htmlstrip = re.compile(r'<.*?>')
	wholetext = re.sub(htmlstrip, '', wholetext)
	wholetext = re.sub('&nbsp;', '', wholetext)

	# need to split at all possible sentence ends
	# latin: ['.', '?', '!']
	# greek: ['.', ';', '!', '·']

	terminations = ['.', '?', '!', '·', ';']
	allsentences = recursivesplit([wholetext], terminations)

	terms = [acuteorgrav(t) for t in so.lemma.formlist]
	lookingfor = "|".join(terms)
	lookingfor = '({lf})'.format(lf=lookingfor)

	matches = [s for s in allsentences if re.search(lookingfor, s)]

	for m in enumerate(matches):
		print(m[0], m[1])

	return matches
