# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from server.semanticvectors.gensimmodels import buildgensimmodel
from server.hipparchiaobjects.vectorobjects import VectorValues
from server.formatting.vectorformatting import formatnnmatches, formatnnsimilarity, nearestneighborgenerateoutput
from server.semanticvectors.vectorgraphing import graphnnmatches
from server.semanticvectors.vectorhelpers import convertmophdicttodict, findwordvectorset
from server.semanticvectors.vectorroutehelperfunctions import emptyvectoroutput
from server.textsandindices.textandindiceshelperfunctions import getrequiredmorphobjects


def generatenearestneighbordata(sentencetuples, workssearched, searchobject, vectorspace):
	"""

	this is where we go after executegensimsearch() makes its function pick

	[a] buildnnvectorspace (if needed)
	[b] do the right sort of search
		findword2vecsimilarities
		findapproximatenearestneighbors
	[c] generate the output

	:param searchobject:
	:param activepoll:
	:param sentencetuples:
	:param workssearched:
	:param starttime:
	:param vectorspace:
	:return:
	"""

	so = searchobject
	vv = so.vectorvalues
	activepoll = so.poll
	termone = so.lemma.dictionaryentry
	imagename = str()

	try:
		termtwo = so.proximatelemma.dictionaryentry
	except AttributeError:
		termtwo = None

	if not vectorspace:
		vectorspace = buildnnvectorspace(sentencetuples, so)
		if vectorspace == 'failed to build model':
			reasons = [vectorspace]
			return emptyvectoroutput(so, reasons)

	if termone and termtwo:
		similarity = findword2vecsimilarities(termone, termtwo, vectorspace)
		similarity = formatnnsimilarity(termone, termtwo, similarity)
		mostsimilar = ['placeholder']
		html = similarity
	else:
		activepoll.statusis('Calculating the nearest neighbors')
		mostsimilar = findapproximatenearestneighbors(termone, vectorspace, vv)
		# [('εὕρηϲιϲ', 1.0), ('εὑρίϲκω', 0.6673248708248138), ('φυϲιάω', 0.5833806097507477), ('νόμοϲ', 0.5505017340183258), ...]
		if not mostsimilar:
			# proper noun? Ϲωκράτηϲ --> ϲωκράτηϲ
			termone = termone[0].lower() + termone[1:]
			mostsimilar = findapproximatenearestneighbors(termone, vectorspace, vv)
		if mostsimilar:
			html = formatnnmatches(mostsimilar, vv)
			activepoll.statusis('Building the graph')
			mostsimilar = mostsimilar[:vv.neighborscap]
			imagename = graphnnmatches(termone, mostsimilar, vectorspace, so)
		else:
			html = '<pre>["{t}" was not found in the vector space]</pre>'.format(t=termone)

	findshtml = '{h}'.format(h=html)

	output = nearestneighborgenerateoutput(findshtml, mostsimilar, imagename, workssearched, searchobject)

	return output


def buildnnvectorspace(sentencetuples, searchobject):
	"""

	find the words
	find the morphology objects you need for those words
	build vectors

	:return:
	"""

	wordbundler = False

	activepoll = searchobject.poll

	# find all words in use
	listsofwords = [s[1] for s in sentencetuples]
	allwords = findwordvectorset(listsofwords)

	# find all possible forms of all the words we used
	# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
	wl = '{:,}'.format(len(listsofwords))
	activepoll.statusis(
		'No stored model for this search. Generating a new one.<br />Finding headwords for {n} sentences'.format(n=wl))

	morphdict = getrequiredmorphobjects(allwords, furtherdeabbreviate=True)

	# associate each word with its possible headwords
	morphdict = convertmophdicttodict(morphdict)

	# import re
	# teststring = r'aesa'
	# kvpairs = [(k,morphdict[k]) for k in morphdict.keys() if re.search(teststring, k)]
	# print('convertmophdicttodict', kvpairs)
	# sample selection:
	# convertmophdicttodict [('caesare', {'caesar'}), ('caesarisque', {'caesar'}), ('caesari', {'caesar'}), ('caesar', {'caesar'}), ('caesa', {'caesum', 'caesa', 'caesus¹', 'caedo'}), ('caesaremque', {'caesar'}), ('caesaris', {'caesar'}), ('caesarem', {'caesar'})]

	if wordbundler:
		morphdict = {t: '·'.join(morphdict[t]) for t in morphdict}

	activepoll.statusis('No stored model for this search. Generating a new one.<br />Building vectors for the headwords in the {n} sentences'.format(n=wl))
	vectorspace = buildgensimmodel(searchobject, morphdict, listsofwords)

	return vectorspace


def findapproximatenearestneighbors(query, mymodel, vectorvalues: VectorValues):
	"""

	search for points in space that are close to a given query point

	the query should be a dictionary headword

	this returns a list of tuples: (word, distance)

	:param query:
	:param mymodel:
	:param vectorvalues:
	:return:
	"""

	explore = max(2500, vectorvalues.neighborscap)

	try:
		mostsimilar = mymodel.wv.most_similar(query, topn=explore)
		mostsimilar = [s for s in mostsimilar if s[1] > vectorvalues.nearestneighborcutoffdistance]
	except KeyError:
		# keyedvectors.py: raise KeyError("word '%s' not in vocabulary" % word)
		mostsimilar = None
	except AttributeError:
		# 'NoneType' object has no attribute 'most_similar'
		mostsimilar = None

	#print('mostsimilar', mostsimilar)

	return mostsimilar


def findword2vecsimilarities(termone, termtwo, mymodel):
	"""

	WordEmbeddingsKeyedVectors in keyedvectors.py gives the methods

		similarity(w1, w2)
			[similarity('woman', 'man')]

	:param query:
	:param morphdict:
	:param sentences:
	:return:
	"""

	similarity = mymodel.wv.similarity(termone, termtwo)

	return similarity

