# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

from flask import session

from server import hipparchia
from server.authentication.authenticationwrapper import requireauthentication
from server.commandlineoptions import getcommandlineargs
from server.dbsupport.lexicaldbfunctions import findentrybyid, headwordsearch, lookformorphologymatches, \
	probedictionary, querytotalwordcounts, reversedictionarylookup
from server.formatting.betacodetounicode import replacegreekbetacode
from server.formatting.jsformatting import dictionaryentryjs, insertlexicalbrowserjs, morphologychartjs
from server.formatting.lexicaformatting import getobservedwordprevalencedata
from server.formatting.miscformatting import consolewarning, validatepollid
from server.formatting.wordformatting import abbreviatedsigmarestoration, attemptsigmadifferentiation, depunct, \
	removegravity, stripaccents, tidyupterm
from server.formatting.wordformatting import setdictionarylanguage
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.lexicaloutputobjects import lexicalOutputObject, multipleWordOutputObject
from server.hipparchiaobjects.morphanalysisobjects import BaseFormMorphology
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.listsandsession.checksession import justlatin, justtlg, probeforsessionvariables
from server.listsandsession.genericlistfunctions import flattenlistoflists
from server.startup import authordict
from server.startup import progresspolldict

JSON_STR = str


@hipparchia.route('/dictsearch/<searchterm>')
@requireauthentication
def dictsearch(searchterm) -> JSON_STR:
	"""
	look up words
	return dictionary entries
	json packing
	:return:
	"""
	returndict = dict()

	searchterm = searchterm[:hipparchia.config['MAXIMUMLEXICALLENGTH']]
	probeforsessionvariables()

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	commandlineargs = getcommandlineargs()
	if commandlineargs.forceuniversalbetacode or hipparchia.config['UNIVERSALASSUMESBETACODE']:
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

	if re.search(r'[a-z]', seeking):
		usedictionary = 'latin'
		usecolumn = 'entry_name'
	else:
		usedictionary = 'greek'
		usecolumn = 'unaccented_entry'

	if not session['available'][usedictionary + '_dictionary']:
		returndict['newhtml'] = 'cannot look up {w}: {d} dictionary is not installed'.format(d=usedictionary, w=seeking)
		return json.dumps(returndict)

	if not session['available'][usedictionary + '_dictionary']:
		returndict['newhtml'] = 'cannot look up {w}: {d} dictionary is not installed'.format(d=usedictionary, w=seeking)
		return json.dumps(returndict)

	limit = hipparchia.config['CAPONDICTIONARYFINDS']

	foundtuples = headwordsearch(stripped, limit, usedictionary, usecolumn)

	# example:
	# results are presorted by ID# via the postgres query
	# foundentries [('scrofa¹', 43118), ('scrofinus', 43120), ('scrofipascus', 43121), ('Scrofa²', 43119), ('scrofulae', 43122)]

	returnlist = list()

	if len(foundtuples) == limit:
		returnlist.append('[stopped searching after {lim} finds]<br>'.format(lim=limit))

	if len(foundtuples) > 0:

		if len(foundtuples) == 1:
			# sending '0' to browserdictionarylookup() will hide the count number
			usecounter = False
		else:
			usecounter = True

		wordobjects = [probedictionary(setdictionarylanguage(f[0]) + '_dictionary', 'entry_name', f[0], '=', dbcursor=dbcursor, trialnumber=0) for f in foundtuples]
		wordobjects = flattenlistoflists(wordobjects)
		outputobjects = [lexicalOutputObject(w) for w in wordobjects]

		# very top: list the finds
		if usecounter:
			findstemplate = '({n})&nbsp;<a class="nounderline" href="#{w}_{wdid}">{w}</a>'
			findslist = [findstemplate.format(n=f[0]+1, w=f[1][0], wdid=f[1][1]) for f in enumerate(foundtuples)]
			returnlist.append('\n<br>\n'.join(findslist))

		# the actual entries
		count = 0
		for oo in outputobjects:
			count += 1
			if usecounter:
				entry = oo.generatelexicaloutput(countervalue=count)
			else:
				entry = oo.generatelexicaloutput()
			returnlist.append(entry)
	else:
		returnlist.append('[nothing found]')

	if session['zaplunates']:
		returnlist = [attemptsigmadifferentiation(x) for x in returnlist]
		returnlist = [abbreviatedsigmarestoration(x) for x in returnlist]

	returndict['newhtml'] = '\n'.join(returnlist)
	returndict['newjs'] = '\n'.join([dictionaryentryjs(), insertlexicalbrowserjs()])

	jsondict = json.dumps(returndict)

	dbconnection.connectioncleanup()

	return jsondict


