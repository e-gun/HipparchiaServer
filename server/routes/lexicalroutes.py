# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

from flask import session

from server import hipparchia
from server.dbsupport.lexicaldbfunctions import lookformorphologymatches, querytotalwordcounts, searchdbforlexicalentry
from server.formatting.betacodetounicode import replacegreekbetacode
from server.formatting.lexicaformatting import dictonaryentryashtml, getobservedwordprevalencedata, \
	multiplelexicalmatchesintohtml
from server.formatting.wordformatting import abbreviatedsigmarestoration, attemptsigmadifferentiation, depunct, \
	removegravity, stripaccents, tidyupterm
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.listsandsession.genericlistfunctions import polytonicsort
from server.listsandsession.sessionfunctions import justlatin, justtlg
from server.listsandsession.sessionfunctions import probeforsessionvariables


@hipparchia.route('/dictsearch/<searchterm>')
def dictsearch(searchterm):
	"""
	look up words
	return dictionary entries
	json packing
	:return:
	"""

	probeforsessionvariables()

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	if hipparchia.config['UNIVERSALASSUMESBETACODE'] == 'yes':
		searchterm = replacegreekbetacode(searchterm.upper())

	allowedpunct = '^$.'
	seeking = depunct(searchterm, allowedpunct)
	seeking = seeking.lower()
	seeking = re.sub('[σς]', 'ϲ', seeking)
	stripped = stripaccents(seeking)

	# don't turn 'injurius' into '[iiII]n[iiII][uuVV]r[iiII][uuVV]s'
	# that will happen if you call stripaccents() prematurely
	stripped = re.sub(r'[uv]', '[uvUV]', stripped)
	stripped = re.sub(r'[ij]', '[ijIJ]', stripped)

	if re.search(r'[a-z]', stripped):
		usedictionary = 'latin'
		usecolumn = 'entry_name'
	else:
		usedictionary = 'greek'
		usecolumn = 'unaccented_entry'

	if not session['available'][usedictionary + '_dictionary']:
		r = [{'value': 'cannot look up {w}: {d} dictionary is not installed'.format(d=usedictionary, w=seeking)}]
		return json.dumps(r)

	limit = hipparchia.config['CAPONDICTIONARYFINDS']

	query = 'SELECT entry_name FROM {d}_dictionary WHERE {c} ~* %s LIMIT {lim}'.format(d=usedictionary, c=usecolumn, lim=limit)
	if stripped[0] == ' ' and stripped[-1] == ' ':
		data = ('^' + stripped[1:-1] + '$',)
	elif stripped[0] == ' ' and stripped[-1] != ' ':
		data = ('^' + stripped[1:] + '.*?',)
	elif stripped[0] == '^' and stripped[-1] == '$':
		# esp if the dictionary sent this via next/previous entry
		data = (stripped,)
	else:
		data = ('.*?' + stripped + '.*?',)

	# print('query, data\n\t{q}\n\t{d}\n'.format(q=query, d=data))

	dbcursor.execute(query, data)

	# note that the dictionary db has a problem with vowel lengths vs accents
	# SELECT * FROM greek_dictionary WHERE entry_name LIKE %s d ('μνᾱ/αϲθαι,μνάομαι',)
	try:
		found = dbcursor.fetchall()
	except:
		found = list()

	if not found:
		variantseeker = seeking[:-1] + '[¹²³⁴⁵⁶⁷⁸⁹]' + seeking[-1]
		data = (variantseeker,)
		dbcursor.execute(query, data)
		found = dbcursor.fetchall()

	if not found:
		# maybe an inflected form was requested (can happen via clicks inside of an entry)
		morph = lookformorphologymatches(seeking, dbcursor)
		if morph:
			guesses = morph.getpossible()
			firstguess = guesses[0].getbaseform()
			stripped = stripaccents(firstguess)
			data = ('^{s}$'.format(s=stripped),)
			# print('lookformorphologymatches() new data=', data)
			dbcursor.execute(query, data)
			found = dbcursor.fetchall()

	# the results should be given the polytonicsort() treatment
	returnarray = list()

	if len(found) == limit:
		returnarray.append({'value': '[stopped searching after {lim} finds]'.format(lim=limit)})

	if len(found) > 0:
		finddict = {f[0]: f for f in found}
		keys = finddict.keys()
		keys = polytonicsort(keys)

		sortedfinds = [finddict[k] for k in keys]

		if len(sortedfinds) == 1:
			# sending '0' to browserdictionarylookup() will hide the count number
			count = -1
		else:
			count = 0

		for entry in sortedfinds:
			count += 1
			returnarray.append({'value': dictonaryentryashtml(count, entry[0])})
	else:
		returnarray.append({'value': '[nothing found]'})

	if session['zaplunates'] == 'yes':
		returnarray = [{'value': attemptsigmadifferentiation(x['value'])} for x in returnarray]
		returnarray = [{'value': abbreviatedsigmarestoration(x['value'])} for x in returnarray]

	returnarray = json.dumps(returnarray)

	dbconnection.connectioncleanup()

	return returnarray


