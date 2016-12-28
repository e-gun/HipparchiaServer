# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""


import re
from collections import deque

from flask import session

from server.formatting_helper_functions import stripaccents


def dropdupes(checklist, matchlist):
	"""
	clean up a list
	drop anything that already has something else like it chosen
	:param uidlist:
	:return:
	"""

	for c in checklist:
		for m in matchlist:
			if c in m:
				checklist.remove(c)

	return checklist


def polytonicsort(unsortedwords):
	# sort() looks at your numeric value, but α and ά and ᾶ need not have neighboring numerical values
	# stripping diacriticals can help this, but then you get words that collide
	# gotta jump through some extra hoops

	# deque() is faster than list when you append

	snipper = re.compile(r'(.*?)(-snip-)(.*?)')

	stripped = deque()
	for word in unsortedwords:
		if len(word) > 0:
			strippedword = stripaccents(word)
			# one modification to stripaccents(): σ for ϲ in order to get the right values
			strippedword = re.sub(r'ϲ', r'σ', strippedword)
			stripped.append(strippedword + '-snip-' + word)
	stripped = sorted(stripped)

	sortedversion = deque()
	for word in stripped:
		cleaned = re.sub(snipper, r'\3', word)
		sortedversion.append(cleaned)

	return sortedversion


def sortauthorandworklists(authorandworklist, authorsdict):
	"""
	send me a list of workuniversalids and i will resort it via the session sortorder
	:param authorandworklist:
	:param authorsdict:
	:return:
	"""
	sortby = session['sortorder']
	templist = []
	newlist = []

	if sortby != 'universalid':
		for a in authorandworklist:
			auid = a[0:6]
			crit = getattr(authorsdict[auid], sortby)
			name = authorsdict[auid].shortname
			if sortby == 'converted_date':
				try:
					crit = float(crit)
				except:
					crit = 9999

			templist.append([crit, a, name])

		# http://stackoverflow.com/questions/5212870/sorting-a-python-list-by-two-criteria#17109098
		# sorted(list, key=lambda x: (x[0], -x[1]))

		templist = sorted(templist, key=lambda x: (x[0], x[2]))
		for t in templist:
			newlist.append(t[1])
	else:
		newlist = authorandworklist

	return newlist


def sortresultslist(hits, authorsdict, worksdict):
	"""

	take a list of hits (which is a list of line objects)
	sort it by the session sort criterion
	mark the list with index numbers (because an mp function will grab this next)

	:param hits:
	:param authorsdict:
	:return:
	"""


	sortby = session['sortorder']
	templist = []
	hitsdict = {}

	for hit in hits:
		auid = hit.wkuinversalid[0:6]
		wkid = hit.wkuinversalid
		sortablestring = authorsdict[auid].shortname + worksdict[wkid].title
		if sortby == 'converted_date':
			try:
				crit = int(worksdict[wkid].converted_date)
				if crit > 2000:
					try:
						crit = int(authorsdict[auid].converted_date)
					except:
						crit = 9999
			except:
				try:
					crit = int(authorsdict[auid].converted_date)
				except:
					crit = 9999
		elif sortby == 'provenance':
			crit = getattr(worksdict[wkid], sortby)
		elif sortby == 'location' or sortby == 'shortname' or sortby == 'authgenre':
			crit = getattr(authorsdict[auid], sortby)
		else:
			crit = hit.wkuinversalid+str(hit.index)

		templist.append([crit, sortablestring, hit])

	# http://stackoverflow.com/questions/5212870/sorting-a-python-list-by-two-criteria#17109098
	# sorted(list, key=lambda x: (x[0], -x[1]))

	templist = sorted(templist, key=lambda x: (x[0], x[1]))

	index = -1
	for t in templist:
		index += 1
		hitsdict[index] = t[2]

	return hitsdict


def dictitemstartswith(originaldict, element, muststartwith):
	"""

	trim a dict via a criterion: muststartwith must begin the item to survive the check

	:param originaldict:
	:param element:
	:param muststartwith:
	:return:
	"""

	muststartwith = '^'+muststartwith
	newdict = prunedict(originaldict, element, muststartwith)

	return newdict


def prunedict(originaldict, element, mustbein):
	"""
	trim a dict via a criterion: mustbein must be in it to survive the check

	:param originaldict:
	:param criterion:
	:param mustbe:
	:return:
	"""
	newdict = {}

	mustbein = re.compile(mustbein)

	for item in originaldict:
		if re.search(mustbein, getattr(originaldict[item], element)) is not None:
			newdict[item] = originaldict[item]

	return newdict


def foundindict(dict, element, mustbein):
	"""
	search for an element in a dict
	return a list of universalids
	:param dict:
	:param element:
	:param mustbein:
	:return:
	"""

	finds = []
	for item in dict:
		if getattr(dict[item], element) is not None:
			if re.search(re.escape(mustbein), getattr(dict[item], element)) is not None:
				finds.append(dict[item].universalid)

	return finds


def tidyuplist(untidylist):
	"""
	sort and remove duplicates
	:param untidylist:
	:return:
	"""
	# not supposed to get 0 lists here, but...
	if len(untidylist) > 0:
		untidylist[:] = [x for x in untidylist if x]
		tidylist = list(set(untidylist))
		tidylist.sort()
	else:
		tidylist = []

	return tidylist