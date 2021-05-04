# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import locale

from server import hipparchia
from server.dbsupport.vectordbfunctions import fetchverctorenvirons
from server.formatting.jsformatting import generatevectorjs
from server.formatting.vectorformatting import formatnnmatches
from server.hipparchiaobjects.searchobjects import SearchOutputObject
from server.listsandsession.searchlistmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server._deprecated._vectors.rudimentaryvectormath import buildrudimentaryvectorspace, caclulatecosinevalues
from server.semanticvectors.vectorgraphing import graphbliteraldistancematches
from server.semanticvectors.vectorhelpers import convertmophdicttodict
from server.listsandsession.genericlistfunctions import findsetofallwords
from server.startup import authordict, lemmatadict, listmapper, workdict
from server.textsandindices.textandindiceshelperfunctions import getrequiredmorphobjects

"""
	THE BASIC MATH

	http://www.puttypeg.net/papers/vector-chapter.pdf

	see esp pp. 155-58 on cosine similarity:
	
		cos(α,β) = α · β / ||α|| ||β||
	
	||α|| = sqrt(α · α)
	
	and α = sum([a1, a2, ... ai])

	1 = most related
	0 = unrelated

"""


def findabsolutevectorsbysentence(searchobject):
	"""

	use the searchlist to grab a collection of sentences

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	generators are tempting, but dealing with generators+MP is a trick:

		TypeError: can't pickle generator objects

	:param searchitem:
	:param vtype:
	:return:
	"""

	so = searchobject
	activepoll = so.poll

	# we are not really a route at the moment, but instead being called by execute search
	# when the δ option is checked; hence the commenting out of the following
	# lemma = cleaninitialquery(request.args.get('lem', ''))

	try:
		lemma = lemmatadict[so.lemma.dictionaryentry]
	except KeyError:
		lemma = None
	except AttributeError:
		# 'NoneType' object has no attribute 'dictionaryentry'
		lemma = None

	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c]]

	if (lemma or so.seeking) and activecorpora:
		activepoll.statusis('Compiling the list of works to search')
		searchlist = compilesearchlist(listmapper, so.session)
	else:
		reasons = ['search list contained zero items']
		return emptyvectoroutput(so, reasons)

	# make sure you don't go nuts
	maxwords = hipparchia.config['MAXVECTORSPACE']
	wordstotal = 0
	for work in searchlist:
		work = work[:10]
		try:
			wordstotal += workdict[work].wordcount
		except TypeError:
			# TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'
			pass

	if wordstotal > maxwords:
		reasons = ['the vector scope max exceeded: {a} > {b} '.format(a=locale.format_string('%d', wordstotal, grouping=True), b=locale.format_string('%d', maxwords, grouping=True))]
		return emptyvectoroutput(so, reasons)

	if len(searchlist) > 0:
		searchlist = flagexclusions(searchlist, so.session)
		workssearched = len(searchlist)
		searchlist = calculatewholeauthorsearches(searchlist, authordict)
		so.searchlist = searchlist

		indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
		so.indexrestrictions = indexrestrictions

		# find all sentences
		activepoll.statusis('Finding all sentences')
		sentencetuples = vectorprepdispatcher(so)
		sentences = [s[1] for s in sentencetuples]
		output = generateabsolutevectorsoutput(sentences, workssearched, so, 'sentences')
	else:
		return emptyvectoroutput(so)

	return output


def findabsolutevectorsfromhits(searchobject, hitdict, workssearched):
	"""
	a pseudo-route: the Δ option was checked and executesearch() branced over to this function

	we searched for a word within N lines/words of another word

	we got some lineobjects that are our hits

	how we vectorize this

	:param searchobject:
	:param hitdict:
	:param activepoll:
	:param starttime:
	:param workssearched:
	:return:
	"""

	so = searchobject
	activepoll = so.poll

	so.proximate = str()
	so.proximatelemma = str()

	activepoll.statusis('Compiling proximite wordlists')
	environs = fetchverctorenvirons(hitdict, so)

	output = generateabsolutevectorsoutput(environs, workssearched, so, 'passages')

	return output


