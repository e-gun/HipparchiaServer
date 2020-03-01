# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server.dbsupport.dblinefunctions import dblineintolineobject, returnfirstlinenumber, worklinetemplate
from server.formatting.miscformatting import consolewarning
from server.formatting.wordformatting import avoidsmallvariants
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.dbtextobjects import dbOpus
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.hipparchiaobjects.helperobjects import LowandHighInfo
from server.startup import workdict


def findvalidlevelvalues(workobject: dbOpus, partialcitationtuple: tuple, cursor) -> LowandHighInfo:
	"""

	tell me some of a citation and i can tell you what is a valid choice at the next step
	i expect the lowest level to be stored at position 0 in the tuple
	note that you should not send me a full citation because i will look at lowestlevel-1

	sample imput:
		workid = lt0474w015
		workstructure = {0: 'line', 1: 'section'}
		partialcitationtuple = ('13',)
	out:
		(Cicero, Pro Sulla 13)

	note that this is mildly costly as a function call when you convert all of the results to lineobjects
	OOP is a lot easier; but you pay a price

	this also means that lowering the init costs of dbworklines is a good idea

	--------------------------------------------------------------------------------

	127.0.0.1 - - [16/Apr/2019 21:55:27] "GET /getworksof/lt2349 HTTP/1.1" 200 -
	--------------------------------------------------------------------------------
	PATH: '/getstructure/lt2349/005'
	         208072 function calls in 0.380 seconds

	   Ordered by: internal time, call count
	   List reduced from 254 to 25 due to restriction <25>

	   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
	    34548    0.099    0.000    0.174    0.000 /Users/erik/hipparchia_venv/HipparchiaServer/server/hipparchiaobjects/worklineobject.py:83(__init__)
	    69098    0.071    0.000    0.071    0.000 {method 'format' of 'str' objects}
	        1    0.063    0.063    0.063    0.063 {method 'execute' of 'psycopg2.extensions.cursor' objects}
	        1    0.061    0.061    0.061    0.061 {method 'fetchall' of 'psycopg2.extensions.cursor' objects}
	    34548    0.031    0.000    0.205    0.000 /Users/erik/hipparchia_venv/HipparchiaServer/server/dbsupport/dblinefunctions.py:24(dblineintolineobject)
    ...

	:param workid:
	:param workstructure:
	:param partialcitationtuple:
	:param cursor:
	:return:
	"""

	workid = workobject.universalid
	workstructure = workobject.structure

	partialcitation = list(partialcitationtuple)
	availablelevels = len(workstructure)

	atlevel = availablelevels-len(partialcitation)
	# cheat in the case where you want to find the top by sending a 'noncitation': 'top'
	# e.g.: /getstructure/gr0003w001/firstline
	if partialcitationtuple[0] == 'firstline':
		atlevel = availablelevels
	if atlevel < 1:
		# i am confused; threatening to probe for level "-1"
		# a selection at level00 will do this to me
		#   /getstructure/gr0003w001/3|36|5|3
		# this needs to be made uncontroversial:
		#   /getstructure/gr0003w001/3|36|5
		# and so: massage the data
		atlevel = 1
		try:
			partialcitation.pop()
		except IndexError:
			atlevel = availablelevels

	audb = workid[0:6]
	lvl = 'l'+str(atlevel - 1)

	# select level_00_value from gr0565w001 where level_03_value='3' AND level_02_value='2' AND level_01_value='1' AND level_00_value NOT IN ('t') ORDER BY index ASC;
	# select level_01_value from gr0565w001 where level_03_value='2' AND level_02_value='1' AND level_01_value NOT IN ('t') ORDER BY index ASC;
	query = 'SELECT {wltmp} FROM {db} WHERE ( wkuniversalid=%s ) AND '.format(wltmp=worklinetemplate, lvl=atlevel-1, db=audb)
	datalist = [workid]
	for level in range(availablelevels - 1, atlevel - 1, -1):
		query += ' level_0{lvl}_value=%s AND '.format(lvl=level)
		datalist.append(partialcitationtuple[availablelevels-level-1])
	query += 'level_0{lvl}_value NOT IN (%s) ORDER BY index'.format(lvl=atlevel-1)
	datalist.append('t')
	data = tuple(datalist)

	cursor.execute(query, data)

	results = cursor.fetchall()
	if results:
		lines = [dblineintolineobject(r) for r in results]
	else:
		lines = None

	if not lines:
		lowandhighobject = LowandHighInfo(availablelevels, atlevel - 1, workstructure[atlevel - 1], '-9999', '', [''])
		return lowandhighobject

	low = getattr(lines[0], lvl)
	high = getattr(lines[-1], lvl)
	rng = [getattr(l, lvl) for l in lines]
	# need to drop dupes and keep the index order
	deduper = set()
	for r in rng:
		if r not in deduper:
			deduper.add(r)
	rng = list(deduper)
	
	try:
		rng = [int(r) for r in rng]
		rng = sorted(rng)
		rng = [str(r) for r in rng]
	except ValueError:
		rng = sorted(rng)

	lowandhighobject = LowandHighInfo(availablelevels, atlevel-1, workstructure[atlevel - 1], low, high, rng)

	return lowandhighobject


