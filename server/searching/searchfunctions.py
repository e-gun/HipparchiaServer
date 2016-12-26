# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server.dbsupport.dbfunctions import dblineintolineobject, makeablankline
from server.formatting_helper_functions import tidyuplist, dropdupes, prunedict, foundindict
from server.searching.searchformatting import cleansearchterm, prunebydate, removespuria
from server.sessionhelpers.sessionfunctions import reducetosessionselections


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
		excludedworks = list(set(excludedworks))
	
	authorandworklist = list(set(authorandworklist) - set(excludedworks))
	
	del ad
	del wd

	return authorandworklist


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


def whereclauses(uidwithatsign, operand, authors):
	"""
	in order to restrict a search to a portion of a work, you will need a where clause
	this builds it out of something like 'gr0003w001_AT_3|12' (Thuc., Bk 3, Ch 12)

	sample output:
		[('level_02_value=%s ', '1'), ('level_01_value=%s ', '3')]

	:param uidwithatsign:
	:param operand: this should be either '=' or '!='
	:return: a tuple consisting of the SQL string and the value to be passed via %s
	"""
	
	whereclausetuples = []
	
	a = uidwithatsign[:6]
	locus = uidwithatsign[14:].split('|')
	
	ao = authors[a]
	for w in ao.listofworks:
		if w.universalid == uidwithatsign[0:10]:
			wk = w
	
	wklvls = list(wk.structure.keys())
	wklvls.reverse()
	
	index = -1
	for l in locus:
		index += 1
		lvstr = 'level_0' + str(wklvls[index]) + '_value' + operand + '%s '
		whereclausetuples.append((lvstr, l))

	# print('whereclausetuples',whereclausetuples)

	return whereclausetuples


def simplesearchworkwithexclusion(seeking, workdbname, authors, cursor):
	"""
	special issues arise if you want to search Iliad less books 1 and 24
	the standard search apparatus can't do this, but this can
	a modified version of substringsearch()

	possible to use finddblinefromincompletelocus() to get a set of line numbers to search
	but is that at all faster? it likely means more queries in the end, not fewer

	problem: l2<>1 AND l1<>10 inside an SQL query will kill ALL 10s at l1, not just in the one segment
	so you cant just string together the where clauses as one giant collection of ANDs
	instead to search Hdt while dropping book 1 and 7.10 and 9.110 you do:

		SELECT * FROM gr0016w001 WHERE (stripped_line ~* 'δεινον' OR hyphenated_words ~* 'δεινον')
		AND (level_02_value<>'1' )
		AND (level_02_value<>'7' OR level_01_value<>'10' )
		AND (level_02_value<>'9'OR level_01_value<>'110' )
		LIMIT 250

	"""
	mylimit = ' LIMIT ' + str(session['maxresults'])
	if session['accentsmatter'] == 'Y':
		columna = 'marked_up_line'
	else:
		columna = 'stripped_line'
	columnb = 'hyphenated_words'
	
	seeking = cleansearchterm(seeking)
	hyphsearch = seeking
	db = workdbname[0:6]
	wkid = workdbname[0:10]
	
	mysyntax = '~*'
	if seeking[0] == ' ':
		# otherwise you will miss words that start lines because they do not have a leading whitespace
		seeking = r'(^|\s)' + seeking[1:]
	elif seeking[0:1] == '\s':
		seeking = r'(^|\s)' + seeking[2:]
	
	restrictions = []
	for p in session['psgexclusions']:
		if workdbname in p:
			restrictions.append(whereclauses(p, '<>', authors))
	
	d = [wkid, seeking, hyphsearch]
	qw = 'AND ('
	for r in restrictions:
		for i in range(0, len(r)):
			qw += r[i][0] + 'OR '
			d.append(r[i][1])
		# drop the trailing ' OR'
		qw = qw[0:-4] + ') AND ('
	# drop the trailing ') AND ('
	qw = qw[0:-6]
	
	query = 'SELECT * FROM ' + db + ' WHERE ( wkuniversalid=%s ) AND ('  \
			+ columna + ' ' + mysyntax + ' %s OR ' + columnb + ' ' + mysyntax + ' %s) ' + qw + ' ORDER BY index ASC '+mylimit
	data = tuple(d)
	cursor.execute(query, data)
	found = cursor.fetchall()
	
	return found


