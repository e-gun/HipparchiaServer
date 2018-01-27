# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import locale
import re
import time

from flask import request, session

from server import hipparchia
from server.formatting.betacodetounicode import replacegreekbetacode
from server.formatting.bibliographicformatting import bcedating
from server.formatting.bracketformatting import gtltsubstitutes
from server.formatting.jsformatting import insertbrowserclickjs
from server.formatting.searchformatting import buildresultobjects, flagsearchterms, htmlifysearchfinds, \
	nocontexthtmlifysearchfinds
from server.formatting.wordformatting import universalregexequivalent, wordlistintoregex
from server.hipparchiaobjects.helperobjects import ProgressPoll, SearchObject
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions, \
	sortresultslist
from server.listsandsession.sessionfunctions import justlatin, justtlg, sessionvariables
from server.listsandsession.whereclauses import configurewhereclausedata
from server.routes.vectorroutes import findvectors
from server.searching.searchdispatching import searchdispatcher
from server.searching.searchfunctions import cleaninitialquery
from server.startup import authordict, lemmatadict, listmapper, poll, workdict


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
	except:
		ts = str(int(time.time()))


	sessionvariables()
	# fork over to the associative vectors fraework if that option we checked
	# return the data derived therefrom instead of "search result" data
	if session['cosinedistancesearch'] == 'yes':
		lemma = cleaninitialquery(request.args.get('lem', ''))
		seeking = cleaninitialquery(request.args.get('skg', ''))
		if len(lemma) > len(seeking):
			output = findvectors(lemma, vtype='lemma')
		else:
			output = findvectors(seeking, vtype='string')
		return output

	# a search can take 30s or more and the user might alter the session while the search is running
	# by toggling onehit, etc that can be a problem, so freeze the values now and rely on this instead
	# of some moving target
	frozensession = session.copy()

	# need to sanitize input at least a bit: remove digits and punctuation
	# dispatcher will do searchtermcharactersubstitutions() and massagesearchtermsforwhitespace() to take
	# care of lunate sigma, etc.

	seeking = cleaninitialquery(request.args.get('skg', ''))
	proximate = cleaninitialquery(request.args.get('prx', ''))
	lemma = cleaninitialquery(request.args.get('lem', ''))
	proximatelemma = cleaninitialquery(request.args.get('plm', ''))

	try:
		lemma = lemmatadict[lemma]
	except KeyError:
		lemma = None

	try:
		proximatelemma = lemmatadict[proximatelemma]
	except KeyError:
		proximatelemma = None

	replacebeta = False
	
	if hipparchia.config['UNIVERSALASSUMESBETACODE'] == 'yes' and re.search('[a-zA-Z]', seeking):
		# why the 'and' condition:
		#   sending unicode 'οὐθενὸϲ' to the betacode function will result in 0 hits
		#   this is something that could/should be debugged within that function,
		#   but in practice it is silly to allow hybrid betacode/unicode? this only
		#   makes the life of a person who wants unicode+regex w/ a betacode option more difficult
		replacebeta = True

	isgreek = re.compile('[α-ωἀἁἂἃἄἅἆἇᾀᾁᾂᾃᾄᾅᾆᾇᾲᾳᾴᾶᾷᾰᾱὰάἐἑἒἓἔἕὲέἰἱἲἳἴἵἶἷὶίῐῑῒΐῖῗὀὁὂὃὄὅόὸὐὑὒὓὔὕὖὗϋῠῡῢΰῦῧύὺᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἤἢἥἣὴήἠἡἦἧὠὡὢὣὤὥὦὧᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷώὼ]')

	if hipparchia.config['TLGASSUMESBETACODE'] == 'yes':
		if justtlg() and (re.search('[a-zA-Z]', seeking) or re.search('[a-zA-Z]', proximate)) and not re.search(isgreek, seeking) and not re.search(isgreek, proximate):
			replacebeta = True

	if replacebeta:
		seeking = seeking.upper()
		seeking = replacegreekbetacode(seeking)
		seeking = seeking.lower()
		proximate = proximate.upper()
		proximate = replacegreekbetacode(proximate)
		proximate = proximate.lower()

	phrasefinder = re.compile('[^\s]\s[^\s]')

	poll[ts] = ProgressPoll(ts)
	activepoll = poll[ts]
	activepoll.activate()
	activepoll.statusis('Preparing to search')

	searchlist = list()
	output = ''
	nosearch = True

	so = SearchObject(ts, seeking, proximate, lemma, proximatelemma, frozensession)

	dmin, dmax = bcedating(frozensession)
	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if frozensession[c] == 'yes']

	if (len(seeking) > 0 or lemma) and activecorpora:
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

		if lemma:
			so.termone = wordlistintoregex(so.lemma.formlist)
			skg = so.termone
			if re.search(isgreek, skg):
				# 'v' is a problem because the lemmata list is going to send 'u'
				# but the greek lemmata are accented
				so.usecolumn = 'accented_line'

		if proximatelemma:
			so.termtwo = wordlistintoregex(so.proximatelemma.formlist)
			prx = so.termtwo
			if re.search(isgreek, prx):
				so.usecolumn = 'accented_line'

		if lemma and not (proximatelemma or proximate):
			# print('executesearch(): a')
			so.searchtype = 'simplelemma'
			so.usewordlist = 'polytonic'
			thesearch = 'all forms of »{skg}«'.format(skg=lemma.dictionaryentry)
			htmlsearch = 'all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.lemma.formlist), skg=so.lemma.dictionaryentry)
		elif lemma and proximatelemma:
			# print('executesearch(): b')
			so.searchtype = 'proximity'
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=so.lemma.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=so.proximatelemma.dictionaryentry)
			htmlsearch = 'all {n} known forms of <span class="sought">»{skg}«</span>{ns} within {sp} {sc} of all {pn} known forms of <span class="sought">»{pskg}«</span>'.format(
				n=len(so.lemma.formlist), skg=so.lemma.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pn=len(so.proximatelemma.formlist), pskg=so.proximatelemma.dictionaryentry
			)
		elif (lemma or proximatelemma) and (seeking or proximate):
			# print('executesearch(): c')
			so.searchtype = 'proximity'
			if lemma:
				lm = so.lemma
				t = proximate
			else:
				lm = so.proximatelemma
				t = seeking
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=lm.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=t)
			htmlsearch = 'all {n} known forms of <span class="sought">»{skg}«</span>{ns} within {sp} {sc} of <span class="sought">»{pskg}«</span>'.format(
				n=len(lm.formlist), skg=lm.dictionaryentry, ns=so.nearstr, sp=so.proximity, sc=so.scope, pskg=t
			)
		elif len(proximate) < 1 and re.search(phrasefinder, seeking) is None:
			# print('executesearch(): d')
			so.searchtype = 'simple'
			thesearch = so.originalseeking
			htmlsearch = '<span class="sought">»{skg}«</span>'.format(skg=so.originalseeking)
		elif re.search(phrasefinder, seeking):
			# print('executesearch(): e')
			so.searchtype = 'phrase'
			thesearch = so.originalseeking
			htmlsearch = '<span class="sought">»{skg}«</span>'.format(skg=so.originalseeking)
		else:
			# print('executesearch(): f')
			so.searchtype = 'proximity'
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=so.originalseeking, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=so.proximate)
			htmlsearch = '<span class="sought">»{skg}«</span>{ns} within {sp} {sc} of <span class="sought">»{pr}«</span>'.format(
				skg=so.originalseeking, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=proximate)

		hits = searchdispatcher(so, activepoll)
		activepoll.statusis('Putting the results in context')

		# hits [<server.hipparchiaclasses.dbWorkLine object at 0x10d952da0>, <server.hipparchiaclasses.dbWorkLine object at 0x10d952c50>, ... ]
		hitdict = sortresultslist(hits, so, authordict, workdict)

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

		if lemma:
			# clean out the whitespace/start/stop checks
			skg = re.sub(r'\(\^\|\\s\)', '', skg)
			skg = re.sub(r'\(\\s\|\$\)', '', skg)

		if proximatelemma:
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
		output['proximate'] = proximate
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
		if len(seeking) == 0:
			reasons.append('there is no search term')
		if len(seeking) > 0 and len(searchlist) == 0:
			reasons.append('zero works match the search criteria')
		output = dict()
		output['title'] = '(empty query)'
		output['found'] = ''
		output['resultcount'] = '0 passages'
		output['scope'] = 0
		output['searchtime'] = '0.00'
		output['proximate'] = proximate
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
