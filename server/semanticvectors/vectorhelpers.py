# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import time
from string import punctuation

from server.dbsupport.dbfunctions import resultiterator, setconnection
from server.formatting.wordformatting import acuteorgrav, buildhipparchiatranstable, removegravity, stripaccents, \
	tidyupterm
from server.hipparchiaobjects.helperobjects import ProgressPoll
from server.searching.proximitysearching import grableadingandlagging
from server.searching.searchdispatching import searchdispatcher
from server.searching.searchfunctions import buildbetweenwhereextension


# bleh: numpy and scipy will fail to install on FreeBSD 11.x
# the work-around functions below might be needed instead: presumably there are markedly slower...


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

	grab a chunk of a database

	turn it into a collection of sentences

	look for the relevant lemma in them

	return those sentences that contain the lemmatized word

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
	# need to turn off semicolon in latin...
	# latin: ['.', '?', '!']
	# greek: ['.', ';', '!', '·']

	terminations = ['.', '?', '!', '·', ';']
	allsentences = recursivesplit([wholetext], terminations)

	if so.lemma:
		terms = [acuteorgrav(t) for t in so.lemma.formlist]
		lookingfor = "|".join(terms)
		lookingfor = '({lf})'.format(lf=lookingfor)
	else:
		lookingfor = so.seeking

	matches = [s for s in allsentences if re.search(lookingfor, s)]

	extrapunct = '\′‵’‘·̆́“”„—†⌈⌋⌊⟫⟪❵❴⟧⟦(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓'
	punct = re.compile('[{s}]'.format(s=re.escape(punctuation + extrapunct)))

	cleanedmatches = [tidyupterm(m, punct) for m in matches]

	# for m in enumerate(cleanedmatches):
	# 	print(m[0], m[1])

	return cleanedmatches


def findwordvectorset(listofwordclusters):
	"""

	get ready to vectorize by splitting and cleaning a set of lines or sentences

	:param listofwordclusters:
	:return:
	"""

	# find all words in use
	allwords = [c.split(' ') for c in listofwordclusters]
	# flatten
	allwords = [item for sublist in allwords for item in sublist]

	minimumgreek = re.compile('[α-ωἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]')
	greekwords = [w for w in allwords if re.search(minimumgreek, w)]

	trans = buildhipparchiatranstable()
	latinwords = [w for w in allwords if not re.search(minimumgreek, w)]

	allwords = [removegravity(w) for w in greekwords] + [stripaccents(w, trans) for w in latinwords]
	allwords = set(allwords) - {''}

	return allwords


def tidyupmophdict(morphdict):
	"""

	:return:
	"""

	morphdict = {k: v for k, v in morphdict.items() if v is not None}
	morphdict = {k: set([p.getbaseform() for p in morphdict[k].getpossible()]) for k in morphdict.keys()}

	# {'θεῶν': {'θεόϲ', 'θέα', 'θεάω', 'θεά'}, 'πώ': {'πω'}, 'πολλά': {'πολύϲ'}, 'πατήρ': {'πατήρ'}, ... }

	# over-aggressive? more thought/care might be required here
	delenda = mostcommonwords()
	morphdict = {k: v for k, v in morphdict.items() if v - delenda == v}

	return morphdict


def findverctorenvirons(hitdict, searchobject):
	"""

	grab the stuff around the term you were looking for and return that as the environs

	:param hitdict:
	:param searchobject:
	:return:
	"""

	dbconnection = setconnection('autocommit', readonlyconnection=False)
	cursor = dbconnection.cursor()

	so = searchobject

	if so.lemma:
		supplement = so.lemma.dictionaryentry
	else:
		supplement = so.termone

	environs = list()
	if so.session['searchscope'] == 'W':
		for h in hitdict:
			leadandlag = grableadingandlagging(hitdict[h], searchobject, cursor)
			environs.append('{a} {b} {c}'.format(a=leadandlag['lead'], b=supplement, c=leadandlag['lag']))

	else:
		# there is a double-count issue if you get a word 2x in 2 lines and then grab the surrounding lines

		distance = int(so.proximity)
		# note that you can slowly iterate through it all or more quickly grab just what you need at one gulp...
		tables = dict()
		for h in hitdict:
			if hitdict[h].authorid not in tables:
				tables[hitdict[h].authorid] = list()
			if hitdict[h].index not in tables[hitdict[h].authorid]:
				tables[hitdict[h].authorid] += list(range(hitdict[h].index-distance, hitdict[h].index+distance))

		tables = {t: set(tables[t]) for t in tables}
		# print('tables', tables)

		# grab all of the lines from all of the tables
		linesdict = dict()
		for t in tables:
			linesdict[t] = bulklinegrabber(t, so.usecolumn, 'index', tables[t], cursor)

		# generate the environs
		dropdupes = set()

		for h in hitdict:
			need = ['{t}@{i}'.format(t=hitdict[h].authorid, i=i) for i in range(hitdict[h].index-distance, hitdict[h].index+distance)]
			for n in need:
				if n not in dropdupes:
					dropdupes.add(n)
					try:
						environs.append(linesdict[hitdict[h].authorid][n])
					except KeyError:
						pass

	cursor.close()

	return environs


