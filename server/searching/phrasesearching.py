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


def subqueryphrasesearch(foundlineobjects, searchphrase, workstosearch, count, commitcount, authorswheredict, activepoll):
	"""
	foundlineobjects, searchingfor, searchlist, commitcount, whereclauseinfo, activepoll

	use subquery syntax to grab multi-line windows of text for phrase searching

	line ends and line beginning issues can be overcome this way, but then you have plenty of
	bookkeeping to do to to get the proper results focussed on the right line

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

	qcomb = QueryCombinator(searchphrase)
	# the last time is the full phrase:  ('one two three four five', '')
	combinations = qcomb.combinations()
	combinations.pop()
	# lines start/end
	sp = re.sub(r'^\s', '(^| )', searchphrase)
	sp = re.sub(r'\s$', '( |$)', sp)

	if session['onehit'] == 'no':
		lim = ' LIMIT ' + str(session['maxresults'])
	else:
		# the windowing problem means that '1' might be something that gets discarded
		lim = ' LIMIT 5'

	if session['accentsmatter'] == 'no':
		ln = 'stripped_line'
		use = 'stripped'
	else:
		ln = 'accented_line'
		use = 'polytonic'

	while len(workstosearch) > 0 and count.value <= int(session['maxresults']):
		try:
			wkid = workstosearch.pop()
			activepoll.remain(len(workstosearch))
		except:
			wkid = 'gr0000w000'

		if wkid != 'gr0000w000':
			commitcount.increment()
			if commitcount.value % 400 == 0:
				dbconnection.commit()
			indices = None
			db = wkid[0:6]
			qtemplate = """SELECT B.index, B.{ln} FROM (SELECT A.index, A.linebundle, A.{ln} FROM
				(SELECT index, {ln},
					concat({ln}, ' ', lead({ln}) OVER (ORDER BY index ASC), ' ', lag({ln}) OVER (ORDER BY index ASC)) as linebundle
					FROM {db} WHERE {whr} ) A
				) B
				WHERE B.linebundle ~ %s {lim}"""

			if re.search(r'x', wkid) is not None:
				# we have exclusions
				wkid = re.sub(r'x', 'w', wkid)
				restrictions = [whereclauses(p, '<>', authorswheredict) for p in session['psgexclusions'] if wkid in p]
				whr = '( wkuniversalid = %s) AND ('
				data = [wkid[0:10]]
				for r in restrictions:
					# build both the query data and the where-clause in tandem
					for i in range(0, len(r)):
						whr += r[i][0] + 'OR '
						data.append(r[i][1])
					# drop the trailing ' OR'
					whr = whr[0:-4] + ') AND ('
				# drop the trailing ') AND ('
				data.append(sp)
				whr = whr[0:-6]
				query = qtemplate.format(db=db, ln=ln, whr=whr, lim=lim)
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
					query = qtemplate.format(db=db, ln=ln, whr=whr, lim=lim)
					data = (d, sp)
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
					query = qtemplate.format(db=db, ln=ln, whr=whr, lim=lim)
					data.append(sp)

			curs.execute(query, tuple(data))
			indices = [i[0] for i in curs.fetchall()]
			# this will yield a bunch of windows: you need to find the centers; see 'while...' below

			locallineobjects = []
			if indices:
				for i in indices:
					query = 'SELECT * FROM ' + wkid[0:6] + ' WHERE index=%s'
					data = (i,)
					curs.execute(query, data)
					locallineobjects.append(dblineintolineobject(curs.fetchone()))

			locallineobjects.reverse()
			# debugging
			# for l in locallineobjects:
			# 	print(l.universalid, l.locus(), getattr(l,use))
			gotmyonehit = False
			while locallineobjects and count.value <= int(session['maxresults']) and gotmyonehit == False:
				# windows of indices come back: e.g., three lines that look like they match when only one matches [3131, 3132, 3133]
				# figure out which line is really the line with the goods
				# it is not nearly so simple as picking the 2nd element in any run of 3: no always runs of 3 + matches in
				# subsequent lines means that you really should check your work carefully; this is not an especially costly
				# operation relative to the whole search and esp. relative to the speed gains of using a subquery search
				lo = locallineobjects.pop()
				if re.search(sp, getattr(lo,use)):
					foundlineobjects.append(lo)
					count.increment(1)
					activepoll.sethits(count.value)
					if session['onehit'] == 'yes':
						gotmyonehit = True
				else:
					try:
						next = locallineobjects[0]
					except:
						next = makeablankline('gr0000w000', -1)

					if lo.wkuinversalid != next.wkuinversalid or lo.index != (next.index - 1):
						# this was the next line on the pile, not the actual next line
						# usually you won't get a hit by grabbing the next line, but sometimes you do...
						query = 'SELECT * FROM ' + wkid[0:6] + ' WHERE index=%s'
						data = (lo.index + 1,)
						curs.execute(query, data)
						try:
							next = dblineintolineobject(curs.fetchone())
						except:
							next = makeablankline('gr0000w000', -1)

					for c in combinations:
						tail = c[0] + '$'
						head = '^' + c[1]
						# debugging
						# print('re',getattr(lo,use),tail, head, getattr(next,use))
						if re.search(tail, getattr(lo,use)) and re.search(head, getattr(next,use)):
							foundlineobjects.append(lo)
							count.increment(1)
							activepoll.sethits(count.value)
							if session['onehit'] == 'yes':
								gotmyonehit = True

	curs.close()
	del dbconnection

	return foundlineobjects



"""

notes on lead and lag

lead and lag example
	https://fle.github.io/detect-value-changes-between-successive-lines-with-postgresql.html

paritions: [over clauses]
	http://tapoueh.org/blog/2013/08/20-Window-Functions


next lines via 'lead':

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

