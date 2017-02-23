# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import psycopg2
import configparser

from server.hipparchiaclasses import dbAuthor, dbOpus, dbWorkLine
from server import hipparchia

config = configparser.ConfigParser()
config.read('config.ini')


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


def loadallauthorsasobjects():
	"""

	return a dict of all possible author objects

	:return:
	"""

	print('loading all authors...')

	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	q = 'SELECT * FROM authors'

	curs.execute(q)
	results = curs.fetchall()

	authorsdict = {r[0]:dbAuthor(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9]) for r in results}

	print('\t',len(authorsdict),'authors loaded')

	return authorsdict


def loadallworksasobjects():
	"""

	return a dict of all possible work objects

	:return:
	"""

	print('loading all works...')

	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	q = 'SELECT universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, ' \
	        'levellabels_04, levellabels_05, workgenre, transmission, worktype, provenance, recorded_date, converted_date, wordcount, ' \
			'firstline, lastline, authentic FROM works'
	curs.execute(q)
	results = curs.fetchall()

	worksdict = {r[0]:dbOpus(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8],
						 r[9], r[10], r[11], r[12], r[13], r[14], r[15], r[16],
						 r[17], r[18], r[19]) for r in results}

	dbconnection.commit()
	curs.close()

	print('\t', len(worksdict), 'works loaded')

	return worksdict


def dbloadasingleworkobject(workuniversalid):
	"""

	if you get stranded down inside a series of function calls you have no way of recaining access to the master dictionary
	of work objects

	:param workuniversalid:
	:return:
	"""

	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

	q = 'SELECT universalid, title, language, publication_info, levellabels_00, levellabels_01, levellabels_02, levellabels_03, ' \
	        'levellabels_04, levellabels_05, workgenre, transmission, worktype, provenance, recorded_date, converted_date, wordcount, ' \
			'firstline, lastline, authentic FROM works WHERE universalid=%s'
	d = (workuniversalid,)
	curs.execute(q,d)
	r = curs.fetchone()

	workobject = dbOpus(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8],
						 r[9], r[10], r[11], r[12], r[13], r[14], r[15], r[16],
						 r[17], r[18], r[19])

	dbconnection.commit()
	curs.close()

	return workobject


def loadallworksintoallauthors(authorsdict, worksdict):
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


def dblineintolineobject(dbline):
	"""
	convert a db result into a db object

	basically all columns pushed straight into the object with one twist: 1, 0, 2, 3, ...

	:param dbline:
	:return:
	"""

	# note the [1], [0], [2], order: wkuinversalid, index, level_05_value, ...

	lineobject = dbWorkLine(dbline[1], dbline[0], dbline[2], dbline[3], dbline[4], dbline[5], dbline[6], dbline[7],
	                        dbline[8], dbline[9], dbline[10], dbline[11], dbline[12])

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

	label = None
	while label == '' or label == None:
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

	workdbname = workobject.universalid[0:6]
	# step two use the index value to grab the environs
	query = 'SELECT * FROM ' + workdbname + ' WHERE (wkuniversalid = %s) AND (index BETWEEN %s AND %s) ORDER BY index'
	data = (workobject.universalid, focusline - (linesofcontext / 2), focusline + (linesofcontext / 2))
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

	dbconnection.set_session(readonly=True)

	return dbconnection


def returnfirstlinenumber(workid, cursor):
	"""
	return the lowest index value
	used to handle exceptions
	:param db:
	:param cursor:
	:return:
	"""

	db = workid[0:6]

	firstline = -1
	while firstline == -1:
		query = 'SELECT min(index) FROM ' + db + ' WHERE wkuniversalid=%s'
		data = (workid,)
		try:
			cursor.execute(query, data)
			found = cursor.fetchone()
			firstline = found[0]
		except:
			workdb = perseusidmismatch(workid,cursor)
			firstline = returnfirstlinenumber(workid, cursor)
		
	return firstline


def perseusidmismatch(badworkdbnumber,cursor):
	"""
	exception handling
	Perseus says you can look something up in gr0006w16: but there is no such thing
	go through the work list and pick the 16th: hope for the best

	more common is asking for w001 when really 002 or 003 is the 1st valid work number

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


def versionchecking(activedbs, expectedsqltemplateversion):
	"""

	send a warning if the corpora were built from a different template than the one active on the server

	:param activedbs:
	:param expectedsqltemplateversion:
	:return:
	"""

	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()

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
	curs.execute(q)
	results = curs.fetchall()

	corpora = {}
	for r in results:
		corpora[r[0]] = (r[1],r[2])

	for db in activedbs:
		if db in corpora:
			if int(corpora[db][0]) != expectedsqltemplateversion:
				print('\nWARNING\n\t VERSION MISMATCH')
				print('\t',labeldecoder[db],'has a builder template version of',str(corpora[db][0]),'( and the data was compiled',corpora[db][1],')')
				print('\t But the server expects the template version to be',str(expectedsqltemplateversion))
				print('\t EXPECT THE WORST IF YOU TRY TO EXECUTE ANY SEARCHES\nWARNING')

	return


def findchronologicalweights(era,language='G'):
	"""

	an initial call to dictionary_headword_wordcounts to figure out the relative weight of the different eras

	how many words are 'early' / 'middle' / 'late'

	:param era:
	:param language:
	:return:
	"""

	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	eramap = {
		'early': 'early_occurrences',
		'middle': 'middle_occurrences',
		'late': 'late_occurrences'
	}

	try:
		theera = eramap[era]
	except:
		return -1

	q = 'SELECT SUM('+theera+') FROM dictionary_headword_wordcounts WHERE entry_name ~ %s'

	if language == 'G':
		d = ('^[^a-z]',)
	else:
		d = ('[^a-z]',)

	curs.execute(q,d)
	sum = curs.fetchall()
	sum = sum[0][0]

	return sum


def findcorpusweight(corpus):
	"""


	:param corpus:
	:return:
	"""

	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	q = 'SELECT SUM('+corpus+'_count) FROM dictionary_headword_wordcounts'

	curs.execute(q)
	sum = curs.fetchall()
	sum = sum[0][0]

	return sum