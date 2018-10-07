# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import re
from typing import List

import psycopg2
from flask import session

from server.formatting.wordformatting import stripaccents, universalregexequivalent
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.dbtextobjects import dbMorphologyObject
from server.hipparchiaobjects.lexicalobjects import dbGreekWord, dbLatinWord
from server.hipparchiaobjects.morphologyobjects import dbLemmaObject
from server.hipparchiaobjects.wordcountobjects import dbHeadwordObject


def searchdbforlexicalentry(seeking, usedict, limit=None) -> List:
	"""

	find an (approximate) entry in a dictionary

	note the syntax: ~

	return a list of wordobjects

	:param seeking:
	:param usedict:
	:param limit:
	:return:
	"""

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
	dbcursor.execute(query, data)
	# print('searchdictionary()',query,'\n\t',data)

	found = dbcursor.fetchall()

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


def grablemmataobjectfor(entryname, db, dbcursor=None):
	"""

	send a word, return a lemmaobject

	:param entryname:
	:param db:
	:return:
	"""

	dbconnection = None
	if not dbcursor:
		dbconnection = ConnectionObject()
		dbconnection.setautocommit()
		dbcursor = dbconnection.cursor()

	if not session['available'][db]:
		lo = dbLemmaObject('[parsing is impossible: lemmata data was not installed]', -1, '')
		return lo

	q = 'SELECT * FROM {db} WHERE dictionary_entry=%s'.format(db=db)
	d = (entryname,)
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


def lookformorphologymatches(word: str, dbcursor, trialnumber=0, revertword=None) -> dbMorphologyObject:
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
	:return:
	"""

	if re.search(r'[a-z]', word):
		usedictionary = 'latin'
	else:
		usedictionary = 'greek'

	# βοῶ̣ντεϲ -> βοῶντεϲ
	word = re.sub(r'̣', '', word)

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

	morphobject = None

	# syntax = '~' if you have to deal with '[uv]' problems, e.g.
	# but that opens up a whole new can of worms

	query = 'SELECT * FROM {d}_morphology WHERE observed_form = %s'.format(d=usedictionary)
	data = (word,)

	# print('lookformorphologymatches() q/d', query, data)

	dbcursor.execute(query, data)
	# fetchone() because all possiblities are stored inside the analysis itself
	analysis = dbcursor.fetchone()

	if analysis:
		morphobject = dbMorphologyObject(*analysis)
	elif trialnumber < maxtrials:
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
				morphobject = lookformorphologymatches(newword, dbcursor, trialnumber, revertword=word)
			elif trialnumber == 2:
				# a proper noun?
				newword = word[0].upper() + word[1:]
				morphobject = lookformorphologymatches(newword, dbcursor, trialnumber, revertword=word)
			elif re.search(r'\'$', word):
				# the last word in a greek quotation might have a 'close quote' that was mistaken for an elision
				newword = re.sub(r'\'', '', word)
				morphobject = lookformorphologymatches(newword, dbcursor, trialnumber)
			elif re.search(r'[ΐϊΰῧϋî]', word):
				# desperate: ῥηϊδίωϲ --> ῥηιδίωϲ
				diacritical = 'ΐϊΰῧϋî'
				plain = 'ίιύῦυi'
				xform = str.maketrans(diacritical, plain)
				newword = word.translate(xform)
				morphobject = lookformorphologymatches(newword, dbcursor, trialnumber=retrywithcapitalization)
			elif re.search(terminalacute, word[-1]):
				# an enclitic problem?
				sub = stripaccents(word[-1])
				newword = word[:-1] + sub
				morphobject = lookformorphologymatches(newword, dbcursor, trialnumber=retrywithcapitalization)
			elif re.search(terminalacute, word[-2]):
				# πλακουντάριόν?
				sub = stripaccents(word[-2])
				newword = word[:-2] + sub + word[-1]
				morphobject = lookformorphologymatches(newword, dbcursor, trialnumber=retrywithcapitalization)
			else:
				return None
		except IndexError:
			morphobject = None

	return morphobject
