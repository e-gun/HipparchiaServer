# -*- coding: utf-8 -*-
import re
from server.dbsupport.dbfunctions import findtoplevelofwork, returnfirstlinenumber, perseusidmismatch, returnfirstwork


def findvalidlevelvalues(workdb, workstructure, partialcitationtuple, cursor):
	"""
	tell me some of a citation and i can tell you what is a valid choice at the next step
	i expect the lowest level to be stored at position 0 in the tuple
	note that you should not send me a full citation because i will look at lowestlevel-1
	:param workdb:
	:param atlevel:
	:return: a tuple with the available levels, current level, level label, low and high value: (2, 0, 'verse', '1', '100'), e.g.
	"""
	availablelevels = len(workstructure)
	atlevel = availablelevels-len(partialcitationtuple)
	# cheat in the case where you want to find the top by sending a 'noncitation': '-1'
	# e.g.: /getstructure?locus=gr0003w001_AT_-1
	if partialcitationtuple[0] == '-1':
		atlevel = availablelevels
	if atlevel < 1:
		# i am confused; threatening to probe for level "-1"
		# a selection at level00 will do this to me
		#   /getstructure?locus=gr0003w001_AT_3|36|5|3
		# this needs to be made uncontroversial:
		#   /getstructure?locus=gr0003w001_AT_3|36|5
		# and so: massage the data
		atlevel = 1
		try:
			partialcitationtuple.pop()
		except:
			atlevel = availablelevels
		
	# select level_00_value from gr0565w001 where level_03_value='3' AND level_02_value='2' AND level_01_value='1' AND level_00_value NOT IN ('t') ORDER BY index ASC;
	# select level_01_value from gr0565w001 where level_03_value='2' AND level_02_value='1' AND level_01_value NOT IN ('t') ORDER BY index ASC;
	query = 'SELECT level_0' + str(atlevel-1) + '_value FROM ' + workdb + ' WHERE '
	datalist = []
	for level in range(availablelevels - 1, atlevel - 1, -1):
		query += ' level_0' + str(level) + '_value=%s AND '
		datalist.append(partialcitationtuple[availablelevels-level-1])
	query += 'level_0' + str(atlevel-1) +'_value NOT IN (%s) ORDER BY index'
	datalist.append('t')
	data = tuple(datalist)
	cursor.execute(query, data)
	values = cursor.fetchall()
	low = values[0][0]
	high = values[-1][0]
	rng = []
	for val in values:
		rng.append(val[0])
	rng = list(set(rng))
	rng.sort()

	lowandhigh = (availablelevels, atlevel-1, workstructure[atlevel - 1], low, high, rng)

	return lowandhigh


def locusintocitation(workobject, citationtuple):
	"""
	transform something like ('9','109','8') into a citations like "Book 8, section 108, line 9"
	:param authorobject:
	:param worknumber:
	:param citationtuple:
	:return:
	"""
	wklvls = list(workobject.structure.keys())
	cite = list(citationtuple)
	# cite.reverse()
	wklvls.reverse()
	citation = ''
	for level in wklvls:
		try:
			citation += workobject.structure[level]+' '+cite[level]+', '
		except:
			# did you send me a partial citation like "book 2"?
			pass
	citation = citation[:-2]
	return citation


def prolixlocus(workobject, citationtuple):
	"""
	transform something like ('9','109','8') into a citation like "Book 8, section 108, line 9"
	differes from the preceding only by a range and a wklvls[level]
	:param authorobject:
	:param worknumber:
	:param citationtuple:
	:return:
	"""
	wklvls = list(workobject.structure.keys())
	wklvls.reverse()
	cite = list(citationtuple)
	cite.reverse()
	citation = ''
	for level in range(0,len(wklvls)):
		try:
			citation += workobject.structure[wklvls[level]]+' '+cite[level]+', '
		except:
			# did you send me a partial citation like "book 2"?
			pass
	citation = citation[:-2]
	return citation


