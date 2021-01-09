# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List

import psycopg2
from flask import session

from server.dbsupport.bulkdboperations import bulklexicalgrab
from server.dbsupport.miscdbfunctions import resultiterator, cleanpoolifneeded
from server.dbsupport.tablefunctions import assignuniquename
from server.formatting.abbreviations import unpackcommonabbreviations
from server.formatting.wordformatting import stripaccents, universalregexequivalent
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.dbtextobjects import dbMorphologyObject, dbLemmaObject
from server.hipparchiaobjects.lexicalobjects import dbDictionaryEntry, dbGreekWord, dbLatinWord
from server.hipparchiaobjects.wordcountobjects import dbHeadwordObject, dbWordCountObject


def headwordsearch(seeking: str, limit: str, usedictionary: str, usecolumn: str) -> List[tuple]:
	"""

	dictsearch() uses this

	hipparchiaDB=# SELECT entry_name, id_number FROM latin_dictionary WHERE entry_name ~* '.*?scrof.*?' ORDER BY id_number ASC LIMIT 50;
	  entry_name  | id_number
	--------------+-----------
	 scrofa¹      |     43118
	 Scrofa²      |     43119
	 scrofinus    |     43120
	 scrofipascus |     43121
	 scrofulae    |     43122
	(5 rows)

	:param seeking:
	:param limit:
	:param usedictionary:
	:param usecolumn:
	:return:
	"""

	cleanpoolifneeded()
	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	qstring = 'SELECT entry_name, id_number FROM {d}_dictionary WHERE {c} ~* %s ORDER BY id_number ASC LIMIT {lim}'

	query = qstring.format(d=usedictionary, c=usecolumn, lim=limit)

	if seeking[0] == ' ' and seeking[-1] == ' ':
		data = ('^' + seeking[1:-1] + '$',)
	elif seeking[0] == ' ' and seeking[-1] != ' ':
		data = ('^' + seeking[1:] + '.*?',)
	elif seeking[0] == '^' and seeking[-1] == '$':
		# esp if the dictionary sent this via next/previous entry
		data = (seeking,)
	else:
		data = ('.*?' + seeking + '.*?',)

	dbcursor.execute(query, data)

	# note that the dictionary db has a problem with vowel lengths vs accents
	# SELECT * FROM greek_dictionary WHERE entry_name LIKE %s d ('μνᾱ/αϲθαι,μνάομαι',)
	try:
		foundentries = dbcursor.fetchall()
	except:
		foundentries = list()

	# print('foundentries', foundentries)
	# '/dictsearch/scrof'
	# foundentries [('scrofa¹', 43118), ('scrofinus', 43120), ('scrofipascus', 43121), ('Scrofa²', 43119), ('scrofulae', 43122)]

	if not foundentries:
		variantseeker = seeking[:-1] + '[¹²³⁴⁵⁶⁷⁸⁹]' + seeking[-1]
		data = (variantseeker,)
		dbcursor.execute(query, data)
		foundentries = dbcursor.fetchall()

	if not foundentries:
		# maybe an inflected form was requested (can happen via clicks inside of an entry)
		morph = lookformorphologymatches(seeking, dbcursor)
		if morph:
			guesses = morph.getpossible()
			firstguess = guesses[0].getbaseform()
			seeking = stripaccents(firstguess)
			data = ('^{s}$'.format(s=seeking),)
			# print('lookformorphologymatches() new data=', data)
			dbcursor.execute(query, data)
			foundentries = dbcursor.fetchall()

	dbconnection.connectioncleanup()

	return foundentries


