# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from collections import deque

from server.dbsupport.miscdbfunctions import perseusidmismatch, resultiterator
from server.dbsupport.tablefunctions import assignuniquename
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.dbtextobjects import dbWorkLine


# this next should be used by *lots* of functions to make sure that what you ask for fits the dbWorkLine() params
worklinetemplate = ['wkuniversalid', 'index', 'level_05_value', 'level_04_value', 'level_03_value',
					'level_02_value', 'level_01_value', 'level_00_value', 'marked_up_line',
					'accented_line', 'stripped_line', 'hyphenated_words', 'annotations']

worklinetemplate = ', '.join(worklinetemplate)


def dblineintolineobject(dbline: tuple) -> dbWorkLine:
	"""

	convert a db result into a db object

	basically all columns pushed straight into the object with *one* twist: 1, 0, 2, 3, ...

	worklinetemplate should fix this

	:param dbline:
	:return:
	"""

	# WARNING: be careful about the [1], [0], [2], order: wkuinversalid, index, level_05_value, ...

	lineobject = dbWorkLine(*dbline)

	return lineobject


def grabonelinefromwork(workdbname: str, lineindex: int, cursor) -> tuple:
	"""
	grab a line and return its contents
	"""

	query = 'SELECT {wtmpl} FROM {wk} WHERE index = %s'.format(wtmpl=worklinetemplate, wk=workdbname)
	data = (lineindex,)
	cursor.execute(query, data)
	foundline = cursor.fetchone()

	return foundline


def returnfirstlinenumber(workid: str, cursor) -> int:
	"""
	return the lowest index value
	used to handle exceptions

	:param workid:
	:param cursor:
	:return:
	"""

	db = workid[0:6]

	firstline = -1
	while firstline == -1:
		query = 'SELECT min(index) FROM {db} WHERE wkuniversalid=%s'.format(db=db)
		data = (workid,)
		try:
			cursor.execute(query, data)
			found = cursor.fetchone()
			firstline = found[0]
		except IndexError:
			workid = perseusidmismatch(workid, cursor)
			firstline = returnfirstlinenumber(workid, cursor)

	return firstline


def makeablankline(work: str, fakelinenumber: int) -> dbWorkLine:
	"""

	sometimes (like in lookoutsidetheline()) you need a dummy line
	this will build one

	:param work:
	:param fakelinenumber:
	:return:
	"""

	lineobject = dbWorkLine(work, fakelinenumber, '-1', '-1', '-1', '-1', '-1', '-1', '', '', '', '', '')

	return lineobject


def bulklinegrabber(table: str, column: str, criterion: str, setofcriteria, cursor) -> dict:
	"""

	snarf up a huge number of lines

	:param table:
	:param column:
	:param criterion:
	:param setofcriteria:
	:param cursor:
	:return:
	"""

	qtemplate = 'SELECT {cri}, {col} FROM {t} WHERE {cri} = ANY(%s)'
	q = qtemplate.format(col=column, t=table, cri=criterion)
	d = (list(setofcriteria),)

	cursor.execute(q, d)
	lines = resultiterator(cursor)

	contents = {'{t}@{i}'.format(t=table, i=l[0]): l[1] for l in lines}

	return contents


def grablistoflines(table: str, uidlist: list) -> list:
	"""

	fetch many lines at once

	select shortname from authors where universalid = ANY('{lt0860,gr1139}');

	:param uidlist:
	:return:
	"""

	dbconnection = ConnectionObject()
	cursor = dbconnection.cursor()

	lines = [int(uid.split('_ln_')[1]) for uid in uidlist]

	qtemplate = 'SELECT {wtmpl} from {tb} WHERE index = ANY(%s)'

	q = qtemplate.format(wtmpl=worklinetemplate, tb=table)
	d = (lines,)
	cursor.execute(q, d)
	lines = cursor.fetchall()

	dbconnection.connectioncleanup()

	lines = [dblineintolineobject(l) for l in lines]

	return lines


def grabbundlesoflines(worksandboundaries: dict, cursor) -> list:
	"""
	grab and return lots of lines
	this is very generic
	typical uses are
		one work + a line range (which may or may not be the whole work: {'work1: (start,stop)}
		multiple (whole) works: {'work1': (start,stop), 'work2': (start,stop), ...}
	but you could one day use this to mix-and-match:
		a completeindex of Thuc + Hdt 3 + all Epic...
	this is, you could use compileauthorandworklist() to feed this function
	the resulting concorances would be massive

	:param worksandboundaries:
	:param cursor:
	:return:
	"""

	lineobjects = deque()

	for w in worksandboundaries:
		db = w[0:6]
		query = 'SELECT {wtmpl} FROM {db} WHERE (index >= %s AND index <= %s)'.format(wtmpl=worklinetemplate, db=db)
		data = (worksandboundaries[w][0], worksandboundaries[w][1])
		cursor.execute(query, data)
		lines = resultiterator(cursor)

		thiswork = [dblineintolineobject(l) for l in lines]
		lineobjects.extend(thiswork)

	return list(lineobjects)


def bulkenvironsfetcher(table: str, searchresultlist: list, context: int) -> list:
	"""

	given a list of SearchResult objects, populate the lineobjects of each SearchResult with their contexts

	:param table:
	:param searchresultlist:
	:param context:
	:return:
	"""

	dbconnection = ConnectionObject(readonlyconnection=False)
	dbconnection.setautocommit()
	cursor = dbconnection.cursor()

	tosearch = deque()
	reversemap = dict()

	for r in searchresultlist:
		resultnumber = r.hitnumber
		focusline = r.getindex()
		environs = list(range(int(focusline - (context / 2)), int(focusline + (context / 2)) + 1))
		tosearch.extend(environs)
		rmap = {e: resultnumber for e in environs}
		reversemap.update(rmap)
		r.lineobjects = list()

	tosearch = [str(x) for x in tosearch]

	tqtemplate = """
	CREATE TEMPORARY TABLE {au}_includelist_{ac} AS
		SELECT values AS 
			includeindex FROM unnest(ARRAY[{lines}]) values
	"""

	# avoidcollisions instead of DROP TABLE IF EXISTS; the table disappears when the connection is cleaned up
	avoidcollisions = assignuniquename()

	tempquery = tqtemplate.format(au=table, ac=avoidcollisions, lines=','.join(tosearch))
	cursor.execute(tempquery)

	qtemplate = """
	SELECT {wtmpl} FROM {au} WHERE EXISTS 
		(SELECT 1 FROM {au}_includelist_{ac} incl WHERE incl.includeindex = {au}.index)
	"""

	query = qtemplate.format(wtmpl=worklinetemplate, au=table, ac=avoidcollisions)
	cursor.execute(query)
	results = resultiterator(cursor)

	lines = [dblineintolineobject(r) for r in results]
	indexedlines = {l.index: l for l in lines}

	for r in searchresultlist:
		environs = list(range(int(r.getindex() - (context / 2)), int(r.getindex() + (context / 2)) + 1))
		for e in environs:
			try:
				r.lineobjects.append(indexedlines[e])
			except KeyError:
				# you requested a line that was outside of the scope of the table
				# so there was no result and the key will not match a find
				pass

	dbconnection.connectioncleanup()

	return searchresultlist
