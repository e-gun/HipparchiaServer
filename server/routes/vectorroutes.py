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
from server.startup import lemmatadict, progresspolldict


@hipparchia.route('/vectors/<vectortype>/<searchid>/<headform>')
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
def analogysearch(searchid, termone, termtwo, termthree):
	"""

	FOR TESTING ONLY; WILL NOT SEND OUTPUT TO BROWSER

	the results are distinctly unsatisfying....

	A:B :: C:D

	http://127.0.0.1:5000/vectoranalogies/0000/one/two/thee

	whole Latin corpus

	so.vectorquerytype analogyfinder
	vir : civis :: uxor : _______
	generateanalogies() similarities are
		 ('virus', 0.6339177489280701)
		 ('vira', 0.5401976108551025)
		 ('viror', 0.5168510675430298)
		 ('homo', 0.4714127480983734)
	generateanalogies() cosimilarities are
		 ('virus', 1.0384498834609985)
		 ('vira', 0.9725769758224487)
		 ('viror', 0.9550812840461731)
		 ('homo', 0.9249561429023743)

	so.vectorquerytype analogyfinder
	emptor : creditor :: possessor : _______
	generateanalogies() similarities are
		 ('venditor', 0.5869967341423035)
		 ('debitor', 0.57599937915802)
		 ('credito', 0.5587280988693237)
		 ('vendito', 0.508560836315155)
	generateanalogies() cosimilarities are
		 ('venditor', 0.937236487865448)
		 ('debitor', 0.9244076013565063)
		 ('credito', 0.9078490734100342)
		 ('vendito', 0.8791030645370483)


	stultitia : sapientia :: arrogantia : _______
	generateanalogies() similarities are
		 ('sapio', 0.5643229484558105)
		 ('sapiens', 0.4648801386356354)
		 ('virtus', 0.37652188539505005)
		 ('phronesis', 0.3369315266609192)
	generateanalogies() cosimilarities are
		 ('sapio', 0.9766638875007629)
		 ('sapiens', 0.8850504755973816)
		 ('virtus', 0.8071112036705017)
		 ('phronesis', 0.7899892926216125)

	all of Greek

	ἀπόδειξιϲ : μέθοδοϲ :: τέχνη : _______
	generateanalogies() similarities are
		 ('ἀποδείκνυμι', 0.562789261341095)
		 ('ἀποδεικτικόϲ', 0.5339866876602173)
		 ('ὑπόθεϲιϲ', 0.5029253959655762)
		 ('ϲυλλογιϲμόϲ', 0.4884676933288574)
	generateanalogies() cosimilarities are
		 ('ἀποδείκνυμι', 0.9568907618522644)
		 ('ἀποδεικτικόϲ', 0.9224797487258911)
		 ('ὑπόθεϲιϲ', 0.9053481817245483)
		 ('ϲυλλογίζομαι', 0.8888764381408691)

	φιλοϲοφία : ἐπιϲτήμη :: γυμναϲία : _______
	generateanalogies() similarities are
		 ('ἐπιϲτημόω', 0.5599137544631958)
		 ('θεωρητικόϲ', 0.4901699423789978)
		 ('γεωμετρία', 0.487331360578537)
		 ('φιλοϲοφέω', 0.482659250497818)
	generateanalogies() cosimilarities are
		 ('ἐπιϲτημόω', 1.0181474685668945)
		 ('γεωμετρία', 0.9427960515022278)
		 ('θεωρητικόϲ', 0.940839946269989)
		 ('φιλοϲοφέω', 0.9274911880493164)


	:param searchid:
	:param termone:
	:param termtwo:
	:param termthree:
	:return:
	"""

	termone = 'φιλοϲοφία'
	termtwo = 'ἐπιϲτήμη'
	termthree = 'γυμναϲία'

	try:
		termone = lemmatadict[termone]
		termtwo = lemmatadict[termtwo]
		termthree = lemmatadict[termthree]
	except KeyError:
		termone = None
		termtwo = None
		termthree = None

	pollid = validatepollid(searchid)

	seeking = str()
	proximate = str()

	so = SearchObject(pollid, seeking, proximate, termone, termtwo, session)
	so.lemmathree = termthree

	return vectorsearch('analogyfinder', pollid, None, so=so)
