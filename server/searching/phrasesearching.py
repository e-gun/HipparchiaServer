# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server.dbsupport.dbfunctions import setconnection, makeablankline, dblineintolineobject
from server.hipparchiaclasses import QueryCombinator
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion, whereclauses, \
	lookoutsideoftheline


def phrasesearch(leastcommon, searchphrase, maxhits, wkid, authorswheredict, activepoll, cursor):
	"""
	a whitespace might mean things are on a new line
	note how horrible something like και δη και is: you will search και first and then...
	that's why we have shortphrasesearch() which is mighty slow too

	:param searchphrase:
	:param cursor:
	:param wkid:
	:param authorswheredict:
	:param activepoll:
	:return:
	"""

	if 'x' not in wkid:
		hits = substringsearch(leastcommon, cursor, wkid, authorswheredict, templimit=maxhits)
	else:
		wkid = re.sub('x', 'w', wkid)
		hits = simplesearchworkwithexclusion(leastcommon, wkid, authorswheredict, cursor, templimit=maxhits)
	
	fullmatches = []
	while hits and len(fullmatches) < int(session['maxresults']):
		hit = hits.pop()
		phraselen = len(searchphrase.split(' '))
		wordset = lookoutsideoftheline(hit[0], phraselen - 1, wkid, cursor)
		if session['accentsmatter'] == 'no':
			wordset = re.sub(r'[\.\?\!;:,·’]', r'', wordset)
		else:
			# the difference is in the apostrophe: δ vs δ’
			wordset = re.sub(r'[\.\?\!;:,·]', r'', wordset)

		if session['nearornot'] == 'T' and re.search(searchphrase, wordset) is not None:
			fullmatches.append(hit)
			activepoll.addhits(1)
		elif session['nearornot'] == 'F' and re.search(searchphrase, wordset) is None:
			fullmatches.append(hit)
			activepoll.addhits(1)
	
	return fullmatches


def shortphrasesearch(count, foundlineobjects, searchphrase, workstosearch, authorswheredict, activepoll):
	"""
	mp aware search for runs of short words

	workstosearch:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']

	authorswheredict: [every author that needs to have a where-clause built because you asked for an '_AT_']
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}

	seeking:
		'si tu non'

	:return:
	"""

	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	searchterms = searchphrase.split(' ')
	searchterms = [x for x in searchterms if x]
	contextneeded = len(searchterms) - 1

	while len(workstosearch) > 0 and count.value <= int(session['maxresults']):
		try:
			wkid = workstosearch.pop()
			activepoll.remain(len(workstosearch))
		except:
			wkid = 'gr0000w000'

		if wkid != 'gr0000w000':
			matchobjects = []
			db = wkid[0:6]
			# check for exclusions
			if re.search(r'x', wkid) is not None:
				wkid = re.sub(r'x', 'w', wkid)
				restrictions = []
				for p in session['psgexclusions']:
					if wkid in p:
						restrictions.append(whereclauses(p, '<>', authorswheredict))
			
				whr = ''
				data = [wkid[0:10]]

				for r in restrictions:
					for i in range(0, len(r)):
						whr += r[i][0] + 'OR '
						data.append(r[i][1])
					# drop the trailing ' OR'
					whr = whr[0:-4] + ') AND ('
				# drop the trailing ') AND ('
				whr = whr[0:-6]
			
				query = 'SELECT * FROM ' + db + ' WHERE ( wkuniversalid = %s) AND ('+ whr + ' ORDER BY index ASC'
				curs.execute(query, tuple(data))
			else:
				if '_AT_' not in wkid:
					wkid = re.sub(r'x', 'w', wkid)
					if len(wkid) == 6:
						# we are searching the whole author
						data = (wkid+'%',)
					else:
						# we are searching an individual work
						data = (wkid[0:10],)
					query = 'SELECT * FROM ' + db + ' WHERE ( wkuniversalid LIKE %s) ORDER BY index'
					curs.execute(query, data)
				else:
					whr = ''
					data = [wkid[0:10]]
					w = whereclauses(wkid, '=', authorswheredict)
					for i in range(0, len(w)):
						whr += 'AND (' + w[i][0] + ') '
						data.append(w[i][1])
					# strip extra ANDs
					whr = whr[4:]
					wkid = re.sub(r'x', 'w', wkid)
					query = 'SELECT * FROM ' + db + ' WHERE ( wkuniversalid = %s) AND ( '+whr+' ORDER BY index'
					curs.execute(query, data)

			fulltext = curs.fetchall()
			
			previous = makeablankline(wkid, -1)
			lineobjects = [dblineintolineobject(f) for f in fulltext]
			lineobjects.append(makeablankline(wkid, -9999))
			del fulltext
			
			if session['accentsmatter'] == 'no':
				acc = 'stripped'
			else:
				acc = 'accented'

			for i in range(0, len(lineobjects) - 1):
				if count.value <= int(session['maxresults']):
					if previous.hashyphenated == True and lineobjects[i].hashyphenated == True:
						core = lineobjects[i].allbutfirstandlastword(acc)
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[1:contextneeded + 1]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					elif previous.hashyphenated == False and lineobjects[i].hashyphenated == True:
						core = lineobjects[i].allbutlastword(acc)
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[0:contextneeded]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					elif previous.hashyphenated == True and lineobjects[i].hashyphenated == False:
						core = lineobjects[i].allbutfirstword(acc)
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[0:contextneeded]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					else:
						# previous.hashyphenated == False and lineobjects[i].hashyphenated == False
						if session['accentsmatter'] == 'no':
							core = lineobjects[i].stripped
						else:
							core = lineobjects[i].unformattedline()
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[0:contextneeded]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					
					try:
						prepend = previous.wordlist(acc)[-1 * contextneeded:]
					except:
						prepend = previous.wordlist(acc)
					
					prepend = ' '.join(prepend)
					supplement = ' '.join(supplement)
					searchzone = prepend + ' ' + core + ' ' + supplement
					searchzone = re.sub(r'\s\s', r' ', searchzone)
					
					if re.search(searchphrase, searchzone) is not None:
						count.increment(1)
						activepoll.sethits(count.value)
						matchobjects.append(lineobjects[i])
					previous = lineobjects[i]

			foundlineobjects += matchobjects


	curs.close()
	del dbconnection
	
	return foundlineobjects


