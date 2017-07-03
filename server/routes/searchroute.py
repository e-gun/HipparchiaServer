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
from server.formatting.searchformatting import htmlifysearchfinds, nocontexthtmlifysearchfinds, jstoinjectintobrowser, \
	buildresultobjects, flagsearchterms
from server.formatting.wordformatting import universalregexequivalent
from server.hipparchiaobjects.helperobjects import ProgressPoll, SearchObject
from server.listsandsession.listmanagement import sortresultslist, calculatewholeauthorsearches, compilesearchlist, \
	flagexclusions
from server.listsandsession.sessionfunctions import sessionvariables, justlatin, justtlg
from server.listsandsession.whereclauses import configurewhereclausedata
from server.searching.searchdispatching import searchdispatcher
from server.searching.searchfunctions import cleaninitialquery
from server.startup import authordict, workdict, listmapper, poll


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
	# a search can take 30s or more and the user might alter the session while the search is running by toggling onehit, etc
	# that can be a problem, so freeze the values now and rely on this instead of some moving target
	frozensession = session.copy()

	# need to sanitize input at least a bit: remove digits and punctuation
	# dispatcher will do searchtermcharactersubstitutions() and massagesearchtermsforwhitespace() to take care of lunate sigma, etc.
	try:
		seeking = cleaninitialquery(request.args.get('seeking', ''))
	except:
		seeking = ''

	try:
		proximate = cleaninitialquery(request.args.get('proximate', ''))
	except:
		proximate = ''

	if len(seeking) < 1 and len(proximate) > 0:
		seeking = proximate
		proximate = ''

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

	searchlist = []
	output = ''
	nosearch = True

	so = SearchObject(ts, seeking, proximate, frozensession)

	dmin, dmax = bcedating(frozensession)
	activecorpora = [c for c in ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	                 if frozensession[c] == 'yes']

	if len(seeking) > 0 and activecorpora:
		activepoll.statusis('Compiling the list of works to search')
		searchlist = compilesearchlist(listmapper, frozensession)

	if len(searchlist) > 0:
		nosearch = False
		# mark works that have passage exclusions associated with them: gr0001x001 instead of gr0001w001 if you are skipping part of w001
		searchlist = flagexclusions(searchlist, frozensession)
		workssearched = len(searchlist)

		activepoll.statusis('Calculating full authors to search')
		searchlist = calculatewholeauthorsearches(searchlist, authordict)
		so.searchlist = searchlist
		activepoll.statusis('Configuring the search restrictions')
		indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
		so.indexrestrictions = indexrestrictions

		if len(proximate) < 1 and re.search(phrasefinder, seeking) is None:
			so.searchtype = 'simple'
			thesearch = so.originalseeking
			htmlsearch = '<span class="sought">»{skg}«</span>'.format(skg=so.originalseeking)
		elif re.search(phrasefinder, seeking):
			so.searchtype = 'phrase'
			thesearch = so.originalseeking
			htmlsearch = '<span class="sought">»{skg}«</span>'.format(skg=so.originalseeking)
		else:
			so.searchtype = 'proximity'
			thesearch = '{skg}{ns} within {sp} {sc} of {pr}'.format(skg=so.originalseeking, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=so.proximate)
			htmlsearch = '<span class="sought">»{skg}«</span>{ns} within {sp} {sc} of <span class="sought">»{pr}«</span>'.format(
				skg=so.originalseeking, ns=so.nearstr, sp=so.proximity, sc=so.scope, pr=proximate)

		hits = searchdispatcher(so, activepoll)
		activepoll.statusis('Putting the results in context')

		# hits [<server.hipparchiaclasses.dbWorkLine object at 0x10d952da0>, <server.hipparchiaclasses.dbWorkLine object at 0x10d952c50>, ... ]
		hitdict = sortresultslist(hits, authordict, workdict)

		resultlist = buildresultobjects(hitdict, authordict, workdict, so, activepoll)

		activepoll.statusis('Converting results to HTML')

		skg = re.compile(universalregexequivalent(so.termone))
		prx = None
		if so.proximate != '' and so.searchtype == 'proximity':
			prx = re.compile(universalregexequivalent(so.termtwo))

		for r in resultlist:
			r.lineobjects = flagsearchterms(r,skg, prx, so)

		if so.context > 0:
			findshtml = htmlifysearchfinds(resultlist, so)
		else:
			findshtml = nocontexthtmlifysearchfinds(resultlist)

		findsjs = jstoinjectintobrowser(resultlist)

		resultcount = len(resultlist)

		if resultcount < so.cap:
			hitmax = 'false'
		else:
			hitmax = 'true'

		# prepare the output
		searchtime = time.time() - starttime
		searchtime = round(searchtime, 2)

		sortorderdecoder = {
			'universalid': 'ID', 'shortname': 'name', 'genres': 'author genre', 'converted_date': 'date', 'location': 'location'
		}
		try:
			locale.setlocale(locale.LC_ALL, 'en_US')
		except locale.Error:
			pass
		resultcount = locale.format('%d', resultcount, grouping=True)
		workssearched = locale.format('%d', workssearched, grouping=True)

		output = {}
		output['title'] = thesearch
		output['found'] = findshtml
		output['js'] = findsjs
		output['resultcount'] = resultcount
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
		if justlatin() == False:
			output['icandodates'] = 'yes'
		else:
			output['icandodates'] = 'no'
		activepoll.deactivate()

	if nosearch:
		reasons = []
		if not activecorpora:
			reasons.append('there are no active databases')
		if len(seeking) == 0:
			reasons.append('there is no search term')
		if len(seeking) > 0 and len(searchlist) == 0:
			reasons.append('zero works match the search criteria')
		output = {}
		output['title'] = '(empty query)'
		output['found'] = ''
		output['resultcount'] = 0
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
