# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server.helperfunctions import stripaccents, buildhipparchiatranstable
from server.listsandsession.sessionfunctions import reducetosessionselections, justlatin
from server.startup import allvaria, allincerta


def compilesearchlist(listmapper, s=session):
	"""
	master author dict + session selctions into a list of dbs to search

	s = session, but feel free to send frozensession
		getsearchlistcontents wants just session
		executesearch might as well use frozensession

	:param authors:
	:return:
	"""

	searching = s['auselections'] + s['agnselections'] + s['wkgnselections'] + s['psgselections'] + s['wkselections'] \
	             + s['alocselections'] + s['wlocselections']
	excluding = s['auexclusions'] + s['wkexclusions'] + s['agnexclusions'] + s['wkgnexclusions'] + s['psgexclusions'] \
	                + s['alocexclusions'] + s['wlocexclusions']

	# trim by active corpora
	ad = reducetosessionselections(listmapper, 'a')
	wd = reducetosessionselections(listmapper, 'w')

	searchlist = []

	# [A] build the inclusion list
	if len(searching) > 0:
		# build lists up from specific items (passages) to more general classes (works, then authors)
		for g in s['wkgnselections']:
			searchlist += foundindict(wd, 'workgenre', g)

		authorlist = []
		for g in s['agnselections']:
			authorlist = foundindict(ad, 'genres', g)
			for a in authorlist:
				for w in ad[a].listofworks:
					searchlist.append(w.universalid)
		del authorlist

		for l in s['wlocselections']:
			searchlist += foundindict(wd, 'provenance', l)

		authorlist = []
		for l in s['alocselections']:
			authorlist = foundindict(ad, 'location', l)
			for a in authorlist:
				for w in ad[a].listofworks:
					searchlist.append(w.universalid)
		del authorlist

		# a tricky spot: when/how to apply prunebydate()
		# if you want to be able to seek 5th BCE oratory and Plutarch, then you need to let auselections take precedence
		# accordingly we will do classes and genres first, then trim by date, then add in individual choices
		searchlist = prunebydate(searchlist, ad, wd)

		# now we look at things explicitly chosen:
		authors = [a for a in s['auselections']]
		try:
			worksof = [w.universalid for a in authors for w in ad[a].listofworks]
		except KeyError:
			# e.g., you had a LAT list with Cicero and then deactivated that set of authors and works
			worksof = []
		works = s['wkselections']
		passages = s['psgselections']

		searchlist += [w for w in works] + worksof + passages
		searchlist = [aw for aw in searchlist if aw]
		searchlist = list(set(searchlist))
	else:
		# you picked nothing and want everything. well, maybe everything...

		# trim by active corpora
		wd = reducetosessionselections(listmapper, 'w')

		searchlist = wd.keys()

		if s['latestdate'] != '1500' or s['earliestdate'] != '-850':
			searchlist = prunebydate(searchlist, ad, wd)

	# [B] now start subtracting from the list of inclusions
	if s['spuria'] == 'no':
		searchlist = removespuria(searchlist, wd)

	# build the exclusion list
	# note that we are not handling excluded individual passages yet
	excludedworks = []

	if len(excluding) > 0:
		excludedauthors = [a for a in s['auexclusions']]

		for g in s['agnexclusions']:
			excludedauthors += foundindict(ad, 'genres', g)

		for l in s['alocexclusions']:
			excludedauthors += foundindict(ad, 'location', l)

		excludedauthors = set(excludedauthors)

		# all works of all excluded authors are themselves excluded
		excludedworks = [w.universalid for a in excludedauthors for w in ad[a].listofworks]

		excludedworks += s['wkexclusions']

		for g in s['wkgnexclusions']:
			excludedworks += foundindict(wd, 'workgenre', g)

		for l in s['wlocexclusions']:
			excludedworks += foundindict(wd, 'provenance', l)

	searchlist = list(set(searchlist) - set(excludedworks))

	return searchlist


def sortsearchlist(searchlist, authorsdict):
	"""
	send me a list of workuniversalids and i will resort it via the session sortorder
	:param searchlist:
	:param authorsdict:
	:return:
	"""
	sortby = session['sortorder']
	templist = []
	newlist = []

	if sortby != 'universalid':
		for a in searchlist:
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

		templist = sorted(templist, key=lambda x: (x[0], x[2], x[1]))
		for t in templist:
			newlist.append(t[1])
	else:
		newlist = searchlist

	return newlist


