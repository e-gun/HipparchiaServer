# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server.dbsupport.dbfunctions import dblineintolineobject, grabonelinefromwork, makeablankline, setconnection
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion, dblooknear


def withinxlines(workdbname, searchobject):
	"""

	after finding x, look for y within n lines of x

	people who send phrases to both halves and/or a lot of regex will not always get what they want
	:param distanceinlines:
	:param additionalterm:
	:return:
	"""

	s = searchobject

	dbconnection = setconnection('not_autocommit')
	cursor = dbconnection.cursor()

	# you will only get session['maxresults'] back from substringsearch() unless you raise the cap
	# "Roman" near "Aetol" will get 3786 hits in Livy, but only maxresults will come
	# back for checking: but the Aetolians are likley not among those passages...
	templimit = 99999

	if 'x' in workdbname:
		workdbname = re.sub('x', 'w', workdbname)
		hits = simplesearchworkwithexclusion(s.termone, workdbname, s, cursor, templimit)
	else:
		hits = substringsearch(s.termone, workdbname, s, cursor, templimit)

	fullmatches = []

	while hits and len(fullmatches) < s.cap:
		hit = hits.pop()
		isnear = dblooknear(hit[0], s.distance + 1, s.termtwo, hit[1], s.usecolumn, cursor)
		if s.near and isnear:
			fullmatches.append(hit)
		elif not s.near and not isnear:
			fullmatches.append(hit)

	dbconnection.commit()
	cursor.close()

	return fullmatches


def withinxwords(workdbname, searchobject):
	"""

	int(session['proximity']), searchingfor, proximate, curs, wkid, whereclauseinfo

	after finding x, look for y within n words of x

	getting to y:
		find the search term x and slice it out of its line
		then build forwards and backwards within the requisite range
		then see if you get a match in the range

	if looking for 'paucitate' near 'imperator' you will find:
		'romani paucitate seruorum gloriatos itane tandem ne'
	this will become:
		'romani' + 'seruorum gloriatos itane tandem ne'


	:param distanceinlines:
	:param additionalterm:
	:return:
	"""
	s = searchobject

	# look out for off-by-one errors
	distance = s.distance+1

	dbconnection = setconnection('not_autocommit')
	cursor = dbconnection.cursor()

	# you will only get session['maxresults'] back from substringsearch() unless you raise the cap
	# "Roman" near "Aetol" will get 3786 hits in Livy, but only maxresults will come
	# back for checking: but the Aetolians are likley not among those passages...
	templimit = 9999

	if 'x' in workdbname:
		workdbname = re.sub('x', 'w', workdbname)
		hits = simplesearchworkwithexclusion(s.termone, workdbname, s, cursor, templimit)
	else:
		hits = substringsearch(s.termone, workdbname, s, cursor, templimit)

	fullmatches = []

	for hit in hits:
		hitline = dblineintolineobject(hit)
		searchzone = getattr(hitline, s.usewordlist)
		match = re.search(s.termone, searchzone)
		# but what if you just found 'paucitate' inside of 'paucitatem'?
		# you will have 'm' left over and this will throw off your distance-in-words count
		past = searchzone[match.end():]
		while past and past[0] != ' ':
			past = past[1:]

		upto = searchzone[:match.start()]
		while upto and upto[-1] != ' ':
			upto = upto[:-1]

		ucount = len([x for x in upto.split(' ') if x])
		pcount = len([x for x in past.split(' ') if x])

		atline = hitline.index
		lagging = [x for x in upto.split(' ') if x]
		while ucount < distance+1:
			atline -= 1
			try:
				previous = dblineintolineobject(grabonelinefromwork(workdbname[0:6], atline, cursor))
			except TypeError:
				# 'NoneType' object is not subscriptable
				previous = makeablankline(workdbname[0:6], -1)
				ucount = 999
			lagging = previous.wordlist(s.usewordlist) + lagging
			ucount += previous.wordcount()
		lagging = lagging[-1*(distance-1):]
		lagging = ' '.join(lagging)

		leading = [x for x in past.split(' ') if x]
		atline = hitline.index
		while pcount < distance+1:
			atline += 1
			try:
				next = dblineintolineobject(grabonelinefromwork(workdbname[0:6], atline, cursor))
			except TypeError:
				# 'NoneType' object is not subscriptable
				next = makeablankline(workdbname[0:6], -1)
				pcount = 999
			leading += next.wordlist(s.usewordlist)
			pcount += next.wordcount()
		leading = leading[:distance-1]
		leading = ' '.join(leading)

		if s.near and (re.search(s.termtwo, leading) or re.search(s.termtwo, lagging)):
			fullmatches.append(hit)
		elif not s.near and not re.search(s.termtwo, leading) and not re.search(s.termtwo, lagging):
			fullmatches.append(hit)

	dbconnection.commit()
	cursor.close()

	return fullmatches


