# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re
import threading
import time

try:
	from rich import print
except ImportError:
	pass

from flask import request, session

from server import hipparchia
from server.authentication.authenticationwrapper import requireauthentication
from server.formatting.bracketformatting import gtltsubstitutes
from server.formatting.jsformatting import insertbrowserclickjs
from server.listsandsession.searchlistintosql import substringsearchintosqldict, rewritesqlsearchdictforlemmata, rawdsqldispatcher
from server.formatting.miscformatting import validatepollid, consolewarning
from server.formatting.searchformatting import buildresultobjects, flagsearchterms, htmlifysearchfinds, \
	nocontexthtmlifysearchfinds
from server.formatting.wordformatting import universalregexequivalent, wordlistintoregex
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.hipparchiaobjects.searchobjects import SearchOutputObject, SearchObject
from server.listsandsession.searchlistmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions, \
	sortresultslist
from server.listsandsession.checksession import probeforsessionvariables
from server.listsandsession.whereclauses import configurewhereclausedata
from server.searching.searchdispatching import searchdispatcher
from server.searching.searchfunctions import buildsearchobject, cleaninitialquery
from server.startup import authordict, listmapper, progresspolldict, workdict, lemmatadict
from server.threading.websocketthread import startwspolling

if hipparchia.config['SEMANTICVECTORSENABLED']:
	from server.semanticvectors.vectorroutehelperfunctions import findabsolutevectorsfromhits
else:
	voff = lambda x: 'vectors have not been enabled in your configuration file'
	findabsolutevectorsfromhits = voff

JSON_STR = str


@hipparchia.route('/search/<action>/<one>', methods=['GET'])
@hipparchia.route('/search/<action>/<one>/<two>')
@requireauthentication
def searchgetter(action: str, one=None, two=None) -> JSON_STR:
	"""

	dispatcher for "/search/..." requests

	"""

	# note the input validation should be handled elsewhere
	# one = depunct(one)
	# two = depunct(two)

	knownfunctions = {'standard':
							{'fnc': executesearch, 'param': [one, None, request]},
						'singleword':
							{'fnc': singlewordsearch, 'param': [one, two]},
						'lemmatized':
							{'fnc': headwordsearch, 'param': [one, two]},
						'confirm':
							{'fnc': checkforactivesearch, 'param': [one]},
						}

	if action not in knownfunctions:
		return json.dumps(str())

	f = knownfunctions[action]['fnc']
	p = knownfunctions[action]['param']

	j = f(*p)

	if hipparchia.config['JSONDEBUGMODE']:
		print('/search/{f}\n\t{j}'.format(f=action, j=j))

	return j


