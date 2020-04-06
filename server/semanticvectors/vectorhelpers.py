# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
import time
from string import punctuation

import numpy as np
import psycopg2
from sklearn.manifold import TSNE

from server import hipparchia
from server.dbsupport.dblinefunctions import dblineintolineobject, grabonelinefromwork, worklinetemplate
from server.dbsupport.lexicaldbfunctions import findcountsviawordcountstable, querytotalwordcounts
from server.dbsupport.miscdbfunctions import resultiterator
from server.dbsupport.tablefunctions import assignuniquename
from server.formatting.wordformatting import acuteorgrav, basiclemmacleanup, buildhipparchiatranstable, \
	elidedextrapunct, extrapunct, minimumgreek, removegravity, stripaccents, tidyupterm
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.hipparchiaobjects.wordcountobjects import dbWordCountObject
from server.searching.searchdispatching import searchdispatcher
from server.searching.searchfunctions import buildbetweenwhereextension
from server.semanticvectors.wordbaggers import buildflatbagsofwords
from server.startup import lemmatadict
# bleh: numpy and scipy will fail to install on FreeBSD 11.x
# the work-around functions below might be needed instead: presumably there are markedly slower...
from server.textsandindices.textandindiceshelperfunctions import getrequiredmorphobjects

vectorranges = {
	'ldacomponents': range(1, 51),
	'ldaiterations': range(1, 26),
	'ldamaxfeatures': range(1, 5001),
	'ldamaxfreq': range(1, 101),
	'ldaminfreq': range(1, 21),
	'ldamustbelongerthan': range(1, 5),
	'vcutlem': range(1, 101),
	'vcutloc': range(1, 101),
	'vcutneighb': range(1, 101),
	'vdim': range(25, 501),
	'vdsamp': range(1, 21),
	'viterat': range(1, 21),
	'vminpres': range(1, 21),
	'vnncap': range(1, 26),
	'vsentperdoc': range(1, 6),
	'vwindow': range(2, 21)
}

vectordefaults = {
	'ldacomponents': hipparchia.config['LDACOMPONENTS'],
	'ldaiterations': hipparchia.config['LDAITERATIONS'],
	'ldamaxfeatures': hipparchia.config['LDAMAXFEATURES'],
	'ldamaxfreq': hipparchia.config['LDAMAXFREQ'],
	'ldaminfreq': hipparchia.config['LDAMINFREQ'],
	'ldamustbelongerthan': hipparchia.config['LDAMUSTBELONGERTHAN'],
	'vcutlem': hipparchia.config['VECTORDISTANCECUTOFFLEMMAPAIR'],
	'vcutloc': hipparchia.config['VECTORDISTANCECUTOFFLOCAL'],
	'vcutneighb': hipparchia.config['VECTORDISTANCECUTOFFNEARESTNEIGHBOR'],
	'vdim': hipparchia.config['VECTORDIMENSIONS'],
	'vdsamp': hipparchia.config['VECTORDOWNSAMPLE'],
	'viterat': hipparchia.config['VECTORTRAININGITERATIONS'],
	'vminpres': hipparchia.config['VECTORMINIMALPRESENCE'],
	'vnncap': hipparchia.config['NEARESTNEIGHBORSCAP'],
	'vsentperdoc': hipparchia.config['SENTENCESPERDOCUMENT'],
	'vwindow': hipparchia.config['VECTORWINDOW'],
}


vectorlabels = {
	'ldacomponents': 'LDA: no. of topics',
	'ldaiterations': 'LDA: iterations',
	'ldamaxfeatures': 'LDA: features',
	'ldamaxfreq': 'LDA: max frequency',
	'ldaminfreq': 'LDA: min frequency',
	'ldamustbelongerthan': 'LDA: min length',
	'vcutlem': 'Cutoff: Lemma pairs',
	'vcutloc': 'Cutoff: Literal distance',
	'vcutneighb': 'Cutoff: Nearest Neighbors',
	'vdim': 'Vector Dimensions',
	'vdsamp': 'Vector downsampling',
	'viterat': 'Training iterations',
	'vminpres': 'Minimal term presence',
	'vnncap': 'Nearest Neighbors cap',
	'vsentperdoc': 'Sentences per document',
	'vwindow': 'Proximity window size'
}


