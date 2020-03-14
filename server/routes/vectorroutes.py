# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from flask import session

from server import hipparchia
from server.formatting.miscformatting import validatepollid
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.hipparchiaobjects.searchobjects import SearchObject, SearchOutputObject
from server.listsandsession.checksession import probeforsessionvariables
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
from server.routes.searchroute import executesearch
from server.searching.searchfunctions import cleaninitialquery
from server.startup import lemmatadict, progresspolldict


@hipparchia.route('/vectors/<vectortype>/<searchid>/<headform>')
def vectorsearch(vectortype, searchid, headform):
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
	               'tensorflowgraph', 'sentencesimilarity', 'topicmodel']

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