def newshortphrasesearch(count, foundlineobjects, searchphrase, workstosearch, authorswheredict, activepoll):
	"""
	mp aware search for runs of short words

	workstosearch:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']

	authorswheredict: [every author that needs to have a where-clause built because you asked for an '_AT_']
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}

	seeking:
		'si tu non'

	three searches:
		all in one line
		2 in one line; one in next
		1 in one line; two in next

	:return:
	"""

	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	qcomb = QueryCombinator(searchphrase)
	# the last time is the full phrase:  ('one two three four five', '')
	combinations = qcomb.combinations()
	combinations.pop()
	firstterm = qcomb.words[0]
	
	if session['accentsmatter'] == 'no':
		ln = 'stripped_line'
	else:
		ln = 'accented_line'

	while len(workstosearch) > 0 and count.value <= int(session['maxresults']):
		try:
			wkid = workstosearch.pop()
			activepoll.remain(len(workstosearch))
		except:
			wkid = 'gr0000w000'

		if wkid != 'gr0000w000':
			indices = None
			db = wkid[0:6]
			qtemplate = """SELECT B.index, B.{ln} FROM (SELECT A.index, A.linebundle, A.{ln} FROM
				(SELECT index, {ln},
					concat({ln}, ' ', lead({ln}) OVER (ORDER BY index ASC), ' ', lag({ln}) OVER (ORDER BY index ASC)) as linebundle
					FROM {db} WHERE {whr} ) A
				) B
				WHERE B.linebundle ~ %s"""
			# check for exclusions
			if re.search(r'x', wkid) is not None:
				wkid = re.sub(r'x', 'w', wkid)
				restrictions = [whereclauses(p, '<>', authorswheredict) for p in session['psgexclusions'] if wkid in p]
				whr = '( wkuniversalid = %s) AND ('
				data = [wkid[0:10]]
				print('restrictions',restrictions)
				for r in restrictions:
					# build both the query data and the where-clause in tandem
					for i in range(0, len(r)):
						whr += r[i][0] + 'OR '
						data.append(r[i][1])
					# drop the trailing ' OR'
					whr = whr[0:-4] + ') AND ('
				# drop the trailing ') AND ('
				data.append(searchphrase)
				whr = whr[0:-6]
				query = qtemplate.format(db=db, ln=ln, whr=whr)
				curs.execute(query, tuple(data))
				indices = [i[0] for i in curs.fetchall() if firstterm in i[1]]
			else:
				if '_AT_' not in wkid:
					whr = '( wkuniversalid ~ %s )'
					wkid = re.sub(r'x', 'w', wkid)
					if len(wkid) == 6:
						# we are searching the whole author
						d = wkid
					else:
						# we are searching an individual work
						d = wkid[0:10]
					query = qtemplate.format(db=db, ln=ln, whr=whr)
					data = (d, searchphrase)
					curs.execute(query, data)
					indices = [i[0] for i in curs.fetchall() if firstterm in i[1]]
					# 'if firstterm in i[1]' is a very imperfect check: καὶ might be in the line but not as part of the phrase you sought
					# nevertheless, provided context > 0, you should be able to spot your find fairly easily
					# this will yield a bunch of windows: find the centers
					# [2833, 2834, 2835, 3000, 3092, 3131, 3132, 3133, 3205, 3206, 3207, ...]
					# [2834, 3000, 3092, 3132, 3206, ...]
				else:
					wkid = re.sub(r'x', 'w', wkid)
					data = [wkid[0:10]]
					whr = ''
					w = whereclauses(wkid, '=', authorswheredict)
					for i in range(0, len(w)):
						whr += 'AND (' + w[i][0] + ') '
						data.append(w[i][1])
					# strip extra ANDs
					whr = '( wkuniversalid = %s) ' + whr
					query = qtemplate.format(db=db, ln=ln, whr=whr)
					data.append(searchphrase)
					curs.execute(query, tuple(data))
					indices = [i[0] for i in curs.fetchall() if firstterm in i[1]]

			locallineobjects = []
			if indices:
				for i in indices:
					query = 'SELECT * FROM ' + wkid[0:6] + ' WHERE index=%s'
					data = (i,)
					curs.execute(query, data)
					locallineobjects.append(dblineintolineobject(curs.fetchone()))

			use = ln.split('_line')[0]
			locallineobjects.reverse()
			for l in locallineobjects:
				print(l.universalid, l.locus(), getattr(l,use))
			while locallineobjects and count.value <= int(session['maxresults']):
				# windows of indices come back: e.g., three lines that look like they match when only one matches [3131, 3132, 3133]
				# figure out which line is really the line with the goods
				lo = locallineobjects.pop()
				sp = re.sub(r'^\s','(^| )', searchphrase)
				sp = re.sub(r'\s$', '( |$)', sp)
				if re.search(sp, getattr(lo,use)):
					foundlineobjects.append(lo)
					count.increment(1)
					activepoll.sethits(count.value)
				else:
					try:
						next = locallineobjects[0]
					except:
						# need access to the next db line
						try:
							query = 'SELECT * FROM ' + wkid[0:6] + ' WHERE index=%s'
							data = (lo.index+1,)
							curs.execute(query, data)
							next = dblineintolineobject(curs.fetchone())
						except:
							next = makeablankline('gr0000w000', -1)

					for c in combinations:
						tail = c[0] + '$'
						head = '^' + c[1]
						if re.search(tail, getattr(lo,use)) and re.search(head, getattr(next,use)):
							foundlineobjects.append(lo)
							count.increment(1)
							activepoll.sethits(count.value)

	curs.close()
	del dbconnection

	return foundlineobjects



