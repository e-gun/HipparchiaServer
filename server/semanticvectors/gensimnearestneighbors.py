# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from typing import List

from server.dbsupport.lexicaldbfunctions import lookformorphologymatches
from server.formatting.vectorformatting import formatnnmatches, formatnnsimilarity, nearestneighborgenerateoutput
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.vectorobjects import VectorValues
from server.semanticvectors.vectorgraphing import graphnnmatches
from server.semanticvectors.vectorhelpers import emptyvectoroutput

JSON_STR = str


def generatenearestneighbordata(sentencetuples, workssearched, searchobject, vectorspace) -> JSON_STR:
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
	imagename = str()

	if so.iamarobot:
		return str()

	try:
		termone = so.lemma.dictionaryentry
	except AttributeError:
		# AttributeError: 'str' object has no attribute 'dictionaryentry'
		# session['baggingmethod'] == 'unlemmatized' (I hope...)
		termone = so.seeking

	try:
		termtwo = so.proximatelemma.dictionaryentry
	except AttributeError:
		termtwo = None

	if not vectorspace:
		# not supposed to make it here any longer...
		return emptyvectoroutput(so, ['generatenearestneighbordata() was not sent a model'])

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
			# you can get back >1000 items
			if so.session['trimvectoryby'] != 'none':
				activepoll.statusis('Trimming by part of speech')
				validset = trimbypartofspeech([m[0] for m in mostsimilar], so.session['trimvectoryby'], so.session['baggingmethod'])
				mostsimilar = [m for m in mostsimilar if m[0] in validset]
			html = formatnnmatches(mostsimilar, vv)
			activepoll.statusis('Building the graph')
			mostsimilar = mostsimilar[:vv.neighborscap]
			imagename = graphnnmatches(termone, mostsimilar, vectorspace, so)
		else:
			html = '<pre>["{t}" was not found in the vector space]</pre>'.format(t=termone)

	findshtml = '{h}'.format(h=html)
	activepoll.allworkis(-1)  # this turns off the % completed notice in the JS
	activepoll.sethits(0)
	output = nearestneighborgenerateoutput(findshtml, mostsimilar, imagename, workssearched, searchobject)

	return output


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


def trimbypartofspeech(listofwords: List[str], partofspeech: str, baggingmethod: str) -> set:
	"""

	return only the verbs, e.g., in a list of words

	:param listofwords:
	:param partofspeech:
	:return:
	"""

	# needs to match list in sessionfunctions.py less 'none'
	trimmingmethods = ['conjugated', 'declined']

	if partofspeech not in trimmingmethods:
		return set(listofwords)

	dbconnection = ConnectionObject()
	dbcursor = dbconnection.cursor()

	morphologyobjecdict = {w: lookformorphologymatches(w, dbcursor) for w in listofwords}
	dbconnection.connectioncleanup()

	# {'serius¹': None, 'solacium': <server.hipparchiaobjects.dbtextobjects.dbMorphologyObject object at 0x155362780>, ... }
	possibilitieslistdict = {m: morphologyobjecdict[m].getpossible() for m in morphologyobjecdict if morphologyobjecdict[m]}

	possible = set()
	if partofspeech == 'conjugated':
		possible = {m for m in possibilitieslistdict if True in [p.isconjugatedverb(bagging=baggingmethod) for p in possibilitieslistdict[m]]}

	if partofspeech == 'declined':
		possible = {m for m in possibilitieslistdict if True in [p.isnounoradjective(bagging=baggingmethod) for p in possibilitieslistdict[m]]}

	trimmedlist = set([w for w in listofwords if w in possible])

	return trimmedlist
