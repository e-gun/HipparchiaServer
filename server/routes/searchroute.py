# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import re

from flask import request, session

from server import hipparchia
from server.formatting.bracketformatting import gtltsubstitutes
from server.formatting.jsformatting import insertbrowserclickjs
from server.formatting.miscformatting import validatepollid
from server.formatting.searchformatting import buildresultobjects, flagsearchterms, htmlifysearchfinds, \
	nocontexthtmlifysearchfinds
from server.formatting.wordformatting import universalregexequivalent, wordlistintoregex
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.hipparchiaobjects.searchobjects import SearchOutputObject
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions, \
	sortresultslist
from server.listsandsession.whereclauses import configurewhereclausedata
from server.searching.searchdispatching import searchdispatcher
from server.searching.searchfunctions import buildsearchobject
if hipparchia.config['SEMANTICVECTORSENABLED'] == 'yes':
	from server.semanticvectors.gensimvectors import executegensimsearch
	from server.semanticvectors.scikitlearntopics import sklearnselectedworks
	from server.semanticvectors.vectorpseudoroutes import findabsolutevectorsbysentence, findabsolutevectorsfromhits
else:
	executegensimsearch = None
	sklearnselectedworks = None
	findabsolutevectorsbysentence = None
	findabsolutevectorsfromhits = None
from server.startup import authordict, listmapper, poll, workdict


@hipparchia.route('/executesearch/<searchid>', methods=['GET'])
def executesearch(searchid):
	"""
	the interface to all of the other search functions
	tell me what you are looking for and i'll try to find it

	the results are returned in a json bundle that will be used to update the html on the page

	note that vector queries also flow through here

	:return:
	"""

	pollid = validatepollid(searchid)

	so = buildsearchobject(pollid, request, session)

	frozensession = so.session

	phrasefinder = re.compile(r'[^\s]\s[^\s]')

	poll[pollid] = ProgressPoll(pollid)
	activepoll = poll[pollid]
	activepoll.activate()
	activepoll.statusis('Preparing to search')
	so.poll = activepoll

	searchlist = list()
	nosearch = True
	output = SearchOutputObject(so)

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if frozensession[c] == 'yes']

	if (len(so.seeking) > 0 or so.lemma or frozensession['tensorflowgraph'] == 'yes' or frozensession['topicmodel'] == 'yes') and activecorpora:
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

		so.vectorquerytype = so.infervectorquerytype()

		# note that cosdistbylineorword requires a hitdict and so has to come later
		vectorfunctions = {'cosdistbysentence': findabsolutevectorsbysentence,
		                   'semanticvectorquery': executegensimsearch,
		                   'nearestneighborsquery': executegensimsearch,
		                   'topicmodel': sklearnselectedworks}

		# for TESTING purposes rewrite one of the definitions
		# vectorfunctions['tensorflowgraph'] = gensimexperiment

		if so.vectorquerytype in vectorfunctions:
			# print('executesearch(): a - vectorquery ({t})'.format(t=so.vectorquerytype))
			fnc = vectorfunctions[so.vectorquerytype]
			output = fnc(so)
			del poll[pollid]
			return output

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
			# print('executesearch(): d - procimity of lemma to word')
			so.searchtype = 'proximity'
			if so.lemma:
				lm = so.lemma
				t = so.proximate
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
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=so.originalseeking, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=so.proximate)
			htmlsearch = '<span class="sought">»{skg}«</span>{ns} within {sp} {sc} of <span class="sought">»{pr}«</span>'
			htmlsearch = htmlsearch.format(skg=so.originalseeking, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=so.proximate)

		hits = searchdispatcher(so)
		activepoll.statusis('Putting the results in context')

		# hits [<server.hipparchiaclasses.dbWorkLine object at 0x10d952da0>, <server.hipparchiaclasses.dbWorkLine object at 0x10d952c50>, ... ]
		hitdict = sortresultslist(hits, so, authordict, workdict)

		if so.vectorquerytype == 'cosdistbylineorword':
			# print('executesearch(): h - cosdistbylineorword')
			# take these hits and head on over to the vector worker
			output = findabsolutevectorsfromhits(so, hitdict, workssearched)
			del poll[pollid]
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
			skg = re.sub(r'\(\^\|\\s\)', '', skg)
			skg = re.sub(r'\(\\s\|\$\)', '', skg)

		if so.proximatelemma:
			prx = re.sub(r'\(\^\|\\s\)', '', prx)
			prx = re.sub(r'\(\\s\|\$\)', '', prx)

		for r in resultlist:
			r.lineobjects = flagsearchterms(r, skg, prx, so)

		if so.context > 0:
			findshtml = htmlifysearchfinds(resultlist, so)
		else:
			findshtml = nocontexthtmlifysearchfinds(resultlist)

		if hipparchia.config['INSISTUPONSTANDARDANGLEBRACKETS'] == 'yes':
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

	del poll[pollid]

	return jsonoutput
