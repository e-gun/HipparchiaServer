# -*- coding: utf-8 -*-

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


def locusintosearchitem(workobject, citationtuple):
	"""
	transform something like ('9','109','8') into a citations like "Book 8, section 108, line 9"
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


def finddblinefromlocus(workobject, citationtuple, cursor):
	# citationtuple ('9','109','8') to focus on line 9, section 109, book 8
	# finddblinefromlocus(h, 1, ('130', '24')) ---> 15033

	lmap = {0: 'level_00_value', 1: 'level_01_value', 2: 'level_02_value', 3: 'level_03_value', 4: 'level_04_value',
	        5: 'level_05_value'}

	wklvs = list(workobject.structure.keys())
	if len(wklvs) != len(citationtuple):
		print('mismatch between shape of work and browsing request: impossible citation of,'
		      +workobject.universalid+' '+workobject.title+'.')
		print(wklvs,'vs',list(citationtuple))
		print('safe to ignore if you requested the first line of a work')

	workdbname = workobject.universalid
	# step one: find the index number of the passage
	query = 'SELECT index FROM ' + workdbname + ' WHERE '
	for level in range(0, len(citationtuple)):
		query += lmap[level] + '=%s AND '
	# drop the final 'AND '
	query = query[:-4]
	data = citationtuple
	cursor.execute(query, data)
	try:
		found = cursor.fetchone()
	except:
		# but maybe the last line is what we wanted...
		# this is a total co-out since not every work even begins with '1'...
		# handle me properly some day
		print('requested locus returned nothing:',query, data)
		indexvalue = 1
	try:
		indexvalue = found[0]
	except:
		print('sought an impossible locus:',query,'d:',data)
		indexvalue = 1

	return indexvalue