def finddblinefromlocus(workdb, citationtuple, cursor):
	# citationtuple ('9','109','8') to focus on line 9, section 109, book 8
	# finddblinefromlocus(h, 1, ('130', '24')) ---> 15033

	lmap = {0: 'level_00_value', 1: 'level_01_value', 2: 'level_02_value', 3: 'level_03_value', 4: 'level_04_value',
	        5: 'level_05_value'}
	
	wklvs = findtoplevelofwork(workdb, cursor)

	if wklvs != len(citationtuple):
		print('mismatch between shape of work and browsing request: impossible citation of'+workdb+'.')
		print(str(wklvs),' levels vs',list(citationtuple))
		print('safe to ignore if you requested the first line of a work')

	# step one: find the index number of the passage
	query = 'SELECT index FROM ' + workdb + ' WHERE '
	for level in range(0, len(citationtuple)):
		query += lmap[level] + '=%s AND '
	# drop the final 'AND '
	query = query[:-4]
	data = citationtuple
	try:
		cursor.execute(query, data)
		found = cursor.fetchone()
		indexvalue = found[0]
	except:
		# print('requested locus returned nothing:', query, data)
		indexvalue = returnfirstlinenumber(workdb, cursor)
		
	return indexvalue


def finddblinefromincompletelocus(workid, citationlist, cursor):
	"""
	need to deal with the perseus bibliographic references which often do not go all the way down to level zero
	use what you have to find the first available db line so you can construck a '_LN_' browseto click
	the citation list arrives in ascending order of levels: 00, 01, 02...
	:param workid:
	:param citationlist:
	:param cursor:
	:return:
	"""
	
	lmap = {0: 'level_00_value', 1: 'level_01_value', 2: 'level_02_value', 3: 'level_03_value', 4: 'level_04_value',
	        5: 'level_05_value'}
	
	try:
		# perseus does not always agree with our ids...
		returnfirstlinenumber(workid, cursor)
		numberoflevels = findtoplevelofwork(workid, cursor)
	except:
		# perseus did not agree with our ids...: euripides, esp
		# what follows is a 'hope for the best' approach
		# notice that this bad id has been carved into the page html already
		
		workid = perseusidmismatch(workid, cursor)
		try:
			numberoflevels = findtoplevelofwork(workid, cursor)
		except:
			print('failed 2x to find the work')
			workid = returnfirstwork(workid[0:6], cursor)
			numberoflevels = findtoplevelofwork(workid, cursor)

	if numberoflevels == len(citationlist):
		# congratulations, you have a fully formed citation (maybe...)
		dblinenumber = finddblinefromlocus(workid, citationlist, cursor)
	elif numberoflevels < len(citationlist):
		# something stupid like plautus' acts and scenes when you only want the line numbers
		# option 1: truncate the 'too long' bits and hope for the best
		# will definitely fail to pull up the right line in the case of plays
		# unless you were looking at act 1 scene 1 anyway
		# newcitationlist = []
		# for i in range(0,numberoflevels):
		#	newcitationlist.append(citationlist[i])
		# citationlist = newcitationlist
		
		# option 2: just give up
		dblinenumber = -9999
	else:
		# you have an incomplete citation: assume that the top level is the last item, etc.
		citationlist = perseuscitationsintohipparchiacitations(citationlist)
		citationlist.reverse()
		query = 'SELECT index FROM ' + workid + ' WHERE '
		try:
			for level in range(numberoflevels-1, numberoflevels-len(citationlist)-1,-1):
				query += lmap[level] + '=%s AND '
		except:
			query += lmap[0] + '=%s AND '
			
		# drop the final 'AND '
		query = query[:-4] + ' ORDER BY index ASC'
		data = tuple(citationlist)
		try:
			cursor.execute(query, data)
			found = cursor.fetchone()
			dblinenumber = found[0]
		except:
			dblinenumber = -9999
		
	return dblinenumber

def perseuscitationsintohipparchiacitations(citationlist):
	"""
	a collections of hopes and prayers that attempts to minimize the misfits between perseus citations and hipparchia citations
	the perseus data is saturated with problems
		euripides work numbers are always bad
		plays are cited by act
		222a and not 222 + a
		plutarch looks like 'Plu.2.263f' and not just '263f'
		sometimes you have '30(31)'
		some citations are not tied to a tlg reference
	:param citationlist:
	:return:
	"""
	newcitationlist = []
	
	for item in citationlist:
		if re.search(r'^p\.',item) is not None:
			item = item[2:]
		item = re.sub(r'\(.*?\)','',item)
		newcitationlist.append(item)
	
	citationlist = newcitationlist
	newcitationlist = []
	
	for item in citationlist:
		try:
			if item[-2].isdigit() and item[-1].islower():
				parta = item[-1]
				partb = item[:-1]
				newcitationlist.append(parta)
				newcitationlist.append(partb)
			else:
				newcitationlist.append(item)
		except:
			# item[-2] was impossible
			newcitationlist.append(item)
	
	return newcitationlist