def executesearch(searchid: str, so=None, req=request) -> JSON_STR:
	"""

	the interface to all of the other search functions

	tell me what you are looking for and i'll try to find it

	the results are returned in a json bundle that will be used to update the html on the page

	note that cosdistbysentence vector queries also flow through here: they need a hitdict

	overview:
		buildsearchobject() and then start modifying elements of the SearchObject

		build a search list via compilesearchlist()
			modify search list via flagexclusions()
			modify search list via calculatewholeauthorsearches()
		build search list restrictions via indexrestrictions()

		search via searchdispatcher()

		format results via buildresultobjects()

	:return:
	"""

	pollid = validatepollid(searchid)

	if not so:
		# there is a so if singlewordsearch() sent you here
		probeforsessionvariables()
		so = buildsearchobject(pollid, req, session)

	frozensession = so.session

	phrasefinder = re.compile(r'[^\s]\s[^\s]')

	progresspolldict[pollid] = ProgressPoll(pollid)
	activepoll = progresspolldict[pollid]

	activepoll.activate()
	activepoll.statusis('Preparing to search')
	so.poll = activepoll

	searchlist = list()
	nosearch = True
	output = SearchOutputObject(so)

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if frozensession[c]]

	if (len(so.seeking) > 0 or so.lemma or frozensession['tensorflowgraph'] or frozensession['topicmodel']) and activecorpora:
		activepoll.statusis('Compiling the list of works to search')
		searchlist = compilesearchlist(listmapper, frozensession)

	if len(searchlist) > 0:
		nosearch = False
		skg = None
		prx = None
		# mark works that have passage exclusions associated with them:
		# gr0001x001 instead of gr0001w001 if you are skipping part of w001
		searchlist = flagexclusions(searchlist, frozensession)
		workssearched = len(searchlist)

		activepoll.statusis('Calculating full authors to search')

		searchlist = calculatewholeauthorsearches(searchlist, authordict)

		so.searchlist = searchlist
		so.usedcorpora = so.wholecorporasearched()

		activepoll.statusis('Configuring the search restrictions')
		so.indexrestrictions = configurewhereclausedata(searchlist, workdict, so)

		# fork over to the associative vectors framework if that option we checked
		# return the data derived therefrom instead of "search result" data

		isgreek = re.compile('[α-ωἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]')

		if so.lemma:
			so.termone = wordlistintoregex(so.lemma.formlist)
			skg = so.termone
			if re.search(isgreek, skg):
				# 'v' is a problem because the lemmata list is going to send 'u'
				# but the greek lemmata are accented
				so.usecolumn = 'accented_line'

		if so.proximatelemma:
			so.termtwo = wordlistintoregex(so.proximatelemma.formlist)
			prx = so.termtwo
			if re.search(isgreek, prx):
				so.usecolumn = 'accented_line'

		if so.lemma and not (so.proximatelemma or so.proximate):
			# print('executesearch(): b - simplelemma')
			so.searchtype = 'simplelemma'
			so.usewordlist = 'polytonic'
			thesearch = 'all forms of »{skg}«'.format(skg=so.lemma.dictionaryentry)
			htmlsearch = 'all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.lemma.formlist), skg=so.lemma.dictionaryentry)
		elif so.lemma and so.proximatelemma:
			# print('executesearch(): c - proximity of lemma to lemma')
			so.searchtype = 'proximity'
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=so.lemma.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=so.proximatelemma.dictionaryentry)
			htmlsearch = 'all {n} known forms of <span class="sought">»{skg}«</span>{ns} within {sp} {sc} of all {pn} known forms of <span class="sought">»{pskg}«</span>'
			htmlsearch = htmlsearch.format(n=len(so.lemma.formlist), skg=so.lemma.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pn=len(so.proximatelemma.formlist), pskg=so.proximatelemma.dictionaryentry)
		elif (so.lemma or so.proximatelemma) and (so.seeking or so.proximate):
			# print('executesearch(): d - proximity of lemma to word')
			so.searchtype = 'proximity'
			if so.lemma:
				lm = so.lemma
				t = so.originalproximate
			else:
				lm = so.proximatelemma
				t = so.seeking
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=lm.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=t)
			htmlsearch = 'all {n} known forms of <span class="sought">»{skg}«</span>{ns} within {sp} {sc} of <span class="sought">»{pskg}«</span>'
			htmlsearch = htmlsearch.format(n=len(lm.formlist), skg=lm.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pskg=t)
		elif len(so.proximate) < 1 and re.search(phrasefinder, so.seeking) is None:
			# print('executesearch(): e - basic wordsearch')
			so.searchtype = 'simple'
			thesearch = so.originalseeking
			htmlsearch = '<span class="sought">»{skg}«</span>'.format(skg=so.originalseeking)
		elif re.search(phrasefinder, so.seeking):
			# print('executesearch(): f - phrase search')
			so.searchtype = 'phrase'
			thesearch = so.originalseeking
			htmlsearch = '<span class="sought">»{skg}«</span>'.format(skg=so.originalseeking)
		else:
			# print('executesearch(): g - proximity of two terms')
			so.searchtype = 'proximity'
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=so.originalseeking, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=so.originalproximate)
			htmlsearch = '<span class="sought">»{skg}«</span>{ns} within {sp} {sc} of <span class="sought">»{pr}«</span>'
			htmlsearch = htmlsearch.format(skg=so.originalseeking, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=so.originalproximate)

		# DEBUGGING AREA BEGINS
		# print('searchlist', searchlist)
		# so.searchsqldict = substringsearchintosqldict(so)
		# if so.searchtype == 'simplelemma':
		# 	so.searchsqldict = rewritesqlsearchdictforlemmata(so)
		# print('substringsearchintosqldict()', so.searchsqldict)
		# searchdispatcher = rawdsqldispatcher
		# DEBUGGING AREA ENDS

		# now that the SearchObject is built, do the search...
		hits = searchdispatcher(so)
		activepoll.statusis('Putting the results in context')

		# hits [<server.hipparchiaclasses.dbWorkLine object at 0x10d952da0>, <server.hipparchiaclasses.dbWorkLine object at 0x10d952c50>, ... ]
		hitdict = sortresultslist(hits, so, authordict, workdict)

		if so.vectorquerytype == 'cosdistbylineorword':
			# print('executesearch(): h - cosdistbylineorword')
			# take these hits and head on over to the vector worker
			output = findabsolutevectorsfromhits(so, hitdict, workssearched)
			del progresspolldict[pollid]
			return output

		resultlist = buildresultobjects(hitdict, authordict, workdict, so)

		activepoll.statusis('Converting results to HTML')

		failtext = """
		<br>
		<pre>
		Search Failed: an invalid regular expression is present in
		
			{x}
			
		check for unbalanced parentheses, etc.</pre>
		"""

		if not skg:
			try:
				skg = re.compile(universalregexequivalent(so.termone))
			except re.error:
				skg = 're.error: BAD REGULAR EXPRESSION'
				htmlsearch = htmlsearch + failtext.format(x=so.termone)
		else:
			# 'doloreq[uv]e' will turn into 'doloreq[[UVuv]v]e' if you don't debracket
			skg = re.sub(r'\[uv\]', 'u', skg)
			skg = re.sub(r'u', '[UVuv]', skg)
			skg = re.sub(r'i', '[IJij]', skg)

		if not prx and so.proximate != '' and so.searchtype == 'proximity':
			try:
				prx = re.compile(universalregexequivalent(so.termtwo))
			except re.error:
				prx = 're.error: BAD REGULAR EXPRESSION'
				htmlsearch = htmlsearch + failtext.format(x=so.termtwo)
		elif prx:
			prx = re.sub(r'\[uv\]', 'u', prx)
			prx = re.sub(r'u', '[UVuv]', prx)
			prx = re.sub(r'i', '[IJij]', prx)

		if so.lemma:
			# clean out the whitespace/start/stop checks
			skg = re.sub(r'\(\^\|\\s\)', str(), skg)
			skg = re.sub(r'\(\\s\|\$\)', str(), skg)

		if so.proximatelemma:
			prx = re.sub(r'\(\^\|\\s\)', str(), prx)
			prx = re.sub(r'\(\\s\|\$\)', str(), prx)

		for r in resultlist:
			r.lineobjects = flagsearchterms(r, skg, prx, so)

		if so.context > 0:
			findshtml = htmlifysearchfinds(resultlist, so)
		else:
			findshtml = nocontexthtmlifysearchfinds(resultlist)

		if hipparchia.config['INSISTUPONSTANDARDANGLEBRACKETS']:
			findshtml = gtltsubstitutes(findshtml)

		findsjs = insertbrowserclickjs('browser')

		resultcount = len(resultlist)

		if resultcount < so.cap:
			hitmax = False
		else:
			hitmax = True

		output.title = thesearch
		output.found = findshtml
		output.js = findsjs
		output.setresultcount(resultcount, 'passages')
		output.setscope(workssearched)
		output.searchtime = so.getelapsedtime()
		output.thesearch = thesearch
		output.htmlsearch = htmlsearch
		output.hitmax = hitmax

	if nosearch:
		if not activecorpora:
			output.reasons.append('there are no active databases')
		if len(so.seeking) == 0:
			output.reasons.append('there is no search term')
		if len(so.seeking) > 0 and len(searchlist) == 0:
			output.reasons.append('zero works match the search criteria')

		output.title = '(empty query)'
		output.setresultcount(0, 'passages')
		output.explainemptysearch()

	activepoll.deactivate()
	jsonoutput = json.dumps(output.generateoutput())

	del progresspolldict[pollid]

	return jsonoutput


