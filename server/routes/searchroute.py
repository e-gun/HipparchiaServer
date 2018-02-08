# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import locale
import re
import time

from flask import request, session

from server import hipparchia
from server.formatting.bibliographicformatting import bcedating
from server.formatting.bracketformatting import gtltsubstitutes
from server.formatting.jsformatting import insertbrowserclickjs
from server.formatting.searchformatting import buildresultobjects, flagsearchterms, htmlifysearchfinds, \
	nocontexthtmlifysearchfinds
from server.formatting.wordformatting import universalregexequivalent, wordlistintoregex
from server.hipparchiaobjects.helperobjects import ProgressPoll
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions, \
	sortresultslist
from server.listsandsession.sessionfunctions import justlatin
from server.listsandsession.whereclauses import configurewhereclausedata
from server.routes.vectorroutes import findlatentsemanticindex, findvectorsbysentence, findvectorsfromhits
from server.searching.searchdispatching import searchdispatcher
from server.searching.searchfunctions import buildsearchobject
from server.startup import authordict, listmapper, poll, workdict


@hipparchia.route('/executesearch/<timestamp>', methods=['GET'])
def executesearch(timestamp):
	"""
	the interface to all of the other search functions
	tell me what you are looking for and i'll try to find it

	the results are returned in a json bundle that will be used to update the html on the page

	:return:
	"""

	starttime = time.time()

	try:
		ts = str(int(timestamp))
	except ValueError:
		ts = str(int(time.time()))

	so = buildsearchobject(ts, request, session)

	frozensession = so.session

	phrasefinder = re.compile('[^\s]\s[^\s]')

	poll[ts] = ProgressPoll(ts)
	activepoll = poll[ts]
	activepoll.activate()
	activepoll.statusis('Preparing to search')

	searchlist = list()
	output = ''
	nosearch = True

	dmin, dmax = bcedating(frozensession)
	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if frozensession[c] == 'yes']

	if (len(so.seeking) > 0 or so.lemma) and activecorpora:
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
		activepoll.statusis('Configuring the search restrictions')
		indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
		so.indexrestrictions = indexrestrictions

		# fork over to the associative vectors framework if that option we checked
		# return the data derived therefrom instead of "search result" data

		isgreek = re.compile('[α-ωἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]')

		if frozensession['cosdistbysentence'] == 'yes':
			# print('cosdistbysentence')
			so.proximate = ''
			so.proximatelemma = ''
			output = findvectorsbysentence(activepoll, so)
			del poll[ts]
			return output

		if frozensession['semanticvectorquery'] == 'yes':
			output = findlatentsemanticindex(activepoll, so)
			del poll[ts]
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
			# print('executesearch(): a')
			so.searchtype = 'simplelemma'
			so.usewordlist = 'polytonic'
			thesearch = 'all forms of »{skg}«'.format(skg=so.lemma.dictionaryentry)
			htmlsearch = 'all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.lemma.formlist), skg=so.lemma.dictionaryentry)
		elif so.lemma and so.proximatelemma:
			# print('executesearch(): b')
			so.searchtype = 'proximity'
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=so.lemma.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=so.proximatelemma.dictionaryentry)
			htmlsearch = 'all {n} known forms of <span class="sought">»{skg}«</span>{ns} within {sp} {sc} of all {pn} known forms of <span class="sought">»{pskg}«</span>'.format(
				n=len(so.lemma.formlist), skg=so.lemma.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pn=len(so.proximatelemma.formlist), pskg=so.proximatelemma.dictionaryentry
			)
		elif (so.lemma or so.proximatelemma) and (so.seeking or so.proximate):
			# print('executesearch(): c')
			so.searchtype = 'proximity'
			if so.lemma:
				lm = so.lemma
				t = so.proximate
			else:
				lm = so.proximatelemma
				t = so.seeking
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=lm.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=t)
			htmlsearch = 'all {n} known forms of <span class="sought">»{skg}«</span>{ns} within {sp} {sc} of <span class="sought">»{pskg}«</span>'.format(
				n=len(lm.formlist), skg=lm.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pskg=t
			)
		elif len(so.proximate) < 1 and re.search(phrasefinder, so.seeking) is None:
			# print('executesearch(): d')
			so.searchtype = 'simple'
			thesearch = so.originalseeking
			htmlsearch = '<span class="sought">»{skg}«</span>'.format(skg=so.originalseeking)
		elif re.search(phrasefinder, so.seeking):
			# print('executesearch(): e')
			so.searchtype = 'phrase'
			thesearch = so.originalseeking
			htmlsearch = '<span class="sought">»{skg}«</span>'.format(skg=so.originalseeking)
		else:
			# print('executesearch(): f')
			so.searchtype = 'proximity'
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=so.originalseeking, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=so.proximate)
			htmlsearch = '<span class="sought">»{skg}«</span>{ns} within {sp} {sc} of <span class="sought">»{pr}«</span>'.format(
				skg=so.originalseeking, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=so.proximate)

		hits = searchdispatcher(so, activepoll)
		activepoll.statusis('Putting the results in context')

		# hits [<server.hipparchiaclasses.dbWorkLine object at 0x10d952da0>, <server.hipparchiaclasses.dbWorkLine object at 0x10d952c50>, ... ]
		hitdict = sortresultslist(hits, so, authordict, workdict)

		if frozensession['cosdistbylineorword'] == 'yes':
			# print('cosdistbylineorword')
			# take these hits and head on over to the vector worker
			output = findvectorsfromhits(so, hitdict, activepoll, starttime, workssearched)
			del poll[ts]
			return output

		resultlist = buildresultobjects(hitdict, authordict, workdict, so, activepoll)

		activepoll.statusis('Converting results to HTML')

		if not skg:
			skg = re.compile(universalregexequivalent(so.termone))
		else:
			skg = re.sub(r'u', '[UVuv]', skg)
			skg = re.sub(r'i', '[IJij]', skg)

		if not prx and so.proximate != '' and so.searchtype == 'proximity':
			prx = re.compile(universalregexequivalent(so.termtwo))
		elif prx:
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
			hitmax = 'false'
		else:
			hitmax = 'true'

		# prepare the output
		searchtime = time.time() - starttime
		searchtime = round(searchtime, 2)

		sortorderdecoder = {
			'universalid': 'ID',
			'shortname': 'name',
			'genres': 'author genre',
			'converted_date': 'date',
			'location': 'location'
		}
		try:
			locale.setlocale(locale.LC_ALL, 'en_US')
		except locale.Error:
			pass

		resultcount = locale.format('%d', resultcount, grouping=True)
		workssearched = locale.format('%d', workssearched, grouping=True)

		output = dict()
		output['title'] = thesearch
		output['found'] = findshtml
		output['js'] = findsjs
		output['resultcount'] = '{r} passages'.format(r=resultcount)
		output['scope'] = workssearched
		output['searchtime'] = str(searchtime)
		output['proximate'] = so.proximate
		output['thesearch'] = thesearch
		output['htmlsearch'] = htmlsearch
		output['hitmax'] = hitmax
		output['onehit'] = frozensession['onehit']
		output['sortby'] = sortorderdecoder[frozensession['sortorder']]
		output['dmin'] = dmin
		output['dmax'] = dmax
		if justlatin() is False:
			output['icandodates'] = 'yes'
		else:
			output['icandodates'] = 'no'
		activepoll.deactivate()

	if nosearch:
		reasons = list()
		if not activecorpora:
			reasons.append('there are no active databases')
		if len(so.seeking) == 0:
			reasons.append('there is no search term')
		if len(so.seeking) > 0 and len(searchlist) == 0:
			reasons.append('zero works match the search criteria')
		output = dict()
		output['title'] = '(empty query)'
		output['found'] = ''
		output['resultcount'] = '0 passages'
		output['scope'] = 0
		output['searchtime'] = '0.00'
		output['proximate'] = so.proximate
		output['thesearch'] = ''
		output['htmlsearch'] = '<span class="emph">nothing</span> (search not executed because {r})'.format(r=' and '.join(reasons))
		output['hitmax'] = 0
		output['dmin'] = dmin
		output['dmax'] = dmax
		if justlatin() is False:
			output['icandodates'] = 'yes'
		else:
			output['icandodates'] = 'no'
		output['sortby'] = frozensession['sortorder']
		output['onehit'] = frozensession['onehit']

	output = json.dumps(output)

	del poll[ts]

	return output
