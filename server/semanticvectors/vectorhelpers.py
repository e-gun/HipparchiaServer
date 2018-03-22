# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import os
import re
import sys
import time
from string import punctuation

import psycopg2

from server import hipparchia
from server.dbsupport.dblinefunctions import dblineintolineobject, grabonelinefromwork
from server.dbsupport.miscdbfunctions import resultiterator
from server.dbsupport.tablefunctions import uniquetablename
from server.formatting.wordformatting import acuteorgrav, buildhipparchiatranstable, removegravity, stripaccents, tidyupterm
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.searchobjects import ProgressPoll
from server.searching.searchdispatching import searchdispatcher
from server.searching.searchfunctions import buildbetweenwhereextension
from server.startup import lemmatadict
# bleh: numpy and scipy will fail to install on FreeBSD 11.x
# the work-around functions below might be needed instead: presumably there are markedly slower...
from server.textsandindices.textandindiceshelperfunctions import getrequiredmorphobjects


def cleantext(texttostrip):
	"""

	if we are using the marked up line, then a lot of gunk needs to go

	:param sentence:
	:return:
	"""

	htmlstrip = re.compile(r'<.*?>')
	wholetext = re.sub(htmlstrip, '', texttostrip)
	wholetext = re.sub('&nbsp;', '', wholetext)

	return wholetext


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
		avoidcollisions = uniquetablename()
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
	query = 'SELECT * FROM {db} {whr}'.format(db=authortable, whr=whr)

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

	columnmap = {'marked_up_line': 'accented', 'accented_line': 'polytonic', 'stripped_line': 'stripped'}
	col = columnmap[so.usecolumn]

	if so.vectorquerytype in requiresids:
		wholetext = ' '.join(['⊏{i}⊐{t}'.format(i=l.universalid, t=getattr(l, col)) for l in lineobjects])
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

	extrapunct = '\′‵’‘·̆́“”„—†⌈⌋⌊⟫⟪❵❴⟧⟦(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓'
	punct = re.compile('[{s}]'.format(s=re.escape(punctuation + extrapunct)))

	if so.vectorquerytype in requiresids:
		# now we mark the source of every sentence by turning it into a tuple: (location, text)
		previousid = lineobjects[0].universalid
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


def convertmophdicttodict(morphdict):
	"""

	return a dict of dicts of possibilities for all of the words we will be using

	key = word-in-use
	value = { maybeA, maybeB, maybeC}

	{'θεῶν': {'θεόϲ', 'θέα', 'θεάω', 'θεά'}, 'πώ': {'πω'}, 'πολλά': {'πολύϲ'}, 'πατήρ': {'πατήρ'}, ... }

	:return:
	"""

	morphdict = {k: v for k, v in morphdict.items() if v is not None}
	morphdict = {k: set([p.getbaseform() for p in morphdict[k].getpossible()]) for k in morphdict.keys()}

	# over-aggressive? more thought/care might be required here
	# the definitely changes the shape of the bags of words...
	delenda = mostcommonheadwords()
	morphdict = {k: v for k, v in morphdict.items() if v - delenda == v}

	return morphdict


def buildlemmatizesearchphrase(phrase):
	"""

	turn a search into a collection of headwords

	:param phrase:
	:return:
	"""

	# phrase = 'vias urbis munera'
	phrase = phrase.strip()
	words = phrase.split(' ')

	morphdict = getrequiredmorphobjects(words)
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
	hits = searchdispatcher(mso, nullpoll)

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


def buildflatbagsofwords(morphdict, sentences):
	"""
	turn a list of sentences into a list of list of headwords

	here we put homonymns next to one another:
		ϲυγγενεύϲ ϲυγγενήϲ

	in buildbagsofwordswithalternates() we have one 'word':
		ϲυγγενεύϲ·ϲυγγενήϲ

	:param morphdict:
	:param sentences:
	:return:
	"""

	bagsofwords = list()
	for s in sentences:
		lemattized = list()
		for word in s:
			try:
				# WARNING: we are treating homonymns as if 2+ words were there instead of just one
				# 'rectum' will give you 'rectus' and 'rego'; 'res' will give you 'reor' and 'res'
				# this necessarily distorts the vector space
				lemattized.append([item for item in morphdict[word]])
			except KeyError:
				pass
		# flatten
		bagsofwords.append([item for sublist in lemattized for item in sublist])

	return bagsofwords


def buildbagsofwordswithalternates(morphdict, sentences):
	"""

	buildbagsofwords() in rudimentaryvectormath.py does this but flattens rather than
	joining multiple possibilities

	here we have one 'word':
		ϲυγγενεύϲ·ϲυγγενήϲ

	there we have two:
		ϲυγγενεύϲ ϲυγγενήϲ

	:param morphdict:
	:param sentences:
	:return:
	"""

	bagsofwords = list()
	for s in sentences:
		lemmatizedsentence = list()
		for word in s:
			try:
				lemmatizedsentence.append('·'.join(morphdict[word]))
			except KeyError:
				pass
		bagsofwords.append(lemmatizedsentence)

	return bagsofwords


def mostcommonheadwords(cheat=True):
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

	return wordstoskip


def mostcommonwords():
	"""

	use mostcommonheadwords to return the most common declined forms

	:return:
	"""

	headwords = mostcommonheadwords()

	wordstoskip = list()
	for h in headwords:
		try:
			wordstoskip.append(lemmatadict[h].formlist)
		except KeyError:
			pass

	return wordstoskip


def readgitdata():
	"""

	find the commit value for the code in use

	a sample lastline:

		'3b0c66079f7337928b02df429f4a024dafc80586 63e01ae988d2d720b65c1bf7db54236b7ad6efa7 EG <egun@antisigma> 1510756108 -0500\tcommit: variable name changes; code tidy-ups\n'

	:return:
	"""

	basepath = os.path.dirname(sys.argv[0])

	gitfile = '/.git/logs/HEAD'
	line = ''

	with open(basepath+gitfile) as fh:
		for line in fh:
			pass
		lastline = line

	gitdata = lastline.split(' ')
	commit = gitdata[1]

	return commit


def determinesettings():
	"""

	what values were set in config.py?

	:return:
	"""

	wecareabout = ['VECTORDIMENSIONS',
					'VECTORWINDOW',
					'VECTORTRAININGITERATIONS',
					'VECTORMINIMALPRESENCE',
					'VECTORDOWNSAMPLE',
					'VECTORDISTANCECUTOFFLOCAL',
					'VECTORDISTANCECUTOFFNEARESTNEIGHBOR',
					'VECTORDISTANCECUTOFFLEMMAPAIR',
					'NEARESTNEIGHBORSCAP',
					'SENTENCESPERDOCUMENT']

	settinglist = list()
	for c in wecareabout:
		settinglist.append('{a}={b}'.format(a=c, b=hipparchia.config[c]))

	settingstring = ' · '.join(settinglist)

	return settingstring


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
