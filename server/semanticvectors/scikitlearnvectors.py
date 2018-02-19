# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import locale
from pprint import pprint
from time import time

try:
	from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer, TfidfVectorizer
	from sklearn.linear_model import SGDClassifier
	from sklearn.model_selection import GridSearchCV
	from sklearn.pipeline import Pipeline
except ImportError:
	print('sklearn is unavailable')
	CountVectorizer = None
	TfidfTransformer = None
	SGDClassifier = None
	GridSearchCV = None
	Pipeline = None

from server import hipparchia
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.vectordispatcher import findheadwords, vectorsentencedispatching
from server.semanticvectors.vectorhelpers import convertmophdicttodict
from server.semanticvectors.vectorpseudoroutes import emptyvectoroutput
from server.startup import authordict, listmapper, workdict


def sklearnselectedworks(activepoll, searchobject):
	"""

	:param activepoll:
	:param searchobject:
	:return:
	"""

	skfunctiontotest = sklearntextfeatureextractionandevaluation
	skfunctiontotest = simplesktextcomparison

	starttime = time()

	so = searchobject

	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c] == 'yes']

	if activecorpora:
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
		so.seeking = r'.'
		sentences = vectorsentencedispatching(so, activepoll)
		output = skfunctiontotest(sentences, activepoll)
	else:
		return emptyvectoroutput(so)

	return output


def sklearntextfeatureextractionandevaluation(sentences, activepoll):
	"""

	see http://scikit-learn.org/stable/auto_examples/model_selection/grid_search_text_feature_extraction.html#sphx-glr-auto-examples-model-selection-grid-search-text-feature-extraction-py


	:return:
	"""

	sentencesaslists = [s.split(' ') for s in sentences]
	allwordsinorder = [item for sublist in sentencesaslists for item in sublist if item]

	morphdict = findheadwords(set(allwordsinorder))
	morphdict = convertmophdicttodict(morphdict)

	headwordsinorder = list()
	for w in allwordsinorder:
		try:
			hwds = [item for item in morphdict[w]]
			headwordsinorder.append('·'.join(hwds))
		except TypeError:
			pass
		except KeyError:
			pass

	pipeline = Pipeline([
		('vect', CountVectorizer()),
		('tfidf', TfidfTransformer()),
		('clf', SGDClassifier()),
	])

	parameters = {
		'vect__max_df': (0.5, 0.75, 1.0),
		# 'vect__max_features': (None, 5000, 10000, 50000),
		'vect__ngram_range': ((1, 1), (1, 2)),  # unigrams or bigrams
		# 'tfidf__use_idf': (True, False),
		# 'tfidf__norm': ('l1', 'l2'),
		'clf__alpha': (0.00001, 0.000001),
		'clf__penalty': ('l2', 'elasticnet'),
		# 'clf__n_iter': (10, 50, 80),
	}

	grid_search = GridSearchCV(pipeline, parameters, n_jobs=-1, verbose=1)

	# categories = [
	# 	'alt.atheism',
	# 	'talk.religion.misc',
	# ]
	#
	# dataset = fetch_20newsgroups(subset='train', categories=categories)
	# print(dataset)

	"""
	done in 65.998s
	
	Best score: 0.935
	Best parameters set:
		clf__alpha: 1e-05
		clf__penalty: 'l2'
		vect__max_df: 0.75
		vect__ngram_range: (1, 2)
	"""

	print("Performing grid search...")
	print("pipeline:", [name for name, _ in pipeline.steps])
	print("parameters:")
	pprint(parameters)
	t0 = time()
	# grid_search.fit(dataset.data, dataset.target)

	print(sentences)
	grid_search.fit(sentences)
	print("done in %0.3fs" % (time() - t0))
	print()

	print("Best score: %0.3f" % grid_search.best_score_)
	print("Best parameters set:")
	best_parameters = grid_search.best_estimator_.get_params()
	for param_name in sorted(parameters.keys()):
		print("\t%s: %r" % (param_name, best_parameters[param_name]))

	return


def simplesktextcomparison(sentences, activepoll):
	"""

	sentences come in as numbered tuples [(id, text), (id2, text2), ...]

	if id is a uid, then you can check matches between works...

	in its simple form this will chack a work against itself (and any other work that
	was on the original searchlist)

	:param sentences:
	:param activepoll:
	:return:
	"""

	sentences = [s[1] for s in sentences if len(s[1].strip().split(' ')) > 1]
	print(sentences)
	tfidf = TfidfVectorizer().fit_transform(sentences)
	pairwisesimilarity = tfidf * tfidf.T  # <class 'scipy.sparse.csr.csr_matrix'>
	# print('pairwisesimilarity', pairwisesimilarity)

	pairwisesimilarity = pairwisesimilarity.tocoo()
	# pwd = {(pairwisesimilarity.row[i], pairwisesimilarity.col[i]): pairwisesimilarity.data[i] for i in range(len(pairwisesimilarity.data))}
	tuples = zip(pairwisesimilarity.row, pairwisesimilarity.col)
	pwd = {t: d for t, d in zip(tuples, pairwisesimilarity.data)}

	pairwise = dict()
	for p in pwd:
		# (1, 3) has the same value in it as does (3, 1)
		# (2, 2) is a comparison of something to itself
		if (p[1], p[0]) not in pairwise.keys() and p[1] != p[0]:
			pairwise[p] = pwd[p]

	mostsimilar = list()
	for pair in sorted(pairwise, key=pairwise.get, reverse=True):
		mostsimilar.append((pair, pairwise[pair]))

	print(mostsimilar[:50])

	for m in mostsimilar[:50]:
		print('score=',m[1])
		print(m[0][0],'s1=', sentences[m[0][0]])
		print(m[0][1],'s2=', sentences[m[0][1]])

	return