def generateabsolutevectorsoutput(listsofwords: list, workssearched: list, searchobject, vtype: str):
	"""


	:return:
	"""
	so = searchobject
	vv = so.vectorvalues
	activepoll = so.poll

	# find all words in use
	allwords = findsetofallwords(listsofwords)
	# print('allwords', allwords)

	# find all possible forms of all the words we used
	# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
	activepoll.statusis('Finding headwords')
	morphdict = getrequiredmorphobjects(allwords, furtherdeabbreviate=True)
	morphdict = convertmophdicttodict(morphdict)

	# find all possible headwords of all of the forms in use
	# note that we will not know what we did not know: count unparsed words too and deliver that as info at the end?
	allheadwords = dict()
	for m in morphdict.keys():
		for h in morphdict[m]:
			allheadwords[h] = m

	if so.lemma:
		# set to none for now
		subtractterm = None
	else:
		subtractterm = so.seeking

	activepoll.statusis('Building vectors')
	vectorspace = buildrudimentaryvectorspace(allheadwords, morphdict, listsofwords, subtractterm=subtractterm)

	# for k in vectorspace.keys():
	# 	print(k, vectorspace[k])

	if so.lemma:
		focus = so.lemma.dictionaryentry
	else:
		focus = so.seeking

	activepoll.statusis('Calculating cosine distances')
	cosinevalues = caclulatecosinevalues(focus, vectorspace, allheadwords.keys())
	# cosinevalues = vectorcosinedispatching(focus, vectorspace, allheadwords.keys())
	# print('generatevectoroutput cosinevalues', cosinevalues)

	# apply the threshold and drop the 'None' items
	threshold = 1.0 - vv.localcutoffdistance
	falseidentity = .02
	cosinevalues = {c: 1 - cosinevalues[c] for c in cosinevalues if cosinevalues[c] and falseidentity < cosinevalues[c] < threshold}
	mostsimilar = [(c, cosinevalues[c]) for c in cosinevalues]
	mostsimilar = sorted(mostsimilar, key=lambda t: t[1], reverse=True)

	findshtml = formatnnmatches(mostsimilar, vv)

	# next we look for the interrelationships of the words that are above the threshold
	activepoll.statusis('Calculating metacosine distances')
	imagename = graphbliteraldistancematches(focus, mostsimilar, so)

	findsjs = generatevectorjs()

	output = SearchOutputObject(so)

	output.title = 'Cosine distances to »{skg}«'.format(skg=focus)
	output.found = findshtml
	output.js = findsjs

	if not so.session['cosdistbylineorword']:
		space = 'related terms in {s} {t}'.format(s=len(listsofwords), t=vtype)
	else:
		dist = so.session['proximity']
		scale = {'words': 'word', 'lines': 'line'}
		if int(dist) > 1:
			plural = 's'
		else:
			plural = str()
		space = 'related terms within {a} {b}{s}'.format(a=dist, b=scale[so.session['searchscope']], s=plural)

	found = max(vv.neighborscap, len(cosinevalues))
	output.setresultcount(found, space)
	output.setscope(workssearched)

	if so.lemma:
		xtra = 'all forms of '
	else:
		xtra = str()

	output.thesearch = '{x}»{skg}«'.format(x=xtra, skg=focus)
	output.htmlsearch = '{x}<span class="sought">»{skg}«</span>'.format(x=xtra, skg=focus)

	output.sortby = 'distance with a cutoff of {c}'.format(c=vv.localcutoffdistance)
	output.image = imagename
	output.searchtime = so.getelapsedtime()

	activepoll.deactivate()

	jsonoutput = json.dumps(output.generateoutput())

	return jsonoutput


def emptyvectoroutput(searchobject, reasons=None):
	"""

	no results; say as much

	:return:
	"""

	if not reasons:
		reasons = list()

	so = searchobject

	output = SearchOutputObject(so)
	output.reasons = reasons

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c]]

	if not activecorpora:
		output.reasons.append('there are no active databases')
	if not (so.lemma or so.seeking):
		output.reasons.append('no search term was provided')

	output.explainemptysearch()

	jsonoutput = json.dumps(output.generateoutput())

	return jsonoutput