def cleantext(texttostrip):
	"""

	if we are using the marked up line, then a lot of gunk needs to go

	:param sentence:
	:return:
	"""

	# PROBLEM #1: names
	# you will get bad 'sentences' in the Latin with things like M. Tullius Cicero.
	# could check for 'sentences' that end with a single letter: '(\s\w)\.' --> '\1'
	# but this will still leave you with 'Ti' and similar items
	#
	# PROBLEM #2: dates
	# the following is not 4 sentences: a. d. VIII Id. Nov.
	#
	# USEFUL FOR THE SOLUTION: marked_up_line is case sensitive
	#
	# Note that the case of the substitute is off; but all we really care about is getting the headword right

	praenomina = {
		'A.': 'Aulus',
		'App.': 'Appius',
		'C.': 'Caius',
		'G.': 'Gaius',
		'Cn.': 'Cnaius',
		'Gn.': 'Gnaius',
		'D.': 'Decimus',
		'L.': 'Lucius',
		'M.': 'Marcus',
		'M.’': 'Manius',
		'N.': 'Numerius',
		'P.': 'Publius',
		'Q.': 'Quintus',
		'S.': 'Spurius',
		'Sp.': 'Spurius',
		'Ser.': 'Servius',
		'Sex.': 'Sextus',
		'T.': 'Titus',
		'Ti': 'Tiberius',
		'V.': 'Vibius'
	}

	datestrings = {
		'a.': 'ante',
		'd.': 'dies',
		'Id.': 'Idibus',
		'Kal.': 'Kalendas',
		'Non.': 'Nonas',
		'prid.': 'pridie',
		'Ian.': 'Ianuarias',
		'Feb.': 'Februarias',
		'Mart.': 'Martias',
		'Apr.': 'Aprilis',
		'Mai.': 'Maias',
		'Iun.': 'Iunias',
		'Quint.': 'Quintilis',
		'Sext.': 'Sextilis',
		'Sept.': 'Septembris',
		'Oct.': 'Octobris',
		'Nov.': 'Novembris',
		'Dec.': 'Decembris'
	}

	searchdict = {**praenomina, **datestrings}

	htmlstrip = re.compile(r'<.*?>')
	wholetext = re.sub(htmlstrip, '', texttostrip)
	wholetext = re.sub('&nbsp;', '', wholetext)
	wholetext = re.sub(r'\w+\.', lambda x: replaceabbreviations(x.group(0), searchdict), wholetext)
	# speakers in plays? need to think about catching:  'XY. (says something) AB. (replies)'

	return wholetext