def singlewordsearch(searchid, searchterm) -> JSON_STR:
	"""

	you get sent here via the morphology tables

	this is a restricted version of executesearch(): single, exact term

	WINDOWS ONLY ERROR: this function will trigger a recursion error

	the situation looks a lot like case #3 @ https://bugs.python.org/issue9592

	but that is supposed to be a closed bug

	cf the complaints at https://forums.fast.ai/t/recursion-error-fastai-v1-0-27-windows-10/30673/10

	"multiprocessing\popen_spawn_win32.py" is the culprit?

	the current 'solution' is to send things to executesearch() instead "if osname == 'nt'"
	this test is inside morphologychartjs(); this is a potential source of future brittleness
	to the extent that one wants to explore refactoring executesearch()

	:param searchid:
	:param searchterm:
	:return:
	"""

	probeforsessionvariables()

	pollid = validatepollid(searchid)
	searchterm = cleaninitialquery(searchterm)
	seeking = ' {s} '.format(s=searchterm)
	proximate = str()
	lemma = str()
	proximatelemma = str()

	so = SearchObject(pollid, seeking, proximate, lemma, proximatelemma, session)

	jsonoutput = executesearch(pollid, so)

	return jsonoutput


def headwordsearch(searchid, headform) -> JSON_STR:
	"""

	you get sent here via the morphology tables

	this is a restricted version of executesearch(): a dictionary headword

	:param searchid:
	:param headform:
	:return:
	"""

	probeforsessionvariables()
	inputlemma = cleaninitialquery(headform)

	try:
		lemma = lemmatadict[inputlemma]
	except KeyError:
		lemma = None

	pollid = validatepollid(searchid)
	seeking = str()
	proximate = str()

	proximatelemma = str()

	so = SearchObject(pollid, seeking, proximate, lemma, proximatelemma, session)

	jsonoutput = executesearch(pollid, so)

	return jsonoutput


