# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import locale

from flask import request, session

from server import hipparchia
from server.dbsupport.vectordbfunctions import fetchverctorenvirons
from server.formatting.jsformatting import generatevectorjs
from server.formatting.miscformatting import validatepollid
from server.formatting.vectorformatting import formatnnmatches
from server.hipparchiaobjects.searchobjects import SearchOutputObject
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.searching.searchfunctions import buildsearchobject, cleaninitialquery
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.rudimentaryvectormath import buildrudimentaryvectorspace, caclulatecosinevalues
from server.semanticvectors.vectorgraphing import graphbliteraldistancematches
from server.semanticvectors.vectorhelpers import convertmophdicttodict, findwordvectorset
from server.startup import authordict, lemmatadict, listmapper, poll, workdict
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

@hipparchia.route('/findvectors/<searchid>', methods=['GET'])
def findabsolutevectors(searchid):
	"""

	meant to be called via a click from a result from a prior search

	:param searchid:
	:return:
	"""

	pollid = validatepollid(searchid)

	so = buildsearchobject(pollid, request, session)
	so.seeking = ''
	so.proximate = ''
	so.proximatelemma = ''

	try:
		so.lemma = lemmatadict[cleaninitialquery(request.args.get('lem', ''))]
	except KeyError:
		so.lemma = None

	poll[pollid] = ProgressPoll(pollid)
	activepoll = poll[pollid]
	activepoll.activate()
	activepoll.statusis('Preparing to search')
	so.poll = activepoll

	# nb: basically forcing so.session['cosdistbysentence'] == 'yes'
	# don't know how to enter executesearch() properly to handle the other option
	# print('cosdistbysentence')

	output = findabsolutevectorsbysentence(so)

	del poll[pollid]

	return output


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
	activecorpora = [c for c in allcorpora if so.session[c] == 'yes']

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
		reasons = ['the vector scope max exceeded: {a} > {b} '.format(a=locale.format('%d', wordstotal, grouping=True), b=locale.format('%d', maxwords, grouping=True))]
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

		output = generatevectoroutput(sentences, workssearched, so, 'sentences')
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

	so.proximate = ''
	so.proximatelemma = ''

	activepoll.statusis('Compiling proximite wordlists')
	environs = fetchverctorenvirons(hitdict, so)

	output = generatevectoroutput(environs, workssearched, so, 'passages')

	return output


def generatevectoroutput(listsofwords, workssearched, searchobject, vtype):
	"""


	:return:
	"""
	so = searchobject
	activepoll = so.poll

	# find all words in use
	allwords = findwordvectorset(listsofwords)

	# find all possible forms of all the words we used
	# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
	activepoll.statusis('Finding headwords')
	morphdict = getrequiredmorphobjects(allwords)
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

	# apply the threshold and drop the 'None' items
	threshold = 1.0 - hipparchia.config['VECTORDISTANCECUTOFFLOCAL']
	falseidentity = .02
	cosinevalues = {c: 1 - cosinevalues[c] for c in cosinevalues if cosinevalues[c] and falseidentity < cosinevalues[c] < threshold}
	mostsimilar = [(c, cosinevalues[c]) for c in cosinevalues]
	mostsimilar = sorted(mostsimilar, key=lambda t: t[1], reverse=True)
	findshtml = formatnnmatches(mostsimilar)

	# next we look for the interrelationships of the words that are above the threshold
	activepoll.statusis('Calculating metacosine distances')
	imagename = graphbliteraldistancematches(focus, mostsimilar, so)

	findsjs = generatevectorjs('findvectors')

	output = SearchOutputObject(so)

	output.title = 'Cosine distances to »{skg}«'.format(skg=focus)
	output.found = findshtml
	output.js = findsjs

	if so.session['cosdistbylineorword'] == 'no':
		space = 'related terms in {s} {t}'.format(s=len(listsofwords), t=vtype)
	else:
		dist = so.session['proximity']
		scale = {'W': 'word', 'L': 'line'}
		if int(dist) > 1:
			plural = 's'
		else:
			plural = ''
		space = 'related terms within {a} {b}{s}'.format(a=dist, b=scale[so.session['searchscope']], s=plural)

	found = max(hipparchia.config['NEARESTNEIGHBORSCAP'], len(cosinevalues))
	output.setresultcount(found, space)
	output.setscope(workssearched)

	if so.lemma:
		xtra = 'all forms of '
	else:
		xtra = ''
	output.thesearch = '{x}»{skg}«'.format(x=xtra, skg=focus)
	output.htmlsearch = '{x}<span class="sought">»{skg}«</span>'.format(x=xtra, skg=focus)

	output.sortby = 'distance with a cutoff of {c}'.format(c=1 - hipparchia.config['VECTORDISTANCECUTOFFLOCAL'])
	output.image = imagename
	output.searchtime = so.getelapsedtime()

	activepoll.deactivate()

	jsonoutput = json.dumps(output.generateoutput())

	return jsonoutput


def emptyvectoroutput(searchobject, reasons=list()):
	"""

	no results; say as much

	:return:
	"""

	so = searchobject

	output = SearchOutputObject(so)
	output.reasons = reasons

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c] == 'yes']

	if not activecorpora:
		output.reasons.append('there are no active databases')
	if not (so.lemma or so.seeking):
		output.reasons.append('no search term was provided')

	output.explainemptysearch()

	jsonoutput = json.dumps(output.generateoutput())

	return jsonoutput