@hipparchia.route('/parse/<observedword>')
def findbyform(observedword):
	"""
	this function sets of a chain of other functions
	find dictionary form
	find the other possible forms
	look up the dictionary form
	return a formatted set of info
	:return:
	"""

	probeforsessionvariables()

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	sanitationerror = '[empty search: <span class="emph">{w}</span> was sanitized into nothingness]'
	dberror = '<br />[the {lang} morphology data has not been installed]'
	notfounderror = '<br />[could not find a match for <span class="emph">{cw}</span> in the morphology table]'
	nodataerror = '<br /><br />no prevalence data for {w}'

	# the next is pointless because: 'po/lemon' will generate a URL '/parse/po/lemon'
	# that will 404 before you can get to replacegreekbetacode()
	# this is a bug in the interaction between Flask and the JS

	# if hipparchia.config['UNIVERSALASSUMESBETACODE'] == 'yes':
	# 	observedword = replacegreekbetacode(observedword.upper())

	# the next makes sense only in the context of pointedly invalid input
	w = depunct(observedword)
	w = tidyupterm(w)
	w = re.sub(r'[σς]', 'ϲ', w)

	# python seems to know how to do this with greek...
	w = w.lower()
	retainedgravity = w
	cleanedword = removegravity(retainedgravity)

	# index clicks will send you things like 'αὖ²'
	cleanedword = re.sub(r'[⁰¹²³⁴⁵⁶⁷⁸⁹]', '', cleanedword)

	# the search syntax is '=' and not '~', so the next should be avoided unless a lot of refactoring will happen
	# cleanedword = re.sub(r'[uv]', r'[uv]', cleanedword)
	# cleanedword = re.sub(r'[ij]', r'[ij]', cleanedword)

	try:
		cleanedword[0]
	except IndexError:
		returnarray = [{'value': sanitationerror.format(w=observedword)}]
		return json.dumps(returnarray)

	isgreek = True
	if re.search(r'[a-z]', cleanedword[0]):
		cleanedword = stripaccents(cleanedword)
		isgreek = False

	# a collection of HTML items that the JS will just dump out later; i.e. a sort of pseudo-page
	returnarray = list()

	morphologyobject = lookformorphologymatches(cleanedword, dbcursor)
	# print('findbyform() mm',morphologyobject.getpossible()[0].transandanal)
	# φέρεται --> morphologymatches [('<possibility_1>', '1', 'φέρω', '122883104', '<transl>fero</transl><analysis>pres ind mp 3rd sg</analysis>')]

	if morphologyobject:
		if hipparchia.config['SHOWGLOBALWORDCOUNTS'] == 'yes':
			returnarray.append(getobservedwordprevalencedata(cleanedword))
		returnarray += multiplelexicalmatchesintohtml(morphologyobject)
	else:
		if isgreek and not session['available']['greek_morphology']:
			returnarray = [
				{'value': dberror.format(lang='Greek')},
				{'entries': '[not found]'}
			]
		elif not isgreek and not session['available']['latin_morphology']:
			returnarray = [
				{'value': dberror.format(lang='Latin')},
				{'entries': '[not found]'}
			]
		else:
			returnarray = [
				{'value': notfounderror.format(cw=cleanedword)},
				{'entries': '[not found]'}
			]

		prev = {'value': getobservedwordprevalencedata(cleanedword)}
		if not prev:
			prev = {'value': getobservedwordprevalencedata(retainedgravity)}
		if not prev:
			prev = {'value': nodataerror.format(w=retainedgravity)}
		returnarray.append(prev)

	returnarray = [r for r in returnarray if r]

	returnarray = [{'observed': cleanedword}] + returnarray

	returnarray = json.dumps(returnarray)

	dbconnection.connectioncleanup()

	return returnarray


