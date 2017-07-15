# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

from server import hipparchia
from server.dbsupport.dbfunctions import setconnection
from server.formatting.betacodetounicode import replacegreekbetacode
from server.formatting.wordformatting import removegravity, stripaccents, tidyupterm
from server.lexica.lexicalookups import browserdictionarylookup, lexicalmatchesintohtml, findtotalcounts, \
	lookformorphologymatches, getobservedwordprevalencedata, findtermamongsenses
from server.listsandsession.listmanagement import polytonicsort
from server.listsandsession.sessionfunctions import justlatin, justtlg


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

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	# the next is pointless because: 'po/lemon' will generate a URL '/parse/po/lemon'
	# that will 404 before you can get to replacegreekbetacode()
	# this is a bug in the interaction between Flask and the JS

	# if hipparchia.config['UNIVERSALASSUMESBETACODE'] == 'yes':
	# 	observedword = replacegreekbetacode(observedword.upper())

	w = re.sub('[\W_|]+', '', observedword)
	# oddly 'ὕβˈριν' survives the '\W' check; should be ready to extend this list
	w = tidyupterm(w)
	# python seems to know how to do this with greek...
	w = w.lower()
	retainedgravity = w
	cleanedword = removegravity(retainedgravity)
	# index clicks will send you things like 'αὖ²'
	cleanedword = re.sub(r'[⁰¹²³⁴⁵⁶⁷⁸⁹]','',cleanedword)

	try:
		cleanedword[0]
	except:
		returnarray = [{'value': '[empty search: {w} was sanitized into nothingness]'.format(w=observedword)}]
		return json.dumps(returnarray)

	if re.search(r'[a-z]', cleanedword[0]):
		cleanedword = stripaccents(cleanedword)

	cleanedword = cleanedword.lower()
	# a collection of HTML items that the JS will just dump out later; i.e. a sort of pseudo-page
	returnarray = []

	morphologyobject = lookformorphologymatches(cleanedword, cur)
	# print('findbyform() mm',morphologyobject.getpossible()[0].transandanal)
	# φέρεται --> morphologymatches [('<possibility_1>', '1', 'φέρω', '122883104', '<transl>fero</transl><analysis>pres ind mp 3rd sg</analysis>')]

	if morphologyobject:
		if hipparchia.config['SHOWGLOBALWORDCOUNTS'] == 'yes':
			returnarray.append(getobservedwordprevalencedata(cleanedword))
		returnarray += lexicalmatchesintohtml(cleanedword, morphologyobject, cur)
	else:
		returnarray = [
			{'value': '<br />[could not find a match for {cw} in the morphology table]'.format(cw=cleanedword)},
			{'entries': '[not found]'}
			]
		prev = getobservedwordprevalencedata(cleanedword)
		if not prev:
			prev = getobservedwordprevalencedata(retainedgravity)
		if not prev:
			prev = {'value': '[no prevalence data for {w}]'.format(w=retainedgravity)}
		returnarray.append(prev)

	returnarray = [r for r in returnarray if r]
	returnarray = [{'observed':cleanedword}] + returnarray
	returnarray = json.dumps(returnarray)

	cur.close()

	return returnarray


@hipparchia.route('/dictsearch/<searchterm>')
def dictsearch(searchterm):
	"""
	look up words
	return dictionary entries
	json packing
	:return:
	"""

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	if hipparchia.config['UNIVERSALASSUMESBETACODE'] == 'yes':
		searchterm = replacegreekbetacode(searchterm.upper())

	seeking = re.sub(r'[!@#$|%()*\'\"\[\]]', '', searchterm)
	seeking = seeking.lower()
	seeking = re.sub('[σς]', 'ϲ', seeking)
	seeking = re.sub('v', '(u|v|U|V)', seeking)

	if re.search(r'[a-z]', seeking):
		usedictionary = 'latin'
		usecolumn = 'entry_name'
	else:
		usedictionary = 'greek'
		usecolumn = 'unaccented_entry'

	seeking = stripaccents(seeking)
	query = 'SELECT entry_name FROM {d}_dictionary WHERE {c} ~* %s'.format(d=usedictionary,c=usecolumn)
	if seeking[0] == ' ' and seeking[-1] == ' ':
		data = ('^' + seeking[1:-1] + '$',)
	elif seeking[0] == ' ' and seeking[-1] != ' ':
		data = ('^' + seeking[1:] + '.*?',)
	else:
		data = ('.*?' + seeking + '.*?',)

	cur.execute(query, data)

	# note that the dictionary db has a problem with vowel lengths vs accents
	# SELECT * FROM greek_dictionary WHERE entry_name LIKE %s d ('μνᾱ/αϲθαι,μνάομαι',)
	try:
		found = cur.fetchall()
	except:
		found = []

	# the results should be given the polytonicsort() treatment
	returnarray = []

	if len(found) > 0:
		finddict = {f[0]:f for f in found}
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
			returnarray.append({'value': browserdictionarylookup(count, entry[0], cur)})
	else:
		returnarray.append({'value':'[nothing found]'})

	returnarray = json.dumps(returnarray)

	cur.close()

	return returnarray


@hipparchia.route('/reverselookup/<searchterm>')
def reverselexiconsearch(searchterm):
	"""
	attempt to find all of the greek/latin dictionary entries that might go with the english search term
	:return:
	"""

	dbc = setconnection('autocommit')
	cur = dbc.cursor()

	entries = []
	returnarray = []

	seeking = re.sub(r'[!@#$|%()*\'\"]', '', searchterm)

	if justlatin():
		searchunder = [('latin','hi')]
	elif justtlg():
		searchunder = [('greek', 'tr')]
	else:
		searchunder = [('greek', 'tr'), ('latin','hi')]

	for s in searchunder:
		usedict = s[0]
		translationlabel = s[1]

		# first see if your term is mentioned at all
		query = 'SELECT entry_name FROM {d}_dictionary WHERE entry_body LIKE %s'.format(d=usedict)
		data = ('%{s}%'.format(s=seeking),)
		cur.execute(query, data)

		matches = cur.fetchall()
		matches = [m[0] for m in matches]

		# then go back and see if it is mentioned in the summary of senses (and not just randomly present in the body)
		for match in matches:
			entries += findtermamongsenses(match, seeking, usedict, translationlabel, cur)

	entries = list(set(entries))

	# we have the matches; now we will sort them either by frequency or by initial letter
	if hipparchia.config['REVERSELEXICONRESULTSBYFREQUENCY'] == 'yes':
		unsortedentries = [(findtotalcounts(e, cur), e) for e in entries]
		entries = []
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
		count = 0
		for entry in entries:
			count += 1
			returnarray.append({'value': browserdictionarylookup(count, entry, cur)})
	else:
		returnarray.append({'value': '<br />[nothing found under "{skg}"]'.format(skg=seeking)})

	returnarray = json.dumps(returnarray)

	cur.close()

	return returnarray
