# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server.searching.searchformatting import aggregatelines
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion


def withinxlines(distanceinlines, firstterm, secondterm, cursor, workdbname, authors):
	"""

	after finding x, look for y within n lines of x

	people who send phrases to both halves and/or a lot of regex will not always get what they want
	:param distanceinlines:
	:param additionalterm:
	:return:
	"""

	# you will only get session['maxresults'] back from substringsearch() unless you raise the cap
	# "Roman" near "Aetol" will get 3786 hits in Livy, but only maxresults will come
	# back for checking: but the Aetolians are likley not among those passages...
	templimit = 9999

	if 'x' in workdbname:
		workdbname = re.sub('x', 'w', workdbname)
		hits = simplesearchworkwithexclusion(firstterm, workdbname, authors, cursor, templimit)
	else:
		hits = substringsearch(firstterm, cursor, workdbname, authors, templimit)

	fullmatches = []
	for hit in hits:
		wordset = aggregatelines(hit[0] - distanceinlines, hit[0] + distanceinlines, cursor, workdbname)
		if session['nearornot'] == 'T' and re.search(secondterm, wordset):
			fullmatches.append(hit)
		elif session['nearornot'] == 'F' and re.search(secondterm, wordset) is None:
			fullmatches.append(hit)
	
	return fullmatches


def withinxwords(distanceinwords, firstterm, secondterm, cursor, workdbname, authors):
	"""

	after finding x, look for y within n words of x

	:param distanceinlines:
	:param additionalterm:
	:return:
	"""

	# you will only get session['maxresults'] back from substringsearch() unless you raise the cap
	# "Roman" near "Aetol" will get 3786 hits in Livy, but only maxresults will come
	# back for checking: but the Aetolians are likley not among those passages...
	templimit = 9999

	distanceinwords += 1

	if 'x' in workdbname:
		workdbname = re.sub('x', 'w', workdbname)
		hits = simplesearchworkwithexclusion(firstterm, workdbname, authors, cursor, templimit)
	else:
		hits = substringsearch(firstterm, cursor, workdbname, authors, templimit)
	
	fullmatches = []
	for hit in hits:
		linesrequired = 0
		wordlist = []
		while len(wordlist) < 2 * distanceinwords + 1:
			wordset = aggregatelines(hit[0] - linesrequired, hit[0] + linesrequired, cursor, workdbname)
			wordlist = wordset.split(' ')
			try:
				wordlist.remove('')
			except:
				pass
			linesrequired += 1
		
		# the word is near the middle...
		center = len(wordlist) // 2
		prior = ''
		next = ''
		if firstterm in wordlist[center]:
			startfrom = center
		else:
			distancefromcenter = 0
			while firstterm not in prior and firstterm not in next:
				distancefromcenter += 1
				try:
					next = wordlist[center + distancefromcenter]
					prior = wordlist[center - distancefromcenter]
				except:
					# print('failed to find next/prior:',authorobject.shortname,distancefromcenter,wordlist)
					# to avoid the infinite loop...
					firstterm = prior
			if firstterm in prior:
				startfrom = center - distancefromcenter
			else:
				startfrom = center + distancefromcenter
		
		searchszone = wordlist[startfrom - distanceinwords:startfrom + distanceinwords]
		searchszone = ' '.join(searchszone)
		
		if session['nearornot'] == 'T' and re.search(secondterm, searchszone):
			fullmatches.append(hit)
		elif session['nearornot'] == 'F' and re.search(secondterm, searchszone) is None:
			fullmatches.append(hit)
	
	return fullmatches