def sortresultslist(hits, authorsdict, worksdict):
	"""

	take a list of hits (which is a list of line objects)
	sort it by the session sort criterion
	mark the list with index numbers (because an mp function will grab this next)

	in:
		[<server.hipparchiaclasses.dbWorkLine object at 0x10d6625f8>, <server.hipparchiaclasses.dbWorkLine object at 0x10d662470>,...]

	out:
		{0: <server.hipparchiaclasses.dbWorkLine object at 0x108981780>, 1: <server.hipparchiaclasses.dbWorkLine object at 0x108981a20>, 2: <server.hipparchiaclasses.dbWorkLine object at 0x108981b70>, ...}

	:param hits:
	:param authorsdict:
	:return:
	"""

	sortby = session['sortorder']
	templist = []

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

	templist = sorted(templist, key=lambda x: (x[0], x[1]))

	hitsdict = {idx: temp[2] for idx, temp in enumerate(templist)}

	return hitsdict


def calculatewholeauthorsearches(searchlist, authordict):
	"""

	we have applied all of our inclusions and exclusions by this point and we might well be sitting on a pile of authorsandworks
	that is really a pile of full author dbs. for example, imagine we have not excluded anything from 'Cicero'

	there is no reason to search that DB work by work since that just means doing a series of "WHERE" searches
	instead of a single, faster search of the whole thing: hits are turned into full citations via the info contained in the
	hit itself and there is no need to derive the work from the item name sent to the dispatcher

	this function will figure out if the list of work uids contains all of the works for an author and can accordingly be collapsed

	this function is *much* faster (50x?) than searching via 196K WHERE clauses

	timing sample shows that E is the bit you need to get right: [all gk, in, dp from -850 to 200 (97836 works)]

		compiletimeA = 0.02765798568725586
		compiletimeB = 0.02765798568725586
		compiletimeC = 0.021197080612182617
		compiletimeD = 0.00425410270690918
		compiletimeE = 3.2394540309906006

	[all gk, in, dp from -850 to 1500 (195825 works)]
		compiletimeE = 6.753650903701782

	50x faster if you make sure that complete is a set and not a list when you hand it to part E
		compiletimeE = 0.1252439022064209

	:param searchlist:
	:param authordict:
	:return:
	"""

	# exclusionfinder = re.compile(r'......x')
	# hasexclusion = [x[0:9] for x in searchlist if re.search(exclusionfinder,x)]

	# A
	authorspresent = [x[0:6] for x in searchlist]
	authorspresent = set(authorspresent)

	# B
	theoreticalpoolofworks = {w.universalid: a for a in authorspresent for w in authordict[a].listofworks }
	# for a in authorspresent:
	# 	for w in authordict[a].listofworks:
	# 		theoreticalpoolofworks[w.universalid] = a

	# C
	for a in searchlist:
		if a in theoreticalpoolofworks:
			del theoreticalpoolofworks[a]

	# D
	# any remaining works in this dict correspond to authors that we are not searching completely
	incomplete = [x for x in theoreticalpoolofworks.values()]
	incomplete = set(incomplete)
	complete = authorspresent - incomplete

	# E
	wholes = [x[0:6] for x in searchlist if x[0:6] in complete]
	parts = [x for x in searchlist if x[0:6] not in complete]
	prunedlist = list(set(wholes)) + list(set(parts))

	return prunedlist


def flagexclusions(searchlist, s=session):
	"""
	some works should only be searched partially
	this flags those items on the searchlist by changing their workname format
	gr0001w001 becomes gr0001x001 if session['wkexclusions'] mentions gr0001w001
	
	this function profiles as relatively slow: likely a faster way to run the loops
	
	:param searchlist:
	:return:
	"""

	if len(s['psgexclusions']) == 0:
		return searchlist
	else:
		modifiedsearchlist = []
		for w in searchlist:
			for x in s['psgexclusions']:
				if '_AT_' not in w and w in x:
					w = re.sub('(....)w(...)', r'\1x\2', w)
					modifiedsearchlist.append(w)
				else:
					modifiedsearchlist.append(w)

		# if you apply 3 restrictions you will now have 3 copies of gr0001x001
		modifiedsearchlist = tidyuplist(modifiedsearchlist)

		return modifiedsearchlist


