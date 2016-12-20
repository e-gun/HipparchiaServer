# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import psycopg2
from server.hipparchiaclasses import dbAuthor, dbOpus, dbWorkLine
from server import hipparchia

def tablenamer(authorobject, thework):
	# tell me the name of your table
	# work 1 is stored as 0: try not to create a table 0; lots of unexpected results can stem from this off-by-one slip
	wk = authorobject.listofworks[thework - 1]
	# wk = authorobject.listworks()[thework - 1]
	nm = authorobject.authornumber
	wn = wk.worknumber

	lg = wk.language
	# how many bilingual authors are there again?
	if lg == 'G':
		pr = 'gr'
	elif lg == 'L':
		pr = 'lt'
	else:
		pr = ''
		print('oh, I do not speak', lg, 'and I will be unable to access a DB')

	workdbname = pr + nm + 'w' + wn

	return workdbname


def labelmaker(workuid, cursor):
	query = 'SELECT levellabels_05,levellabels_04,levellabels_03,levellabels_02,levellabels_01,levellabels_00 from works where universalid = %s'
	# query = 'SELECT levellabels_00,levellabels_01,levellabels_02,levellabels_03,levellabels_04,levellabels_05 from works where universalid = %s'
	data = (workuid,)
	try:
		cursor.execute(query, data)
	except:
		print('somehow failed to find work info for', workuid)

	results = cursor.fetchone()
	return results


def loadallauthors(cursor):
	"""
	build a full set of author objects
	be careful about how much you really need this: a source of lag
	currently called by:
		setavalablegenrelist
	:param cursor:
	:return:
	"""
	query = 'SELECT * from authors ORDER BY shortname ASC'
	cursor.execute(query)
	authorlist = cursor.fetchall()

	authorobjects = []
	for author in authorlist:
		authorobjects.append(dbauthorandworkmaker(author[0],cursor))

	return authorobjects


def dbauthormakersubroutine(uid, cursor):
	# only call this AFTER you have built all of the work objects so that they can be placed into it

	query = 'SELECT * from authors where universalid = %s'
	data = (uid,)
	cursor.execute(query, data)
	try:
		results = cursor.fetchone()
	except:
		# browser forward was producing random errors:
		# 'failed to find the requested author: SELECT * from authors where universalid = %s ('gr1194',)'
		# but this is the author being browsed and another click will browse him further
		# a timing issue: the solution seems to be 'hipparchia.run(threaded=False, host="0.0.0.0")'
		print('failed to find the requested author:', query, data)
		# note that there is no graceful way out of this: you have to have an authorobject in the end
		
	# (universalid, language, idxname, akaname, shortname, cleanname, genres, recorded_date, converted_date, location)
	# supposed to fit the dbAuthor class exactly
	author = dbAuthor(results[0], results[1], results[2], results[3], results[4], results[5], results[6], results[7],
	                  results[8], results[9])

	return author


def dbauthorandworkmaker(authoruid, cursor):
	# note that this will return an AUTHOR filled with WORKS
	# the original Opus objects only exist at the end of HD reads
	# rebuild them from the DB instead: note that this object is simpler than the earlier version, but the stuff you need should all be there...
		
	author = dbauthormakersubroutine(authoruid, cursor)

	query = 'SELECT universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, ' \
	        'levellabels_04, levellabels_05, workgenre, transmission, worktype, provenance, recorded_date, converted_date, wordcount, ' \
			'firstline, lastline, authentic FROM works WHERE universalid LIKE %s'
	data = (authoruid + '%',)
	cursor.execute(query, data)
	try:
		results = cursor.fetchall()
	except:
		# see the notes on the exception to dbauthormakersubroutine: you can get here and then die for the same reason
		print('failed to find the requested work:', query, data)
		results = []

	for match in results:
		work = dbOpus(match[0], match[1], match[2], match[3], match[4], match[5], match[6], match[7], match[8],
		              match[9], match[10], match[11], match[12], match[13], match[14], match[15], match[16],
					  match[17], match[18], match[19])
		author.addwork(work)

	return author


def dblineintolineobject(work, dbline):
	"""
	convert a db result into a db object
	they query had to be for all columns and in order:
		query = 'SELECT index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, stripped_line, hypenated_words, annotations FROM ' + work + ' ORDER BY index ASC'
	:param dbline:
	:return:
	"""

	lineobject = dbWorkLine(work, dbline[0], dbline[1], dbline[2], dbline[3], dbline[4], dbline[5], dbline[6],
	                        dbline[7], dbline[8], dbline[9], dbline[10], dbline[11])
	
	return lineobject


