# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json

from flask import session

from server import hipparchia
from server.authentication.authenticationwrapper import requireauthentication
from server.formatting.miscformatting import validatepollid
from server.formatting.wordformatting import depunct
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.hipparchiaobjects.searchobjects import SearchObject, SearchOutputObject
from server.startup import lemmatadict, progresspolldict

if hipparchia.config['SEMANTICVECTORSENABLED']:
	from server.semanticvectors.externalvectorsearches import externalvectors
	from server.semanticvectors.vectorpipeline import pythonvectors
else:
	voff = lambda x: 'vectors have not been enabled in your configuration file'
	executegensimsearch = voff
	sklearnselectedworks = voff
	findabsolutevectorsbysentence = voff
	findabsolutevectorsfromhits = voff
	pythonvectors = voff

JSON_STR = str


@hipparchia.route('/vectors/<vectortype>/<searchid>/<one>')
@hipparchia.route('/vectors/<vectortype>/<searchid>/<one>/<two>/<three>')
@requireauthentication
def dispatchvectorsearch(vectortype: str, searchid: str, one=None, two=None, three=None) -> JSON_STR:
	"""

	dispatcher for "/vectors/..." requests

	"""

	if not hipparchia.config['SEMANTICVECTORSENABLED']:
		so = SearchObject(str(), str(), str(), str(), str(), session)
		oo = SearchOutputObject(so)
		target = 'searchsummary'
		message = '[semantic vectors have not been enabled]'
		return oo.generatenulloutput(itemname=target, itemval=message)

	pollid = validatepollid(searchid)
	one = depunct(one)
	two = depunct(two)
	three = depunct(three)

	simple = [pollid, one]
	triple = [pollid, one, two, three]

	knownfunctions = {	'nearestneighborsquery':
							{'bso': simple, 'pref': 'CONCEPTMAPPINGENABLED'},
						'analogies':
							{'bso': triple, 'pref': 'VECTORANALOGIESENABLED'},
						'topicmodel':
							{'bso': simple, 'pref': 'TOPICMODELINGENABLED'},
						'vectortestfunction':
							{'bso': simple, 'pref': 'TESTINGVECTORBUTTONENABLED'},
						'unused':
							{'fnc': lambda: str(), 'bso': None, 'pref': None},
						}

	if not knownfunctions[vectortype]['pref'] or not hipparchia.config[knownfunctions[vectortype]['pref']]:
		return json.dumps('this type of search has not been enabled')

	bso = knownfunctions[vectortype]['bso']

	so = None

	if len(bso) == 4:
		so = buildtriplelemmasearchobject(*bso)

	if len(bso) == 2:
		so = buildsinglelemmasearchobject(*bso)

	so.vectorquerytype = vectortype

	progresspolldict[pollid] = ProgressPoll(pollid)
	so.poll = progresspolldict[pollid]
	so.poll.activate()
	so.poll.statusis('Preparing to vectorize')

	if hipparchia.config['EXTERNALVECTORHELPER']:
		j = externalvectors(so)
	else:
		j = pythonvectors(so)

	if hipparchia.config['JSONDEBUGMODE']:
		print('/vectors/{f}\n\t{j}'.format(f=vectortype, j=j))

	try:
		del so.poll
	except AttributeError:
		pass

	return j


def buildsinglelemmasearchobject(pollid: str, one: str) -> SearchObject:
	"""

	build a search object w/ one lemma

	"""
	try:
		lemma = lemmatadict[one]
	except KeyError:
		lemma = None

	seeking = str()
	proximate = str()
	proximatelemma = str()
	so = SearchObject(pollid, seeking, proximate, lemma, proximatelemma, session)

	if so.session['baggingmethod'] == 'unlemmatized':
		so.seeking = so.searchtermcleanup(one)

	return so


def buildtriplelemmasearchobject(pollid, one, two, three) -> SearchObject:
	"""

	build a search object w/ three lemmata

	"""

	seeking = str()
	proximate = str()

	if not session['baggingmethod'] == 'unlemmatized':
		try:
			termone = lemmatadict[one]
			termtwo = lemmatadict[two]
			termthree = lemmatadict[three]
		except KeyError:
			termone = None
			termtwo = None
			termthree = None

		so = SearchObject(pollid, seeking, proximate, termone, termtwo, session)
		so.lemmathree = termthree
	else:
		so = SearchObject(pollid, one, two, True, True, session)
		so.lemmathree = True
		so.termthree = so.searchtermcleanup(three)

	return so
