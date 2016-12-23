# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import re

"""
simple loaders called when HipparchiaServer launches
these lists will contain (more or less...) globally available values
the main point is to avoid constant calls to the DB
for commonly used info
"""


def buildaugenresdict(authordict):
	"""
	build lists of author genres: [ g1, g2, ...]

	do this by corpus and tag it accordingly


	:param authordict:
	:return:
	"""

	gklist = []
	ltlist = []
	inlist = []
	dplist = []

	genresdict = { 'gr': gklist, 'lt': ltlist, 'in': inlist, 'dp': dplist }

	for a in authordict:
		if authordict[a].genres is not None and authordict[a].genres != '':
			g = authordict[a].genres.split(',')
			l = authordict[a].universalid[0:2]
			genresdict[l] += g

	for l in ['gr', 'lt', 'in', 'dp']:
		genresdict[l] = list(set(genresdict[l]))
		genresdict[l] = [re.sub(r'^\s|\s$','',x) for x in genresdict[l]]
		genresdict[l].sort()

	return genresdict


def buildworkgenresdict(workdict):
	"""
	load up the list of work genres: [ g1, g2, ...]
	this will see heavy use throughout the world of 'views.py'
	:param authordict:
	:return:
	"""

	gklist = []
	ltlist = []
	inlist = []
	dplist = []

	genresdict = { 'gr': gklist, 'lt': ltlist, 'in': inlist, 'dp': dplist }

	for w in workdict:
		if workdict[w].workgenre is not None and workdict[w].workgenre != '':
			g = workdict[w].workgenre.split(',')
			l = workdict[w].universalid[0:2]
			genresdict[l] += g

	for l in ['gr', 'lt', 'in', 'dp']:
		genresdict[l] = list(set(genresdict[l]))
		genresdict[l] = [re.sub(r'^\s|\s$','',x) for x in genresdict[l]]
		genresdict[l].sort()

	return genresdict


def buildauthorlocationdict(authordict):
	"""
	build lists of author locations: [ g1, g2, ...]

	do this by corpus and tag it accordingly


	:param authordict:
	:return:
	"""

	gklist = []
	ltlist = []
	inlist = []
	dplist = []

	locationdict = { 'gr': gklist, 'lt': ltlist, 'in': inlist, 'dp': dplist }

	for a in authordict:
		if authordict[a].location is not None and authordict[a].location != '':
			loc = authordict[a].location.split(',')
			l = authordict[a].universalid[0:2]
			locationdict[l] += loc

	for l in ['gr', 'lt', 'in', 'dp']:
		locationdict[l] = list(set(locationdict[l]))
		locationdict[l] = [re.sub(r'^\s|\s$','',x) for x in locationdict[l]]
		locationdict[l].sort()

	return locationdict


def buildworkprovenancedict(workdict):
	"""
	load up the list of work provenances
	used in offerprovenancehints()

	:param workdict:
	:return:
	"""

	gklist = []
	ltlist = []
	inlist = []
	dplist = []

	locationdict = { 'gr': gklist, 'lt': ltlist, 'in': inlist, 'dp': dplist }

	for w in workdict:
		if workdict[w].provenance is not None and workdict[w].provenance != '':
			loc = workdict[w].provenance.split(',')
			l = workdict[w].universalid[0:2]
			locationdict[l] += loc

	for l in ['gr', 'lt', 'in', 'dp']:
		locationdict[l] = list(set(locationdict[l]))
		locationdict[l] = [re.sub(r'^\s|\s$','',x) for x in locationdict[l]]
		locationdict[l].sort()

	return locationdict