def replaceabbreviations(foundstring, searchdict):
	"""

	pass lambda results through this: make sure a sentence end is not really a common abbrevation

	:param foundstring:
	:param searchdict:
	:return:
	"""

	if foundstring in searchdict.keys():
		# reduce ...
		# foundstring = re.sub(r'\.', '', foundstring)
		# or expand...
		foundstring = searchdict[foundstring]

	return foundstring


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

	:param authortable:
	:param searchobject:
	:param cursor:
	:return:
	"""

	so = searchobject

	r = so.indexrestrictions[authortable]

	if r['type'] == 'temptable':
		# make the table
		q = r['where']['tempquery']
		avoidcollisions = assignuniquename()
		q = re.sub('_includelist', '_includelist_{a}'.format(a=avoidcollisions), q)
		cursor.execute(q)
		# now you can work with it
		wtempate = """
		EXISTS
			(SELECT 1 FROM {tbl}_includelist_{a} incl WHERE incl.includeindex = {tbl}.index
		"""
		whereextensions = wtempate.format(a=avoidcollisions, tbl=authortable)
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

	# vanilla grab-it-all
	query = 'SELECT {wtmpl} FROM {db} {whr}'.format(wtmpl=worklinetemplate, db=authortable, whr=whr)

	# vs. something that skips titles (but might drop the odd other thing or two...)
	# but this noes not play nicely with 'temptable'
	# if re.search('WHERE', whr):
	# 	whr = whr + ' AND'
	# else:
	# 	whr = 'WHERE'
	# query = 'SELECT {c} FROM {db} {whr} level_00_value != %s'.format(c=so.usecolumn, db=authortable, whr=whr)
	data = ('t',)
	cursor.execute(query, data)
	results = resultiterator(cursor)
	results = [dblineintolineobject(line) for line in results]

	# kill off titles and salutations: dangerous if there is a body l1 value of 't' out there
	results = [r for r in results if r.l1 not in ['t', 'sa']]

	results = parsevectorsentences(so, results)

	return results


def parsevectorsentences(searchobject, lineobjects):
	"""

	take raw lines, join them together, clean them and then return tuples of lines and ids

	the ids may or may not be needed later

	sentencetuples:
		[('lt0588w001_ln_8', 'sed ii erunt fere qui expertes litterarum graecarum nihil rectum nisi quod ipsorum moribus conueniat putabunt'),
		('lt0588w001_ln_10', 'hi si didicerint non eadem omnibus esse honesta atque turpia sed omnia maiorum institutis iudicari non admirabuntur nos in graiorum uirtutibus exponendis mores eorum secutos'),
		('lt0588w001_ln_13', 'neque enim cimoni fuit turpe atheniensium summo uiro sororem germanam habere in matrimonio quippe cum ciues eius eodem uterentur instituto'),
		(id, text), ...]

	:param searchobject:
	:param lineobjects:
	:return:
	"""
	so = searchobject

	requiresids = ['semanticvectorquery', 'nearestneighborsquery', 'sentencesimilarity']

	columnmap = {'marked_up_line': 'markedup', 'accented_line': 'polytonic', 'stripped_line': 'stripped'}
	col = columnmap[so.usecolumn]

	if so.vectorquerytype in requiresids:
		wholetext = ' '.join(['⊏{i}⊐{t}'.format(i=l.getlineurl(), t=getattr(l, col)) for l in lineobjects])
	else:
		wholetext = ' '.join([getattr(l, col) for l in lineobjects])

	if so.usecolumn == 'marked_up_line':
		wholetext = cleantext(wholetext)

	# need to split at all possible sentence ends
	# need to turn off semicolon in latin...
	# latin: ['.', '?', '!']
	# greek: ['.', ';', '!', '·']

	terminations = ['.', '?', '!', '·', ';']
	allsentences = recursivesplit([wholetext], terminations)

	# print('type(so.lemma)', type(so.lemma))
	if so.vectorquerytype == 'cosdistbysentence':
		terms = [acuteorgrav(t) for t in so.lemma.formlist]
		lookingfor = "|".join(terms)
		lookingfor = '({lf})'.format(lf=lookingfor)
	else:
		lookingfor = so.seeking

	if lookingfor != '.':
		# uv problem...
		allsentences = [basiclemmacleanup(s) for s in allsentences]
		matches = [s for s in allsentences if re.search(lookingfor, s)]
	else:
		matches = allsentences

	# hyphenated line-ends are a problem
	matches = [re.sub(r'-\s{1,2}', '', m) for m in matches]

	# more cleanup
	matches = [m.lower() for m in matches]
	matches = [' '.join(m.split()) for m in matches]

	# how many sentences per document?
	# do values >1 make sense? Perhaps in dramatists...
	bundlesize = so.sentencebundlesize

	if bundlesize > 1:
		# https://stackoverflow.com/questions/44104729/grouping-every-three-items-together-in-list-python
		matches = [' '.join(bundle) for bundle in zip(*[iter(matches)] * bundlesize)]

	# FIXME: there is a problem with  τ’ and δ’ and the rest (refactor via indexmaker.py)
	# nevertheless, most of these words are going to be stopwords anyway
	punct = re.compile('[{s}]'.format(s=re.escape(punctuation + elidedextrapunct)))

	if so.vectorquerytype in requiresids:
		# now we mark the source of every sentence by turning it into a tuple: (location, text)
		previousid = lineobjects[0].getlineurl()
		idfinder = re.compile(r'⊏(.*?)⊐')
		taggedmatches = list()
		for m in matches:
			ids = re.findall(idfinder, m)
			if ids:
				taggedmatches.append((ids[0], re.sub(idfinder, '', m)))
				previousid = ids[-1]
			else:
				taggedmatches.append((previousid, m))

		cleanedmatches = [(lineid, tidyupterm(m, punct)) for lineid, m in taggedmatches]
	else:
		cleanedmatches = [(n, tidyupterm(m, punct)) for n, m in enumerate(matches)]

	return cleanedmatches


def findwordvectorset(listofwordclusters: list) -> set:
	"""

	get ready to vectorize by splitting and cleaning a set of lines or sentences

	:param listofwordclusters:
	:return:
	"""

	# find all words in use
	allwords = [c.split(' ') for c in listofwordclusters]
	# flatten
	allwords = [item for sublist in allwords for item in sublist]

	greekwords = [w for w in allwords if re.search(minimumgreek, w)]

	trans = buildhipparchiatranstable()
	latinwords = [w for w in allwords if not re.search(minimumgreek, w)]

	allwords = [removegravity(w) for w in greekwords] + [stripaccents(w, trans) for w in latinwords]

	punct = re.compile('[{s}]'.format(s=re.escape(punctuation + extrapunct)))

	allwords = [re.sub(punct, '', w) for w in allwords]

	allwords = set(allwords) - {''}

	return allwords


def convertmophdicttodict(morphdict: dict) -> dict:
	"""

	return a dict of dicts of possibilities for all of the words we will be using

	key = word-in-use
	value = { maybeA, maybeB, maybeC}

	{'θεῶν': {'θεόϲ', 'θέα', 'θεάω', 'θεά'}, 'πώ': {'πω'}, 'πολλά': {'πολύϲ'}, 'πατήρ': {'πατήρ'}, ... }

	:return:
	"""

	dontskipunknowns = True

	parseables = {k: v for k, v in morphdict.items() if v is not None}
	parseables = {k: set([p.getbaseform() for p in parseables[k].getpossible()]) for k in parseables.keys()}

	if dontskipunknowns:
		# if the base for was not found, associate a word with itself
		unparseables = {k: {k} for k, v in morphdict.items() if v is None}
		newmorphdict = {**unparseables, **parseables}
	else:
		newmorphdict = parseables

	# over-aggressive? more thought/care might be required here
	# the definitely changes the shape of the bags of words...
	delenda = mostcommonheadwords()
	newmorphdict = {k: v for k, v in newmorphdict.items() if v - delenda == v}

	return newmorphdict


def buildlemmatizesearchphrase(phrase: str) -> str:
	"""

	turn a search into a collection of headwords

	:param phrase:
	:return:
	"""

	# phrase = 'vias urbis munera'
	phrase = phrase.strip()
	words = phrase.split(' ')

	morphdict = getrequiredmorphobjects(words, furtherdeabbreviate=True)
	morphdict = convertmophdicttodict(morphdict)
	# morphdict {'munera': {'munero', 'munus'}, 'urbis': {'urbs'}, 'uias': {'via', 'vio'}}

	listoflistofheadwords = buildflatbagsofwords(morphdict, [words])
	# [['via', 'vio', 'urbs', 'munero', 'munus']]

	lemmatizesearchphrase = ' '.join(listoflistofheadwords[0])
	# lemmatizesearchphrase = 'via vio urbs munus munero'

	return lemmatizesearchphrase


def bruteforcefinddblinefromsentence(thissentence, modifiedsearchobject):
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
	mso.poll = nullpoll
	hits = searchdispatcher(mso)

	# if len(hits) > 1:
	# 	print('findlocusfromsentence() found {h} hits when looking for {s}'.format(h=len(hits), s=mso.seeking))

	return hits


def finddblinesfromsentences(thissentence, sentencestuples, cursor):
	"""

	given a sentencelist ['word1', 'word2', word3', ...] , look for a match in a sentence tuple collection:
		[(universalid1, text1), (universalid2, text2), ...]

	returns a list of dblines

	:param thissentence:
	:param sentencestuples:
	:return:
	"""

	thissentence = ' '.join(thissentence)

	matches = list()
	for s in sentencestuples:
		cleans = s[1].strip()
		if cleans == thissentence:
			matches.append(s[0])

	fetchedlines = convertlineuidstolineobject(matches, cursor)

	return fetchedlines


def convertlineuidstolineobject(listoflines, cursor):
	"""

	given a list of universalids, fetch the relevant lines

	would be more efficient if you grabbed all of them at once
	for any given table.

	but note that these lists are usually just one item long

	:return:
	"""

	fetchedlines = list()
	for uid in listoflines:
		fetchedlines.append(convertsingleuidtodblineobject(uid, cursor))

	return fetchedlines


def convertsingleuidtodblineobject(lineuid, cursor):
	"""

	:param lineuid:
	:param cursor:
	:return:
	"""

	# print('convertsingleuidtodblineobject() lineuid', lineuid)

	db = lineuid.split('_')[0][:6]
	ln = lineuid.split('_')[-1]

	try:
		myline = grabonelinefromwork(db, ln, cursor)
		fetchedline = dblineintolineobject(myline)
	except psycopg2.ProgrammingError:
		# psycopg2.ProgrammingError: relation "l" does not exist
		fetchedline = None

	return fetchedline


def mostcommoninflectedforms(cheat=True) -> set:
	"""

	figure out what gets used the most

	can use this to drop items from sentences before we get to
	headwords and their homonym problems

	hipparchiaDB=# SELECT entry_name,total_count FROM wordcounts_a ORDER BY total_count DESC LIMIT 10;
	entry_name | total_count
	------------+-------------
	ad         |       68000
	a          |       65487
	aut        |       32020
	ab         |       26047
	atque      |       21686
	autem      |       20164
	ac         |       19066
	an         |       12405
	ante       |        9535
	apud       |        7399
	(10 rows)

	hipparchiaDB=# SELECT entry_name,total_count FROM wordcounts_α ORDER BY total_count DESC LIMIT 10;
	entry_name | total_count
	------------+-------------
	ἀπό        |      256257
	αὐτοῦ      |      242718
	ἄν         |      225966
	ἀλλά       |      219506
	ἀλλ        |      202609
	αὐτόν      |      163403
	αὐτῶν      |      145216
	αὐτῷ       |      134328
	αἱ         |      102667
	αὐτόϲ      |       89056

	mostcommoninflectedforms()
	('καί', 4507887)
	('δέ', 1674979)
	('τό', 1496102)
	('τοῦ', 1286914)
	('τῶν', 1127343)
	('τήν', 1053085)
	('τῆϲ', 935988)
	('ὁ', 874987)
	...
	('οἷϲ', 40448)
	('πολλά', 40255)
	('δραχμαί', 40212)
	('εἶπεν', 40154)
	('ἄλλων', 40104)
	...

	('c', 253099)
	('et', 227463)
	('in', 183970)
	('est', 105956)
	('non', 96510)
	('ut', 75705)
	('ad', 68000)
	('cum', 66544)
	('a', 65487)
	('si', 62655)
	('quod', 56694)
	...

	('ipsa', 5372)
	('inquit', 5342)
	('nomine', 5342)
	('sint', 5342)
	('nobis', 5317)
	('primum', 5297)
	('itaque', 5271)
	('unde', 5256)
	('illi', 5227)
	('siue', 5208)
	('illud', 5206)
	('eos', 5186)
	('pace', 5114)
	('parte', 5049)
	('n', 5032)
	('tempore', 5018)
	('satis', 5007)
	('rerum', 4999)
	...

	:param cheat:
	:return:
	"""

	if not cheat:
		dbconnection = ConnectionObject()
		dbcursor = dbconnection.cursor()

		latinletters = 'abcdefghijklmnopqrstuvwxyz'
		greekletters = '0αβψδεφγηιξκλμνοπρϲτυωχθζ'

		# needed for initial probe
		# limit = 50
		# qtemplate = """
		# SELECT entry_name,total_count FROM wordcounts_{letter} ORDER BY total_count DESC LIMIT {lim}
		# """

		qtemplate = """
		SELECT entry_name FROM wordcounts_{letter} WHERE total_count > %s ORDER BY total_count DESC 
		"""

		greekmorethan = 40000
		latinmorethan = 5031
		countlist = list()

		for letters, cap in [(latinletters, latinmorethan), (greekletters, greekmorethan)]:
			langlist = list()
			for l in letters:
				data = (cap,)
				dbcursor.execute(qtemplate.format(letter=l), data)
				tophits = resultiterator(dbcursor)
				langlist.extend([t[0] for t in tophits])
			# langlist = sorted(langlist, key=lambda x: x[1], reverse=True)
			countlist.extend(langlist)

		print('mostcommoninflectedforms()')
		mcif = set(countlist)
		print(mcif)
	else:
		mcif = {'ita', 'a', 'inquit', 'ego', 'die', 'nunc', 'nos', 'quid', 'πάντων', 'ἤ', 'με', 'θεόν', 'δεῖ', 'for',
		        'igitur', 'ϲύν', 'b', 'uers', 'p', 'ϲου', 'τῷ', 'εἰϲ', 'ergo', 'ἐπ', 'ὥϲτε', 'sua', 'me', 'πρό', 'sic',
		        'aut', 'nisi', 'rem', 'πάλιν', 'ἡμῶν', 'φηϲί', 'παρά', 'ἔϲτι', 'αὐτῆϲ', 'τότε', 'eos', 'αὐτούϲ',
		        'λέγει', 'cum', 'τόν', 'quidem', 'ἐϲτιν', 'posse', 'αὐτόϲ', 'post', 'αὐτῶν', 'libro', 'm', 'hanc',
		        'οὐδέ', 'fr', 'πρῶτον', 'μέν', 'res', 'ἐϲτι', 'αὐτῷ', 'οὐχ', 'non', 'ἐϲτί', 'modo', 'αὐτοῦ', 'sine',
		        'ad', 'uero', 'fuit', 'τοῦ', 'ἀπό', 'ea', 'ὅτι', 'parte', 'ἔχει', 'οὔτε', 'ὅταν', 'αὐτήν', 'esse',
		        'sub', 'τοῦτο', 'i', 'omnes', 'break', 'μή', 'ἤδη', 'ϲοι', 'sibi', 'at', 'mihi', 'τήν', 'in', 'de',
		        'τούτου', 'ab', 'omnia', 'ὃ', 'ἦν', 'γάρ', 'οὐδέν', 'quam', 'per', 'α', 'autem', 'eius', 'item', 'ὡϲ',
		        'sint', 'length', 'οὗ', 'λόγον', 'eum', 'ἀντί', 'ex', 'uel', 'ἐπειδή', 're', 'ei', 'quo', 'ἐξ',
		        'δραχμαί', 'αὐτό', 'ἄρα', 'ἔτουϲ', 'ἀλλ', 'οὐκ', 'τά', 'ὑπέρ', 'τάϲ', 'μάλιϲτα', 'etiam', 'haec',
		        'nihil', 'οὕτω', 'siue', 'nobis', 'si', 'itaque', 'uac', 'erat', 'uestig', 'εἶπεν', 'ἔϲτιν', 'tantum',
		        'tam', 'nec', 'unde', 'qua', 'hoc', 'quis', 'iii', 'ὥϲπερ', 'semper', 'εἶναι', 'e', '½', 'is', 'quem',
		        'τῆϲ', 'ἐγώ', 'καθ', 'his', 'θεοῦ', 'tibi', 'ubi', 'pro', 'ἄν', 'πολλά', 'τῇ', 'πρόϲ', 'l', 'ἔϲται',
		        'οὕτωϲ', 'τό', 'ἐφ', 'ἡμῖν', 'οἷϲ', 'inter', 'idem', 'illa', 'n', 'se', 'εἰ', 'μόνον', 'ac', 'ἵνα',
		        'ipse', 'erit', 'μετά', 'μοι', 'δι', 'γε', 'enim', 'ille', 'an', 'sunt', 'esset', 'γίνεται', 'omnibus',
		        'ne', 'ἐπί', 'τούτοιϲ', 'ὁμοίωϲ', 'παρ', 'causa', 'neque', 'cr', 'ἐάν', 'quos', 'ταῦτα', 'h', 'ante',
		        'ἐϲτίν', 'ἣν', 'αὐτόν', 'eo', 'ὧν', 'ἐπεί', 'οἷον', 'sed', 'ἀλλά', 'ii', 'ἡ', 't', 'te', 'ταῖϲ', 'est',
		        'sit', 'cuius', 'καί', 'quasi', 'ἀεί', 'o', 'τούτων', 'ἐϲ', 'quae', 'τούϲ', 'minus', 'quia', 'tamen',
		        'iam', 'd', 'διά', 'primum', 'r', 'τιϲ', 'νῦν', 'illud', 'u', 'apud', 'c', 'ἐκ', 'δ', 'quod', 'f',
		        'quoque', 'tr', 'τί', 'ipsa', 'rei', 'hic', 'οἱ', 'illi', 'et', 'πῶϲ', 'φηϲίν', 'τοίνυν', 's', 'magis',
		        'unknown', 'οὖν', 'dum', 'text', 'μᾶλλον', 'λόγοϲ', 'habet', 'τοῖϲ', 'qui', 'αὐτοῖϲ', 'suo', 'πάντα',
		        'uacat', 'τίϲ', 'pace', 'ἔχειν', 'οὐ', 'κατά', 'contra', 'δύο', 'ἔτι', 'αἱ', 'uet', 'οὗτοϲ', 'deinde',
		        'id', 'ut', 'ὑπό', 'τι', 'lin', 'ἄλλων', 'τε', 'tu', 'ὁ', 'cf', 'δή', 'potest', 'ἐν', 'eam', 'tum',
		        'μου', 'nam', 'θεόϲ', 'κατ', 'ὦ', 'cui', 'nomine', 'περί', 'atque', 'δέ', 'quibus', 'ἡμᾶϲ', 'τῶν',
		        'eorum'}

	return mcif


def uselessforeignwords() -> set:
	"""

	stuff that clogs up the data, esp in the papyri, etc

	quite incomplete at the moment; a little thought could derive a decent amount of it algorithmically

	:return:
	"""

	useless = {'text', 'length', 'unknown', 'break', 'uestig', 'uac'}

	return useless


def mostcommonheadwords(cheat=True) -> set:
	"""

	fetch N most common Greek and Latin

	build an exclusion list from this and return it: wordstoskip

	but first prune the common word list of words you nevertheless are interested in

	:return: wordstoskip
	"""

	if cheat:
		# this is what you will get if you calculate
		# since it tends not to change, you can cheat unless/until you modify
		# either the dictionaries or wordswecareabout or the cutoff...
		wordstoskip = {'omne', 'νωδόϲ', 'aut', 'eccere', 'quin', 'tu', 'ambi',
			'fue', 'hau¹', 'ἠμέν', 'eu', 'διό', 'πρόϲ', 'μέχριπερ', 'αὐτόϲ',
			'περί', 'ἀτάρ', 'ὄφρα', 'ῥά¹', 'πω²', 'cata', 'apage', 'τίϲ',
			'per1', 'ne³', 'αὐτοῦ', 'ἕ', 'de²', 'chaere', 'ἄν²', 'ἤ¹', 'euoe',
			'for', 'neque', 'εἶἑν', 'b', 'ab', 'vaha', 'ἐπί²', 'ὅτι', 'Juno',
			'euhoe', 'sum¹', 'au', 'μένω', 'sine', 'oho', 'sui', 'ὡϲ', 'ehem',
			'istic¹', 'τοι¹', 'pro²', 'ἤ²', 'io¹', 'τήιοϲ', 'em³', 'ohe',
			'abusque', 'ἆρα²', 'alius²', 'μέϲφι', 'atque', 'fu', 'em²', 'γοῦν',
			'proh', 'ἔτι', 'cis', 'vel', 'παι', 'bombax', 'τίη', 'πηρόϲ',
			'babae', 'en', 'edo¹', 'θην', 'δέ', 'si', 'ai¹', 'in', 'γάρον',
			'ἐάν', 'heia', 'οὐδείϲ', 'hui', 'eho', 'quis¹', 'οὐ', 'τῇ',
			'alleluja', 'κατά¹', 'οὗτοϲ', 'καί', 'huc', 'tatae', 'heus!', 'ad',
			'non', 'ille', 'verus', 'κατά', 'γίγνομαι', 'ἄν¹', 'ζεύϲ', 'ἄνω¹',
			'ὁτιή', 'ἐν', 'πῃ', 'δέ¹', 'cum', 'γάροϲ', 'μετά', 'ἐκάϲ', 'ἀλλά',
			'hallelujah', 'eheu', 'ἐξέτι', 'incircum', 'mu', 'eo¹', 'προϲάμβ',
			'a', 'praeterpropter', 'et', 'qui¹', 'tat', 'evax', 'venio',
			'ὅϲτιϲ', 'penes', 'νή²', 'εἰϲ', 'παρά', 'γάρ', 'ἀμφί', 'ἤγουν',
			'oh', 'ἰδέ¹', 'trans', 'idem', 'ἐπάν', 'o²', 'ἐκ', 'ὅϲ', 'ito',
			'res', 'ἀνά', 'ἠτε', 'tenus²', 'τοίνυν', 'ἐπί', 'papae', 'ἄτερ',
			'atat', 'verum', 'τιϲ', 'ἀπέκ', 'st', 'heu!', 'ah', 'εἰ', 'εἰμί',
			'πᾶϲ', 'buttuti', 'am', 'a²', 'hem', 'τοιγάρ', 'ἄλλοϲ', 'cum¹',
			'οὖν', 'ambe', 'μή', 'vah', 'is', 'οὐ²', 'ὑπέκ', 'hic', 'sub', 'τε',
			'μήν¹', 'μά¹', 'καὶ¹', 'ἐρι²', 'οὕτωϲ', 'euax', 'ὑπό', 'ipse',
			'an¹', 'quam', 'vae', 'Q', 'ἄνα', 'τε¹', 'de', 'prior', 'magnus',
			'phu²', 'προπάροιθε', 'hehae', 'eia', 'oiei', 'εἰ¹', 'uls', 'aha',
			'in¹', 'Pollux', 'abs', 'πλήν', 'δή¹', 'ce', 'ὅτι¹', 'μέν', 'sed',
			'ἀπό', 'θωρακοί', 'hei', 'τῷ', 'πότε', 'ego', 'ha!', 'a³', 'prox',
			'pol', 'ex', 'ei²', 'dudum', 'διά', 'ὁ', 'ut', 'ὅτι²', 'phy', 'fi¹',
			'ἐπεί¹', 'ἐγώ', 'ϲύ', 'ϲύν', 'euge', 'ho!', 'ὁΐ', 'oi', 'γε', 'ἡμόϲ'}
	else:
		wordswecareabout = {
			'facio', 'possum', 'video', 'dico²', 'vaco', 'volo¹', 'habeo', 'do', 'vis',
			'ἔδω', 'δέω¹', 'δεῖ', 'δέομαι', 'ἔχω', 'λέγω¹', 'φημί', 'θεόϲ', 'ποιέω', 'πολύϲ',
			'ἄναξ', 'λόγοϲ'
		}

		dbconnection = ConnectionObject()
		dbcursor = dbconnection.cursor()

		qtemplate = """
		SELECT entry_name,total_count FROM dictionary_headword_wordcounts 
			WHERE entry_name ~ '[{yesorno}a-zA-Z]' ORDER BY total_count DESC LIMIT {lim}
		"""

		counts = dict()

		# grab the raw data: a greek query and a latin query
		# note that different limits have been set for each language
		for gl in {('', 50), ('^', 75)}:
			yesorno = gl[0]
			lim = gl[1]
			dbcursor.execute(qtemplate.format(yesorno=yesorno, lim=lim))
			tophits = resultiterator(dbcursor)
			tophits = {t[0]: t[1] for t in tophits}
			counts.update(tophits)

		# results = ['{wd} - {ct}'.format(wd=c, ct=counts[c]) for c in counts]
		#
		# for r in results:
		# 	print(r)

		wordstoskip = list(counts.keys() - wordswecareabout)

		qtemplate = """
		SELECT entry_name FROM {d} WHERE pos=ANY(%s)
		"""

		exclude = ['interj.', 'prep.', 'conj.', 'partic.']
		x = (exclude,)

		uninteresting = list()
		for d in ['greek_dictionary', 'latin_dictionary']:
			dbcursor.execute(qtemplate.format(d=d), x)
			finds = resultiterator(dbcursor)
			uninteresting += [f[0] for f in finds]

		wordstoskip = set(wordstoskip + uninteresting)

		dbconnection.connectioncleanup()

		# print('wordstoskip =', wordstoskip)

	wordstoskip.union(uselessforeignwords())

	return wordstoskip


def mostcommonwordsviaheadwords() -> set:
	"""

	use mostcommonheadwords to return the most common declined forms

		... 'ὁ', 'χἤ', 'χὤ', 'τάν', 'τοῦ', 'τώϲ', ...

	:return:
	"""

	headwords = mostcommonheadwords()

	wordstoskip = list()
	for h in headwords:
		try:
			wordstoskip.extend(lemmatadict[h].formlist)
		except KeyError:
			pass

	mostcommonwords = set(wordstoskip)

	mostcommonwords.union(uselessforeignwords())

	return mostcommonwords


def removestopwords(sentencestring, stopwords):
	"""

	take a sentence and throw out the stopwords in it

	:param sentencestring:
	:param stopwords:
	:return:
	"""

	wordlist = sentencestring.split(' ')
	wordlist = [removegravity(w) for w in wordlist if removegravity(w) not in stopwords]
	newsentence = ' '.join(wordlist)
	return newsentence


def relativehomonymnweight(worda, wordb, morphdict) -> float:
	"""

	NOT YET CALLED BY ANY VECTOR CODE

	accepto and acceptum share many forms, what is the liklihood that accepta comes from the verb and not the noun?

	est: is it from esse or edere?

	This is a huge problem. One way to approcimate an answer would be to take the sum of the non-overlapping forms
	and then use this as a ratio that yields a pseudo-probability

	Issues that arise: [a] perfectly convergent forms; [b] non-overlap in only one quarter; [c] corporal-sensitive
	variations (i.e., some forms more likely in an inscriptional context)

	hipparchiaDB=# select total_count from dictionary_headword_wordcounts where entry_name='sum¹';
	 total_count
	-------------
	      118369
	(1 row)

	hipparchiaDB=# select total_count from dictionary_headword_wordcounts where entry_name='edo¹';
	 total_count
	-------------
	      159481
	(1 row)

	:param worda:
	:param wordb:
	:param morphdict:
	:return:
	"""

	aheadwordobject = querytotalwordcounts(worda)
	bheadwordobject = querytotalwordcounts(wordb)
	atotal = aheadwordobject.t
	btotal = bheadwordobject.t
	try:
		totalratio = atotal/btotal
	except ZeroDivisionError:
		# how you managed to pick a zero headword would be interesting to know
		totalratio = -1

	auniqueforms = morphdict[worda] - morphdict[wordb]
	buniqueforms = morphdict[wordb] - morphdict[worda]

	auniquecounts = [dbWordCountObject(*findcountsviawordcountstable(wd)) for wd in auniqueforms]
	buniquecounts = [dbWordCountObject(*findcountsviawordcountstable(wd)) for wd in buniqueforms]

	aunique = sum([x.t for x in auniquecounts])
	bunique = sum([x.t for x in buniquecounts])
	try:
		uniqueratio = aunique/bunique
	except ZeroDivisionError:
		uniqueratio = -1

	if uniqueratio <= 0:
		return totalratio
	else:
		return uniqueratio


def reducetotwodimensions(model) -> dict:
	"""
	copied from
	https://radimrehurek.com/gensim/auto_examples/tutorials/run_word2vec.html#sphx-glr-auto-examples-tutorials-run-word2vec-py

	:param model:
	:return:
	"""

	dimensions = 2  # final num dimensions (2D, 3D, etc)

	vectors = list()  # positions in vector space
	labels = list()  # keep track of words to label our data again later
	for word in model.wv.vocab:
		vectors.append(model.wv[word])
		labels.append(word)

	# convert both lists into numpy vectors for reduction
	vectors = np.asarray(vectors)
	labels = np.asarray(labels)

	# reduce using t-SNE
	vectors = np.asarray(vectors)
	tsne = TSNE(n_components=dimensions, random_state=0)
	vectors = tsne.fit_transform(vectors)

	xvalues = [v[0] for v in vectors]
	yvalues = [v[1] for v in vectors]

	returndict = dict()
	returndict['xvalues'] = xvalues
	returndict['yvalues'] = yvalues
	returndict['labels'] = labels

	return returndict


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
