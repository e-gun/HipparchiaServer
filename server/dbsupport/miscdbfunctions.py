# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import configparser

import psycopg2

from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.dbtextobjects import dbAuthor, dbOpus

# to fiddle with some day:
# 'In our testing asyncpg is, on average, 3x faster than psycopg2 (and its asyncio variant -- aiopg).'
# https://github.com/MagicStack/asyncpg
# pypy3
# pypy3 support is EXPERIMENTAL (and unlikely to be actively pursued)
#   mostly works
#   not obviously faster (since searches are 95% waiting for postgres...)
#   sometimes much slower (and right where you might think that 'more python' was happening)
#       index to aristotle
#           python3: 9.68s
#           pypy3: 72.54s
#   bugs out if you have lots of hits
#       psycopg2cffi._impl.exceptions.OperationalError
#       [substantially lower the commit count?]

config = configparser.ConfigParser()
config.read('config.ini')


def resultiterator(cursor, chunksize=5000):
	"""

	Yield a generator from fetchmany to keep memory usage down in contrast to

		results = curs.fetchall()

	see: http://code.activestate.com/recipes/137270-use-generators-for-fetching-large-db-record-sets/

	:param cursor:
	:param chunksize:
	:return:
	"""

	while True:
		try:
			results = cursor.fetchmany(chunksize)
		except psycopg2.ProgrammingError:
			# psycopg2.ProgrammingError: no results to fetch
			# you only see this when using the PooledConnectionObject (which is itself buggy)
			results = None
		if not results:
			break
		for result in results:
			yield result


def dbloadasingleworkobject(workuniversalid: str) -> dbOpus:
	"""

	if you get stranded down inside a series of function calls you have no way of regaining access to the master dictionary
	of work objects

	:param workuniversalid:
	:return:
	"""

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	q = """
	SELECT universalid, title, language, publication_info, 
		levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05, 
		workgenre, transmission, worktype, provenance, recorded_date, converted_date, wordcount, 
		firstline, lastline, authentic FROM works WHERE universalid=%s
	"""

	d = (workuniversalid,)
	cursor.execute(q, d)
	r = cursor.fetchone()

	workobject = dbOpus(*r)

	dbconnection.connectioncleanup()

	return workobject


def findtoplevelofwork(workuid: str, cursor) -> int:
	"""
	give me a db name and I will peek into it to see what its top level is
	a way to get around generating an author object when the lexical passages are flowing freely
	:param workuid:
	:param cursor:
	:return:
	"""

	query = """
	SELECT levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05 
		FROM works WHERE universalid = %s
	"""

	data = (workuid,)
	try:
		cursor.execute(query, data)
		results = cursor.fetchone()
		results = list(results)
	except:
		results = ['zero', '', '', '', '', '']

	label = None
	while label == '' or label == None:
		try:
			label = results.pop()
		except IndexError:
			# pop from empty list
			results = '[emptypop]'
		
	numberoflevels = len(results)+1

	return numberoflevels


def findselectionboundaries(workobject: dbOpus, selection: str, cursor) -> tuple:
	"""
	
	ask for _AT_x|y|z
	
	return (startline, endline) 
	
	:param selection: 
	:return: 
	"""

	locus = selection[14:].split('|')

	wklvls = list(workobject.structure.keys())
	wklvls.reverse()

	whereclausetuples = list()

	index = -1
	for l in locus:
		index += 1
		lvstr = 'level_0{i}_value=%s '.format(i=wklvls[index])
		whereclausetuples.append((lvstr, l))

	qw = ['wkuniversalid=%s']
	d = [workobject.universalid]
	for i in range(0, len(whereclausetuples)):
		qw.append(whereclausetuples[i][0])
		d.append(whereclausetuples[i][1])
	qw = ' AND '.join(qw)

	q = 'SELECT index FROM {au} WHERE ({whcl}) ORDER BY index ASC'.format(au=workobject.authorid, whcl=qw)
	d = tuple(d)
	cursor.execute(q, d)
	results = cursor.fetchall()

	boundaries = [r[0] for r in results]
	try:
		boundaries = (boundaries[0], boundaries[-1])
	except IndexError:
		boundaries = None

	return boundaries


def simplecontextgrabber(authortable: str, focusline: int, linesofcontext: int, cursor) -> list:
	"""

	grab a pile of lines centered around the focusline

	:param authortable:
	:param focusline:
	:param linesofcontext:
	:param cursor:
	:return:
	"""

	query = 'SELECT * FROM {uid} WHERE (index BETWEEN %s AND %s) ORDER BY index'.format(uid=authortable)
	data = (focusline - int(linesofcontext / 2), focusline + int(linesofcontext / 2))
	cursor.execute(query, data)
	foundlines = cursor.fetchall()

	return foundlines