"""

notes on lead and lag

lead and lag example
	https://fle.github.io/detect-value-changes-between-successive-lines-with-postgresql.html

	select index,stripped_line from lt1212 where stripped_line ~ 'stuprator'

paritions: [over clauses]
	http://tapoueh.org/blog/2013/08/20-Window-Functions


next lines:

select
	index,
	stripped_line,
    lead(stripped_line) over (ORDER BY index) as next_line
from lt1212 where index > 9000 and index < 9010
ORDER BY index asc


[a] a span is generated by the subquery clause SQ
select SQ.index, SQ.stripped_line, SQ.nextline
from
	(
	select index, stripped_line,
	lead(stripped_line) over (ORDER BY index asc) as nextline
	from lt1212
	where (index > 9000 and index < 9010)
	) SQ

[b] searching within it
select SQ.index, SQ.stripped_line, SQ.nextline
from
	(
	select index, stripped_line,
	lead(stripped_line) over (ORDER BY index asc) as nextline
	from lt1212
	where (index > 9000 and index < 9010)
	) SQ
where SQ.stripped_line ~ 'quidam' and SQ.nextline ~ 'ae '

[c] searching all of apuleius: 'sed' within one line of 'stupr'
[can use lead(stripped_line, N) to look further ahead]

select SQ.index, SQ.prevline, SQ.stripped_line, SQ.nextline
from
	(
	select index, stripped_line,
	lead(stripped_line, 1) over (ORDER BY index asc) as nextline,
    lag(stripped_line, 1) over (ORDER BY index asc) as prevline
	from lt1212
	where (index > 0)
	) SQ
where SQ.stripped_line ~ 'stupr' and SQ.prevline ~ 'sed'

[d] returning a linebundle before and after a hit:

select SQ.index, concat(SQ.prevline, SQ.stripped_line, SQ.nextline) as linebundle
from
	(
	select index, stripped_line,
	lead(stripped_line) over (ORDER BY index asc) as nextline,
    lag(stripped_line) over (ORDER BY index asc) as prevline
	from lt1212
	where (index > 0)
	) SQ
where SQ.stripped_line ~ 'stupr'

[e] searching a linebundle:

select B.index, B.linebundle
from
(select A.index, A.linebundle
from
(select index, stripped_line,
	concat(stripped_line, ' ', lead(stripped_line) over (ORDER BY index asc), ' ', lag(stripped_line) over (ORDER BY index asc)) as linebundle
	from lt1212
	where (index > 0)
 ) A
 ) B
 where B.linebundle ~ 'et tamen'



"""

