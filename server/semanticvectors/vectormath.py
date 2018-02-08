# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from collections import defaultdict
from multiprocessing import Manager, Process

from gensim import corpora, models
from gensim.models import Word2Vec
from gensim.similarities.index import AnnoyIndexer

from server.dbsupport.dbfunctions import setthreadcount
from server.hipparchiaobjects.helperobjects import SemanticVectorCorpus

try:
	# import THROWEXCEPTION
	import numpy as np
	from scipy.spatial.distance import cosine as cosinedist
except ImportError:
	print('WARNING: vector math will be slow; install numpy and scipy for exponential speed gains')
	from math import sqrt


def finddotproduct(listofavalues, listofbvalues):
	"""

	(a1 * b1)  + (a2 * b2) + ... (ai * bi)

	:param listofvalues:
	:return:
	"""

	try:
		dotproduct = sum(listofavalues[i] * listofbvalues[i] for i in range(len(listofavalues)))
	except IndexError:
		dotproduct = None

	return dotproduct


def findvectorlength(listofvalues):
	"""

	||α|| = sqrt(α · α)

	:param listofvalues:
	:return:
	"""

	try:
		vlen = np.linalg.norm(listofvalues)
	except NameError:
		# np was not imported
		dotproduct = finddotproduct(listofvalues, listofvalues)
		vlen = sqrt(dotproduct)

	return vlen


def findcosinedist(avalues, lemmavalues, lemmavaluelength):
	"""

	calculate without appeal to scipy or numpy

	'pax' in L:
		scipy - Searched 836 texts and found 21 related terms in 2913 sentences (27.85s)
		noscipy - Did not finish after several minutes

	'pax' in Vergil:
		scipy - Searched 3 texts and found 135 related terms in 46 sentences (2.67s)
		noscipy - Searched 3 texts and found 555 related terms in 46 sentences (14.29s)

	:param avalues:
	:param lemmavalues:
	:return:
	"""

	try:
		cosinevals = finddotproduct(avalues, lemmavalues) / (findvectorlength(avalues) * lemmavaluelength)
	except ZeroDivisionError:
		return None

	return cosinevals


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

	try:
		cosinedist
		lvl = None
	except NameError:
		# we did not import numpy/scipy
		lvl = findvectorlength(lemmavalues)

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

		try:
			cosinevals[w] = cosinedist(avalues, lemmavalues)
		except NameError:
			# we did not import numpy/scipy
			cosinevals[w] = findcosinedist(avalues, lemmavalues, lvl)

	return cosinevals