def perseusidmismatch(badworkdbnumber: str, cursor) -> str:
	"""
	exception handling
	Perseus says you can look something up in gr0006w16: but there is no such thing
	go through the work list and pick the 16th: hope for the best

	more common is asking for w001 when really 002 or 003 is the 1st valid work number

	:param badworkdbnumber:
	:param cursor:
	:return:
	"""
	
	newworkid = '[na]'
	# print('ick: perseus wants',badworkdbnumber,'but this does not exist')
	
	while newworkid == '[na]':
		query = 'SELECT universalid FROM works WHERE universalid LIKE %s ORDER BY universalid ASC'
		data = (badworkdbnumber[0:6]+'%',)
		try:
			cursor.execute(query, data)
			works = cursor.fetchall()
			try:
				oldnumber = int(badworkdbnumber[8:10])
				newworkid = works[oldnumber][0]
			except IndexError:
				newworkid = returnfirstwork(badworkdbnumber[0:6], cursor)
		except psycopg2.DatabaseError as e:
			print('perseusidmismatch() - could not execute', query)
			print('Error:', e)
			newworkid = returnfirstwork(badworkdbnumber[0:6], cursor)

	return newworkid


def returnfirstwork(authorid: str, cursor) -> str:
	"""
	more exception handling
	this will produce bad results, but it will not kill the program
	:param authorid:
	:param cursor:
	:return:
	"""

	# print('panic and grab first work of',authorid)
	query = 'SELECT universalid FROM works WHERE universalid LIKE %s ORDER BY universalid'
	data = (authorid+'%',)
	cursor.execute(query, data)
	found = cursor.fetchone()
	try:
		found = found[0]
	except IndexError:
		# yikes: an author we don't know about
		# perseus will send you gr1415, but he is not in the db
		# homer...
		found = returnfirstwork('gr0012w001', cursor)
	
	return found


def makeanemptyauthor(universalid: str) -> dbAuthor:
	"""
	avoiding an exception by evoking an empty author object temporarily
	:param universalid:
	:return:
	"""
	
	# (universalid, language, idxname, akaname, shortname, cleanname, genres, recorded_date, converted_date, location)
	aobject = dbAuthor(universalid, '', '', '', '', '', '', '', '', '')
	
	return aobject


def makeanemptywork(universalid: str) -> dbOpus:
	"""
	avoiding an exception by evoking an empty work object temporarily
	:param universalid:
	:return:
	"""
	
	# universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03,
	# levellabels_04, levellabels_05, workgenre, transmission, worktype, provenance, recorded_date, converted_date, wordcount,
	# firstline, lastline, authentic
	wkobject = dbOpus(universalid, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', 0, 0, '')
	
	return wkobject


def versionchecking(activedbs: list, expectedsqltemplateversion: str) -> str:
	"""

	send a warning if the corpora were built from a different template than the one active on the server

	:param activedbs:
	:param expectedsqltemplateversion:
	:return:
	"""

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	activedbs += ['lx', 'lm']
	labeldecoder = {
		'lt': 'The corpus of Latin authors',
		'gr': 'The corpus of Greek authors',
		'in': 'The corpus of classical inscriptions',
		'dp': 'The corpus of papyri',
		'ch': 'The corpus of Christian era inscriptions',
		'lx': 'The lexical database',
		'lm': 'The parsing database'
	}

	q = 'SELECT corpusname, templateversion, corpusbuilddate FROM builderversion'
	cursor.execute(q)
	results = cursor.fetchall()

	corpora = {r[0]: (r[1], r[2]) for r in results}

	for db in activedbs:
		if db in corpora:
			if int(corpora[db][0]) != expectedsqltemplateversion:
				t = """
				WARNING: VERSION MISMATCH
				{d} has a builder template version of {v}
				(and was compiled {t})
				But the server expects the template version to be {e}.
				EXPECT THE WORST IF YOU TRY TO EXECUTE ANY SEARCHES
				"""
				print(t.format(d=labeldecoder[db], v=corpora[db][0], t=corpora[db][1], e=expectedsqltemplateversion))

	buildinfo = ['\t{corpus}: {date} [{prolix}]'.format(corpus=c, date=corpora[c][1], prolix=labeldecoder[c])
				for c in sorted(corpora.keys())]
	buildinfo = '\n'.join(buildinfo)

	dbconnection.connectioncleanup()

	return buildinfo


def probefordatabases() -> dict:
	"""

	figure out which non-author tables are actually installed

	:return:
	"""

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	available = dict()

	possible = ['greek_dictionary', 'greek_lemmata', 'greek_morphology',
	            'latin_dictionary', 'latin_lemmata', 'latin_morphology',
	            'wordcounts_0']

	for p in possible:
		q = 'SELECT * FROM {table} LIMIT 1'.format(table=p)
		try:
			cursor.execute(q)
			results = cursor.fetchall()
		except psycopg2.ProgrammingError:
			# psycopg2.ProgrammingError: relation "greek_morphology" does not exist
			results = False

		if results:
			available[p] = True
		else:
			available[p] = False

	dbconnection.connectioncleanup()

	return available