def prunebydate(searchlist, authorobjectdict, workobjectdict):
	"""
	send me a list of authorsandworks and i will trim it via the session date limit variables
	note that 'varia' and 'incerta' need to be handled here since they have special dates:
		incerta = 2500
		varia = 2000
		[failedtoparse = 9999]
	:param searchlist:
	:param authorobjectdict:
	:return:
	"""
	trimmedlist = []

	if justlatin() == False and (session['earliestdate'] != '-850' or session['latestdate'] != '1500'):
		# [a] first prune the bad dates
		min = int(session['earliestdate'])
		max = int(session['latestdate'])
		if min > max:
			min = max
			session['earliestdate'] = session['latestdate']

		for universalid in searchlist:
			w = workobjectdict[universalid]
			try:
				# does the work have a date? if not, we will throw an exception
				if w.datefallsbetween(min, max):
					trimmedlist.append(universalid)
			except TypeError:
				# no work date? then we will look inside the author for the date
				authorid = universalid[0:6]
				try:
					if authorobjectdict[authorid].datefallsbetween(min, max):
						trimmedlist.append(universalid)
				except TypeError:
					# the author can't tell you his date; you must be building a list with both latin authors and something else
					trimmedlist.append(universalid)
		# [b] then add back in any varia and/or incerta as needed
		if session['varia'] == 'yes':
			varia = list(allvaria.intersection(searchlist))
			trimmedlist += varia
		if session['incerta'] == 'yes':
			incerta = list(allincerta.intersection(searchlist))
			trimmedlist += incerta

	else:
		trimmedlist = searchlist

	return trimmedlist


def removespuria(searchlist, worksdict):
	"""
	at the moment pretty crude: just look for [Sp.] or [sp.] at the end of a title
	toss it from the list if you find it
	:param searchlist:
	:param cursor:
	:return:
	"""
	trimmedlist = []

	sp = re.compile(r'\[(S|s)p\.\]')

	for aw in searchlist:
		wk = re.sub(r'(......)x(...)', '\1w\2', aw[0:10])
		title = worksdict[wk].title
		try:
			if re.search(sp,title):
				for w in session['wkselections']:
					if w in aw:
						trimmedlist.append(aw)
				for w in session['psgselections']:
					if w in aw:
						trimmedlist.append(aw)
			else:
				trimmedlist.append(aw)
		except:
			trimmedlist.append(aw)

	return trimmedlist


def buildhintlist(seeking, listofposiblities):
	"""

	:param seeking:
	:param listofposiblities:
	:return:
	"""

	query = seeking.lower()
	qlen = len(query)
	hintlist = [{'value': p} for p in listofposiblities if query == p.lower()[0:qlen]]

	return hintlist


#
# GENERIC LIST MANAGEMENT
#


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


def dropdupes(checklist, matchlist):
	"""
	clean up a list
	drop anything that already has something else like it chosen
	:param uidlist:
	:return:
	"""

	c = set(checklist)
	m = set(matchlist)

	c = list(c-m)

	return c


def polytonicsort(unsortedwords):
	"""
	sort() looks at your numeric value, but α and ά and ᾶ need not have neighboring numerical values
	stripping diacriticals can help this, but then you get words that collide
	gotta jump through some extra hoops

		[a] build an unaccented copy of the word in front of the word
		[b] substitute sigmas for lunate sigmas (because lunate comes after omega...)
			θαλαττησ-snip-θαλάττηϲ
		[c] sort the augmented words (where ά and ᾶ only matter very late in the game)
		[d] remove the augment
		[e] return

	:param unsortedwords:
	:return:
	"""

	transtable = buildhipparchiatranstable()

	stripped = [re.sub(r'ϲ', r'σ', stripaccents(word, transtable))+ '-snip-' + word for word in unsortedwords if word]

	stripped = sorted(stripped)

	snipper = re.compile(r'(.*?)(-snip-)(.*?)')

	sortedversion = [re.sub(snipper, r'\3', word) for word in stripped]

	return sortedversion


def foundindict(searchdict, element, mustbein):
	"""
	search for an element in a dict
	return a list of universalids

	searchdict:
		{ ... 'gr2625': <server.hipparchiaclasses.dbAuthor object at 0x1096e9cf8>, 'gr1890': <server.hipparchiaclasses.dbAuthor object at 0x1096e9d68>,
		'gr0045': <server.hipparchiaclasses.dbAuthor object at 0x1096e9dd8>, 'gr2194': <server.hipparchiaclasses.dbAuthor object at 0x1096e9e48>}
	element:
		genres
	mustbein:
		Astrologici

	:param searchdict:
	:param element:
	:param mustbein:
	:return:
	"""

	finds = [searchdict[x].universalid for x in searchdict
	         if getattr(searchdict[x], element) and getattr(searchdict[x], element) == mustbein]

	return finds