def reversedictionarylookup(seeking: str, usedict: str, limit=None) -> List:
	"""

	find an (approximate) entry in a dictionary

	note the syntax: ~

	return a list of wordobjects

	:param seeking:
	:param usedict:
	:param limit:
	:return:
	"""

	cleanpoolifneeded()
	dbconnection = ConnectionObject()
	dbconnection.setautocommit()
	dbcursor = dbconnection.cursor()

	assert usedict in ['greek', 'latin'], 'searchdbforlexicalentry() needs usedict to be "greek" or "latin"'

	objecttemplate = None

	fields = 'entry_name, metrical_entry, id_number, pos, translations, entry_body, {extra}'

	if usedict == 'greek':
		objecttemplate = dbGreekWord
		fields = fields.format(extra='unaccented_entry')
	elif usedict == 'latin':
		objecttemplate = dbLatinWord
		fields = fields.format(extra='entry_key')

	if limit:
		qstring = 'SELECT {f} FROM {d}_dictionary WHERE translations ~ %s LIMIT {lim}'
	else:
		qstring = 'SELECT {f} FROM {d}_dictionary WHERE translations ~ %s'

	query = qstring.format(f=fields, d=usedict, lim=limit)
	data = ('{s}'.format(s=seeking),)
	dbcursor.execute(query, data)
	matches = dbcursor.fetchall()

	wordobjects = [objecttemplate(*m) for m in matches]

	dbconnection.connectioncleanup()

	return wordobjects


def findentrybyid(usedict: str, entryid: str) -> dbDictionaryEntry:
	"""

	find by id number

	hipparchiaDB=# select * from greek_dictionary limit 0;
	 entry_name | metrical_entry | unaccented_entry | id_number | pos | translations | entry_body
	------------+----------------+------------------+-----------+-----+--------------+------------
	(0 rows)


	hipparchiaDB=# select * from latin_dictionary limit 0;
	 entry_name | metrical_entry | id_number | entry_key | pos | translations | entry_body
	------------+----------------+-----------+-----------+-----+--------------+------------
	(0 rows)


	:param usedict:
	:param entryid:
	:return:
	"""

	cleanpoolifneeded()
	dbconnection = ConnectionObject()
	dbconnection.setautocommit()
	dbcursor = dbconnection.cursor()

	assert usedict in ['greek', 'latin'], 'searchdbforlexicalentry() needs usedict to be "greek" or "latin"'

	if usedict == 'latin':
		extracolumn = 'entry_key'
	else:
		extracolumn = 'unaccented_entry'

	qtemplate = """SELECT entry_name, metrical_entry, id_number, pos, translations, 
					entry_body, {ec}
					FROM {d}_dictionary WHERE id_number = %s"""

	query = qtemplate.format(ec=extracolumn, d=usedict)
	data = (entryid,)
	try:
		dbcursor.execute(query, data)
	except:
		# older database: int vs float on this column
		# psycopg2.errors.InvalidTextRepresentation: invalid input syntax for integer: "13493.0"
		eidconverted = str(int(float(entryid)))
		data = (eidconverted,)
		dbcursor.execute(query, data)
	match = dbcursor.fetchone()

	if match:
		wordobject = convertdictionaryfindintowordobject(match, '{d}_dictionary'.format(d=usedict), dbcursor)
	else:
		wordobject = None

	dbconnection.connectioncleanup()

	return wordobject


def querytotalwordcounts(word: str, dbcursor=None) -> dbHeadwordObject:
	"""

	use the dictionary_headword_wordcounts table

	[a] take a dictionary entry: ἄκρατοϲ
	[b] look it up

	return a countobject

	:param word:
	:param dbcursor:
	:return:
	"""

	dbconnection = None
	if not dbcursor:
		dbconnection = ConnectionObject()
		dbconnection.setautocommit()
		dbcursor = dbconnection.cursor()

	table = 'dictionary_headword_wordcounts'
	qtemplate = """
		SELECT 
			entry_name , total_count, gr_count, lt_count, dp_count, in_count, ch_count,
			frequency_classification, early_occurrences, middle_occurrences ,late_occurrences, 
			acta, agric, alchem, anthol, apocalyp, apocryph, apol, astrol, astron, biogr, bucol, caten, chronogr, comic, comm, 
			concil, coq, dialog, docu, doxogr, eccl, eleg, encom, epic, epigr, epist, evangel, exeget, fab, geogr, gnom, gramm, 
			hagiogr, hexametr, hist, homilet, hymn, hypoth, iamb, ignotum, invectiv, inscr, jurisprud, lexicogr, liturg, lyr, 
			magica, math, mech, med, metrolog, mim, mus, myth, narrfict, nathist, onir, orac, orat, paradox, parod, paroem, 
			perieg, phil, physiognom, poem, polyhist, prophet, pseudepigr, rhet, satura, satyr, schol, tact, test, theol, trag
		FROM {tbl} WHERE entry_name=%s
	"""

	q = qtemplate.format(tbl=table)
	d = (word,)
	try:
		dbcursor.execute(q, d)
		hw = dbcursor.fetchone()
	except psycopg2.ProgrammingError:
		# psycopg2.ProgrammingError: relation "dictionary_headword_wordcounts" does not exist
		# you have not installed the wordcounts (yet)
		hw = None

	try:
		hwcountobject = dbHeadwordObject(*hw)
	except:
		# print('failed to initialize dbHeadwordObject for', word)
		hwcountobject = None

	if dbconnection:
		dbconnection.connectioncleanup()

	return hwcountobject


