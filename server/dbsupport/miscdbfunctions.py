# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from multiprocessing import Process
from os import name as osname

import psycopg2

from server import hipparchia
from server.formatting.miscformatting import consolewarning
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


def findselectionboundaries(workobject: dbOpus, selection: str, cursor) -> tuple:
	"""
	
	selections look like
		lt2806w002_AT_3|4
		lt0474w005_FROM_4501_TO_11915
	return (startline, endline) 
	
	:param selection: 
	:return: 
	"""

	if '_FROM_' in selection:
		span = selection.split('_FROM_')[1]
		boundaries = tuple(span.split('_TO_'))
		return boundaries

	# OK, then we must be an '_AT_' ...
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
	# BRITTLE, but circular import if you try to grab this from its real home: dblinefunctions.py
	worklinetemplate = """
			wkuniversalid,
			index,
			level_05_value,
			level_04_value,
			level_03_value,
			level_02_value,
			level_01_value,
			level_00_value,
			marked_up_line,
			accented_line,
			stripped_line,
			hyphenated_words,
			annotations"""

	query = 'SELECT {wtmpl} FROM {uid} WHERE (index BETWEEN %s AND %s) ORDER BY index'.format(wtmpl=worklinetemplate, uid=authortable)
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
			consolewarning('perseusidmismatch() - could not execute', query)
			consolewarning('Error:', e)
			newworkid = returnfirstwork(badworkdbnumber[0:6], cursor)

	return newworkid


def returnfirstwork(authorid: str, dbcursor=None) -> str:
	"""
	more exception handling
	this will produce bad results, but it will not kill the program
	:param authorid:
	:param dbcursor:
	:return:
	"""

	needscleanup = False
	if not dbcursor:
		dbconnection = ConnectionObject()
		dbcursor = dbconnection.cursor()
		needscleanup = True

	# print('panic and grab first work of',authorid)
	query = 'SELECT universalid FROM works WHERE universalid LIKE %s ORDER BY universalid'
	data = (authorid+'%',)
	dbcursor.execute(query, data)
	found = dbcursor.fetchone()
	try:
		found = found[0]
	except IndexError:
		# yikes: an author we don't know about
		# perseus will send you gr1415, but he is not in the db
		# homer...
		found = returnfirstwork('gr0012w001', dbcursor)

	if needscleanup:
		dbconnection.connectioncleanup()

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


def getpostgresserverversion() -> str:
	"""

	what it says on the label...

	hipparchiaDB=# select version();

	------------------------------------------------------------------------------------------------------------------
	PostgreSQL 11.1 on x86_64-apple-darwin17.7.0, compiled by Apple LLVM version 10.0.0 (clang-1000.11.45.5), 64-bit
	(1 row)


	hipparchiaDB=# SHOW server_version;
	server_version
	----------------
	11.1
	(1 row)

	:return:
	"""

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	q = 'SHOW server_version;'
	cursor.execute(q)
	v = cursor.fetchone()
	version = v[0]

	dbconnection.connectioncleanup()

	return version


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


def icanpickleconnections(dothecheck=False) -> bool:
	"""

	some platforms can/can't pickle the connection

	check at startup and notify

	otherwise guess; checking every time would be the safe but very inefficient way to go

	the old ICANPICKLECONNECTIONS setting used to be able to force the answer via configs

	note that 'False' when the answer is in fact 'True' will produce problems: the posix people can't use the nt
	workaround; and the nt people can't do things the posix way

	:param dothecheck:
	:return:
	"""

	if not dothecheck:
		if osname == 'nt':
			return False

		if osname == 'posix':
			return True

	result = True
	c = (ConnectionObject(),)
	j = Process(target=type, args=c)

	try:
		j.start()
		j.join()
	except TypeError:
		result = False

	c[0].connectioncleanup()

	return result


def cleanpoolifneeded():
	"""

	clean out the pool if neccessary before starting
	this seems like the safest time for a reset of the pool: otherwise you could have workers working
	but if you have a multi-user environment AND pool problems this code might make things worse

	:return:
	"""

	if hipparchia.config['ENABLEPOOLCLEANING'] and hipparchia.config['CONNECTIONTYPE'] == 'pool':
		c = ConnectionObject()
		if c.poolneedscleaning:
			c.resetpool()
		c.connectioncleanup()
	return
