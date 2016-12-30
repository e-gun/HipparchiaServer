# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from collections import deque
from flask import session
from server.formatting_helper_functions import stripaccents
from server.listsandsession.sessionfunctions import reducetosessionselections, justlatin


def compileauthorandworklist(listmapper):
	"""
	master author dict + session selctions into a list of dbs to search
	:param authors:
	:return:
	"""

	searchlist = session['auselections'] + session['agnselections'] + session['wkgnselections'] + session[
		'psgselections'] + session['wkselections'] + session['alocselections'] + session['wlocselections']
	exclusionlist = session['auexclusions'] + session['wkexclusions'] + session['agnexclusions'] + session[
		'wkgnexclusions'] + session['psgexclusions'] + session['alocexclusions'] + session['wlocexclusions']

	# trim by active corpora
	ad = reducetosessionselections(listmapper, 'a')
	wd = reducetosessionselections(listmapper, 'w')

	authorandworklist = []

	# build the inclusion list
	if len(searchlist) > 0:
		if len(session['agnselections'] + session['wkgnselections'] + session['alocselections'] + session['wlocselections']) == 0:
			# you have only asked for specific passages and there are no genre constraints
			# 	eg: just Aeschylus + Aristophanes, Frogs
			# for the sake of speed we will handle this separately from the more complex case
			# the code at the end of the 'else' section ought to match the code that follows
			# the passage checks are superfluous if rationalizeselections() got things right

			passages = session['psgselections']
			works = session['wkselections']
			works = tidyuplist(works)
			works = dropdupes(works, passages)

			for w in works:
				authorandworklist.append(w)

			authors = []
			for a in session['auselections']:
				authors.append(a)

			tocheck = works + passages
			authors = dropdupes(authors, tocheck)
			for a in authors:
				for w in ad[a].listofworks:
					authorandworklist.append(w.universalid)
			del authors
			del works

			if len(session['psgselections']) > 0:
				authorandworklist = dropdupes(authorandworklist, session['psgselections'])
				authorandworklist = session['psgselections'] + authorandworklist

			authorandworklist = list(set(authorandworklist))

			if session['spuria'] == 'N':
				authorandworklist = removespuria(authorandworklist, wd)
		else:
			# build lists up from specific items (passages) to more general classes (works, then authors)

			authorandworklist = []
			for g in session['wkgnselections']:
				authorandworklist += foundindict(wd, 'workgenre', g)

			authorlist = []
			for g in session['agnselections']:
				authorlist = foundindict(ad, 'genres', g)
			for a in authorlist:
				for w in ad[a].listofworks:
					authorandworklist.append(w.universalid)
			del authorlist

			for l in session['wlocselections']:
				authorandworklist += foundindict(wd, 'provenance', l)

			authorlist = []
			for l in session['alocselections']:
				authorlist = foundindict(ad, 'location', l)
			for a in authorlist:
				for w in ad[a].listofworks:
					authorandworklist.append(w.universalid)
			del authorlist

			# a tricky spot: when/how to apply prunebydate()
			# if you want to be able to seek 5th BCE oratory and Plutarch, then you need to let auselections take precedence
			# accordingly we will do classes and genres first, then trim by date, then add in individual choices
			authorandworklist = prunebydate(authorandworklist, ad, wd)

			# now we look at things explicitly chosen:
			# the passage checks are superfluous if rationalizeselections() got things right

			passages = session['psgselections']
			works = session['wkselections']
			works = tidyuplist(works)
			works = dropdupes(works, passages)

			for w in works:
				authorandworklist.append(w)

			authors = []
			for a in session['auselections']:
				authors.append(a)

			tocheck = works + passages
			authors = dropdupes(authors, tocheck)
			for a in authors:
				for w in ad[a].listofworks:
					authorandworklist.append(w.universalid)
			del authors
			del works

			if len(session['psgselections']) > 0:
				authorandworklist = dropdupes(authorandworklist, session['psgselections'])
				authorandworklist = session['psgselections'] + authorandworklist

			authorandworklist = list(set(authorandworklist))

			if session['spuria'] == 'N':
				authorandworklist = removespuria(authorandworklist, wd)

	else:
		# you picked nothing and want everything. well, maybe everything...

		# trim by active corpora
		wd = reducetosessionselections(listmapper, 'w')

		authorandworklist = wd.keys()

		if session['latestdate'] != '1500' or session['earliestdate'] != '-850':
			authorandworklist = prunebydate(authorandworklist, ad, wd)

		if session['spuria'] == 'N':
			authorandworklist = removespuria(authorandworklist, wd)

	# build the exclusion list
	# note that we are not handling excluded individual passages yet
	excludedworks = []

	if len(exclusionlist) > 0:
		excludedworks = []
		excludedauthors = []

		for g in session['agnexclusions']:
			excludedauthors += foundindict(ad, 'genres', g)

		for l in session['alocexclusions']:
			excludedauthors += foundindict(ad, 'location', l)

		for a in session['auexclusions']:
			excludedauthors.append(a)

		excludedauthors = tidyuplist(excludedauthors)

		for a in excludedauthors:
			for w in ad[a].listofworks:
				excludedworks.append(w.universalid)
		del excludedauthors

		for g in session['wkgnexclusions']:
			excludedworks += foundindict(wd, 'workgenre', g)

		for l in session['wlocexclusions']:
			excludedworks += foundindict(wd, 'provenance', l)

		excludedworks += session['wkexclusions']
		excludedworks = set(excludedworks)

	authorandworklist = list(set(authorandworklist) - set(excludedworks))

	del ad
	del wd

	return authorandworklist


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