def probedictionary(usedictionary: str, usecolumn: str, seeking: str, syntax: str, dbcursor=None, trialnumber=0) -> List:
	"""

	this will make several stabs at finding a word in the dictionary

	we need to do this because sometimes a find in the morphology dictionary does not point to something
	you can find in the dictionary of meanings

	sample values:
		dictionary:	'greek_dictionary'
		usecolumn: 'entry_name'
		seeking: 'προχοΐδιον'
		syntax: '=' or 'LIKE'

	still unimplemented:
		τήθη vs τηθή; the parser has the latter, the dictionary expects the former (but knows of the latter)

	:param dbcursor:
	:param usedictionary:
	:param usecolumn:
	:param seeking:
	:param syntax:
	:param trialnumber:
	:return:
	"""
	# print('seeking/trial',seeking,trialnumber)

	dbconnection = None
	if not dbcursor:
		dbconnection = ConnectionObject()
		dbconnection.setautocommit()
		dbcursor = dbconnection.cursor()

	maxtrials = 8
	trialnumber += 1
	accenteddiaresis = re.compile(r'αί|εί|οί|υί|ηί|ωί')
	unaccenteddiaresis = re.compile(r'αι|ει|οι|υι|ηι|ωι')

	# nothingfound = convertdictionaryfindintoobject('nothing', 'nodict')

	if usedictionary == 'latin_dictionary':
		extracolumn = 'entry_key'
	else:
		extracolumn = 'unaccented_entry'

	qtemplate = """SELECT entry_name, metrical_entry, id_number, pos, translations, 
					entry_body, {ec}
					FROM {d} WHERE {col} {sy} %s ORDER BY id_number ASC"""
	query = qtemplate.format(ec=extracolumn, d=usedictionary, col=usecolumn, sy=syntax)
	data = (seeking,)
	# print('searchdictionary()',query,'\n\t',data)

	try:
		dbcursor.execute(query, data)
		found = dbcursor.fetchall()
	except psycopg2.DataError:
		# thrown by dbcursor.execute()
		# invalid regular expression: parentheses () not balanced
		# ό)μβροϲ is a (bogus) headword; how many others are there?
		found = list()

	# we might be at trial 2+ and so we need to strip the supplement we used at trial #1
	if trialnumber > 2:
		seeking = re.sub(r'\[¹²³⁴⁵⁶⁷⁸⁹\]', '', seeking)
		seeking = re.sub(r'\^', '', seeking)

	foundobjects = None

	if len(found) > 0:
		foundobjects = [convertdictionaryfindintowordobject(f, usedictionary, dbcursor) for f in found]
	elif trialnumber == 1:
		# failure...
		# the word is probably there, we have just been given the wrong search term; try some other solutions
		# [1] first guess: there were multiple possible entries, not just one
		newword = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]', '', seeking.lower())
		foundobjects = probedictionary(usedictionary, usecolumn, newword, '=', dbcursor, trialnumber)
	elif trialnumber == 2:
		# grab any/all variants: ⁰¹²³⁴⁵⁶⁷⁸⁹
		newword = '^{sk}[¹²³⁴⁵⁶⁷⁸⁹]'.format(sk=seeking)
		foundobjects = probedictionary(usedictionary, usecolumn, newword, '~', dbcursor, trialnumber)
	# elif trialnumber < maxtrials and '-' in seeking:
	# 	newword = attemptelision(seeking)
	# 	foundobject = searchdictionary(cursor, dictionary, usecolumn, newword, '=', trialnumber)
	elif trialnumber < maxtrials and seeking[-1] == 'ω':
		# ὑποϲυναλείφομαι is in the dictionary, but greek_lemmata says to look for ὑπό-ϲυναλείφω
		newword = seeking[:-1] + 'ομαι'
		foundobjects = probedictionary(usedictionary, usecolumn, newword, '=', dbcursor, trialnumber)
	elif trialnumber < maxtrials and re.search(r'ομαι$', seeking):
		# χαρίζω is in the dictionary, but greek_lemmata says to look for χαρίζομαι
		newword = seeking[:-4] + 'ω'
		foundobjects = probedictionary(usedictionary, usecolumn, newword, '=', dbcursor, trialnumber)
	elif trialnumber < maxtrials and re.search(accenteddiaresis, seeking):
		# false positives very easy here, but we are getting desperate and have nothing to lose
		diaresis = re.search(accenteddiaresis, seeking)
		head = seeking[:diaresis.start()]
		tail = seeking[diaresis.end():]
		vowels = diaresis.group(0)
		vowels = vowels[0] + 'ΐ'
		newword = head + vowels + tail
		foundobjects = probedictionary(usedictionary, usecolumn, newword, '=', dbcursor, trialnumber)
	elif trialnumber < maxtrials and re.search(unaccenteddiaresis, seeking):
		diaresis = re.search(unaccenteddiaresis, seeking)
		head = seeking[:diaresis.start()]
		tail = seeking[diaresis.end():]
		vowels = diaresis.group(0)
		vowels = vowels[0] + 'ϊ'
		newword = head + vowels + tail
		foundobjects = probedictionary(usedictionary, usecolumn, newword, '=', dbcursor, trialnumber)
	elif trialnumber < maxtrials:
		# τήθη vs τηθή; the parser has the latter, the dictionary expects the former (but knows of the latter)
		trialnumber = maxtrials - 1
		newword = re.sub(r'\[¹²³⁴⁵⁶⁷⁸⁹\]', '', seeking)
		newword = stripaccents(newword)
		newword = universalregexequivalent(newword)
		# strip '(' and ')'
		newword = '^{wd}$'.format(wd=newword[1:-1])
		foundobjects = probedictionary(usedictionary, usecolumn, newword, '~', dbcursor, trialnumber)

	if dbconnection:
		dbconnection.connectioncleanup()

	return foundobjects