def locusintocitation(workobject: dbOpus, lineobject: dbWorkLine) -> str:
	"""

	generate a prolix citation like "Book 8, section 108, line 9"

	:param workobject:
	:param lineobject:
	:return:
	"""

	wklvls = list(workobject.structure.keys())
	cite = list(lineobject.locustuple())
	wklvls.reverse()
	citation = list()
	for level in wklvls:
		try:
			if workobject.isnotliterary() and workobject.structure[level] == ' ' and cite[level] == 'recto':
				# ' ' ==> 'face' which is likely 'recto'
				# this check will make it so you don't see 'recto' over and over again when looking at inscriptions
				pass
			else:
				citation.append(workobject.structure[level]+' '+cite[level])
		except KeyError:
			# did you send me a partial citation like "book 2"?
			pass

	citation = ', '.join(citation)

	citation = avoidsmallvariants(citation)

	return citation


def prolixlocus(workobject: dbOpus, citationtuple: tuple) -> str:
	"""
	transform something like ('9','109','8') into a citation like "Book 8, section 108, line 9"
	differs from the preceding because it does not have access to the lineobject: sessionselectionsinfo()
	can only send you level numbers

	:param workobject:
	:param citationtuple:
	:return:
	"""

	wklvls = list(workobject.structure.keys())
	wklvls.reverse()
	cite = list(citationtuple)
	cite.reverse()
	citation = list()
	for level in range(0, len(wklvls)):
		try:
			citation.append(workobject.structure[wklvls[level]]+' '+cite[level])
		except IndexError:
			# did you send me a partial citation like "book 2"?
			pass

	citation = ', '.join(citation)

	return citation


