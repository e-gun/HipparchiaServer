# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server.dbsupport.dbfunctions import dblineintolineobject, grabonelinefromwork, makeablankline, setconnection
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion, dblooknear


def withinxlines(distanceinlines, firstterm, secondterm, workdbname, authors):
	"""

	after finding x, look for y within n lines of x

	people who send phrases to both halves and/or a lot of regex will not always get what they want
	:param distanceinlines:
	:param additionalterm:
	:return:
	"""
	dbconnection = setconnection('not_autocommit')
	cursor = dbconnection.cursor()

	# you will only get session['maxresults'] back from substringsearch() unless you raise the cap
	# "Roman" near "Aetol" will get 3786 hits in Livy, but only maxresults will come
	# back for checking: but the Aetolians are likley not among those passages...
	templimit = 99999

	if 'x' in workdbname:
		workdbname = re.sub('x', 'w', workdbname)
		hits = simplesearchworkwithexclusion(firstterm, workdbname, authors, cursor, templimit)
	else:
		hits = substringsearch(firstterm, cursor, workdbname, authors, templimit)

	fullmatches = []
	if session['accentsmatter'] == 'yes':
		usecolumn = 'accented_line'
	else:
		usecolumn = 'stripped_line'

	while hits and len(fullmatches) < int(session['maxresults']):
		hit = hits.pop()
		near = dblooknear(hit[0], distanceinlines + 1, secondterm, hit[1], usecolumn, cursor)
		if session['nearornot'] == 'T' and near:
			fullmatches.append(hit)
		elif session['nearornot'] == 'F' and not near:
			fullmatches.append(hit)

	dbconnection.commit()
	cursor.close()

	return fullmatches


def withinxwords(distanceinwords, firstterm, secondterm, workdbname, whereclauseinfo):
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
	dbconnection = setconnection('not_autocommit')
	cursor = dbconnection.cursor()

	# you will only get session['maxresults'] back from substringsearch() unless you raise the cap
	# "Roman" near "Aetol" will get 3786 hits in Livy, but only maxresults will come
	# back for checking: but the Aetolians are likley not among those passages...
	templimit = 9999

	distanceinwords += 1

	if session['accentsmatter'] == 'yes':
		use = 'polytonic'
	else:
		use = 'stripped'

	if 'x' in workdbname:
		workdbname = re.sub('x', 'w', workdbname)
		hits = simplesearchworkwithexclusion(firstterm, workdbname, whereclauseinfo, cursor, templimit)
	else:
		hits = substringsearch(firstterm, cursor, workdbname, whereclauseinfo, templimit)

	fullmatches = []

	for hit in hits:
		hitline = dblineintolineobject(hit)
		searchzone = getattr(hitline,use)
		match = re.search(firstterm, searchzone)
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
		while ucount < distanceinwords+1:
			atline -= 1
			try:
				previous = dblineintolineobject(grabonelinefromwork(workdbname[0:6], atline, cursor))
			except TypeError:
				# 'NoneType' object is not subscriptable
				previous = makeablankline(workdbname[0:6], -1)
				ucount = 999
			lagging = previous.wordlist(use) + lagging
			ucount += previous.wordcount()
		lagging = lagging[-1*(distanceinwords-1):]
		lagging = ' '.join(lagging)

		leading = [x for x in past.split(' ') if x]
		atline = hitline.index
		while pcount < distanceinwords+1:
			atline += 1
			try:
				next = dblineintolineobject(grabonelinefromwork(workdbname[0:6], atline, cursor))
			except TypeError:
				# 'NoneType' object is not subscriptable
				next = makeablankline(workdbname[0:6], -1)
				pcount = 999
			leading += next.wordlist(use)
			pcount += next.wordcount()
		leading = leading[:distanceinwords-1]
		leading = ' '.join(leading)

		if session['nearornot'] == 'T'  and (re.search(secondterm,leading) or re.search(secondterm,lagging)):
			fullmatches.append(hit)
		elif session['nearornot'] == 'F' and not re.search(secondterm,leading) and not re.search(secondterm,lagging):
			fullmatches.append(hit)

	dbconnection.commit()
	cursor.close()

	return fullmatches