def convertdictionaryfindintowordobject(foundline: tuple, usedictionary: str, dbcursor):
	"""

	dictionary = greek_dictionary or latin_dictionary

	foundline is a db line with the extra parameter last:
		entry_name, metrical_entry, id_number, entry_type, entry_options, , translations, entry_body + extra

	example:
		foundline ('ἑτερόφθαλμοϲ', 'ἑτερόφθαλμοϲ', '43226', 'main', 'n', '[transl]', '<orth extent="suff" lang="greek" opt="n">ἑτερόφθαλμ-οϲ</orth>, <itype lang="greek" opt="n">ον</itype>, <sense id="n43226.0" n="A" level="1" opt="n"><tr opt="n">one-eyed</tr>, <bibl n="Perseus:abo:tlg,0014,024:141" default="NO" valid="yes"><author>D.</author> <biblScope>24.141</biblScope></bibl>, <bibl n="Perseus:abo:tlg,0086,025:1023a:5" default="NO" valid="yes"><author>Arist.</author><title>Metaph.</title><biblScope>1023a5</biblScope></bibl>; <foreign lang="greek">ἑ. γενομένη ἡ Ἑλλάϲ</foreign>, metaph., of the proposed destruction of Athens, Leptines ap. <bibl n="Perseus:abo:tlg,0086,038:1411a:5" default="NO" valid="yes"><author>Arist.</author><title>Rh.</title><biblScope>1411a5</biblScope></bibl>, cf. <bibl default="NO"><author>Demad.</author><biblScope>65</biblScope></bibl> <bibl default="NO"><author>B.</author></bibl>, <bibl default="NO"><author>Plu.</author><biblScope>2.803a</biblScope></bibl>. </sense><sense n="II" id="n43226.1" level="2" opt="n"> <tr opt="n">with different-coloured eyes,</tr> <bibl n="Perseus:abo:tlg,4080,001:16:2:1" default="NO"><author>Gp.</author> <biblScope>16.2.1</biblScope></bibl>.</sense>', 'ετεροφθαλμοϲ')

	:param foundline:
	:param usedictionary:
	:return:
	"""
	# print('foundline',foundline)

	if usedictionary == 'greek_dictionary':
		wordobject = dbGreekWord(*foundline)
	elif usedictionary == 'latin_dictionary':
		wordobject = dbLatinWord(*foundline)
	else:
		# you actually want a hollow object
		wordobject = dbGreekWord(None, None, None, None, None, None, None)

	ntemplate = 'SELECT entry_name, id_number FROM {d} WHERE id_number > %s ORDER BY id_number ASC LIMIT 1;'

	q = ntemplate.format(d=usedictionary)
	d = (wordobject.id,)
	dbcursor.execute(q, d)
	e = dbcursor.fetchone()

	try:
		wordobject.nextentry = e[0]
		wordobject.nextentryid = e[1]
	except TypeError:
		# TypeError: 'NoneType' object is not subscriptable
		pass

	ptemplate = 'SELECT entry_name, id_number FROM {d} WHERE id_number < %s ORDER BY id_number DESC LIMIT 1;'

	q = ptemplate.format(d=usedictionary)
	d = (wordobject.id,)
	dbcursor.execute(q, d)
	e = dbcursor.fetchone()

	try:
		wordobject.preventry = e[0]
		wordobject.preventryid = e[1]
	except TypeError:
		# TypeError: 'NoneType' object is not subscriptable
		pass

	return wordobject


