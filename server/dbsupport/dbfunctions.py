# -*- coding: utf-8 -*-
# assuming py35 or higher
import psycopg2
from server.hipparchiaclasses import dbAuthor, dbOpus
from server import hipparchia

def tablenamer(authorobject, thework):
	# tell me the name of your table
	# work 1 is stored as 0: try not to create a table 0; lots of unexpected results can stem from this off-by-one slip
	wk = authorobject.listofworks[thework - 1]
	# wk = authorobject.listworks()[thework - 1]
	nm = authorobject.authornumber
	wn = wk.worknumber

	if wn < 10:
		nn = '00' + str(wn)
	elif wn < 100:
		nn = '0' + str(wn)
	else:
		nn = str(wn)

	lg = wk.language
	# how many bilingual authors are there again?
	if lg == 'G':
		pr = 'gr'
	elif lg == 'L':
		pr = 'lt'
	else:
		pr = ''
		print('oh, I do not speak', lg, 'and I will be unable to access a DB')

	workdbname = pr + nm + 'w' + nn

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
		
	# (universalid, language, idxname, akaname, shortname, cleanname, genres, floruit, location)
	# supposed to fit the dbAuthor class exactly
	author = dbAuthor(results[0], results[1], results[2], results[3], results[4], results[5], results[6], results[7],
	                  results[8])

	return author


def dbauthorandworkmaker(authoruid, cursor):
	# note that this will return an AUTHOR filled with WORKS
	# the original Opus objects only exist at the end of HD reads
	# rebuild them from the DB instead: note that this object is simpler than the earlier version, but the stuff you need should all be there...
		
	author = dbauthormakersubroutine(authoruid, cursor)

	query = 'SELECT * from works where universalid LIKE %s'
	data = (authoruid + '%',)
	cursor.execute(query, data)
	try:
		results = cursor.fetchall()
	except:
		# see the notes on the exception to dbauthormakersubroutine: you can get here and then die for the same reason
		print('failed to find the requested work:', query, data)
	# (universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, levellabels_04, levellabels_05)

	for match in results:
		work = dbOpus(match[0], match[1], match[2], match[3], match[4], match[5], match[6], match[7], match[8],
		              match[9])
		author.addwork(work)

	return author


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
	query = 'SELECT * FROM ' + workdbname + ' WHERE index BETWEEN %s AND %s'
	data = (focusline - (linesofcontext / 2), focusline + (linesofcontext / 2))
	cursor.execute(query, data)
	foundlines = cursor.fetchall()

	return foundlines


def indexintocitationtuple(workdbname, indexvalue, cursor):
	"""
	tell me a line number inthe db and i will get you the citation associated with it
	:param workuid:
	:param indexvalue:
	:return:
	"""

	query = 'SELECT level_00_value, level_01_value, level_02_value, level_03_value, level_04_value, level_05_value FROM ' + workdbname + ' WHERE index = %s'
	data = (indexvalue,)
	cursor.execute(query, data)
	cit = cursor.fetchone()
	
	citationtuple = list(cit)
	citationtuple = [x for x in citationtuple if (x != '-1') and (x != None)]
	citationtuple = tuple(citationtuple)
	
	return citationtuple


def setconnection(autocommit='n'):
	dbconnection = psycopg2.connect(user=hipparchia.config['DBUSER'], host=hipparchia.config['DBHOST'],
	                                port=hipparchia.config['DBPORT'], database=hipparchia.config['DBNAME'],
	                                password=hipparchia.config['DBPASS'])
	if autocommit == 'autocommit':
		dbconnection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
	
	return dbconnection