def findtoplevelofwork(workuid, cursor):
	"""
	give me a db name and I will peek into it to see what its top level is
	a way to get around generating an author object when the lexical passages are flowing freely
	:param workuid:
	:param cursor:
	:return:
	"""

	query = 'SELECT levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05 from works where universalid = %s'
	data = (workuid,)
	try:
		cursor.execute(query, data)
		results = cursor.fetchone()
		results = list(results)
	except:
		results = ['zero','','','','', '']
	
	label = ''
	while label == '':
		try:
			label = results.pop()
		except:
			# pop from empty list
			results = '[emptypop]'
		
	numberoflevels = len(results)+1
	
	return numberoflevels


def simplecontextgrabber(workobject, focusline, linesofcontext, cursor):
	"""
	grab a pile of lines centered around the focusline
	:param workobject:
	:param focusline:
	:param linesofcontext:
	:param cursor:
	:return:
	"""

	workdbname = workobject.universalid
	# step two use the index value to grab the environs
	query = 'SELECT * FROM ' + workdbname + ' WHERE index BETWEEN %s AND %s ORDER BY index'
	data = (focusline - (linesofcontext / 2), focusline + (linesofcontext / 2))
	cursor.execute(query, data)
	foundlines = cursor.fetchall()

	return foundlines


def grabonelinefromwork(workdbname, lineindex, cursor):
	"""
	grab a line and return its contents
	"""
	
	query = 'SELECT * FROM ' + workdbname + ' WHERE index = %s'
	data = (lineindex,)
	cursor.execute(query, data)
	foundline = cursor.fetchone()
	
	return foundline


def setconnection(autocommit='n'):
	dbconnection = psycopg2.connect(user=hipparchia.config['DBUSER'], host=hipparchia.config['DBHOST'],
	                                port=hipparchia.config['DBPORT'], database=hipparchia.config['DBNAME'],
	                                password=hipparchia.config['DBPASS'])
	if autocommit == 'autocommit':
		dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
	
	return dbconnection


def returnfirstlinenumber(workdb, cursor):
	"""
	return the lowest index value
	used to handle exceptions
	:param db:
	:param cursor:
	:return:
	"""
	firstline = -1
	while firstline == -1:
		query = 'SELECT min(index) FROM  ' + workdb
		try:
			cursor.execute(query)
			found = cursor.fetchone()
			firstline = found[0]
		except:
			workdb = perseusidmismatch(workdb,cursor)
			firstline = returnfirstlinenumber(workdb, cursor)
		
	return firstline


def perseusidmismatch(badworkdbnumber,cursor):
	"""
	exception handling
	Perseus says you can look something up in gr0006w16: but there is no such thing
	go through the work list and pick the 16th: hope for the best
	:param workdb:
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
			except:
				newworkid = returnfirstwork(badworkdbnumber[0:6], cursor)
		except psycopg2.DatabaseError as e:
			print('perseusidmismatch() - could not execute', query)
			print('Error:', e)
			newworkid = returnfirstwork(badworkdbnumber[0:6], cursor)

	return newworkid


def returnfirstwork(authorid, cursor):
	"""
	more exception handling
	this will produce bad results, but it will not kill the program
	:param authorid:
	:param cursor:
	:return:
	"""

	# print('panic and grab first work of',authorid)
	query = 'SELECT universalid FROM  works WHERE universalid LIKE %s ORDER BY universalid'
	data = (authorid+'%',)
	cursor.execute(query, data)
	found = cursor.fetchone()
	try:
		found = found[0]
	except:
		# yikes: an author we don't know about
		# perseus will send you gr1415, but he is not in the db
		# homer...
		found = returnfirstwork('gr0012w001', cursor)
	
	return found


def makeablankline(work, fakelinenumber):
	"""
	sometimes (like in lookoutsidetheline()) you need a dummy line
	this will build one
	:param work:
	:return:
	"""
	
	lineobject = dbWorkLine(work, fakelinenumber, '-1', '-1', '-1', '-1', '-1', '-1', '', '', '', '', '')
	
	return lineobject


def makeanemptyauthor(universalid):
	"""
	avoiding an exception by evoking an empty author object temporarily
	:param universalid:
	:return:
	"""
	
	# (universalid, language, idxname, akaname, shortname, cleanname, genres, recorded_date, converted_date, location)
	aobject = dbAuthor(universalid, '', '', '', '', '', '', '', '', '')
	
	return aobject


def makeanemptywork(universalid):
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