def findcountsviawordcountstable(wordtocheck):
	"""

	used to look up a list of specific observed forms
	(vs. dictionary headwords)

	:param wordtocheck:
	:return:
	"""

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	initial = stripaccents(wordtocheck[0])
	# alternatives = re.sub(r'[uv]','[uv]',c)
	# alternatives = '^'+alternatives+'$'
	if initial in 'abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ':
		# note that we just lost "'φερον", "'φερεν", "'φέρεν", "'φερεϲ", "'φερε",...
		# but the punctuation killer probably zapped them long ago
		# this needs to be addressed in HipparchiaBuilder
		q = 'SELECT * FROM wordcounts_{i} WHERE entry_name = %s'.format(i=initial)
	else:
		q = 'SELECT * FROM wordcounts_0 WHERE entry_name = %s'

	d = (wordtocheck,)
	try:
		dbcursor.execute(q, d)
		result = dbcursor.fetchone()
	except psycopg2.ProgrammingError:
		# psycopg2.ProgrammingError: relation "wordcounts_ε" does not exist
		# you did not build the wordcounts at all?
		result = None

	dbconnection.connectioncleanup()

	return result


def grablemmataobjectfor(db, dbcursor=None, word=None, xref=None, allowsuperscripts=False):
	"""

	send a word, return a lemmaobject

	hipparchiaDB=# select * from greek_lemmata limit 0;
	 dictionary_entry | xref_number | derivative_forms
	------------------+-------------+------------------

	EITHER 'word' should be set OR 'xref' should be set: not both

	at the moment we only use 'word' in both calls to this function:
		hipparchiaobjects/lexicaloutputobjects.py
		hipparchiaobjects/morphanalysisobjects.py

	'allowsuperscripts' because sometimes you are supposed to search under δέω² and sometimes you are not...

	:param db:
	:param dbcursor:
	:param word:
	:param xref:
	:param allowsuperscripts:
	:return:
	"""

	dbconnection = None
	if not dbcursor:
		dbconnection = ConnectionObject()
		dbconnection.setautocommit()
		dbcursor = dbconnection.cursor()

	field = str()
	data = None

	if xref:
		field = 'xref_number'
		data = xref

	if word:
		field = 'dictionary_entry'
		data = word

	if not allowsuperscripts:
		data = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]', '', data)

	if not session['available'][db]:
		lo = dbLemmaObject('[parsing is impossible: lemmata data was not installed]', -1, '')
		return lo

	if not data:
		lo = dbLemmaObject('[programming error: no word or xref set in grablemmataobjectfor()]', -1, '')
		return lo

	q = 'SELECT * FROM {db} WHERE {f}=%s'.format(db=db, f=field)
	d = (data,)

	dbcursor.execute(q, d)
	lem = dbcursor.fetchone()

	try:
		lemmaobject = dbLemmaObject(*lem)
	except TypeError:
		# 'NoneType' object is not subscriptable
		lemmaobject = dbLemmaObject('[entry not found]', -1, '')

	if dbconnection:
		dbconnection.connectioncleanup()

	return lemmaobject


