# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from flask import redirect, session, url_for

from server import hipparchia
from server.authentication.authenticationwrapper import requireauthentication
from server.formatting.miscformatting import validatepollid
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.hipparchiaobjects.searchobjects import SearchObject, SearchOutputObject
from server.listsandsession.checksession import probeforsessionvariables
from server.routes.searchroute import executesearch
from server.startup import lemmatadict, progresspolldict

if hipparchia.config['SEMANTICVECTORSENABLED']:
	from server.semanticvectors.gensimvectors import executegensimsearch
	from server.semanticvectors.scikitlearntopics import sklearnselectedworks
	from server.semanticvectors.vectorroutehelperfunctions import findabsolutevectorsbysentence
else:
	voff = lambda x: 'vectors have not been enabled in your configuration file'
	executegensimsearch = voff
	sklearnselectedworks = voff
	findabsolutevectorsbysentence = voff
	findabsolutevectorsfromhits = voff


@hipparchia.route('/vectors/<vectortype>/<searchid>/<headform>')
@requireauthentication
def vectorsearch(vectortype, searchid, headform, so=None):
	"""

	you get sent here if you have something clicked in the vector boxes: see 'documentready.js'

	this is a restricted version of executesearch(): a dictionary headword

	no particular virtue in breaking this out yet; but separation of vector routes is likely
	useful in the long run

	:param searchid:
	:param headform:
	:return:
	"""

	if not hipparchia.config['SEMANTICVECTORSENABLED']:
		so = SearchObject(str(), str(), str(), str(), str(), session)
		oo = SearchOutputObject(so)
		target = 'searchsummary'
		message = '[semantic vectors have not been enabled]'
		return oo.generatenulloutput(itemname=target, itemval=message)

	probeforsessionvariables()

	vectorboxes = ['cosdistbysentence', 'cosdistbylineorword', 'semanticvectorquery', 'nearestneighborsquery',
	               'tensorflowgraph', 'sentencesimilarity', 'topicmodel', 'analogyfinder']

	try:
		lemma = lemmatadict[headform]
	except KeyError:
		lemma = None

	pollid = validatepollid(searchid)

	if not so:
		seeking = str()
		proximate = str()
		proximatelemma = str()
		so = SearchObject(pollid, seeking, proximate, lemma, proximatelemma, session)

	if so.session['baggingmethod'] == 'unlemmatized' and not so.seeking:
		# analogysearch() might have already set so.seeking
		so.seeking = so.searchtermcleanup(headform)

	progresspolldict[pollid] = ProgressPoll(pollid)
	activepoll = progresspolldict[pollid]
	activepoll.activate()
	activepoll.statusis('Preparing to vectorize')
	so.poll = activepoll

	output = SearchOutputObject(so)

	# note that cosdistbylineorword requires a hitdict and has to executesearch() to get one

	if vectortype in vectorboxes:
		so.vectorquerytype = vectortype

		vectorfunctions = {'cosdistbysentence': findabsolutevectorsbysentence,
		                   'semanticvectorquery': executegensimsearch,
		                   'nearestneighborsquery': executegensimsearch,
		                   'analogyfinder': executegensimsearch,
		                   'topicmodel': sklearnselectedworks}

		# for TESTING purposes rewrite one of the definitions
		# vectorfunctions['tensorflowgraph'] = gensimexperiment

		if so.vectorquerytype in vectorfunctions:
			fnc = vectorfunctions[so.vectorquerytype]
			jsonoutput = fnc(so)
			del progresspolldict[pollid]
			return jsonoutput

		if so.vectorquerytype == 'cosdistbylineorword':
			jsonoutput = executesearch(pollid, so)
			return jsonoutput

	# nothing happened...
	target = 'searchsummary'
	message = '[unknown vector query type]'

	return output.generatenulloutput(itemname=target, itemval=message)


@hipparchia.route('/vectoranalogies/<searchid>/<termone>/<termtwo>/<termthree>')
@requireauthentication
def analogysearch(searchid, termone, termtwo, termthree):
	"""

	the results are distinctly unsatisfying....

	what is the lesson here? it probably teaches you something about the other results that is worth knowing...

	A:B :: C:D

	http://127.0.0.1:5000/vectoranalogies/0000/one/two/thee

	:param searchid:
	:param termone:
	:param termtwo:
	:param termthree:
	:return:
	"""

	if not hipparchia.config['VECTORANALOGIESENABLED']:
		return redirect(url_for('frontpage'))

	pollid = validatepollid(searchid)

	seeking = str()
	proximate = str()

	if not session['baggingmethod'] == 'unlemmatized':
		try:
			termone = lemmatadict[termone]
			termtwo = lemmatadict[termtwo]
			termthree = lemmatadict[termthree]
		except KeyError:
			termone = None
			termtwo = None
			termthree = None

		so = SearchObject(pollid, seeking, proximate, termone, termtwo, session)
		so.lemmathree = termthree
	else:
		so = SearchObject(pollid, termone, termtwo, True, True, session)
		so.lemmathree = True
		so.termthree = so.searchtermcleanup(termthree)

	# vectorsearch(vectortype, searchid, headform, so=None)
	return vectorsearch('analogyfinder', pollid, None, so=so)
