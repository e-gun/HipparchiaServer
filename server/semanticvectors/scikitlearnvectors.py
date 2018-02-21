# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
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
from server.semanticvectors.vectorhelpers import convertmophdicttodict, convertsingleuidtodblineobject
from server.semanticvectors.vectorpseudoroutes import emptyvectoroutput
from server.formatting.vectorformatting import skformatmostimilar
from server.formatting.jsformatting import insertbrowserclickjs
from server.startup import authordict, listmapper, workdict
from server.dbsupport.dbfunctions import setconnection
from server.formatting.bibliographicformatting import bcedating


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
	so.vectortype = 'sentencesimilarity'

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
		sentencetuples = vectorsentencedispatching(so, activepoll)
		if len(sentencetuples) > hipparchia.config['MAXSENTENCECOMPARISONSPACE']:
			reasons = ['scope of search exceeded allowed maximum: {a} > {b}'.format(a=len(sentencetuples), b=hipparchia.config['MAXSENTENCECOMPARISONSPACE'])]
			return emptyvectoroutput(so, reasons)
		similaritiesdict = skfunctiontotest(sentencetuples, activepoll)
		# similaritiesdict: {id: (scoreA, lindobjectA1, sentA1, lindobjectA2, sentA2), id2: (scoreB, lindobjectB1, sentB1, lindobjectB2, sentB2), ... }
		corehtml = skformatmostimilar(similaritiesdict)
		output = generatesimilarsentenceoutput(corehtml, so, activepoll, starttime, workssearched, len(similaritiesdict))
	else:
		return emptyvectoroutput(so)

	return output


def generatesimilarsentenceoutput(corehtml, searchobject, activepoll, starttime, workssearched, matches):
	"""

	:param corehtml:
	:param searchobject:
	:return:
	"""

	so = searchobject
	dmin, dmax = bcedating(so.session)

	findsjs = insertbrowserclickjs('browser')

	searchtime = time() - starttime
	searchtime = round(searchtime, 2)
	workssearched = locale.format('%d', workssearched, grouping=True)

	output = dict()
	output['title'] = 'Similar sentences'
	output['found'] = corehtml
	output['js'] = findsjs
	output['resultcount'] = '{n} sentences above the cutoff'.format(n=matches)
	output['scope'] = workssearched
	output['searchtime'] = str(searchtime)
	output['proximate'] = ''

	if so.lemma:
		all = 'all forms of »{skg}«'.format(skg=lm)
	else:
		all = ''
	if so.proximatelemma:
		near = ' all forms of »{skg}«'.format(skg=pr)
	else:
		near = ''
	output['thesearch'] = '{all}{near}'.format(all=all, near=near)

	if so.lemma:
		all = 'all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.lemma.formlist), skg=lm)
	else:
		all = ''
	if so.proximatelemma:
		near = ' and all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.proximatelemma.formlist), skg=pr)
	else:
		near = ''
	output['htmlsearch'] = '{all}{near}'.format(all=all, near=near)
	output['hitmax'] = ''
	output['onehit'] = ''
	output['sortby'] = 'proximity'
	output['dmin'] = dmin
	output['dmax'] = dmax

	activepoll.deactivate()

	output = json.dumps(output)

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


def simplesktextcomparison(sentencetuples, activepoll):
	"""

	sentences come in as numbered tuples [(id, text), (id2, text2), ...]

	if id is a uid, then you can check matches between works...

	in its simple form this will check a work against itself (and any other work that
	was on the original searchlist)

	:param sentences:
	:param activepoll:
	:return:
	"""

	cap = 50
	mustbelongerthan = 2
	cutoff = .2
	antianaphora = 3
	avoidinternalxrefs = True
	avoidauthorxrefs = False

	sentencetuples = [s for s in sentencetuples if len(s[1].strip().split(' ')) > mustbelongerthan]
	sentences = [s[1] for s in sentencetuples]

	activepoll.statusis('Calculating tfidf for {n} sentences'.format(n=len(sentences)))
	tfidf = TfidfVectorizer().fit_transform(sentences)
	activepoll.statusis('Calculating pairwise similarity for {n} sentences'.format(n=len(sentences)))
	pairwisesimilarity = tfidf * tfidf.T  # <class 'scipy.sparse.csr.csr_matrix'>
	# print('pairwisesimilarity', pairwisesimilarity)

	pairwisesimilarity = pairwisesimilarity.tocoo()
	# pwd = {(pairwisesimilarity.row[i], pairwisesimilarity.col[i]): pairwisesimilarity.data[i] for i in range(len(pairwisesimilarity.data))}
	tuples = zip(pairwisesimilarity.row, pairwisesimilarity.col)
	pwd = {t: d for t, d in zip(tuples, pairwisesimilarity.data)}

	activepoll.statusis('Fetching and sifting results'.format(n=len(sentences)))
	pairwise = dict()
	for p in pwd:
		# (1, 3) has the same value in it as does (3, 1)
		# (2, 2) is a comparison of something to itself
		if (p[1], p[0]) not in pairwise.keys() and p[1] != p[0]:
			pairwise[p] = pwd[p]

	mostsimilar = list()
	for pair in sorted(pairwise, key=pairwise.get, reverse=True):
		mostsimilar.append((pair, pairwise[pair]))

	mostsimilar = [m for m in mostsimilar if m[1] > cutoff]
	mostsimilar = mostsimilar[:cap]

	# for m in mostsimilar[:50]:
	# 	print('score=', m[1])
	# 	print(sentencetuples[m[0][0]][0],'s1=', sentences[m[0][0]])
	# 	print(sentencetuples[m[0][1]][0],'s2=', sentences[m[0][1]])

	dbconnection = setconnection('autocommit', readonlyconnection=False)
	cursor = dbconnection.cursor()

	similaritiesdict = {id: (m[1], convertsingleuidtodblineobject(sentencetuples[m[0][0]][0], cursor), sentences[m[0][0]],
	                         convertsingleuidtodblineobject(sentencetuples[m[0][1]][0], cursor), sentences[m[0][1]])
	               for id, m in enumerate(mostsimilar)}

	# {id: (scoreA, lineobjectA1, sentA1, lineobjectA2, sentA2), id2: (scoreB, lineobjectB1, sentB1, lineobjectB2, sentB2), ... }

	cursor.close()
	dbconnection.close()
	del dbconnection


	if avoidinternalxrefs:
		similaritiesdict = {s: similaritiesdict[s] for s in similaritiesdict
		                    if similaritiesdict[s][1].wkuinversalid != similaritiesdict[s][3].wkuinversalid}

	if avoidauthorxrefs:
		similaritiesdict = {s: similaritiesdict[s] for s in similaritiesdict
		                    if similaritiesdict[s][1].authorid != similaritiesdict[s][3].authorid}

	if antianaphora > 0:
		anaphoratracker = set()
		trimmedsd = dict()
		for s in similaritiesdict:
			for item in [similaritiesdict[s][1], similaritiesdict[s][3]]:
				wk = item.wkuinversalid
				testzone = range(item.index - antianaphora, item.index + antianaphora)
				test = set(['{w}_LN_{i}'.format(w=wk, i=t) for t in testzone])
				if anaphoratracker - test != anaphoratracker:
					pass
				else:
					trimmedsd[s] = similaritiesdict[s]
					anaphoratracker.add(item.universalid)
	else:
		trimmedsd = similaritiesdict


	return trimmedsd