def finddblinefromlocus(workobject: dbOpus, citationtuple: tuple, dbcursor, findlastline=False) -> int:
	"""

	citationtuple ('9','109','8') to focus on line 9, section 109, book 8
	finddblinefromlocus(h, 1, ('130', '24')) ---> 15033

	findlastline lets you grab the end of a segment: needed for the "endpoint" selection code

	:param workid:
	:param citationtuple:
	:param dbcursor:
	:return:
	"""

	workid = workobject.universalid

	lmap = {0: 'level_00_value',
	        1: 'level_01_value',
	        2: 'level_02_value',
	        3: 'level_03_value',
	        4: 'level_04_value',
	        5: 'level_05_value'}

	workdb = workid[0:6]

	if workid[0:2] in ['in', 'dp', 'ch']:
		wklvs = 2
	else:
		wklvs = workobject.availablelevels

	if wklvs != len(citationtuple):
		consolewarning('mismatch between shape of work and browsing request: impossible citation of {w}.'.format(w=workid))
		print(str(wklvs), ' levels vs', list(citationtuple))
		print('safe to ignore if you requested the first line of a work')

	# step one: find the index number of the passage
	query = 'SELECT index FROM {w} WHERE ( wkuniversalid=%s ) AND '.format(w=workdb)
	lq = list()
	for level in range(0, len(citationtuple)):
		lq.append('{l}=%s'.format(l=lmap[level]))

	if not findlastline:
		query = query + ' AND '.join(lq) + ' ORDER BY index ASC'
	else:
		query = query + ' AND '.join(lq) + ' ORDER BY index DESC'

	# if the last selection box was empty you are sent '_0' instead of a real value
	# (because the first line of lvl05 is not necc. '1')
	# so we need to kill off 'level_00_value=%s AND ', etc
	# example: ('-1', '256', 'beta') [here the 1st line is actually '10t', btw]

	citation = list(citationtuple)

	if citation[0] == '_0':
		query = re.sub(r'level_00_value=%s AND ', '', query)
		citation = citation[1:]

	if not citation:
		indexvalue = workdict[workid].starts
		return indexvalue

	data = tuple([workid] + citation)

	try:
		dbcursor.execute(query, data)
		found = dbcursor.fetchone()
		indexvalue = found[0]
	except TypeError:
		# TypeError: 'NoneType' object is not subscriptable
		indexvalue = returnfirstlinenumber(workdb, dbcursor)

	# print('finddblinefromlocus() - indexvalue:', indexvalue)

	return indexvalue


