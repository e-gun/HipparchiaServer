# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import multiprocessing
import re

import psycopg2

from typing import Generator

from server.dbsupport.dblinefunctions import worklinetemplate
from server.dbsupport.miscdbfunctions import resultiterator
from server.dbsupport.tablefunctions import assignuniquename
from server.hipparchiaobjects.searchobjects import SearchObject
from server.searching.searchfunctions import buildbetweenwhereextension


def substringsearch(seeking: str, authortable: str, searchobject: SearchObject, cursor, templimit=None) -> Generator:
	"""

	actually one of the most basic search types: look for a string/substring

	the whereclause is built conditionally:

	sample 'unrestricted':
		SELECT * FROM gr0059 WHERE  ( stripped_line ~* %s )  LIMIT 200 ('βαλλ',)
	sample 'between':
		SELECT * FROM gr0032 WHERE (index BETWEEN 1846 AND 2856) AND (index NOT BETWEEN 1846 AND 2061) AND ( stripped_line ~* %s )  LIMIT 200 ('βαλλ',)
	sample 'temptable':
		[create the temptable]
		SELECT * FROM in1204 WHERE EXISTS (SELECT 1 FROM in1204_includelist incl WHERE incl.includeindex = in1204.index AND in1204.accented_line ~* %s)  LIMIT 200 ('τούτου',)

	:param seeking:
	:param authortable:
	:param searchobject:
	:param cursor:
	:param templimit:
	:return:
	"""

	so = searchobject

	if templimit:
		lim = str(templimit)
	else:
		lim = str(so.cap)

	if so.onehit:
		mylimit = ' LIMIT 1'
	else:
		mylimit = ' LIMIT {lim}'.format(lim=lim)

	mysyntax = '~*'
	found = list()

	r = so.indexrestrictions[authortable]
	whereextensions = ''

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
		whr = 'WHERE {xtn} AND {au}.{col} {sy} %s)'.format(au=authortable, col=so.usecolumn, sy=mysyntax, xtn=whereextensions)
	elif r['type'] == 'between':
		whereextensions = buildbetweenwhereextension(authortable, so)
		whr = 'WHERE {xtn} ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax, xtn=whereextensions)
	elif r['type'] == 'unrestricted':
		whr = 'WHERE {xtn} ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax, xtn=whereextensions)
	else:
		# should never see this
		print('error in substringsearch(): unknown whereclause type', r['type'])
		whr = 'WHERE ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax)

	qtemplate = 'SELECT {wtmpl} FROM {db} {whr} {lm}'
	q = qtemplate.format(wtmpl=worklinetemplate, db=authortable, whr=whr, lm=mylimit)
	d = (seeking,)

	# print('q/d\nq:\t{q}\nd:\t{d}\n'.format(q=q, d=d))

	try:
		cursor.execute(q, d)
		found = resultiterator(cursor)
	except psycopg2.DataError:
		# e.g., invalid regular expression: parentheses () not balanced
		print('DataError; cannot search for »{d}«\n\tcheck for unbalanced parentheses and/or bad regex'.format(d=d[0]))
	except psycopg2.InternalError:
		# current transaction is aborted, commands ignored until end of transaction block
		print('psycopg2.InternalError; did not execute', q, d)
	except psycopg2.DatabaseError:
		# psycopg2.DatabaseError: error with status PGRES_TUPLES_OK and no message from the libpq
		# added to track PooledConnection threading issues
		# will see: 'DatabaseError for <cursor object at 0x136bab520; closed: 0> @ Process-4'
		print('DatabaseError for {c} @ {p}'.format(c=cursor, p=multiprocessing.current_process().name))
		print('\tq, d', q, d)

	return found


# DEAD CODE KEPT AROUND SO THAT A BAD WHEEL IS NOT REINVENTED
#
# if so.searchtype == 'zz_never_meet_condition_simplelemma':
# 	# lemmatized searching gets very slow if the number of forms is large
# 	# faster to use arrays? nope...: see below
# 	# mix and match? [array of items that look like ['a|b|c', 'd|e|f', ...] nope...
#
# 	# Sample SQL:
# 	# CREATE TEMPORARY TABLE lemmatizedforms AS SELECT term FROM unnest(ARRAY['hospitium', 'hospitio']) term;
# 	# SELECT index, stripped_line FROM lt1212 WHERE stripped_line ~* ANY (SELECT term FROM lemmatizedforms);
#
# 	"""
# 	ARRAYS + TEMP TABLE VERSION
#
# 	Sought all 12 known forms of »hospitium«
# 	Searched 7,461 texts and found 250 passages (31.64s)
# 	Sorted by name
# 	[Search suspended: result cap reached.]
#
# 	"""
#
# 	"""
# 	MIXANDMATCH: ARRAYS of REREGEX
#
# 	Sought all 12 known forms of »hospitium«
# 	Searched 7,461 texts and found 250 passages (15.73s)
# 	Sorted by name
# 	[Search suspended: result cap reached.]
#
# 	"""
#
# 	"""
# 	GIANTREGEX VERSION
#
# 	Sought all 12 known forms of »hospitium«
# 	Searched 7,461 texts and found 250 passages (1.72s)
# 	Sorted by name
# 	[Search suspended: result cap reached.]
# 	"""
#
# 	forms = so.lemma.formlist
# 	# MIXANDMATCH if the next three lines are enabled
# 	n = 3
# 	forms = [forms[i:i + n] for i in range(0, len(forms), n)]
# 	forms = [wordlistintoregex(f) for f in forms]
#
# 	qtemplate = """
# 	DROP TABLE IF EXISTS lemmatizedforms_{wd};
# 	CREATE TEMPORARY TABLE IF NOT EXISTS lemmatizedforms_{wd} AS
# 		SELECT term FROM unnest(%s) term
# 	"""
# 	q = qtemplate.format(wd=so.lemma.dictionaryentry)
# 	d = (forms,)
# 	cursor.execute(q, d)
#
# 	# now modify the '%s' that we have from above
# 	whr = re.sub(r'%s', 'ANY (SELECT term FROM lemmatizedforms_{wd})'.format(wd=so.lemma.dictionaryentry), whr)
