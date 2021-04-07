# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from server.formatting.vectorformatting import analogiesgenerateoutput
from server.semanticvectors.gensimnearestneighbors import buildnnvectorspace
from server.semanticvectors.vectorroutehelperfunctions import emptyvectoroutput

JSON_STR = str


def generateanalogies(sentencetuples, workssearched, searchobject, vectorspace) -> JSON_STR:
	"""

	very much in progress

	need a formatting function like nearestneighborgenerateoutput()

	until then this is console only

		most_similar(positive=None, negative=None, topn=10, restrict_vocab=None, indexer=None)
			[analogies; most_similar(positive=['woman', 'king'], negative=['man']) --> queen]

		most_similar_cosmul(positive=None, negative=None, topn=10)
		[analogy finder; most_similar_cosmul(positive=['baghdad', 'england'], negative=['london']) --> iraq]

	:param sentencetuples:
	:param searchobject:
	:param vectorspace:
	:return:
	"""

	so = searchobject
	if not so.lemmaone or not so.lemmatwo or not so.lemmathree:
		return emptyvectoroutput(so, '[did not have three valid lemmata]')
	if not vectorspace:
		vectorspace = buildnnvectorspace(sentencetuples, so)
		if vectorspace == 'failed to build model':
			reasons = [vectorspace]
			return emptyvectoroutput(so, reasons)

	if so.session['baggingmethod'] != 'unlemmatized':
		a = so.lemmaone.dictionaryentry
		b = so.lemmatwo.dictionaryentry
		c = so.lemmathree.dictionaryentry
	else:
		a = so.seeking
		b = so.proximate
		c = so.termthree

	positive = [a, b]
	negative = [c]

	# similarities are less interesting than cosimilarities
	# similarities = vectorspace.wv.most_similar(positive=positive, negative=negative, topn=4)

	try:
		similarities = vectorspace.wv.most_similar(positive=positive, negative=negative, topn=4)
	except KeyError as theexception:
		# KeyError: "word 'terra' not in vocabulary"
		missing = re.search(r'word \'(.*?)\'', str(theexception))
		try:
			similarities = [('"{m}" was missing from the vector space'.format(m=missing.group(1)), 0)]
		except AttributeError:
			similarities = [('[you ended up with an "X not Present" in your results]', 0)]

	try:
		cosimilarities = vectorspace.wv.most_similar_cosmul(positive=positive, negative=negative, topn=5)
	except KeyError as theexception:
		# KeyError: "word 'terra' not in vocabulary"
		missing = re.search(r'word \'(.*?)\'', str(theexception))
		try:
			cosimilarities = [('"{m}" was missing from the vector space'.format(m=missing.group(1)), 0)]
		except AttributeError:
			cosimilarities = [('[you ended up with an "X not Present" in your results]', 0)]

	simlabel = [('<b>similarities</b>', str())]
	cosimlabel = [('<b>cosimilarities</b>', str())]
	similarities = [(s[0], round(s[1], 3)) for s in similarities]
	cosimilarities = [(s[0], round(s[1], 3)) for s in cosimilarities]

	output = simlabel + similarities + cosimlabel + cosimilarities

	# print('generateanalogies() output', output)

	output = analogiesgenerateoutput(searchobject, output)

	# print('generateanalogies() output', output)

	return output