def finddblinefromincompletelocus(workobject: dbOpus, citationlist: list, dbcursor, trialnumber=0, findlastline=False) -> dict:
	"""

	this is used both by the browser selection boxes and by perseus passage lookups

	need to deal with the perseus bibliographic references which often do not go all the way down to level zero
	use what you have to find the first available db line so you can construct a '/browse/line/...' browseto click
	the citation list arrives in ascending order of levels: 00, 01, 02...

	sent something like:
		lt1002w001
		['28', '7', '1']

	= 'Quintilian IO 1.7.28'

	:param workobject:
	:param citationlist:
	:param dbcursor:
	:param trialnumber:
	:return:
	"""

	dbconnection = None
	if not dbcursor:
		# we were not passed a cursor
		dbconnection = ConnectionObject()
		dbcursor = dbconnection.cursor()

	# print('citationlist',workobject.universalid,citationlist)

	if trialnumber > 4:
		# catch any accidental loops
		successcode = 'abandoned effort to find a citation after 4 guesses'
		dblinenumber = workobject.starts
		results = {'code': successcode, 'line': dblinenumber}
		return results

	trialnumber += 1

	lmap = {0: 'level_00_value', 1: 'level_01_value', 2: 'level_02_value', 3: 'level_03_value', 4: 'level_04_value',
			5: 'level_05_value'}

	numberoflevels = workobject.availablelevels

	# now wrestle with the citation
	# almost all of this code is an attempt to deal with Perseus citation formatting
	# life is easy when tcfindstartandstop() calls this

	if numberoflevels == len(citationlist):
		# congratulations, you have a fully formed citation. Or do you?
		#
		# [a] good news if this is aeneid book 1, line 1
		# [b] bad news if this is Cic. Cat. 1, 2, 4 because that '2' is not 'section' and that '4' is not 'line'
		# instead the dictionary means oration 1, section 4, line 1 but the dictionary used an old citation format
		# Hipparchia will return oration 1, section 2, line 4 because this is a valid selection
		# that's a shame: but at least you are somewhat close to where you want to be
		# [c] also bad news if this is Cic. Mil. 9, 25
		# there is no line 25 to section 9. When no result is returned we will dump the 9 and see if just 25 works
		# is usually does

		dblinenumber = finddblinefromlocus(workobject, tuple(citationlist), dbcursor, findlastline)
		if dblinenumber:
			successcode = 'success'
		else:
			# for lt0474w058 PE will send section=33, 11, 1, 1
			# but Cicero, Epistulae ad Quintum Fratrem is book, letter, section, line
			results = perseuslookupleveltrimmer(workobject, citationlist, dbcursor, trialnumber)
			return results
	elif numberoflevels < len(citationlist):
		# something stupid like plautus' acts and scenes when you only want the line numbers
		# how can this be fixed?

		# option 1: truncate the 'too long' bits and hope for the best
		# will definitely fail to pull up the right line in the case of plays
		# unless you were looking at act 1 scene 1 anyway
		# newcitationlist = []
		# for i in range(0,numberoflevels):
		#	newcitationlist.append(citationlist[i])
		# citationlist = newcitationlist

		# option 2: just give up
		dblinenumber = workobject.starts
		citationlist.reverse()
		cl = ', '.join(citationlist)
		successcode = 'Sending first line. Perseus reference structure does not fit with a valid Hipparchia ' \
			'reference: <span class="bold">{pe}</span> ⇎ <span class="bold">{hi}</span>'.format(pe=cl, hi=workobject.citation())

	else:
		# you have an incomplete citation: assume that the top level is the last item, etc.
		citationlist = perseuscitationsintohipparchiacitations(citationlist)
		citationlist.reverse()
		# the last selection box was empty and you were sent '_0' instead of a real value
		citationlist = [c for c in citationlist if c != '_0']
		auid = workobject.universalid[0:6]

		query = list()
		query.append('SELECT index FROM {a} WHERE wkuniversalid=%s'.format(a=auid))
		try:
			for level in range(numberoflevels-1, numberoflevels-len(citationlist)-1, -1):
				query.append('{lvl}=%s'.format(lvl=lmap[level]))
		except:
			query.append('{lvl}=%s'.format(lvl=lmap[0]))

		query = ' AND '.join(query)
		if not findlastline:
			query += ' ORDER BY index ASC'
		else:
			query += ' ORDER BY index DESC'

		data = tuple([workobject.universalid]+citationlist)

		try:
			dbcursor.execute(query, data)
			found = dbcursor.fetchone()
			dblinenumber = found[0]
			# often actually true...
			successcode = 'success'
		except TypeError:
			# TypeError: 'NoneType' object is not subscriptable
			# print('nothing found: returning first line')
			if trialnumber < 2:
				citationlist = perseuslookupchangecase(citationlist)
				results = finddblinefromincompletelocus(workobject, citationlist, dbcursor, trialnumber)
				return results
			elif workobject.universalid[0:6] == 'lt1014':
				# The dictionary regularly (but inconsistently!) points to Seneca Maior [lt1014] when it is citing Seneca Minor [lt107]'
				# but what follows will not save the day: "lt1014w001/Ira, 2:11:2", "lt1014w001/Cons. ad Marc. 1:6", and
				# "lt1014w001/Ep. 70:15" are all fundamentally broken: lt1017 will still not get you the right work numbers
				#
				# print('minor for maior b', workobject.universalid, workobject.title)
				# newworkobject = dbloadasingleworkobject('lt1017'+workobject.universalid[6:])
				# print('nwo',newworkobject.universalid, newworkobject.title)
				# results = finddblinefromincompletelocus(newworkobject, citationlist, cursor, trialnumber)				# return results
				dblinenumber = workobject.starts
				successcode = """
				The dictionary regularly points to Seneca Maior [lt1014] when it is citing Seneca Minor [lt107].
				<br >These citations are broken and cannot be easily fixed. 
				Not only is the author number wrong, so too is the work number. Sorry about that.
				"""
			else:
				dblinenumber = workobject.starts
				successcode = """
				Sending first line of the work. Perseus reference did not return a valid Hipparchia reference:
				<span class="bold">{pe}</span> vs <span class="bold">{hi}</span>
				"""
				successcode = successcode.format(pe=', '.join(citationlist), hi=workobject.citation())
				if 'Frag' in workobject.title:
					successcode += '<br >The edition used by the lexicon might not match the local edition of the fragments.'

	results = {'code': successcode, 'line': dblinenumber}

	if dbconnection:
		# we grabbed a connection because we were not passed a cursor
		dbconnection.connectioncleanup()

	# print('query,data', query, data)
	return results