@hipparchia.route('/parse/<observedword>')
@hipparchia.route('/parse/<observedword>/<authorid>')
@requireauthentication
def findbyform(observedword, authorid=None) -> JSON_STR:
	"""
	this function sets of a chain of other functions
	find dictionary form
	find the other possible forms
	look up the dictionary form
	return a formatted set of info
	:return:
	"""

	if authorid and authorid not in authordict:
		authorid = None

	observedword = observedword[:hipparchia.config['MAXIMUMLEXICALLENGTH']]

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

	# if hipparchia.config['UNIVERSALASSUMESBETACODE']:
	# 	observedword = replacegreekbetacode(observedword.upper())

	# the next makes sense only in the context of pointedly invalid input
	w = depunct(observedword)
	w = w.strip()
	w = tidyupterm(w)
	w = re.sub(r'[σς]', 'ϲ', w)

	# python seems to know how to do this with greek...
	w = w.lower()
	retainedgravity = w
	cleanedword = removegravity(retainedgravity)

	# index clicks will send you things like 'αὖ²'
	cleanedword = re.sub(r'[⁰¹²³⁴⁵⁶⁷⁸⁹]', str(), cleanedword)

	# the search syntax is '=' and not '~', so the next should be avoided unless a lot of refactoring will happen
	# cleanedword = re.sub(r'[uv]', r'[uv]', cleanedword)
	# cleanedword = re.sub(r'[ij]', r'[ij]', cleanedword)

	# a collection of HTML items that the JS will just dump out later; i.e. a sort of pseudo-page
	returndict = dict()

	try:
		cleanedword[0]
	except IndexError:
		returndict['newhtml'] = sanitationerror.format(w=observedword)
		return json.dumps(returndict)

	isgreek = True
	if re.search(r'[a-z]', cleanedword[0]):
		cleanedword = stripaccents(cleanedword)
		isgreek = False

	morphologyobject = lookformorphologymatches(cleanedword, dbcursor)
	# print('findbyform() mm',morphologyobject.getpossible()[0].transandanal)
	# φέρεται --> morphologymatches [('<possibility_1>', '1', 'φέρω', '122883104', '<transl>fero</transl><analysis>pres ind mp 3rd sg</analysis>')]

	if morphologyobject:
		oo = multipleWordOutputObject(cleanedword, morphologyobject, authorid)
		returndict['newhtml'] = oo.generateoutput()
	else:
		newhtml = list()
		if isgreek and not session['available']['greek_morphology']:
			newhtml.append(dberror.format(lang='Greek'))
		elif not isgreek and not session['available']['latin_morphology']:
			newhtml.append(dberror.format(lang='Latin'))
		else:
			newhtml.append(notfounderror.format(cw=cleanedword))

		prev = getobservedwordprevalencedata(cleanedword)
		if not prev:
			newhtml.append(getobservedwordprevalencedata(retainedgravity))
		if not prev:
			newhtml.append(nodataerror.format(w=retainedgravity))
		else:
			newhtml.append(prev)
		try:
			returndict['newhtml'] = '\n'.join(newhtml)
		except TypeError:
			returndict['newhtml'] = '[nothing found]'

	returndict['newjs'] = '\n'.join([dictionaryentryjs(), insertlexicalbrowserjs()])
	jsondict = json.dumps(returndict)

	dbconnection.connectioncleanup()

	return jsondict