def substringsearch(seeking, cursor, workdbname, authors):
	"""
	actually one of the most basic search types: look for a string/substring
	this is brute force: you wade through the full text of the work
	:param seeking:
	:param cursor:
	:param workdbname:
	:param authors:
	:return:
	"""
	
	mylimit = 'LIMIT ' + str(session['maxresults'])
	if session['accentsmatter'] == 'Y':
		# columna = 'marked_up_line'
		column = 'accented_line'
	else:
		column = 'stripped_line'

	audbname = workdbname[0:6]
	seeking = cleansearchterm(seeking)
	
	mysyntax = '~*'
	if seeking[0] == ' ':
		# otherwise you will miss words that start lines because they do not have a leading whitespace
		seeking = r'(^|\s)' + seeking[1:]
	elif seeking[0:1] == '\s':
		seeking = r'(^|\s)' + seeking[2:]
	
	found = []
	
	if len(workdbname) == 10:
		# e.g., 'lt1002w003'
		query = 'SELECT * FROM ' + audbname + ' WHERE ( wkuniversalid=%s ) AND ( ' + column + ' ' + mysyntax + ' %s ) ' + mylimit
		data = (workdbname, seeking)
	elif len(workdbname) == 6:
		# e.g., 'lt0025'
		query = 'SELECT * FROM ' + audbname + ' WHERE ( ' + column + ' ' + mysyntax + ' %s ) ' + mylimit
		data = (seeking,)
	else:
		# e.g., 'lt0914w001_AT_3'
		qw = ''
		db = workdbname[0:6]
		wid = workdbname[0:10]
		d = [wid, seeking]
		w = whereclauses(workdbname, '=', authors)
		for i in range(0, len(w)):
			qw += 'AND (' + w[i][0] + ') '
			d.append(w[i][1])

		query = 'SELECT * FROM ' + db + ' WHERE ( wkuniversalid=%s ) AND (' + column + ' ' + mysyntax + ' %s) ' + qw + ' ORDER BY index ASC ' + mylimit
		data = tuple(d)
	
	try:
		cursor.execute(query, data)
		found = cursor.fetchall()
	except:
		print('could not execute', query, data)

	return found


def lookoutsideoftheline(linenumber, numberofextrawords, workid, cursor):
	"""
	grab a line and add the N words at the tail and head of the previous and next lines
	this will let you search for phrases that fall along a line break "και δη | και"
	
	if you wanted to look for 'ἀείδων Ϲπάρτηϲ'
	you need this individual line:
		2.1.374  δεξιτερὴν γὰρ ἀνέϲχε μετάρϲιον, ὡϲ πρὶν ἀείδων
	to turn extend out to:
		ὑφαίνων δεξιτερὴν γὰρ ἀνέϲχε μετάρϲιον ὡϲ πρὶν ἀείδων ϲπάρτηϲ
		
	:param linenumber:
	:param numberofextrawords:
	:param workdbname:
	:param cursor:
	:return:
	"""

	workdbname = workid[0:6]

	query = 'SELECT * FROM ' + workdbname + ' WHERE index >= %s AND index <= %s'
	data = (linenumber-1, linenumber+1)
	cursor.execute(query, data)
	results = cursor.fetchall()
	lines = []
	for r in results:
		lines.append(dblineintolineobject(workdbname, r))

	# will get key errors if there is no linenumber+/-1
	if len(lines) == 2:
		if lines[0].index == linenumber:
			lines = [makeablankline(workdbname, linenumber-1)] + lines
		else:
			lines.append(makeablankline(workdbname, linenumber+1))
	if len(lines) == 1:
		lines = [makeablankline(workdbname, linenumber-1)] + lines
		lines.append(makeablankline(workdbname, linenumber+1))
	
	ldict = {}
	for line in lines:
		ldict[line.index] = line
	
	text = []
	for line in lines:
		if session['accentsmatter'] == 'Y':
			wordsinline = line.wordlist('polytonic')
		else:
			wordsinline = line.wordlist('stripped')
		
		if line.index == linenumber-1:
			text = wordsinline[(numberofextrawords * -1):]
		elif line.index == linenumber:
			text += wordsinline
		elif line.index == linenumber+1:
			text += wordsinline[0:numberofextrawords]
			
	aggregate = ' '.join(text)
	aggregate = re.sub(r'\s\s',r' ', aggregate)
	aggregate = ' ' + aggregate + ' '
	
	return aggregate