def buildvectorspace(allheadwords, morphdict, sentences, subtractterm=None):
	"""

	build a vector space of all headwords for all words in all sentences

	for example one sentence of Frogs and Mice is:
		'εἰμὶ δὲ κοῦροϲ Τρωξάρταο πατρὸϲ μεγαλήτοροϲ'

	if you look for 'father' this will turn into:

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
				# WARNING: we are treating homonymns as if 2+ words were there instead of just one
				# 'rectum' will give you 'rectus' and 'rego'; 'res' will give you 'reor' and 'res'
				# this necessarily distorts the vector space
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


def vectorcosinedispatching(focusword, vectorspace, headwords):
	"""

	this is a lot slower than single thread until reconceptualized
		Pool will thow away time on mp locks
		Manager will throw away time on posix.waitpid

	could first send everything out to a berkeleyDB and just read from it?

	at the moment a lot of vectorizing is "fast enough" single threaded

	work this out "later"

	:return:
	"""

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

	try:
		cosinedist
		lvl = None
	except NameError:
		# we did not import numpy/scipy
		lvl = findvectorlength(lemmavalues)

	workpiledict = dict()
	for w in headwords:
		avalues = list()
		for num in numberedsentences:
			avalues.append(vectorspace[num][w])
		workpiledict[w] = (avalues, lemmavalues, lvl)

	manager = Manager()
	managedheadwords = manager.list(headwords)
	cosinevals = manager.dict()

	workers = setthreadcount()

	targetfunction = vectorcosineworker
	argumentuple = (managedheadwords, workpiledict, cosinevals)

	jobs = [Process(target=targetfunction, args=argumentuple) for i in range(workers)]

	for j in jobs:
		j.start()
	for j in jobs:
		j.join()

	# print('cosinevals', cosinevals)

	return dict(cosinevals)


def vectorcosineworker(headwords, workpiledict, resultdict):
	"""

	itemfromworkpile = (avalues, lemmavalues, lemmalength)

	:return:
	"""

	while headwords:
		try:
			headword = headwords.pop()
		except IndexError:
			headword = None

		if headword:
			item = workpiledict[headword]
			avalues = item[0]
			lemmavalues = item[1]
			lemmalength = item[2]

			try:
				cv = cosinedist(avalues, lemmavalues)
			except NameError:
				# scipy not available
				cv = findcosinedist(avalues, lemmavalues, lemmalength)

			resultdict[headword] = cv

	return resultdict


def lsibuildspace(morphdict, sentences):
	"""

	:param allheadwords:
	:param morphdict:
	:param sentences:
	:return:
	"""

	sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
	sentences = [s for s in sentences if s]

	bagsofwords = buildbagsofwords(morphdict, sentences)

	lsidictionary = corpora.Dictionary(bagsofwords)

	lsicorpus = [lsidictionary.doc2bow(bag) for bag in bagsofwords]

	termfreqinversedocfreq = models.TfidfModel(lsicorpus)

	corpustfidf = termfreqinversedocfreq[lsicorpus]

	semanticindex = models.LsiModel(corpustfidf, id2word=lsidictionary, num_topics=350)

	"""	
	"An empirical study of required dimensionality for large-scale latent semantic indexing applications"
	Bradford 2008
	
	For a term-document matrix that has been decomposed via SVD with a non-zero diagonal... 
	
	Dimensionality is reduced by deleting all but the k largest values on 
	this diagonal, together with the corresponding columns in the
	other two matrices. This truncation process is used to generate a
	k-dimensional vector space. Both terms and documents are represented
	by k-dimensional vectors in this vector space.
	
	Landauer and Dumais in 1997: They found that the degree of match 
	between cosine measures in the LSI space and human judgment
	was strongly dependent on k, with a maximum for k = 300
	
	It is clear that there will be a growing degradation of representational
	fidelity as the dimensionality is increased beyond 400. Depending
	upon the application, such behavior may preclude use of
	dimensionality greater than 400.  
	
	recommendations:
	300: thousands to 10s of thousands

	"""

	corpus = SemanticVectorCorpus(semanticindex, corpustfidf, lsidictionary, lsicorpus, bagsofwords, sentences)

	return corpus


def findapproximatenearestneighbors(query, morphdict, sentences):
	"""

	search for points in space that are close to a given query point

	the query should be a dictionary headword

	:param query:
	:param morphdict:
	:param sentences:
	:return:
	"""

	sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
	sentences = [s for s in sentences if s]

	bagsofwords = buildbagsofwords(morphdict, sentences)

	workers = setthreadcount()

	# Note that for a fully deterministically-reproducible run, you must also limit the model to a single worker thread (workers=1), to eliminate ordering jitter from OS thread scheduling.
	model = Word2Vec(bagsofwords, min_count=1, seed=1, workers=workers)
	indexer = AnnoyIndexer(model, 2)
	mostsimilar = model.most_similar(query, topn=10, indexer=indexer)

	return mostsimilar


def findword2vecsimilarities(query, morphdict, sentences):
	"""

	:param query:
	:param morphdict:
	:param sentences:
	:return:
	"""

	sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
	sentences = [s for s in sentences if s]

	bagsofwords = buildbagsofwords(morphdict, sentences)

	workers = setthreadcount()

	# Note that for a fully deterministically-reproducible run, you must also limit the model to a single worker thread (workers=1), to eliminate ordering jitter from OS thread scheduling.
	model = Word2Vec(bagsofwords, min_count=1, seed=1, workers=workers)



	return



def buildbagsofwords(morphdict, sentences):
	"""

	turn a list of sentences into a list of list of headwords

	:param morphdict:
	:param sentences:
	:return:
	"""

	bagsofwords = list()
	for s in sentences:
		lemattized = list()
		for word in s:
			try:
				# WARNING: we are treating homonymns as if 2+ words were there instead of just one
				# 'rectum' will give you 'rectus' and 'rego'; 'res' will give you 'reor' and 'res'
				# this necessarily distorts the vector space
				lemattized.append([item for item in morphdict[word]])
			except KeyError:
				pass
		# flatten
		bagsofwords.append([item for sublist in lemattized for item in sublist])

	prevalence = defaultdict(int)
	for bag in bagsofwords:
		for word in bag:
			prevalence[word] += 1

	bagsofwords = [[w for w in bag if prevalence[w] > 1] for bag in bagsofwords]

	return bagsofwords