@hipparchia.route('/reverselookup/<searchterm>')
def reverselexiconsearch(searchterm):
	"""
	attempt to find all of the greek/latin dictionary entries that might go with the english search term

	'ape' will drive this crazy; what is needed is a lookup for only the senses

	this can be built into the dictionary via beautiful soup

	:return:
	"""

	probeforsessionvariables()

	returnarray = list()

	seeking = depunct(searchterm)

	if justlatin():
		searchunder = [('latin', 'hi')]
	elif justtlg():
		searchunder = [('greek', 'tr')]
	else:
		searchunder = [('greek', 'tr'), ('latin', 'hi')]

	limit = hipparchia.config['CAPONDICTIONARYFINDS']

	entries = list()
	for s in searchunder:
		usedict = s[0]
		translationlabel = s[1]
		# first see if your term is mentioned at all
		wordobjects = searchdbforlexicalentry(seeking, usedict, limit)
		entries += [w.entry for w in wordobjects]

	if len(entries) == limit:
		returnarray.append({'value': '[stopped searching after {lim} finds]'.format(lim=limit)})

	entries = list(set(entries))

	# we have the matches; now we will sort them either by frequency or by initial letter
	if hipparchia.config['REVERSELEXICONRESULTSBYFREQUENCY'] == 'yes':
		unsortedentries = [(querytotalwordcounts(e), e) for e in entries]
		entries = list()
		for e in unsortedentries:
			hwcountobject = e[0]
			term = e[1]
			if hwcountobject:
				entries.append((hwcountobject.t, term))
			else:
				entries.append((0, term))
		entries = sorted(entries, reverse=True)
		entries = [e[1] for e in entries]
	else:
		entries = polytonicsort(entries)
	# now we retrieve and format the entries
	if entries:
		# summary of entry values first
		countobjectdict = {e: querytotalwordcounts(e) for e in entries}
		summary = list()
		count = 0
		for c in countobjectdict.keys():
			count += 1
			try:
				totalhits = countobjectdict[c].t
			except:
				totalhits = 0
			summary.append((count, c, totalhits))

		summary = sorted(summary, key=lambda x: x[2], reverse=True)
		summary = ['<span class="sensesum">({n})&nbsp;{w} <span class="small">({t:,})</span></span><br />'.format(n=e[0], w=e[1], t=e[2]) for e in summary]
		# summary = ['<p class="dictionaryheading">{w}</p>'.format(w=seeking)] + summary
		returnarray.append({'value': '\n'.join(summary)})

		# then the entries proper
		count = 0
		for entry in entries:
			count += 1
			returnarray.append({'value': dictonaryentryashtml(count, entry)})
	else:
		returnarray.append({'value': '<br />[nothing found under "{skg}"]'.format(skg=seeking)})

	returnarray = json.dumps(returnarray)

	return returnarray