@hipparchia.route('/reverselookup/<searchid>/<searchterm>')
@requireauthentication
def reverselexiconsearch(searchid, searchterm) -> JSON_STR:
	"""
	attempt to find all of the greek/latin dictionary entries that might go with the english search term

	'ape' will drive this crazy; what is needed is a lookup for only the senses

	this can be built into the dictionary

	:param searchid:
	:param searchterm:
	:return:
	"""

	searchterm = searchterm[:hipparchia.config['MAXIMUMLEXICALLENGTH']]
	pollid = validatepollid(searchid)
	progresspolldict[pollid] = ProgressPoll(pollid)
	activepoll = progresspolldict[pollid]
	activepoll.activate()
	activepoll.statusis('Search lexical entries for "{t}"'.format(t=searchterm))

	probeforsessionvariables()

	returndict = dict()
	returnarray = list()

	seeking = depunct(searchterm)

	if justlatin():
		searchunder = [('latin', 'hi')]
	elif justtlg():
		searchunder = [('greek', 'tr')]
	else:
		searchunder = [('greek', 'tr'), ('latin', 'hi')]

	limit = hipparchia.config['CAPONDICTIONARYFINDS']

	entriestuples = list()
	for s in searchunder:
		usedict = s[0]
		translationlabel = s[1]
		# first see if your term is mentioned at all
		wordobjects = reversedictionarylookup(seeking, usedict, limit)
		entriestuples += [(w.entry, w.id) for w in wordobjects]

	if len(entriestuples) == limit:
		returnarray.append('[stopped searching after {lim} finds]\n<br>\n'.format(lim=limit))

	entriestuples = list(set(entriestuples))

	unsortedentries = [(querytotalwordcounts(e[0]), e[0], e[1]) for e in entriestuples]
	entries = list()
	for e in unsortedentries:
		hwcountobject = e[0]
		term = e[1]
		idval = e[2]
		if hwcountobject:
			entries.append((hwcountobject.t, term, idval))
		else:
			entries.append((0, term, idval))
	entries = sorted(entries, reverse=True)
	entriestuples = [(e[1], e[2]) for e in entries]

	# now we retrieve and format the entries
	if entriestuples:
		# summary of entry values first
		countobjectdict = {e: querytotalwordcounts(e[0]) for e in entriestuples}
		summary = list()
		count = 0
		for c in countobjectdict.keys():
			count += 1
			try:
				totalhits = countobjectdict[c].t
			except:
				totalhits = 0
			# c[0]: the word; c[1]: the id
			summary.append((count, c[0], c[1], totalhits))

		summarytemplate = """
		<span class="sensesum">({n})&nbsp;
			<a class="nounderline" href="#{w}_{wdid}">{w}</a>&nbsp;
			<span class="small">({t:,})</span>
		</span>
		"""

		summary = sorted(summary, key=lambda x: x[3], reverse=True)
		summary = [summarytemplate.format(n=e[0], w=e[1], wdid=e[2], t=e[3]) for e in summary]
		returnarray.append('\n<br />\n'.join(summary))

		# then the entries proper
		dbconnection = ConnectionObject()
		dbconnection.setautocommit()
		dbcursor = dbconnection.cursor()

		wordobjects = [probedictionary(setdictionarylanguage(e[0]) + '_dictionary', 'entry_name', e[0], '=', dbcursor=dbcursor, trialnumber=0) for e in entriestuples]
		wordobjects = flattenlistoflists(wordobjects)
		outputobjects = [lexicalOutputObject(w) for w in wordobjects]
		if len(outputobjects) > 1:
			usecounter = True
		else:
			usecounter = False

		count = 0
		for oo in outputobjects:
			count += 1
			if usecounter:
				entry = oo.generatelexicaloutput(countervalue=count)
			else:
				entry = oo.generatelexicaloutput()
			returnarray.append(entry)
	else:
		returnarray.append('<br />[nothing found under "{skg}"]'.format(skg=seeking))

	returndict['newhtml'] = '\n'.join(returnarray)
	returndict['newjs'] = '\n'.join([dictionaryentryjs(), insertlexicalbrowserjs()])

	jsondict = json.dumps(returndict)

	del progresspolldict[pollid]

	return jsondict