# code with no future

def trimtriples(triplist):
	"""

	too kludgy;  [503, 505] might not be a hole...

	runs of consecutive lines where we want just the middle

	a twist: [1391, 1393, 1395, 9444, 9446, 9452, 9454]
	here you want the excluded middle: 1392 and 1394

	triplist = [2833, 2834, 2835, 3000, 3092, 3131, 3132, 3133, 3205, 3206, 3207, 3221, 3222, 3223, 3225, 3226, 3227, 3253,
       3254, 3255, 3320, 3321, 3322, 3351, 3352, 3353, 3449, 3450, 3451, 3516, 3517, 3518, 3534, 3535, 3536, 3665,
       3666, 3667, 3674, 3675, 3676, 3680, 3681, 3682, 3705, 3706, 3707, 3728, 3733, 3734, 3735, 3882, 3883, 3884,
       3934, 3935, 3936, 4291, 4292, 4293, 4343, 4354, 4355, 4356, 4738, 4739, 4740, 4750, 4751, 4752, 4840, 4841,
       4842, 4850, 4851, 4852, 4896, 4897, 4898, 5146, 5147, 5148, 5189, 5190, 5191, 5765, 5766, 5767, 6485, 6486,
       6487, 6741, 6742, 6743, 6919, 6920, 6921, 6979, 6980, 6981, 7103, 7104, 7105, 7191, 7192, 7193, 7891, 7892,
       7893, 8497, 8498, 8499, 8561, 8562, 8563, 8584, 8585, 8586, 8591, 8592, 8593, 8617, 8765, 8766, 8767, 8889,
       8890, 8891, 9190, 9191, 9192, 9286, 9287, 9288, 9416, 9417, 9418, 9670, 9671, 9672, 9680, 9681, 9682, 9802,
       9853, 9854, 9855, 10042, 10043, 10044, 10083, 10176, 10177, 10178, 10341, 10342, 10343, 10661, 10662, 10663,
       10673, 10674, 10675, 10874, 10875, 10876, 10878]

	newlist [2834, 3000, 3092, 3132, 3206, 3222, 3226, 3254, 3321, 3352, 3450, 3517, 3535, 3666, 3675, 3681, 3706, 3728,
	3734, 3883, 3935, 4292, 4343, 4355, 4739, 4751, 4841, 4851, 4897, 5147, 5190, 5766, 6486, 6742, 6920, 6980, 7104,
	7192, 7892, 8498, 8562, 8585, 8592, 8617, 8766, 8890, 9191, 9287, 9417, 9671, 9681, 9802, 9854, 10043, 10083, 10177,
	10342, 10662, 10674, 10875, 10878]


	:param triplatelist:
	:return:
	"""

	newlist = []
	keepnext = True
	for i in range(0, len(triplist)):
		try:
			plustwo = triplist[i + 2]
		except:
			plustwo = -2
		try:
			plusone = triplist[i + 1]
		except:
			plusone = -1
		if plustwo == triplist[i] + 2 and plusone == triplist[i] + 1:
			# at start of triplet; skip this one; mark next for keeping
			keepnext = True
		elif keepnext == True and plusone == triplist[i] + 1:
			# in middle of triplet; keep this; skip next
			newlist.append(triplist[i])
			keepnext = False
		elif plusone == triplist[i] + 2:
			# found a gap
			newlist.append(triplist[i]+1)
			keepnext = False
		elif keepnext == False:
			# at end of triple; skip this; get ready to take next
			keepnext = True
		elif keepnext == True and plusone != triplist[i] + 1:
			# not in a run
			newlist.append(triplist[i])
			keepnext = True

	return newlist