def bulklinegrabber(table, column, criterion, setofcriteria, cursor):
	"""


	:param table:
	:param setofindices:
	:return:
	"""

	qtemplate = 'SELECT {cri}, {col} FROM {t} WHERE {cri} = ANY(%s)'
	q = qtemplate.format(col=column, t=table, cri=criterion)
	d = (list(setofcriteria),)

	cursor.execute(q, d)
	lines = resultiterator(cursor)

	contents = {'{t}@{i}'.format(t=table, i=l[0]): l[1] for l in lines}

	return contents


def finddblinefromsentence(thissentence, modifiedsearchobject):
	"""

	get a locus from a random sentence coughed up by the vector corpus

	:param thissentence:
	:param searchobject:
	:return:
	"""

	nullpoll = ProgressPoll(time.time())
	mso = modifiedsearchobject
	mso.lemma = None
	mso.proximatelemma = None
	mso.searchtype = 'phrase'
	mso.usecolumn = 'accented_line'
	mso.usewordlist = 'polytonic'
	mso.accented = True
	mso.seeking = ' '.join(thissentence[:6])
	mso.termone = mso.seeking
	mso.termtwo = ' '.join(thissentence[-5:])
	hits = searchdispatcher(mso, nullpoll)

	# if len(hits) > 1:
	# 	print('findlocusfromsentence() found {h} hits when looking for {s}'.format(h=len(hits), s=mso.seeking))

	return hits


def mostcommonwords():
	"""

	fetch N most common Greek and Latin

	build an exclusion list from this and return it: wordstoskip

	but first prune the common word list of words you nevertheless are interested in

	:return: wordstoskip
	"""

	wordswecareabout = {
		'facio', 'possum', 'video', 'dico²', 'vaco', 'volo¹', 'habeo', 'do', 'vis',
		'ἔδω', 'δέω¹', 'δεῖ', 'δέομαι', 'ἔχω', 'λέγω¹', 'φημί', 'θεόϲ', 'ποιέω', 'πολύϲ',
		'ἄναξ', 'λόγοϲ'
	}

	dbconnection = setconnection('not_autocommit', readonlyconnection=False)
	cursor = dbconnection.cursor()

	qtemplate = """
	SELECT entry_name,total_count FROM dictionary_headword_wordcounts 
		WHERE entry_name ~ '[{yesorno}a-zA-Z]' ORDER BY total_count DESC LIMIT {lim};
	"""

	counts = dict()

	# grab the raw data: a greek query and a latin query
	# note that different limits have been set for each language
	for gl in {('', 50), ('^', 75)}:
		yesorno = gl[0]
		lim = gl[1]
		cursor.execute(qtemplate.format(yesorno=yesorno, lim=lim))
		tophits = resultiterator(cursor)
		tophits = {t[0]: t[1] for t in tophits}
		counts.update(tophits)

	# results = ['{wd} - {ct}'.format(wd=c, ct=counts[c]) for c in counts]
	#
	# for r in results:
	# 	print(r)

	wordstoskip = counts.keys() - wordswecareabout

	dbconnection.commit()
	cursor.close()

	return wordstoskip


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
περί - 307599
θεόϲ - 304809
ἐάν - 304374
φημί - 287951
ἄλλοϲ - 277173
ἐκάϲ - 271358
ἄν¹ - 269787
ἄνω¹ - 258911
πηρόϲ - 250986
παρά - 250106
ἀνά - 248289
αὐτοῦ - 243025
ποιέω - 239161
πολύϲ - 237066
ἄναξ - 230384
λόγοϲ - 228499
ἄνα - 226730
ἄν² - 226125
οὖν - 217914
οὕτωϲ - 208591
οὐδείϲ - 205806
μετά - 199346
ἔτι - 197966
ὑπό - 194308
"""