def checkforactivesearch(searchid, trialnumber=0) -> JSON_STR:
	"""

	test the activity of a poll so you don't start conjuring a bunch of key errors if you use wscheckpoll() prematurely

	note that uWSGI does not look like it will ever be able to work with the polling: poll[ts].getactivity() will
	never return anything because the processing and threading of uWSGI means that the poll is not going
	to be available to the instance; redis, vel. sim could fix this, but that's a lot of trouble to go to

	at a minimum you can count on uWSGI giving you a KeyError when you ask for poll[ts]

	:param searchid:
	:return:
	"""

	maxtrials = 4
	trialnumber = trialnumber + 1

	pollid = validatepollid(searchid)
	pollport = hipparchia.config['PROGRESSPOLLDEFAULTPORT']

	if trialnumber >= maxtrials:
		# note that very short searches can trigger this: rare word in a small author, etc.
		w = 'checkforactivesearch() cannot find the poll for {p} after {t} tries'
		consolewarning(w.format(p=pollid, t=trialnumber), color='magenta')
		return json.dumps('cannot_find_the_poll')

	activethreads = [t.name for t in threading.enumerate()]
	if 'websocketpoll' not in activethreads:
		pollstart = threading.Thread(target=startwspolling, name='websocketpoll', args=())
		pollstart.start()

	if hipparchia.config['EXTERNALWSGI'] and hipparchia.config['POLLCONNECTIONTYPE'] == 'redis':
		return externalwsgipolling(pollid)

	try:
		if progresspolldict[pollid].getactivity():
			return json.dumps(pollport)
	except KeyError:
		time.sleep(.10)
		return checkforactivesearch(searchid, trialnumber)


def externalwsgipolling(pollid) -> JSON_STR:
	"""

	polls can make it through WGSI; the real problem are the threads

	so ignore the problem...

	:param pollid:
	:return:
	"""

	time.sleep(.10)
	pollport = hipparchia.config['UWSGIPOLLPORT']

	# the following is just to get feedback when debugging...
	# keep keytypes in sync with "progresspoll.py" and RedisProgressPoll()

	# keytypes = {'launchtime': float,
	#             'portnumber': int,
	#             'active': bytes,
	#             'remaining': int,
	#             'poolofwork': int,
	#             'statusmessage': bytes,
	#             'hitcount': int,
	#             'notes': bytes}
	#
	# mykey = 'active'
	#
	# c = establishredisconnection()
	# c.set_response_callback('GET', keytypes[mykey])
	# storedkey = '{id}_{k}'.format(id=pollid, k=mykey)
	# try:
	# 	response = c.get(storedkey)
	# except TypeError:
	# 	# TypeError: cannot convert 'NoneType' object to bytes
	# 	response = b'no response'
	# print('response', response)

	return json.dumps(pollport)