@hipparchia.route('/dictionaryidsearch/<language>/<entryid>')
@requireauthentication
def dictionaryidsearch(language, entryid) -> JSON_STR:
	"""

	fed by /morphologychart/

	:param language:
	:param entryid:
	:return:
	"""

	knownlanguages = ['greek', 'latin']
	if language not in knownlanguages:
		language = 'greek'

	try:
		entryid = str(float(entryid))
	except ValueError:
		entryid = None

	wordobject = findentrybyid(language, entryid)

	if wordobject:
		oo = lexicalOutputObject(wordobject)
		entry = oo.generatelexicaloutput()

		if session['zaplunates']:
			entry = attemptsigmadifferentiation(entry)
			entry = abbreviatedsigmarestoration(entry)
	else:
		entry = '[nothing found in {lg} lexicon at ID value {x}]'.format(lg=language, x=entryid)

	returndict = dict()
	returndict['newhtml'] = entry
	returndict['newjs'] = '\n'.join([dictionaryentryjs(), insertlexicalbrowserjs()])

	jsondict = json.dumps(returndict)

	return jsondict


@hipparchia.route('/morphologychart/<language>/<lexicalid>/<xrefid>/<headword>')
@requireauthentication
def knownforms(lexicalid, language, xrefid, headword) -> JSON_STR:
	"""

	display all known forms of...

	you are supposed to be sent here via the principle parts click from a lexical entry

	this means you have access to a BaseFormMorphology() object

	that is how/why you know the paramaters already

	:param xrefid:
	:return:
	"""

	# sanitize all input...

	headword = headword[:hipparchia.config['MAXIMUMLEXICALLENGTH']]

	knownlanguages = ['greek', 'latin']
	if language not in knownlanguages:
		language = 'greek'

	try:
		lexicalid = str(float(lexicalid))
	except ValueError:
		lexicalid = 'invalid_user_input'

	try:
		xrefid = str(int(xrefid))
	except ValueError:
		xrefid = 'invalid_user_input'

	headword = depunct(headword)
	headword = re.sub(r'[σς]', 'ϲ', headword)

	try:
		bfo = BaseFormMorphology(headword, xrefid, language, lexicalid, session)
	except:
		consolewarning('could not initialize BaseFormMorphology() object')
		return 'could not initialize BaseFormMorphology() object'

	# if this is active a click on the word will do a lemmatized lookup of it
	# topofoutput = """
	# <div class="center">
	# 	<span class="verylarge">All known forms of <lemmatizable headform="{w}">{w}</lemmatizable></span>
	# </div>
	# """

	# if this is active a clock on the word will return you to the dictionary entry for it
	topofoutput = """
	<div class="center">
		<span class="verylarge">All known forms of <dictionaryidsearch entryid="{eid}" language="{lg}">{w}</dictionaryidsearch></span>
	</div>
	"""

	returnarray = list()

	if bfo.iammostlyconjugated():
		returnarray.append(topofoutput.format(w=bfo.headword, eid=bfo.lexicalid, lg=bfo.language))
		returnarray = returnarray + bfo.buildhtmlverbtablerows(session)

	if bfo.iamdeclined():
		returnarray.append(topofoutput.format(w=bfo.headword, eid=bfo.lexicalid, lg=bfo.language))
		returnarray = returnarray + bfo.buildhtmldeclinedtablerows()

	returndict = dict()
	returndict['newhtml'] = '\n'.join(returnarray)
	returndict['newjs'] = morphologychartjs()

	if session['zaplunates']:
		returndict['newhtml'] = attemptsigmadifferentiation(returndict['newhtml'])
		returndict['newhtml'] = abbreviatedsigmarestoration(returndict['newhtml'])

	jsondict = json.dumps(returndict)

	return jsondict
