import re
from collections import deque

from server.dbsupport.dbfunctions import findselectionboundaries, setconnection


def configurewhereclausedata(searchlist, workdict, searchobject):
	"""

	constructs the framework for the where clauses to send to postgres when making the query

	this returns a dict that will guide the actual construction of the clauses later

	see also wholeworktemptablecontents() and wholeworkbetweenclausecontents() for the format of a final query

	'type' is the logic trigger: 'unrestricted', 'between', or 'temptable'
	'where' is the material sent to the constructor
		between is list of endpoints
		temptable is a dict containing 'tempdata', and 'tempquery'

	sample return values for indexedauthorlist [key, value]
	all of plato:
		gr0059 {'type': 'unrestricted', 'where': False}
	plato's apology:
		gr0059 {'type': 'between', 'where': {'listofboundaries': [(678, 1671)], 'listofomissions': None}}
	plato less the republic [note that as simple 'where not' would be more efficient (but trickier to code); ntl this version is still more efficient than the old way]:
		gr0059 {'type': 'between', 'where': {'listofboundaries': [(70077, 72021), (56668, 69366), (73928, 74045), (74046, 74048), (2174, 4890), (7344, 10409), (678, 1671), (40848, 41023), (36927, 38230), (26117, 26469), (39791, 40276), (25520, 26116), (30107, 31594), (26817, 27290), (27291, 28359), (23822, 25519), (56310, 56667), (55744, 56309), (74049, 74166), (21739, 23821), (72022, 72322), (1672, 2173), (17039, 19691), (28360, 29326), (1, 677), (40277, 40847), (53063, 55743), (69367, 70076), (10410, 12901), (15406, 17038), (4891, 7343), (29327, 30106), (12902, 15405), (38231, 39266), (72323, 73927), (31595, 33615), (33616, 36926), (19692, 21738), (26470, 26816), (39267, 39790)], 'listofomissions': None}}
	xenophon hellenica less books 3 and 6:
		gr0032 {'type': 'between', 'where': {'listofboundaries': [(1, 7918)], 'listofomissions': [(5434, 6683), (1846, 2856)]}}
	xenophon hellenica 3 less chh 2 and 4:
		gr0032 {'type': 'between', 'where': {'listofboundaries': [(1846, 2856)], 'listofomissions': [(2062, 2313), (2422, 2664)]}}
	asia minor 400 B.C.E to 345 B.C.E: [only one table shown]
		in1008 {'type': 'temptable', 'where': {'tempdata': (10083, 10084, 10085, 10086, 10087, 10088, 10103, 10104, 10105, 10106, 10107, 10108, 10109, 10110, 10111, 10112, 10113, 10114, 10115, 10116, 10117, 10118, 10119, 10120, 10121, 10122, 10123, 10124, 10125, 10126, 10127, 10128, 10645), 'tempquery': 'CREATE TEMPORARY TABLE in1008_includelist AS SELECT x AS includeindex FROM %s'}}

	:param searchlist:
	:param workdict:
	:param searchobject:
	:return: indexedauthorlist
	"""

	so = searchobject
	indexedauthorlist = dict()

	hasexclusions = [p[0:10] for p in so.psgexclusions if p]
	hasselections = [p[0:10] for p in so.psgselections if p]

	if hasexclusions != [] or hasselections != []:
		cleanlistmapper = {wk: re.sub(r'(......)x', '\1w', wk[0:10]) for wk in searchlist}
		incompleteworks = {x[0:10] for x in searchlist
		                   if (cleanlistmapper[x] in hasselections or cleanlistmapper[x] in hasexclusions)}
	else:
		incompleteworks = dict()

	wholeauthors = {x for x in searchlist if len(x) == 6}
	wholeworks = {x for x in searchlist if len(x) == 10 and x[6] != 'x'}

	literaryworks = {x for x in wholeworks if workdict[x].isliterary()}
	nonliteraryworks = {x for x in wholeworks if workdict[x].isnotliterary()}

	# [A] LITERARY AUTHORS
	literyauthors = dict()
	for w in literaryworks:
		try:
			literyauthors[w[0:6]].append(workdict[w])
		except KeyError:
			literyauthors[w[0:6]] = [workdict[w]]

	# only valid for whole works: still need to handle works with inset selections and exclusions

	# sample:
	# literaryinclusionmapper {'gr0019': {'listofboundaries': [(12799, 14613), (1, 1347)], 'listofomissions': None}, 'gr0085': {'listofboundaries': [(3417, 4561), (1, 1156)], 'listofomissions': None}}

	literaryinclusionmapper = {l: {'listofboundaries': wholeworkbetweenclausecontents(literyauthors[l]),
	                               'listofomissions': []}
	                           for l in literyauthors}

	# [B] NON-LITERARY AUTHORS
	nonliteryauthors = dict()
	for n in nonliteraryworks:
		try:
			nonliteryauthors[n[0:6]]
			nonliteryauthors[n[0:6]].extend(workdict[n].lines())
		except KeyError:
			nonliteryauthors[n[0:6]] = deque(workdict[n].lines())

	# unneeded?
	nonliteryauthors = {nl: set(nonliteryauthors[nl]) for nl in nonliteryauthors}

	# only valid for whole works: still need to handle works with inset selections and exclusions
	nonliteraryinclusionmapper = {n: wholeworktemptablecontents(n, nonliteryauthors[n]) for n in nonliteryauthors}

	# [C] WORKS WITH INTERANL INCLUSIONS/EXCLUSIONS
	# now take care of the includes and excludes (which will ultimately be versions of the 'between' syntax
	# sample
	# ixlist [('gr0032w001', {'listofboundaries': [(908, 1845), (5434, 6683)], 'listofomissions': None}), ('gr0032w002', {'listofboundaries': [(9959, 10037)], 'listofomissions': None}), ('gr0003w001', {'listofboundaries': [(4883, 7059)], 'listofomissions': [(4907, 4931), (4932, 4950)]})]

	ixlist = [partialworkbetweenclausecontents(workdict[re.sub('(....)x(...)', r'\1w\2', wk)], searchobject)
	          for wk in incompleteworks]

	# consolidate this list to match literaryinclusionmapper dict above.
	# sample:
	# {'gr0032': {'listofboundaries': [(1, 7918)], 'listofomissions': [(5434, 6683), (1846, 2856)]}}

	partialworks = dict()
	for i in ixlist:
		if i[1]['listofboundaries']:
			try:
				partialworks[i[0][0:6]]['listofboundaries'] = list(set(partialworks[i[0][0:6]]['listofboundaries'] + i[1]['listofboundaries']))
				partialworks[i[0][0:6]]['listofomissions'] = list(set(partialworks[i[0][0:6]]['listofomissions'] + i[1]['listofomissions']))
			except KeyError:
				partialworks[i[0][0:6]] = i[1]
		if i[1]['listofomissions']:
			try:
				partialworks[i[0][0:6]]['listofboundaries'] = list(set(partialworks[i[0][0:6]]['listofboundaries'] + i[1]['listofboundaries']))
				partialworks[i[0][0:6]]['listofomissions'] = list(set(partialworks[i[0][0:6]]['listofomissions'] + i[1]['listofomissions']))
			except KeyError:
				partialworks[i[0][0:6]] = i[1]

	# now build the final list out of the separate parts from A, B, and C above

	for w in wholeauthors:
		indexedauthorlist[w] = {'type': 'unrestricted', 'where': False}
	for l in literaryinclusionmapper:
		indexedauthorlist[l] = {'type': 'between', 'where': literaryinclusionmapper[l]}
	for n in nonliteraryinclusionmapper:
		indexedauthorlist[n] = {'type': 'temptable', 'where': nonliteraryinclusionmapper[n]}

	for i in partialworks:
		try:
			indexedauthorlist[i]
			supplement = True
		except KeyError:
			supplement = False
		if not supplement:
			indexedauthorlist[i] = {'type': 'between', 'where': partialworks[i]}
		else:
			indexedauthorlist[i]['where']['listofboundaries'] = list(set(indexedauthorlist[i]['where']['listofboundaries'] + partialworks[i]['listofboundaries']))
			indexedauthorlist[i]['where']['listofomissions'] = list(set(indexedauthorlist[i]['where']['listofomissions'] + partialworks[i]['listofomissions']))

	return indexedauthorlist