def findparserxref(wordobject) -> str:
	"""

	used in LEXDEBUGMODE to find the parser xrefvalue for a headword

	:param entryname:
	:return:
	"""

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	if wordobject.isgreek():
		lang = 'greek'
	else:
		lang = 'latin'

	trimmedentry = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]', '', wordobject.entry)

	q = 'SELECT * FROM {lang}_lemmata WHERE dictionary_entry=%s'.format(lang=lang)
	d = (wordobject.entry,)
	dbcursor.execute(q, d)
	results = dbcursor.fetchall()

	if not results:
		d = (trimmedentry,)
		dbcursor.execute(q, d)
		results = dbcursor.fetchall()

	# it is not clear that more than one item will ever be returned
	# but if that happened, you need to be ready to deal with it
	lemmaobjects = [dbLemmaObject(*r) for r in results]
	xrefs = [str(l.xref) for l in lemmaobjects]

	xrefvalues = ', '.join(xrefs)

	dbconnection.connectioncleanup()

	return xrefvalues


def lookformorphologymatches(word: str, dbcursor, trialnumber=0, revertword=None, rewrite=None, furtherdeabbreviate=False) -> dbMorphologyObject:
	"""

	hipparchiaDB=# select * from greek_morphology limit 1;
	 observed_form |   xrefs   | prefixrefs |                                                             possible_dictionary_forms
	---------------+-----------+------------+---------------------------------------------------------------------------------------------------------------------------------------------------
	 Τηνίουϲ       | 114793123 |            | <possibility_1>Τήνιοϲ<xref_value>114793123</xref_value><xref_kind>0</xref_kind><transl> </transl><analysis>masc acc pl</analysis></possibility_1>+
               |           |            |
	hipparchiaDB=# select * from greek_lemmata where xref_number=114793123;
	 dictionary_entry | xref_number |                  derivative_forms
	------------------+-------------+----------------------------------------------------
	 τήνιοϲ           |   114793123 | {τηνίων,τήνια,τηνίουϲ,τήνιοι,τηνίοιϲ,τηνία,τήνιοϲ}

	funky because we need to poke at words several times and to try combinations of fixes

	ought to pass a cursor to this one because this function will have trouble cleaning the connection properly

	:param word:
	:param dbcursor:
	:param trialnumber:
	:param revertword:
	:param rewrite:
	:param furtherdeabbreviate: a vector run has already turned 'm.' into Marcus, so it is safe to turn 'm' into 'mille'
	:return:
	"""

	if re.search(r'[a-z]', word):
		usedictionary = 'latin'
	else:
		usedictionary = 'greek'

	# βοῶ̣ντεϲ -> βοῶντεϲ
	word = re.sub(r'̣', str(), word)

	ihavesession = True
	try:
		session['available'][usedictionary + '_morphology']
	except RuntimeError:
		# vectorbot thread does not have access to the session...
		# we will *dangerously guess* that we can skip the next check because vectorbotters
		# are quite likely to have beefy installations...
		ihavesession = False

	if ihavesession and not session['available'][usedictionary + '_morphology']:
		return None

	maxtrials = 4
	retrywithcapitalization = 1
	trialnumber += 1

	# the things that can confuse me
	terminalacute = re.compile(r'[άέίόύήώ]')

	morphobjects = None

	# syntax = '~' if you have to deal with '[uv]' problems, e.g.
	# but that opens up a whole new can of worms

	query = 'SELECT * FROM {d}_morphology WHERE observed_form = %s'.format(d=usedictionary)
	data = (word,)

	# print('lookformorphologymatches() q/d', query, data)

	dbcursor.execute(query, data)
	# NOT TRUE: fetchone() because all possiblities are stored inside the analysis itself
	# loss of case sensitivity is a problem here: Latro vs latro.
	analyses = dbcursor.fetchall()

	if analyses:
		morphobjects = [dbMorphologyObject(*a) for a in analyses]
		if rewrite:
			for m in morphobjects:
				m.observed = rewrite
				m.rewritten = True
	elif trialnumber < maxtrials:
		# turn 'kal' into 'kalends', etc.
		# not very costly as this is a dict lookup, and less costly than any call to the db
		newword = unpackcommonabbreviations(word, furtherdeabbreviate)
		if newword != word:
			return lookformorphologymatches(newword, dbcursor, 0, rewrite=word)

		if revertword:
			word = revertword
		# this code lets you make multiple stabs at an answer if you have already failed once
		# need to be careful about the retries that reset the trialnumber: could infinite loop if not careful
		# [a] something like πλακουντάριόν τι will fail because of the enclitic (greek_morphology can find πλακουντάριον and πλακουντάριοϲ)
		# [b] something like προχοίδιόν τι will fail twice over because of the enclitic and the diaresis

		try:
			# have to 'try...' because there might not be a word[-2]
			if trialnumber == 1:
				# elided ending? you will ask for ἀλλ, but you need to look for ἀλλ'
				newword = word + "'"
				morphobjects = lookformorphologymatches(newword, dbcursor, trialnumber, revertword=word)
			elif trialnumber == 2:
				# a proper noun?
				newword = word[0].upper() + word[1:]
				morphobjects = lookformorphologymatches(newword, dbcursor, trialnumber, revertword=word)
			elif re.search(r'\'$', word):
				# the last word in a greek quotation might have a 'close quote' that was mistaken for an elision
				newword = re.sub(r'\'', '', word)
				morphobjects = lookformorphologymatches(newword, dbcursor, trialnumber)
			elif re.search(r'[ΐϊΰῧϋî]', word):
				# desperate: ῥηϊδίωϲ --> ῥηιδίωϲ
				diacritical = 'ΐϊΰῧϋî'
				plain = 'ίιύῦυi'
				xform = str.maketrans(diacritical, plain)
				newword = word.translate(xform)
				morphobjects = lookformorphologymatches(newword, dbcursor, trialnumber=retrywithcapitalization)
			elif re.search(terminalacute, word[-1]):
				# an enclitic problem?
				sub = stripaccents(word[-1])
				newword = word[:-1] + sub
				morphobjects = lookformorphologymatches(newword, dbcursor, trialnumber=retrywithcapitalization)
			elif re.search(terminalacute, word[-2]):
				# πλακουντάριόν?
				sub = stripaccents(word[-2])
				newword = word[:-2] + sub + word[-1]
				morphobjects = lookformorphologymatches(newword, dbcursor, trialnumber=retrywithcapitalization)
			else:
				return None
		except IndexError:
			morphobjects = None

	if not morphobjects:
		return None

	# OK: we have a list of dbMorphologyObjects; this needs to be turned into a single object...
	# def __init__(self, observed, xrefs, prefixrefs, possibleforms):

	if isinstance(morphobjects, dbMorphologyObject):
		# you got here after multiple tries
		# if you don't do the next, the len() check will fail
		morphobjects = [morphobjects]

	if len(morphobjects) == 1:
		morphobject = morphobjects[0]
	else:
		flatten = lambda l: [item for sublist in l for item in sublist]
		ob = morphobjects[0].observed
		xr = flatten([m.xrefs for m in morphobjects])
		xr = ', '.join(xr)
		pr = flatten([m.prefixrefs for m in morphobjects])
		pr = ', '.join(pr)
		pf = flatten([m.possibleforms.split('\n') for m in morphobjects])
		# note that you will have multiple '<possibility_1>' entries now... Does not matter ATM, but a bug waiting to bite
		pf = '\n'.join(pf)
		morphobject = dbMorphologyObject(ob, xr, pr, pf)

	return morphobject


