# -*- coding: utf-8 -*-
# assuming py35 or higher
from flask import session

from server.dbsupport.citationfunctions import finddblinefromlocus
from .dbobjects import *


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


def contextgrabber(authorobject, worknumber, citationtuple, contexttuple):
	# WARNING
	# this is not integrated into the current shape of things...
	# citationtuple ('9', '109', '8') to focus on line 9, section 109, book 8
	# contexttuple (1,5) means give me all of the surrounding level one material +/-5 lvl 1 units
	# note that the former is a string and the latter an int
	# probably produces interesting results if you want 342c5 +/- 'c' ...
	lmap = {0: 'level_00_value', 1: 'level_01_value', 2: 'level_02_value', 3: 'level_03_value', 4: 'level_04_value',
	        5: 'level_05_value'}

	wk = authorobject.listofworks[worknumber - 1]
	wklvs = list(wk.structure.keys())
	if len(wklvs) != len(citationtuple):
		print('mismatch between shape of work and context request: impossible citation')
		print(list(wk.structure.keys()),'vs',list(citationtuple))
	if contexttuple[0] > len(wklvs) - 1:
		print('mismatch between shape of work and context request: impossible context')

	workdbname = tablenamer(authorobject, worknumber)
	query = 'SELECT * FROM ' + workdbname + ' WHERE '

	# you can discard any level lower than the first digit of the contexttuple
	# WHERE ... lvl=cited applies to levels higher than that value

	datalist = []
	for level in range(contexttuple[0] + 1, len(citationtuple)):
		query += lmap[level] + '= %s AND '
		datalist.append(citationtuple[level])
	query += lmap[contexttuple[0]] + ' BETWEEN %s and %s'
	try:
		high = int(citationtuple[contexttuple[0]]) + contexttuple[1]
		low = int(citationtuple[contexttuple[0]]) - contexttuple[1]
		datalist.append(str(low))
		datalist.append(str(high))
	except:
		# did you try to add a number to a letter?
		# will do nothing special for now
		datalist.append(citationtuple[contexttuple[0]])
		datalist.append(citationtuple[contexttuple[0]])

	data = tuple(datalist)
	cursor.execute(query, data)
	found = cursor.fetchall()

	# note that this is a string search so the results can have some oddities:
	# kludge to eliminate them is to force only consecutive lines to display by checking the index values

	return found


def simplecontextgrabber(workobject, citationtuple, linesofcontext, cursor):
	# citationtuple ('9','109','8') to focus on line 9, section 109, book 8
	# simplecontextgrabber(h, 1, ('130', '24'),4, cursor)

	focusline = finddblinefromlocus(workobject, citationtuple, cursor)
	workdbname = workobject.universalid
	# step two use the index value to grab the environs
	# The variables placeholder must always be a %s, even if a different placeholder (such as a %d for integers or %f for floats) may look more appropriate
	query = 'SELECT * FROM ' + workdbname + ' WHERE index BETWEEN %s AND %s'
	data = (focusline - (linesofcontext / 2), focusline + (linesofcontext / 2))
	cursor.execute(query, data)
	foundlines = cursor.fetchall()

	return foundlines


##
## search functions
##