def perseuslookupleveltrimmer(workobject: dbOpus, citationlist: list, cursor, trialnumber: int) -> dict:
	"""

	you had a valid looking citation, but it was not in fact valid

	for example, Cicero's Phillipcs should be cited as oration, section, line
	but perseus will send  3:10:25. This is in fact oration 3, section 25

	Cicero's verrines seem to be (usually) broken: actio, book, section, (line)
	dictionary will send 2:18:45 when the right answer is 2.2.45(.1) (and the 'wrong'
	request should be 2.2.18.45)

	it seems that dropping the penultimate item is usually going to be the good second guess

	you should not be able to reach this function 2x because dropping an item from citationlist
	will cause you to fail the 'if' in finddblinefromincompletelocus() on the next pass

	peeling this off in case we need to add more ways of guessing how to make the second try

	:param workobject:
	:param citationlist:
	:param cursor:
	:param trialnumber:
	:return:
	"""

	try:
		newcitationlist = citationlist[:1]+citationlist[2:]
	except:
		dblinenumber = workobject.starts
		successcode = 'Sending first line of the work. Perseus reference did not return a valid Hipparchia ' \
		              'reference: <span class="bold">{pe}</span> vs <span class="bold">{hi}</span>'.format(pe=', '.join(citationlist), hi=workobject.citation())
		results = {'code': successcode, 'line': dblinenumber}
		return results

	results = finddblinefromincompletelocus(workobject, newcitationlist, cursor, trialnumber)

	return results


def perseuslookupchangecase(citationlist: list) -> list:
	"""

	['25', 'cal'] instead of ['25', 'Cal'] when searching seutonius?

	:param citationlist:
	:return:
	"""

	newcitationlist = list()

	for item in citationlist:
		if re.search(r'[a-z]', item[0]):
			item = item[0].upper() + item[1:]
		elif re.search(r'[A-Z]', item[0]):
			item = item[0].lower() + item[1:]
		newcitationlist.append(item)

	newcitationlist.reverse()

	return newcitationlist


def perseusdelabeler(citationlist: list, workobject: dbOpus) -> list:
	"""

	the dictionary will send you things like 'life=cl.' or 'section=7'

	try to map them onto a hipparchia structure

	return the best guess

	:param citationlist:
	:param workobject:
	:return:
	"""

	allables = [workobject.levellabels_00, workobject.levellabels_01, workobject.levellabels_02, workobject.levellabels_03,
	              workobject.levellabels_04, workobject.levellabels_05]

	allables = [a for a in allables if a]

	lmap = {allables[i]: i for i in range(0, len(allables))}

	allables.reverse()
	citationlist.reverse()

	newcitationlist = ['' for c in range(0, len(allables))]

	count = len(allables)
	for c in citationlist:
		count -= 1
		if len(c.split('=')) > 1:
			if c.split('=')[0] in allables:
				# try to assign 'section', etc. to the right place on the list
				mapto = lmap[c.split('=')[0]]
				newcitationlist[mapto] = c.split('=')[1]
			else:
				# i don't know this label: Cicero, Cato Maior de Senectute is supposed to be section, line, but you will be sent chapter=2
				# just clean out the label name and hope for the best
				newcitationlist[count] = c.split('=')[1]
		else:
			newcitationlist[count] = c

	newcitationlist = [re.sub(r'\.', '', n) for n in newcitationlist if n]

	# print('newcitationlist', newcitationlist)

	return newcitationlist


def perseuscitationsintohipparchiacitations(citationlist: list) -> list:
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

	newcitationlist = list()
	
	for item in citationlist:
		if re.search(r'^p\.', item):
			item = item[2:]
		item = re.sub(r'\(.*?\)', '', item)
		newcitationlist.append(item)
	
	citationlist = newcitationlist
	newcitationlist = list()

	for item in citationlist:
		try:
			if item[-2].isdigit() and item[-1].islower():
				parta = item[-1]
				partb = item[:-1]
				newcitationlist.append(parta)
				newcitationlist.append(partb)
			else:
				newcitationlist.append(item)
		except IndexError:
			# item[-2] was impossible
			newcitationlist.append(item)
	
	return newcitationlist
