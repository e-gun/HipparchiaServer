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


"""

	ANOTHER DEAD END...

	you can use psql's to_tsvector() and to_tsquery() functions

	what you do via substringsearch()

	q:	SELECT * FROM lt1020 WHERE ( (index BETWEEN 9768 AND 13860) ) AND ( stripped_line ~* %s )  LIMIT 200
	d:	('(^|\\s)precatae(\\s|$)|(^|\\s)precor(\\s|$)|(^|\\s)precamini(\\s|$)|(^|\\s)precand[uv]m(\\s|$)|(^|\\s)precer(\\s|$)|(^|\\s)precat[uv]s(\\s|$)|(^|\\s)precor[uv]e(\\s|$)|(^|\\s)precam[uv]rq[uv]e(\\s|$)|(^|\\s)precabor(\\s|$)|(^|\\s)precanda(\\s|$)',)

	sample 'tsvector' search:
		SELECT * FROM lt1020 WHERE to_tsvector(accented_line) @@ to_tsquery('precor');

	results:
	
		substringsearch()
			Sought all 64 known forms of »preco«
			Searched 836 texts and found 1,385 passages (3.98s)
			Sorted by name
	
		tsvectorsearch()
			Sought all 64 known forms of »preco«
			Searched 836 texts and found 1,629 passages (58.39s)
			Sorted by name

	to_tsvector() is way slower: presumably substringsearch() has index to the index while to_tsvector() is effectively reindexing everything
	AND there is also a mismatch in the results...

	the difference between the two sets of results:

		{'line/lt1017w012/19950', 'line/lt0959w007/22909',
			'line/lt0959w002/2874', 'line/lt1512w001/3715',
			'line/lt0975w001/1614', 'line/lt1017w016/44879',
			'line/lt1020w001/1939', 'line/lt0893w001/2382',
			'line/lt0959w006/13769', 'line/lt0959w007/26242',
			'line/lt0893w005/6467', 'line/lt0959w008/27102',
			'line/lt1254w001/7396', 'line/lt1017w008/8356',
			'line/lt1017w001/1020', 'line/lt0893w001/66',
			'line/lt1035w001/4642', 'line/lt1017w003/3010',
			'line/lt0959w006/10283', 'line/lt0975w001/918',
			'line/lt1017w009/10632', 'line/lt0959w007/23294',
			'line/lt0959w002/2651', 'line/lt0474w057/133448',
			'line/lt1017w001/575', 'line/lt1345w001/2081',
			'line/lt0893w003/3828', 'line/lt0890w001/45',
			'line/lt0550w001/5916', 'line/lt0959w006/14092',
			'line/lt1020w002/12520', 'line/lt1345w001/4984',
			'line/lt0660w002/1331', 'line/lt1017w004/4069',
			'line/lt1017w002/2055', 'line/lt0472w001/2079',
			'line/lt1017w009/9248', 'line/lt0893w001/2786',
			'line/lt0474w036/51672', 'line/lt2028w001/31',
			'line/lt0893w001/559', 'line/lt0959w006/21359',
			'line/lt1512w006/11520', 'line/lt0893w001/818',
			'line/lt2349w005/13128', 'line/lt0620w001/3045',
			'line/lt0890w001/84', 'line/lt0893w006/7923',
			'line/lt0893w004/5690', 'line/lt2349w005/11351',
			'line/lt0690w003/5038', 'line/lt1017w008/7966',
			'line/lt2349w005/13129', 'line/lt0893w005/7484',
			'line/lt0972w001/4066', 'line/lt0893w005/7175',
			'line/lt0959w002/3429', 'line/lt1017w003/2858',
			'line/lt0893w005/6609', 'line/lt0893w005/6625',
			'line/lt1351w005/17121', 'line/lt0400w003/810',
			'line/lt2349w005/29263', 'line/lt0660w002/1444',
			'line/lt0959w004/7028', 'line/lt2349w005/12243',
			'line/lt0959w006/15468', 'line/lt0969w001/155',
			'line/lt1017w003/2985', 'line/lt1017w007/7342',
			'line/lt1017w007/6802', 'line/lt0959w006/16035',
			'line/lt0690w003/10534', 'line/lt1017w006/6551'}

		'prece' seems to be the issue
		
		NOTE that it is NOT on the formlist

		terms ['precatae', 'precor', 'precamini', 'precandum', 'precer',
			'precatus', 'precorue', 'precamurque', 'precabor', 'precanda',
			'precando', 'precantia', 'precareris', 'precaturque',
			'precesque', 'precetur', 'precabaturque', 'precaretur',
			'precatu', 'precare', 'precata', 'precatusque', 'precentur',
			'precantibusque', 'precanti', 'precarentur', 'precem', 'preces',
			'precaturi', 'precaturus', 'precabuntur', 'precandi',
			'precantem', 'precabatur', 'precorque', 'precantemque',
			'precabantur', 'precabar', 'precemur', 'precaremur', 'precatam',
			'precandam', 'precans', 'precantes', 'precarer', 'precantur',
			'precabare', 'precarere', 'precaris', 'precatur', 'precatum',
			'precamur', 'precarique', 'precantique', 'precantium',
			'precabamur', 'precatique', 'precari', 'precante',
			'precabanturque', 'precantis', 'preceris', 'precantibus',
			'precati']

	it does not seem like it is worth the trouble to figure out how 'prece' gets found by a first draft that was 20x slower than the current implementation

"""


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
