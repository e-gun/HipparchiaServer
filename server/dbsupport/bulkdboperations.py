# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from typing import List

import psycopg2

from server.dbsupport.tablefunctions import assignuniquename
from server.dbsupport.miscdbfunctions import resultiterator
from server.formatting.miscformatting import timedecorator
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.dbtextobjects import dbAuthor, dbOpus, dbLemmaObject


@timedecorator
def loadallauthorsasobjects() -> dict:
	"""

	return a dict of all possible author objects

	:return:
	"""

	print('loading all authors...', end='')

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	q = 'SELECT * FROM authors'

	cursor.execute(q)
	results = resultiterator(cursor)

	authorsdict = {r[0]: dbAuthor(*r) for r in results}

	print('\t', len(authorsdict), 'authors loaded', end='')

	dbconnection.connectioncleanup()

	return authorsdict


@timedecorator
def loadallworksasobjects() -> dict:
	"""

	return a dict of all possible work objects

	:return:
	"""

	print('loading all works...  ', end='')

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	q = """
	SELECT universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02,
		levellabels_03, levellabels_04, levellabels_05, workgenre, transmission, worktype, provenance, 
		recorded_date, converted_date, wordcount, firstline, lastline, authentic FROM works
	"""

	cursor.execute(q)
	results = resultiterator(cursor)

	worksdict = {r[0]: dbOpus(*r) for r in results}

	print('\t', len(worksdict), 'works loaded', end='')

	dbconnection.connectioncleanup()

	return worksdict


@timedecorator
def loadlemmataasobjects() -> dict:
	"""

	return a dict of all possible lemmataobjects

	hipparchiaDB=# select * from greek_lemmata limit 1;
	 dictionary_entry | xref_number |    derivative_forms
	------------------+-------------+------------------------
	 ζῳοτροφία        |    49550639 | {ζῳοτροφίᾳ,ζῳοτροφίαϲ}

	:return:
	"""

	print('loading all lemmata...', end=str())
	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	q = """
	SELECT dictionary_entry, xref_number, derivative_forms FROM {lang}_lemmata
	"""

	lemmatadict = dict()

	languages = {1: 'greek', 2: 'latin'}

	for key in languages:
		cursor.execute(q.format(lang=languages[key]))
		results = resultiterator(cursor)
		lemmatadict = {**{r[0]: dbLemmaObject(*r) for r in results}, **lemmatadict}

	print('\t', len(lemmatadict), 'lemmata loaded', end=str())
	# print('lemmatadict["molestus"]', lemmatadict['molestus'].formlist)
	# print('lemmatadict["Mausoleus"]', lemmatadict['Mausoleus'].formlist)
	# print('lemmatadict["λύω"]', lemmatadict['λύω'].formlist)

	dbconnection.connectioncleanup()

	return lemmatadict


def loadallworksintoallauthors(authorsdict, worksdict) -> dict:
	"""

	add the right work objects to the proper author objects

	:param authorsdict:
	:param worksdict:
	:return:
	"""

	for wkid in worksdict.keys():
		auid = wkid[0:6]
		authorsdict[auid].addwork(worksdict[wkid])

	return authorsdict


def bulklexicalgrab(listofwords: List[str], tabletouse: str, targetcolumn: str, language: str) -> list:
	"""

	grab a bunch of lex/morph entries by using a temp table

	e.g.,
		lexicalresults = bulklexicalgrab(listofwords, 'dictionary', 'entry_name', language)
		results = bulklexicalgrab(listofwords, 'morphology', 'observed_form', language)

	:param listofwords:
	:param tabletouse:
	:return:
	"""

	dbconnection = ConnectionObject(readonlyconnection=False)
	dbcursor = dbconnection.cursor()

	tqtemplate = """
	CREATE TEMP TABLE bulklex_{rnd} AS
		SELECT values AS 
			entriestocheck FROM unnest(ARRAY[%s]) values
	"""

	uniquename = assignuniquename(12)
	tempquery = tqtemplate.format(rnd=uniquename)
	data = (listofwords,)
	dbcursor.execute(tempquery, data)

	qtemplate = """
	SELECT * FROM {lg}_{thetable} WHERE EXISTS 
		(SELECT 1 FROM bulklex_{rnd} tocheck WHERE tocheck.entriestocheck = {lg}_{thetable}.{target})
	"""

	query = qtemplate.format(rnd=uniquename, thetable=tabletouse, target=targetcolumn, lg=language)

	try:
		dbcursor.execute(query)
		results = resultiterator(dbcursor)
	except psycopg2.ProgrammingError:
		# if you do not have the wordcounts installed: 'ProgrammingError: relations "wordcounts_a" does not exist
		results = list()

	dbconnection.connectioncleanup()

	return results