def calculatewholeauthorsearches(authorandworklist, authordict):
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

	:param authorandworklist:
	:param authordict:
	:return:
	"""

	# A
	authorspresent = [x[0:6] for x in authorandworklist]
	authorspresent = set(authorspresent)

	# B
	theoreticalpoolofworks = {}
	for a in authorspresent:
		for w in authordict[a].listofworks:
			theoreticalpoolofworks[w.universalid] = a

	# C
	for a in authorandworklist:
		if a in theoreticalpoolofworks:
			del theoreticalpoolofworks[a]

	# D
	# any remaining works in this dict correspond to authors that we are not searching completely
	incomplete = [x for x in theoreticalpoolofworks.values()]
	incomplete = set(incomplete)
	complete = authorspresent - incomplete

	# E
	wholes = [x[0:6] for x in authorandworklist if x[0:6] in complete]
	parts = [x for x in authorandworklist if x[0:6] not in complete]
	prunedlist = list(set(wholes)) + list(set(parts))

	# prunedlist = []
	#
	# for a in authorandworklist:
	# 	if a[0:6] in complete:
	# 		prunedlist.append(a[0:6])
	# 	else:
	# 		prunedlist.append(a)
	# prunedlist = list(set(prunedlist))

	return prunedlist


def flagexclusions(authorandworklist):
	"""
	some works whould only be searched partially
	this flags those items on the authorandworklist by changing their workname format
	gr0001w001 becomes gr0001x001 if session['wkexclusions'] mentions gr0001w001
	:param authorandworklist:
	:return:
	"""
	modifiedauthorandworklist = []
	for w in authorandworklist:
		if len(session['psgexclusions']) > 0:
			for x in session['psgexclusions']:
				if '_AT_' not in w and w in x:
					w = re.sub('w', 'x', w)
					modifiedauthorandworklist.append(w)
				else:
					modifiedauthorandworklist.append(w)
		else:
			modifiedauthorandworklist.append(w)

	# if you apply 3 restrictions you will now have 3 copies of gr0001x001
	modifiedauthorandworklist = tidyuplist(modifiedauthorandworklist)

	return modifiedauthorandworklist


def prunebydate(authorandworklist, authorobjectdict, workobjectdict):
	"""
	send me a list of authorsandworks and i will trim it via the session date limit variables

	:param authorandworklist:
	:param authorobjectdict:
	:return:
	"""
	trimmedlist = []

	if justlatin() == False and (session['earliestdate'] != '-850' or session['latestdate'] != '1500'):
		min = int(session['earliestdate'])
		max = int(session['latestdate'])
		if min > max:
			min = max
			session['earliestdate'] = session['latestdate']

		for aw in authorandworklist:
			w = workobjectdict[aw]
			try:
				# does the work have a date?
				int(w.converted_date)
				if w.earlier(min) or w.later(max):
					pass
				else:
					trimmedlist.append(aw)
			except:
				# then we will look inside the author for the date
				aid = aw[0:6]
				try:
					if authorobjectdict[aid].earlier(min) or authorobjectdict[aid].later(max):
						pass
						# print('passing',aw ,authorobjectdict[aid].converted_date)
					else:
						trimmedlist.append(aw)
					# print('append', aw, authorobjectdict[aid].converted_date)
				except:
					# the author can't tell you his date; you must be building a list with both latin authors and something else
					trimmedlist.append(aw)

	else:
		trimmedlist = authorandworklist

	return trimmedlist


def removespuria(authorandworklist, worksdict):
	"""
	at the moment pretty crude: just look for [Sp.] or [sp.] at the end of a title
	toss it from the list if you find it
	:param authorandworklist:
	:param cursor:
	:return:
	"""
	trimmedlist = []

	sp = re.compile(r'\[(S|s)p\.\]')

	for aw in authorandworklist:
		wk = re.sub(r'x',r'w',aw[0:10])
		title = worksdict[wk].title
		try:
			if re.search(sp,title) is not None:
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

	for c in checklist:
		for m in matchlist:
			if c in m:
				checklist.remove(c)

	return checklist


def polytonicsort(unsortedwords):
	"""
	sort() looks at your numeric value, but α and ά and ᾶ need not have neighboring numerical values
	stripping diacriticals can help this, but then you get words that collide
	gotta jump through some extra hoops

	deque() is faster than list when you append

	:param unsortedwords:
	:return:
	"""

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