def bulkfindwordcounts(listofwords: List[str]) -> List[dbWordCountObject]:
	"""

	note that the lists of words should all start with the same letter since the wordcount tables are letter-keyed

	hipparchiaDB=# CREATE TEMP TABLE bulkcounter_51807f8bbe08 AS SELECT values AS  entriestocheck FROM unnest(ARRAY['κατακλειούϲηϲ', 'κατακλῇϲαι', 'κατακλεῖϲαι']) values;

	hipparchiaDB=# SELECT * FROM wordcounts_κ WHERE EXISTS (SELECT 1 FROM bulkcounter_51807f8bbe08 tocheck WHERE tocheck.entriestocheck = wordcounts_κ.entry_name);
	  entry_name   | total_count | gr_count | lt_count | dp_count | in_count | ch_count
	---------------+-------------+----------+----------+----------+----------+----------
	 κατακλεῖϲαι   |          31 |       30 |        0 |        0 |        1 |        0
	 κατακλειούϲηϲ |           3 |        3 |        0 |        0 |        0 |        0
	 κατακλῇϲαι    |           1 |        1 |        0 |        0 |        0 |        0
	(3 rows)

	:param listofwords:
	:return:
	"""

	dbconnection = ConnectionObject(readonlyconnection=False)
	dbcursor = dbconnection.cursor()

	try:
		firstletteroffirstword = stripaccents(listofwords[0][0])
	except IndexError:
		return list()

	if firstletteroffirstword not in 'abcdefghijklmnopqrstuvwxyzαβψδεφγηιξκλμνοπρϲτυωχθζ':
		firstletteroffirstword = '0'

	tqtemplate = """
	CREATE TEMP TABLE bulkcounter_{rnd} AS
		SELECT values AS 
			entriestocheck FROM unnest(ARRAY[%s]) values
	"""

	uniquename = assignuniquename(12)
	tempquery = tqtemplate.format(rnd=uniquename)
	data = (listofwords,)
	dbcursor.execute(tempquery, data)

	qtemplate = """
	SELECT * FROM wordcounts_{x} WHERE EXISTS 
		(SELECT 1 FROM bulkcounter_{rnd} tocheck WHERE tocheck.entriestocheck = wordcounts_{x}.entry_name)
	"""

	query = qtemplate.format(rnd=uniquename, x=firstletteroffirstword)
	try:
		dbcursor.execute(query)
		results = resultiterator(dbcursor)
	except psycopg2.ProgrammingError:
		# if you do not have the wordcounts installed: 'ProgrammingError: relations "wordcounts_a" does not exist
		results = list()

	wordcountobjects = [dbWordCountObject(*r) for r in results]

	dbconnection.connectioncleanup()

	return wordcountobjects


def bulkfindmorphologyobjects(listofwords: List[str], language: str) -> List[dbMorphologyObject]:
	"""

	generate a list of morphology objects from a list of words: this is substantially faster than executing
	lookformorphologymatches() over and over again

	you need to send known good data here: lookformorphologymatches() is how you hook up a random word to the parser

	CREATE TEMP TABLE bulkmorph_159d3b63b36c AS
		SELECT values AS
			entriestocheck FROM unnest(ARRAY[%s]) values

	(['διηλλάξαντο', 'διηλλάξαμεν', 'διαλλάττωμεν', ...],)

	:param listofwords:
	:return:
	"""

	results = bulklexicalgrab(listofwords, 'morphology', 'observed_form', language)
	morphobjects = [dbMorphologyObject(*r) for r in results]

	return morphobjects
