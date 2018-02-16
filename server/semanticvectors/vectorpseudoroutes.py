# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import locale
import time

from flask import request, session

from server import hipparchia
from server.formatting.bibliographicformatting import bcedating
from server.formatting.jsformatting import generatevectorjs
from server.hipparchiaobjects.helperobjects import ProgressPoll
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions, \
	polytonicsort
from server.listsandsession.whereclauses import configurewhereclausedata
from server.searching.searchfunctions import buildsearchobject, cleaninitialquery
from server.semanticvectors.rudimentaryvectormath import buildrudimentaryvectorspace, caclulatecosinevalues
from server.semanticvectors.vectordispatcher import findheadwords, vectorsentencedispatching
from server.semanticvectors.vectorhelpers import convertmophdicttodict, findverctorenvirons, findwordvectorset
from server.startup import authordict, lemmatadict, listmapper, poll, workdict

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

@hipparchia.route('/findvectors/<timestamp>', methods=['GET'])
def findabsolutevectors(timestamp):
	"""

	meant to be called via a click from a result from a prior search

	:param timestamp:
	:return:
	"""

	try:
		ts = str(int(timestamp))
	except ValueError:
		ts = str(int(time.time()))

	so = buildsearchobject(ts, request, session)
	so.seeking = ''
	so.proximate = ''
	so.proximatelemma = ''

	try:
		so.lemma = lemmatadict[cleaninitialquery(request.args.get('lem', ''))]
	except KeyError:
		so.lemma = None

	poll[ts] = ProgressPoll(ts)
	activepoll = poll[ts]
	activepoll.activate()
	activepoll.statusis('Preparing to search')

	# nb: basically forcing so.session['cosdistbysentence'] == 'yes'
	# don't know how to enter executesearch() properly to handle the other option
	# print('cosdistbysentence')

	output = findabsolutevectorsbysentence(activepoll, so)

	del poll[ts]

	return output


def findabsolutevectorsbysentence(activepoll, searchobject):
	"""

	use the searchlist to grab a collection of sentences

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	:param searchitem:
	:param vtype:
	:return:
	"""

	starttime = time.time()

	so = searchobject

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
		sentences = vectorsentencedispatching(so, activepoll)

		output = generatevectoroutput(sentences, workssearched, so, activepoll, starttime, 'sentences')
	else:
		return emptyvectoroutput(so)

	return output


def findabsolutevectorsfromhits(searchobject, hitdict, activepoll, starttime, workssearched):
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

	activepoll.statusis('Compiling proximite wordlists')
	environs = findverctorenvirons(hitdict, so)

	output = generatevectoroutput(environs, workssearched, so, activepoll, starttime, 'passages')

	return output


def generatevectoroutput(listsofwords, workssearched, searchobject, activepoll, starttime, vtype):
	"""


	:return:
	"""
	so = searchobject
	dmin, dmax = bcedating(so.session)

	# find all words in use
	allwords = findwordvectorset(listsofwords)

	# find all possible forms of all the words we used
	# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
	activepoll.statusis('Finding headwords')
	morphdict = findheadwords(allwords)
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
	cosinevalues = {c: cosinevalues[c] for c in cosinevalues if cosinevalues[c] and falseidentity < cosinevalues[c] < threshold}

	# now we have the relationship of everybody to our lemmatized word

	# print('CORE COSINE VALUES')
	# for v in polytonicsort(cosinevalues):
	# 	print(v, cosinevalues[v])
	ccv = [(cosinevalues[v], v) for v in cosinevalues]
	ccv = sorted(ccv, key=lambda t: t[0])
	ccv = ['\t{a}\t<lemmaheadword id="{b}">{b}</lemmaheadword>'.format(a=round(c[0], 3), b=c[1]) for c in ccv]
	ccv = '\n'.join(ccv)

	# next we look for the interrelationships of the words that are above the threshold
	activepoll.statusis('Calculating metacosine distances')
	metacosinevals = dict()
	metacosinevals[focus] = cosinevalues
	for v in cosinevalues:
		metac = caclulatecosinevalues(v, vectorspace, cosinevalues.keys())
		# metac = vectorcosinedispatching(v, vectorspace, cosinevalues.keys())
		metac = {c: metac[c] for c in metac if metac[c] and falseidentity < metac[c] < threshold}
		metacosinevals[v] = metac

	mcv = list(['\nrelationships of these terms to one another\n'])
	for headword in polytonicsort(metacosinevals.keys()):
		# print(headword)
		# for word in metacosinevals[headword]:
		# 	print('\t', word, metacosinevals[headword][word])
		if headword != focus:
			insetvals = [(metacosinevals[headword][word], word) for word in metacosinevals[headword]]
			insetvals = sorted(insetvals, key=lambda t: t[0])
			insetvals = ['\t{a}\t<lemmaheadword id="{b}">{b}</lemmaheadword>'.format(a=round(c[0], 3), b=c[1]) for c in insetvals]
			if insetvals:
				mcv.append('<lemmaheadword id="{h}">{h}</lemmaheadword>'.format(h=headword))
			mcv += insetvals
	if len(mcv) > 1:
		mcv = '\n'.join(mcv)
	else:
		mcv = ''

	findshtml = '<pre>{ccv}</pre>\n\n<pre>{mcv}</pre>'.format(ccv=ccv, mcv=mcv)

	findsjs = generatevectorjs('findvectors')

	searchtime = time.time() - starttime
	searchtime = round(searchtime, 2)
	workssearched = locale.format('%d', workssearched, grouping=True)

	output = dict()
	output['title'] = 'Cosine distances to »{skg}«'.format(skg=focus)
	output['found'] = findshtml
	# ultimately the js should let you clock on any top word to find its associations...
	output['js'] = findsjs
	output['resultcount'] = '{c} related terms in {s} {t}'.format(c=len(cosinevalues), s=len(listsofwords), t=vtype)
	output['scope'] = workssearched
	output['searchtime'] = str(searchtime)
	output['proximate'] = ''
	if so.lemma:
		xtra = 'all forms of '
	else:
		xtra = ''
	output['thesearch'] = '{x}»{skg}«'.format(x=xtra, skg=focus)
	output['htmlsearch'] = '{x}<span class="sought">»{skg}«</span>'.format(x=xtra, skg=focus)
	output['hitmax'] = ''
	output['onehit'] = ''
	output['sortby'] = 'distance with a cutoff of {c}'.format(c=1 - hipparchia.config['VECTORDISTANCECUTOFFLOCAL'])
	output['dmin'] = dmin
	output['dmax'] = dmax
	activepoll.deactivate()

	output = json.dumps(output)

	return output


def emptyvectoroutput(searchobject, reasons=list()):
	"""

	no results; say as much

	:return:
	"""

	so = searchobject
	output = dict()
	dmin, dmax = bcedating(so.session)

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c] == 'yes']

	if not activecorpora:
		reasons.append('there are no active databases')
	if not (so.lemma or so.seeking):
		reasons.append('no search term was provided')

	output['title'] = '(empty query)'
	output['found'] = ''
	output['resultcount'] = 0
	output['scope'] = 0
	output['searchtime'] = '0.00'
	output['proximate'] = so.proximate
	output['thesearch'] = ''
	output['htmlsearch'] = '<span class="emph">nothing</span> (search not executed because {r})'.format(r=' and '.join(reasons))
	output['hitmax'] = 0
	output['dmin'] = dmin
	output['dmax'] = dmax
	output['sortby'] = so.session['sortorder']
	output['onehit'] = so.session['onehit']

	output = json.dumps(output)

	return output