def wholeworkbetweenclausecontents(listofworkobjects):
	"""

	Ultimately you need this to search Aristophanes' Birds and Clouds:

		WHERE (index BETWEEN 2885 AND 4633) AND (index BETWEEN 7921 AND 9913)'

	template = '(index BETWEEN {min} AND {max})'
	whereclause = 'WHERE ' + ' AND '.join(wheres)

	for now just return the relevant numbers as a list of tuples:
		[(start1, end1), (start2,end2),...]

	:param listofworkobjects:
	:return:
	"""

	listofboundaries = [(w.starts, w.ends) for w in listofworkobjects]

	return listofboundaries


def wholeworktemptablecontents(authorid, setoflinenumbers):
	"""
	in the original paradigm we can end up searching a table 100x in the course of each search
	inscriptions by date produces this; and these are noticeably slower searches

	the following represents 130k individual queries (and the associated overhead)

		Sought »παρουϲίᾳ«
		Searched 130,451 texts and found 5 passages (100.94s)
		Searched between 1C.E. and 200 C.E.
		Sorted by date

	instead you can search the table once with something a long set of wheres [where universalid = x or y or z]
		[syntax: where value IN (value1,value2,...)]

	a temporary table solution is the fastest when the list of values gets big

	contrast:

		Sought »παρουϲίᾳ«
		Searched 129,941 texts and found 5 passages (2.87s)
		Searched between 1C.E. and 200 C.E.
		Sorted by name

	see:
		http://stackoverflow.com/questions/24647503/performance-issue-in-update-query
		http://stackoverflow.com/questions/17037508/sql-when-it-comes-to-not-in-and-not-equal-to-which-is-more-efficient-and-why/17038097#17038097
		https://gist.github.com/ringerc/5755247

	NB: might need to execute 'GRANT TEMPORARY ON hipparchiaDB TO hippa_rd' if there are permission problems; also
	the connection to the db can't be readonly any longer

		[a] make a tmp table
			CREATE TEMPORARY TABLE dp0201_includelist(linenumber integer);
			INSERT INTO dp0201_includelist SELECT val FROM unnest(ARRAY[1,2,3,4,5,6,7,8,22,33]) val;

			which is approx the same as:
			CREATE TEMPORARY TABLE dp0201_includelist AS SELECT val FROM unnest(ARRAY[1,2,3,4,5,6,7,8,22,33]) val;

		[b] search authordb via an inner join ('include') or left outer join ('exclude') on the temp table
			SELECT * FROM dp0201 WHERE EXISTS (SELECT 1 FROM dp0201_includelist incl WHERE incl.linenumber = dp0201.index);

		[c] an actual search for a word
			SELECT * FROM dp0201 WHERE EXISTS
				(SELECT 1 FROM dp0201_includelist incl WHERE incl.linenumber = dp0201.index
				AND dp0201.stripped_line ~ 'περι');

		WHERE NOT EXISTS syntax is too cumbersome to implement in light of all of the other issues in the air
		(inclusion lists, etc)? It is not clear that the speed gains are going to justify trying to do this.

	:param authorid:
	:param setoflinenumbers:
	:return:
	"""

	if setoflinenumbers:
		lines = [str(x) for x in setoflinenumbers]
		lines = ','.join(lines)
	else:
		lines = '-1'

	tempquery = 'CREATE TEMPORARY TABLE {au}_includelist AS SELECT values AS includeindex FROM unnest(ARRAY[{lines}]) values'.format(
		au=authorid, lines=lines)
	returndict = {'tempquery': tempquery}

	return returndict


def partialworkbetweenclausecontents(workobject, searchobject):
	"""


	:param listofworkobjects:
	:param workswithselections:
	:param searchobject:
	:return:
	"""

	hasselections = [p[0:10] for p in searchobject.psgselections if p]

	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	blist = list()
	olist = list()
	for sel in searchobject.psgselections:
		if workobject.universalid == sel[0:10]:
			boundariestuple = findselectionboundaries(workobject, sel, curs)
			blist.append(boundariestuple)
	for sel in searchobject.psgexclusions:
		if workobject.universalid == sel[0:10]:
			boundariestuple = findselectionboundaries(workobject, sel, curs)
			olist.append(boundariestuple)
			if workobject.universalid not in hasselections:
				# if you exclude a subsection, then you implicitly include the whole
				# unless you have only selected a higher level subsection
				# exclude x., mem. 3 means you want to search x., mem.
				# BUT exclude x., mem. 3.4 has a different force if you included x.,  mem. 3
				blist.append((workobject.starts, workobject.ends))

	blist = list(set(blist))
	olist = list(set(olist))

	endpoints = (workobject.universalid, {'listofboundaries': blist, 'listofomissions': olist})

	return endpoints