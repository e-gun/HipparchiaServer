# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

import numpy as np
from scipy.spatial.distance import cosine as cosinedist


def finddotproduct(listofavalues, listofbvalues):
	"""

	(a1 * b1)  + (a2 * b2) + ... (ai * bi)

	using numpy instead

	:param listofvalues:
	:return:
	"""

	if len(listofavalues) == len(listofbvalues):
		dotproduct = sum(listofavalues[i] * listofbvalues[i] for i in range(len(listofavalues)))
	else:
		dotproduct = None

	return dotproduct


def findvectorlength(listofvalues):
	"""

	||α|| = sqrt(α · α)

	:param listofvalues:
	:return:
	"""

	# dotproduct = finddotproduct(listofvalues, listofvalues)
	# vlen = sqrt(dotproduct)

	vlen = np.linalg.norm(listofvalues)

	return vlen


def caclulatecosinevalues(focusword, vectorspace, headwords):
	"""

	cos(α,β) = α · β / ||α|| ||β||
	||α|| = sqrt(α · α)
	α = sum([a1, a2, ... ai])

	:param focusword:
	:param vectorspace:
	:param headwords:
	:return:
	"""

	# lengths = dict()
	# for w in headwords:
	# 	vals = list()
	# 	for key in vectorspace.keys():
	# 		vals.append(vectorspace[key][w])
	#
	# 	lengths[w] = findvectorlength(vals)

	numberedsentences = vectorspace.keys()

	lemmavalues = list()

	for num in numberedsentences:
		try:
			lemmavalues.append(vectorspace[num][focusword])
		except KeyError:
			# print('KeyError in caclulatecosinevalues()')
			# we know that the word appears, but it might have been there more than once...
			# we just lost that information when the KeyError bit
			lemmavalues.append(1)

	cosinevals = dict()
	for w in headwords:
		avalues = list()
		for num in numberedsentences:
			avalues.append(vectorspace[num][w])
		# print(avalues, ',', lemmavalues, w)
		# scipy will choke if you send it div-by-zero data
		# RuntimeWarning: invalid value encountered in true_divide dist = 1.0 - np.dot(u, v) / (norm(u) * norm(v))
		# be careful not to end up with 0 in lemmavalues with 'voluptas' becuase of the 'v-for-u' issue
		# print('w/av/bv', sum(avalues), sum(lemmavalues), '({w})'.format(w=w))
		if sum(avalues) != 0:
			cosinevals[w] = cosinedist(avalues, lemmavalues)
		else:
			cosinevals[w] = None

	return cosinevals


def buildvectorspace(allheadwords, morphdict, sentences, subtractterm=None):
	"""

	build a vector space of all headwords for all words in all sentences

	for example one sentence of Frogs and Mice is:
		'εἰμὶ δὲ κοῦροϲ Τρωξάρταο πατρὸϲ μεγαλήτοροϲ'

	this will turn into:

	{'ἐλαιόω': 0, 'ἔλαιον': 0, 'ἔλαιοϲ': 0, 'μέγαϲ': 0, 'πόντοϲ': 0, 'κῆρυξ': 0,
	'ὄχθη': 0, 'κοῦροϲ': 1, 'κόροϲ': 1, 'Τρωξάρτηϲ': 1, 'τείρω': 0, 'πω': 0,
	'ἄρα': 0, 'μῦϲ': 0, 'ὑπό': 0, 'κηρύϲϲω': 0, 'ἀνατρέφω': 0, 'πατήρ': 0,
	'ὄρθροϲ': 0, 'Ὑδρομέδουϲα': 0, 'ἀνήρ': 0, 'ἀνδρόω': 0, 'νοέω': 0, 'ϲθένοϲ': 0,
	'νῦν': 0, 'βλάπτω': 0, 'νεκρόϲ': 0, 'ἐπαρωγόϲ': 0, 'κακόϲ': 0, 'δῶμα': 0, 'μέϲοϲ': 0,
	 'δέμαϲ': 0, 'ϲτέμμα': 0, 'μίγνυμι': 0, 'οὐδόϲ': 0, 'οὐδέ': 0, 'φιλότηϲ': 0,
	 'κελεύω': 0, 'ὀξύϲ': 0, 'ἀγορήνδε': 0, 'Ἠριδανόϲ': 0, 'πολύϲ': 0, 'τλήμων': 0,
	 'ἐπεί': 0, 'δύϲτηνοϲ': 0, 'παρά': 0, 'πηρόϲ': 0, 'ἐκτελέω': 0, 'ἐπινήχομαι': 0,
	  'ἄν¹': 0, 'λύχνοϲ': 0, 'λίμνη': 0, 'ἤδη': 0, 'ἦδοϲ': 0, 'θεάω': 0, 'θεά': 0,
	  'θέα': 0, 'θεόϲ': 0, 'ἐάν': 0, 'ἄν²': 0, 'ἀνά': 0, 'μεγαλήτωρ': 1, 'Πηλεύϲ':
	  0, 'ἑόϲ': 0, 'ὕπτιοϲ': 0, 'τότε': 0, 'ἐκ-ἁπλόω': 0, 'ἔρδω': 0, 'ἕνεκα': 0}

	a lemmatized search should not include the subtractterm (since it is unlikely to be a headword)

	:param allheadwords:
	:param morphdict:
	:param sentences:
	:return:
	"""

	vectorspace = dict()
	vectormapper = dict()
	extracount = dict()

	for n, s in enumerate(sentences):
		if subtractterm:
			# pull it out because it will not lemmatize
			# and then allheadwords.keys() will thrown an exception
			# note that if you have the same word 2x in an sentence we just lost count of that...
			extracount[n] = len(re.findall(subtractterm, s))
			s = re.sub(subtractterm, '', s)
		words = s.split(' ')
		vectormapper[n] = [w for w in words if w]

	for n, wordlist in vectormapper.items():
		vectorspace[n] = {w: 0 for w in allheadwords.keys()}

		headwords = list()
		for w in wordlist:
			try:
				countable = [item for item in morphdict[w]]
			except KeyError:
				# 'καί', etc. are skipped
				countable = list()
			headwords += countable

		for h in headwords:
			vectorspace[n][h] += 1

		if subtractterm:
			vectorspace[n][subtractterm] = extracount[n]

	return vectorspace