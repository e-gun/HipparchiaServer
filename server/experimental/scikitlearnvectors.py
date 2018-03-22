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
	from sklearn.decomposition import NMF, LatentDirichletAllocation, TruncatedSVD

except ImportError:
	print('sklearn is unavailable')
	CountVectorizer = None
	TfidfTransformer = None
	SGDClassifier = None
	GridSearchCV = None
	Pipeline = None

try:
	# will hurl out a bunch of DeprecationWarning messages at the moment...
	import pyLDAvis
	import pyLDAvis.sklearn as ldavis
except ImportError:
	print('pyLDAvis is not available')
	pyLDAvis = None
	ldavis = None

from server import hipparchia
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.vectorhelpers import buildflatbagsofwords, buildbagsofwordswithalternates, convertmophdicttodict, mostcommonwords
from server.dbsupport.dblinefunctions import grablistoflines
from server.semanticvectors.vectorpseudoroutes import emptyvectoroutput
from server.formatting.vectorformatting import skformatmostimilar
from server.formatting.jsformatting import insertbrowserclickjs
from server.startup import authordict, listmapper, workdict
from server.formatting.bibliographicformatting import bcedating
from server.textsandindices.textandindiceshelperfunctions import getrequiredmorphobjects

def sklearnselectedworks(searchobject):
	"""

	:param activepoll:
	:param searchobject:
	:return:
	"""

	skfunctiontotest = sklearntextfeatureextractionandevaluation
	skfunctiontotest = simplesktextcomparison
	skfunctiontotest = ldatopicmodeling
	skfunctiontotest = ldatopicgraphing

	so = searchobject
	activepoll = so.poll

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

		# if skfunctiontotest == ldatopicgraphing:
		# 	so.sentencebundlesize = 2

		sentencetuples = vectorprepdispatcher(so)
		if len(sentencetuples) > hipparchia.config['MAXSENTENCECOMPARISONSPACE']:
			reasons = ['scope of search exceeded allowed maximum: {a} > {b}'.format(a=len(sentencetuples), b=hipparchia.config['MAXSENTENCECOMPARISONSPACE'])]
			return emptyvectoroutput(so, reasons)
		similaritiesdict = skfunctiontotest(sentencetuples, so)

		if skfunctiontotest == ldatopicgraphing:
			# kludge for now: this is already html
			corehtml = similaritiesdict
			return corehtml

		# similaritiesdict: {id: (scoreA, lindobjectA1, sentA1, lindobjectA2, sentA2), id2: (scoreB, lindobjectB1, sentB1, lindobjectB2, sentB2), ... }
		corehtml = skformatmostimilar(similaritiesdict)
		output = generatesimilarsentenceoutput(corehtml, so, workssearched, len(similaritiesdict))
	else:
		return emptyvectoroutput(so)

	return output


def generatesimilarsentenceoutput(corehtml, searchobject, workssearched, matches):
	"""

	:param corehtml:
	:param searchobject:
	:return:
	"""

	so = searchobject
	activepoll = so.poll
	dmin, dmax = bcedating(so.session)

	findsjs = insertbrowserclickjs('browser')

	searchtime = so.getelapsedtime()
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
		allforms = 'all forms of »{skg}«'.format(skg=so.lemma)
	else:
		allforms = ''
	if so.proximatelemma:
		near = ' all forms of »{skg}«'.format(skg=so.proximatelemma)
	else:
		near = ''
	output['thesearch'] = '{af}{near}'.format(af=allforms, near=near)

	if so.lemma:
		allforms = 'all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.lemma.formlist), skg=lm)
	else:
		allforms = ''
	if so.proximatelemma:
		near = ' and all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.proximatelemma.formlist), skg=pr)
	else:
		near = ''
	output['htmlsearch'] = '{af}{near}'.format(af=allforms, near=near)
	output['hitmax'] = ''
	output['onehit'] = ''
	output['sortby'] = 'proximity'
	output['dmin'] = dmin
	output['dmax'] = dmax

	activepoll.deactivate()

	output = json.dumps(output)

	return output


def sklearntextfeatureextractionandevaluation(sentences, searchobject):
	"""

	see http://scikit-learn.org/stable/auto_examples/model_selection/grid_search_text_feature_extraction.html#sphx-glr-auto-examples-model-selection-grid-search-text-feature-extraction-py

	and

	http://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction

	:return:
	"""

	sentencesaslists = [s.split(' ') for s in sentences]
	allwordsinorder = [item for sublist in sentencesaslists for item in sublist if item]

	morphdict = getrequiredmorphobjects(set(allwordsinorder))
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


def simplesktextcomparison(sentencetuples, searchobject):
	"""

	sentences come in as numbered tuples [(id, text), (id2, text2), ...]

	if id is a uid, then you can check matches between works...

	in its simple form this will check a work against itself (and any other work that
	was on the original searchlist)

	:param sentencetuples:
	:param searchobject:
	:return:
	"""

	activepoll = searchobject.poll

	cap = 50
	mustbelongerthan = 2
	cutoff = .2
	antianaphora = 3
	avoidinternalxrefs = False
	avoidauthorxrefs = False
	avoidcommonwords = True

	sentencetuples = [s for s in sentencetuples if len(s[1].strip().split(' ')) > mustbelongerthan]
	sentences = [s[1] for s in sentencetuples]

	if avoidcommonwords:
		stopwords = mostcommonwords()
		cleanedsentences = list()
		for s in sentences:
			swords = s.split(' ')
			cleanedsentences.append(' '.join([s for s in swords if s not in stopwords]))
	else:
		cleanedsentences = sentences

	activepoll.statusis('Calculating tfidf for {n} sentences'.format(n=len(sentences)))
	#vectorizer = TfidfVectorizer(stop_words=stopwords)
	vectorizer = TfidfVectorizer()
	tfidf = vectorizer.fit_transform(cleanedsentences)
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

	# this is slow if you do one-by-one db transactions
	# should find out all the lines you need from a table and fetch all at once...
	needlines = [sentencetuples[m[0][0]][0] for m in mostsimilar]
	needlines += [sentencetuples[m[0][1]][0] for m in mostsimilar]
	needtables = set([uid[:6] for uid in needlines])

	activepoll.statusis('Fetching...'.format(n=len(sentences)))
	gabbedlineobjects = list()
	for t in needtables:
		fetchlines = [l for l in needlines if l[:6] == t]
		gabbedlineobjects += grablistoflines(t, fetchlines)

	activepoll.statusis('Sifting...'.format(n=len(sentences)))
	linemapper = {l.universalid.lower(): l for l in gabbedlineobjects}

	similaritiesdict = {id: (m[1], linemapper[sentencetuples[m[0][0]][0]], sentences[m[0][0]],
						linemapper[sentencetuples[m[0][1]][0]], sentences[m[0][1]])
						for id, m in enumerate(mostsimilar)}

	# {id: (scoreA, lineobjectA1, sentA1, lineobjectA2, sentA2), id2: (scoreB, lineobjectB1, sentB1, lineobjectB2, sentB2), ... }

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


def print_top_words(model, feature_names, n_top_words):
	for topic_idx, topic in enumerate(model.components_):
		message = "Topic #%d: " % topic_idx
		message += " ".join([feature_names[i]
		                     for i in topic.argsort()[:-n_top_words - 1:-1]])
		print(message)
	print()

	return


def ldatopicmodeling(sentencetuples, searchobject):
	"""

	see:
		http://scikit-learn.org/stable/auto_examples/applications/plot_topics_extraction_with_nmf_lda.html#sphx-glr-auto-examples-applications-plot-topics-extraction-with-nmf-lda-py

	CountVectorizer:
	max_df : float in range [0.0, 1.0] or int, default=1.0
		When building the vocabulary ignore terms that have a document frequency strictly higher than the given threshold (corpus-specific stop words).

	min_df : float in range [0.0, 1.0] or int, default=1
		When building the vocabulary ignore terms that have a document frequency strictly lower than the given threshold. This value is also called cut-off in the literature.

	see sample results at end of file

	:param sentencetuples:
	:param activepoll:
	:return:
	"""

	maxfeatures = 2000
	components = 15
	topwords = 15

	maxfreq = .60
	minfreq = 5
	iterations = 12

	mustbelongerthan = 2

	sentencetuples = [s for s in sentencetuples if len(s[1].strip().split(' ')) > mustbelongerthan]
	sentences = [s[1] for s in sentencetuples]

	sentencesaslists = [s.split(' ') for s in sentences]
	allwordsinorder = [item for sublist in sentencesaslists for item in sublist if item]

	morphdict = getrequiredmorphobjects(set(allwordsinorder))
	morphdict = convertmophdicttodict(morphdict)

	# going forward we we need a list of lists of headwords
	# there are two ways to do this:
	#   'ϲυγγενεύϲ ϲυγγενήϲ' vs 'ϲυγγενεύϲ·ϲυγγενήϲ'

	bagofwordsfunction = buildflatbagsofwords
	# bagofwordsfunction = buildbagsofwordswithalternates

	bagsofwordlists = bagofwordsfunction(morphdict, sentencesaslists)
	bagsofsentences = [' '.join(b) for b in bagsofwordlists]

	# Use tf (raw term count) features for LDA.
	ldavectorizer = CountVectorizer(max_df=maxfreq,
									min_df=minfreq,
									max_features=maxfeatures)

	ldavectorized = ldavectorizer.fit_transform(bagsofsentences)

	lda = LatentDirichletAllocation(n_components=components,
									max_iter=iterations,
									learning_method='online',
									learning_offset=50.,
									random_state=0)

	lda.fit(ldavectorized)

	print("\nTopics in LDA model:")
	tf_feature_names = ldavectorizer.get_feature_names()
	print_top_words(lda, tf_feature_names, topwords)

	# Use tf-idf features for NMF.
	tfidfvectorizer = TfidfVectorizer(max_df=0.95, min_df=2,
	                                   max_features=maxfeatures)

	tfidf = tfidfvectorizer.fit_transform(bagsofsentences)

	# Fit the NMF model
	nmf = NMF(n_components=components,
				random_state=1,
				alpha=.1,
				l1_ratio=.5).fit(tfidf)

	print("\nTopics in NMF model (Frobenius norm):")
	tfidffeaturenames = tfidfvectorizer.get_feature_names()
	print_top_words(nmf, tfidffeaturenames, topwords)

	# Fit the NMF model
	print("Fitting the NMF model (generalized Kullback-Leibler divergence) with "
	      "tf-idf features, n_samples=%d and n_features=%d..."
	      % (len(sentences), maxfeatures))

	nmf = NMF(n_components=components,
				random_state=1,
				beta_loss='kullback-leibler',
				solver='mu',
				max_iter=1000,
				alpha=.1,
				l1_ratio=.5).fit(tfidf)

	print("\nTopics in NMF model (generalized Kullback-Leibler divergence):")
	tfidffeaturenames = tfidfvectorizer.get_feature_names()
	print_top_words(nmf, tfidffeaturenames, topwords)

	return


def ldatopicgraphing(sentencetuples, searchobject):
	"""

	see:
		http://scikit-learn.org/stable/auto_examples/applications/plot_topics_extraction_with_nmf_lda.html#sphx-glr-auto-examples-applications-plot-topics-extraction-with-nmf-lda-py

	see also:

		https://nlpforhackers.io/topic-modeling/

	CountVectorizer:
	max_df : float in range [0.0, 1.0] or int, default=1.0
	    When building the vocabulary ignore terms that have a document frequency strictly higher than the given threshold (corpus-specific stop words).

	min_df : float in range [0.0, 1.0] or int, default=1
	    When building the vocabulary ignore terms that have a document frequency strictly lower than the given threshold. This value is also called cut-off in the literature.


	see:
		https://stackoverflow.com/questions/27697766/understanding-min-df-and-max-df-in-scikit-countvectorizer#35615151

	max_df is used for removing terms that appear too frequently, also known as "corpus-specific stop words". For example:

		max_df = 0.50 means "ignore terms that appear in more than 50% of the documents".
		max_df = 25 means "ignore terms that appear in more than 25 documents".

	The default max_df is 1.0, which means "ignore terms that appear in more than 100% of the documents". Thus, the default setting does not ignore any terms.

	min_df is used for removing terms that appear too infrequently. For example:

		min_df = 0.01 means "ignore terms that appear in less than 1% of the documents".
		min_df = 5 means "ignore terms that appear in less than 5 documents".

	The default min_df is 1, which means "ignore terms that appear in less than 1 document". Thus, the default setting does not ignore any terms.

	notes:
		maxfreq of 1 will give you a lot of excessively common words: 'this', 'that', etc.
		maxfreq of

	on the general issue of graphing see also:
		https://speakerdeck.com/bmabey/visualizing-topic-models
		https://de.dariah.eu/tatom/topic_model_visualization.html

	on the axes:
		https://stats.stackexchange.com/questions/222/what-are-principal-component-scores

	:param sentencetuples:
	:param activepoll:
	:return:
	"""
	activepoll = searchobject.poll

	maxfeatures = 2000
	components = 15  # topics

	maxfreq = .75   # but .60 seems nice...
	minfreq = 5
	iterations = 12

	mustbelongerthan = 3

	sentencetuples = [s for s in sentencetuples if len(s[1].strip().split(' ')) > mustbelongerthan]
	sentences = [s[1] for s in sentencetuples]

	sentencesaslists = [s.split(' ') for s in sentences]
	allwordsinorder = [item for sublist in sentencesaslists for item in sublist if item]

	activepoll.statusis('Finding all headwords')
	morphdict = getrequiredmorphobjects(set(allwordsinorder))
	morphdict = convertmophdicttodict(morphdict)

	activepoll.statusis('Building bags of words')
	# going forward we we need a list of lists of headwords
	# there are two ways to do this:
	#   'ϲυγγενεύϲ ϲυγγενήϲ' vs 'ϲυγγενεύϲ·ϲυγγενήϲ'

	bagofwordsfunction = buildflatbagsofwords
	# bagofwordsfunction = buildbagsofwordswithalternates

	bagsofwordlists = bagofwordsfunction(morphdict, sentencesaslists)
	bagsofsentences = [' '.join(b) for b in bagsofwordlists]

	# print('bagsofsentences[:3]', bagsofsentences[3:])

	activepoll.statusis('Running the LDA vectorizer')
	# Use tf (raw term count) features for LDA.
	ldavectorizer = CountVectorizer(max_df=maxfreq,
									min_df=minfreq,
									max_features=maxfeatures)

	ldavectorized = ldavectorizer.fit_transform(bagsofsentences)

	ldamodel = LatentDirichletAllocation(n_components=components,
										max_iter=iterations,
										learning_method='online',
										learning_offset=50.,
										random_state=0)

	ldamodel.fit(ldavectorized)

	visualisation = ldavis.prepare(ldamodel, ldavectorized, ldavectorizer)
	pyLDAvis.save_html(visualisation, 'ldavis.html')
	ldavishtml = pyLDAvis.prepared_data_to_html(visualisation)

	return ldavishtml


"""

ldatopicmodeling() sample results

===

maxfeatures = 1000
components = 15
topwords = 15

maxfreq = .66
minfreq = 5
iterations = 15

Topics in LDA model:
Topic #0: superus summus amicus¹ summum summa amicus² amicus possum tantus habeo autem vir dedo dico² nam
Topic #1: suus suum sua bellum bellus suo rex possum nam lacedaemonius lacedaemonii volo¹ atheniensis athenienses omnis
Topic #2: habeo adverto adverro filius adversus populus¹ populus² natus natus¹ adversus² utor nascor pater natus² bellus
Topic #3: malus malus¹ malus³ malus² fortuna malum malum² fortuno desero² per ante paucus pauci gero¹ desertus
Topic #4: proficiscor proficio profectus³ lego¹ legatus proficisco pervenio mitto advenio adventus fio legatum dico² epaminondas fallo
Topic #5: possum statuo forus¹ forum¹ forus forum statua potens noster potentia¹ convenio pono corrumpo sepelio memoria
Topic #6: publicus publica publicum publico licet liceo¹ liceor possum persequor familia conicio quisquam polliceor diu vinculum
Topic #7: pario² modus par modo parus¹ pario³ pareo morior mortuus talis paro² paro¹ ubi talus respondeo
Topic #8: locum locus loco sero¹ facio arma dies satis sata satum armo hostis possum reliquus adversarius
Topic #9: multus multa multi multo² multa¹ mille potis possum milium post annus duco dio dux privo
Topic #10: exercitus² exerceo exercio capio capio¹ interficio interfacio castra castrum jam hostis castro navis adeo² adeo¹
Topic #11: primus prima nitor¹ proelium nisi apud proelio proelior nam regius communis audeo cado liber¹ commune
Topic #12: magus² magis magis² vita versor perpetuus verso perpetuum tantus perpetuo² plerus pleo consul do consulo
Topic #13: confacio conficio quaero setius nihilum poena quare vix aedes concito quidem multitudo tantus afficio patrium
Topic #14: facio factum factus² capio¹ capio caput capitum tempus pecunia damno classis oppugno¹ oppugno² judicium oppidum


Topics in NMF model (Frobenius norm):
Topic #0: possum habeo nam enim tantus autem utor video dico² modus tempus omnis capio capio¹ parvus
Topic #1: suus suum sua suo sus civis proficiscor adventus advenio pars domus video do tueor potestas
Topic #2: facio factum factus² timor opprimo classis tempus brevis deduco imprudens celer¹ lego² imperator coepio ullus
Topic #3: multus multa multi multa¹ multo² valeo plurimus post tamen bonum virtus pars bonus societas mille
Topic #4: bellus bellum gero¹ pax persequor pario³ pario² gesta indico² inter proficisco proficiscor administro tempus coepio
Topic #5: exercitus² exerceo exercio mitto apud praesum praetor miles interficio interfacio filius proelium occaedes occido¹ hostis
Topic #6: solus¹ solus solum¹ sol etiam timor plurimus efficio defendo princeps graecia athenae quisquam atticus regio
Topic #7: patrius¹ patrius² patria patrium fero nam libero tamen tyrannus duco possum restituo expello revoco civis
Topic #8: locum locus loco hostis dies castrum castra rogo castro uno urbs copia¹ manus¹ pono idoneus
Topic #9: publicus publica publicum publico carthago possum quisquam totus¹ totus² vinclum vinculum civitas populus¹ populus² numquam
Topic #10: rex rego lacedaemonius lacedaemonii regius mitto imperium agesilaus permulceo datames ops¹ artaxerxes praefectus¹ praefectus ceter
Topic #11: atheniensis athenienses lacedaemonii lacedaemonius filius chabrias themistocles alcibiades restituo apud civitas classis lysander socius timotheus
Topic #12: superus summus summa summum imperium sic laus apud defero aurum seleucus dimico trado fero milito
Topic #13: sero¹ sata satis satum reliquus audio tutum praesidium unus inquam gratia tueor admiror thebani thebanus
Topic #14: adverto adverro adversus adversus² adversum² datames copia¹ miles fortuna italia suscipio secundus¹ antigonus milito fortuno

Fitting the NMF model (generalized Kullback-Leibler divergence) with tf-idf features, n_samples=1560 and n_features=1000...

Topics in NMF model (generalized Kullback-Leibler divergence):
Topic #0: tempus tantus tum nam video nullus nitor¹ tam nisi parvus possum nemo quidem quantus peto
Topic #1: suus suum sua suo sus possum civis vivo tueor video tamen advenio enim adventus vinco
Topic #2: facio factum factus² possum volo¹ quare imperator uter lego² pervenio studeo timor athenae forus¹ utrum
Topic #3: multus multi possum multa multo² multa¹ parvus vivo eumenes dionysius cicero vir plurimus liber¹ dio
Topic #4: bellum bellus gero¹ persequor valeo multus paucus facio pauci gesta peloponnesius indico² dux pauca setius
Topic #5: exercitus² exerceo mitto exercio interfacio interficio navis classis jam praeficio praesum navo consul duco barbarus
Topic #6: atheniensis athenienses lacedaemonius lacedaemonii etiam solus¹ solus solum¹ sol graecia atticus opera propter alcibiades opus¹
Topic #7: patrius² patrius¹ patria possum hostis pugno tamen arma castrum libero castra fero armo adversarius audeo
Topic #8: locus locum utor usus² loco volo¹ uto par divus video dies manus¹ modus urbs parus¹
Topic #9: publicus publicum publica possum populus¹ populus² capio ibi capio¹ publico redeo indo inde revorto totus¹
Topic #10: proficiscor dico² habeo autem proficio magus² rex enim magis² magis proficisco profectus³ video morior volo¹
Topic #11: nam rex rego ceter consilium ceterus regius pario² capio¹ ceterum capio consilior jubeo sequor talis
Topic #12: superus summus omnis omnes sic unus summa summum nemo modus virtus uno modo fides¹ vita
Topic #13: primus filius prima sero¹ natus natus¹ natus² animus satum satis sata nascor annus pater fortuna
Topic #14: apud proelium adverro adverto amicus¹ adversus amicus amicus² adversus² proelior proelio accido² accido¹ secundus¹ liceor


===

components = 15
topwords = 15

maxfreq = .50
minfreq = 5
iterations = 15

Topics in LDA model:
Topic #0: superus summus amicus¹ summum summa amicus² amicus possum tantus habeo autem vir dedo dico² nam
Topic #1: suus suum sua bellum bellus suo rex possum nam lacedaemonius lacedaemonii volo¹ atheniensis athenienses omnis
Topic #2: habeo adverto adverro filius adversus populus¹ populus² natus natus¹ adversus² utor nascor pater natus² bellus
Topic #3: malus malus¹ malus³ malus² fortuna malum malum² fortuno desero² per ante paucus pauci gero¹ desertus
Topic #4: proficiscor proficio profectus³ lego¹ legatus proficisco pervenio mitto advenio adventus fio legatum dico² epaminondas fallo
Topic #5: possum statuo forus¹ forum¹ forus forum statua potens noster potentia¹ convenio pono corrumpo sepelio memoria
Topic #6: publicus publica publicum publico licet liceo¹ liceor possum persequor familia conicio quisquam polliceor diu vinculum
Topic #7: pario² modus par modo parus¹ pario³ pareo morior mortuus talis paro² paro¹ ubi talus respondeo
Topic #8: locum locus loco sero¹ facio arma dies satis sata satum armo hostis possum reliquus adversarius
Topic #9: multus multa multi multo² multa¹ mille potis possum milium post annus duco dio dux privo
Topic #10: exercitus² exerceo exercio capio capio¹ interficio interfacio castra castrum jam hostis castro navis adeo² adeo¹
Topic #11: primus prima nitor¹ proelium nisi apud proelio proelior nam regius communis audeo cado liber¹ commune
Topic #12: magus² magis magis² vita versor perpetuus verso perpetuum tantus perpetuo² plerus pleo consul do consulo
Topic #13: confacio conficio quaero setius nihilum poena quare vix aedes concito quidem multitudo tantus afficio patrium
Topic #14: facio factum factus² capio¹ capio caput capitum tempus pecunia damno classis oppugno¹ oppugno² judicium oppidum


Topics in NMF model (Frobenius norm):
Topic #0: possum habeo nam enim tantus autem utor video dico² modus tempus omnis capio capio¹ parvus
Topic #1: suus suum sua suo sus civis proficiscor adventus advenio pars domus video do tueor potestas
Topic #2: facio factum factus² timor opprimo classis tempus brevis deduco imprudens celer¹ lego² imperator coepio ullus
Topic #3: multus multa multi multa¹ multo² valeo plurimus post tamen bonum virtus pars bonus societas mille
Topic #4: bellus bellum gero¹ pax persequor pario³ pario² gesta indico² inter proficisco proficiscor administro tempus coepio
Topic #5: exercitus² exerceo exercio mitto apud praesum praetor miles interficio interfacio filius proelium occaedes occido¹ hostis
Topic #6: solus¹ solus solum¹ sol etiam timor plurimus efficio defendo princeps graecia athenae quisquam atticus regio
Topic #7: patrius¹ patrius² patria patrium fero nam libero tamen tyrannus duco possum restituo expello revoco civis
Topic #8: locum locus loco hostis dies castrum castra rogo castro uno urbs copia¹ manus¹ pono idoneus
Topic #9: publicus publica publicum publico carthago possum quisquam totus¹ totus² vinclum vinculum civitas populus¹ populus² numquam
Topic #10: rex rego lacedaemonius lacedaemonii regius mitto imperium agesilaus permulceo datames ops¹ artaxerxes praefectus¹ praefectus ceter
Topic #11: atheniensis athenienses lacedaemonii lacedaemonius filius chabrias themistocles alcibiades restituo apud civitas classis lysander socius timotheus
Topic #12: superus summus summa summum imperium sic laus apud defero aurum seleucus dimico trado fero milito
Topic #13: sero¹ sata satis satum reliquus audio tutum praesidium unus inquam gratia tueor admiror thebani thebanus
Topic #14: adverto adverro adversus adversus² adversum² datames copia¹ miles fortuna italia suscipio secundus¹ antigonus milito fortuno

Fitting the NMF model (generalized Kullback-Leibler divergence) with tf-idf features, n_samples=1560 and n_features=1000...

Topics in NMF model (generalized Kullback-Leibler divergence):
Topic #0: tempus tantus nam tum video nullus nitor¹ tam nisi possum parvus nemo quidem quantus causa
Topic #1: suus suum sua suo sus possum vivo civis tueor video advenio enim adventus tamen vinco
Topic #2: facio factum factus² possum volo¹ quare imperator lego² uter pervenio studeo timor athenae forus¹ utrum
Topic #3: multus multi possum multa multo² multa¹ parvus vivo eumenes dionysius cicero vir plurimus liber¹ dio
Topic #4: bellum bellus gero¹ persequor valeo multus facio gesta dux peloponnesius indico² pax setius persuadeo confugio
Topic #5: exercitus² exerceo mitto exercio interfacio interficio navis classis consul jam praeficio praesum navo duco barbarus
Topic #6: atheniensis athenienses lacedaemonius lacedaemonii etiam solus¹ solus solum¹ sol graecia atticus propter opera alcibiades opus¹
Topic #7: patrius² patrius¹ patria hostis possum pugno tamen adversarius castrum arma libero castra armo copia¹ fero
Topic #8: locus locum utor usus² loco volo¹ uto par divus manus¹ video modus urbs parus¹ dius
Topic #9: publicus publicum publica possum populus¹ populus² capio capio¹ ibi publico indo redeo inde revorto totus¹
Topic #10: dico² habeo proficiscor autem proficio rex magus² enim magis² magis proficisco profectus³ do volo¹ video
Topic #11: nam rex rego consilium ceter ceterus regius pario² capio¹ ceterum capio consilior jubeo sequor talis
Topic #12: superus summus omnis omnes sic unus summa summum nemo modus virtus uno modo fides¹ do
Topic #13: primus filius prima sero¹ natus¹ natus natus² animus satum satis sata nascor annus pater fortuna
Topic #14: apud proelium adverro adverto amicus¹ adversus amicus amicus² adversus² proelior proelio accido² accido¹ secundus¹ liceor

===

maxfeatures = 2000
components = 15
topwords = 15

maxfreq = .60
minfreq = 5
iterations = 12

Topics in LDA model:
Topic #0: capio capio¹ filius nam interficio interfacio facio proelium alius¹ alii brevis extremus parens² parens barbarum²
Topic #1: romanus consul consulo eumenes cornelius finis imperator scipio¹ prudens prudentia adjutus² adjuvo obvius hamilcar pello
Topic #2: locum locus magis magus² magis² loco castra castrum hostis facio conficio confacio castro adversarius copia¹
Topic #3: mos fortuna secundus¹ graecus morus¹ fero fortuno morum graece morus² morus secunda cado graecum secundo²
Topic #4: praeficio lego¹ liber¹ legatus praefectus praefectus¹ liberi populus¹ populus² eques autem libet libo¹ legatum nam
Topic #5: nitor¹ nisi rex morior mortuus nam rego paro² paro¹ mitto intereo possum scribo ubi interficio
Topic #6: multus facio multa multi multo² etiam multa¹ possum solus¹ solus tempus solum¹ sol proficiscor bonum
Topic #7: divus dius dio dies totus¹ totus² dionysius acies no¹ acieris nemo syracusae locum audio posterus
Topic #8: mille milium adeo¹ adeo² perpetuus perpetuum decem perpetuo² appello nemo annus fio centum circiter circito
Topic #9: amicus¹ amicus amicus² malus malus¹ malus² malus³ malum malum² fides¹ fides² diligens amica diligo fido
Topic #10: memoria memor¹ forum¹ forum forus¹ forus statuo statua foro abstinentia imperatum chabrias impero decedo nullus
Topic #11: atticus attici caesar antonius brutus¹ constituo attice attica attice² felicitas¹ felicito constitutum contemno potestas aedes
Topic #12: publicus publica publicum publico liceo¹ licet liceor possum noster desino apud communis profligo¹ commune video
Topic #13: par modus parus¹ pario³ pario² modo possum nonnullus parum tantus claudius nonnulli numero¹ numerus apud
Topic #14: suus suum sua facio bellum bellus habeo possum nam suo enim tantus unus utor rex


Topics in NMF model (Frobenius norm):
Topic #0: possum habeo nam enim locum locus superus omnis omnes video autem summus do dico² utor
Topic #1: suus suum sua suo sus civis pars video potestas domus tueor adventus advenio voluntas constituo
Topic #2: facio factum factus² timor imprudens classis tempus celer¹ coepio offendo¹ deduco miltiades opprimo sentio salamina
Topic #3: multus multa multi multa¹ multo² valeo bonum plurimus post societas virtus tamen mille bonus gero¹
Topic #4: bellus bellum gero¹ pax persequor gesta indico² inter peloponnesius tempus coepio dux gestus² nam administro
Topic #5: solus¹ solus solum¹ sol etiam timor defendo plurimus atticus princeps prodo quisquam periculum habeo prosum
Topic #6: atheniensis athenienses filius chabrias themistocles alcibiades restituo lacedaemonii lacedaemonius oppugno² oppugno¹ socius celer¹ apud lysander
Topic #7: exercitus² exerceo exercio mitto praesum filius apud praetor imperium miles occaedes occido¹ nam praeficio paro²
Topic #8: patrius¹ patrius² patria patrium caritas libero fero tyrannus tamen revoco nam expello restituo possum duco
Topic #9: rex lacedaemonius lacedaemonii rego regius imperium mitto agesilaus permulceo praefectus praefectus¹ artaxerxes praeficio praesum societas
Topic #10: pario³ pario² par parus¹ modus modo ceter ceterus felicito felicitas¹ marcellus apud castellum claudius jubeo
Topic #11: capio capio¹ consilium capitum caput talus talis captus consilior captus² damno judicium absolvo antigonus amicitia
Topic #12: proficiscor proficio profectus³ proficisco iter phocion pervenio dico² insidior insidiae domus duco sponte fallo pugno
Topic #13: natus¹ natus nascor natus² dico² filius annus uxor relinquo morior nato amplus gener sic filia
Topic #14: adverto adverro adversus adversus² adversum² copia¹ datames adversum adversa italia antigonus miles suscipio proelior proelio

Fitting the NMF model (generalized Kullback-Leibler divergence) with tf-idf features, n_samples=1560 and n_features=2000...

Topics in NMF model (generalized Kullback-Leibler divergence):
Topic #0: do nemo nam omnis video tempus omnes tum enim tantus sic habeo autem scribo adeo¹
Topic #1: suus suum sua suo sus video tamen tueor voluntas fortuna possum civis vivo domus dico²
Topic #2: facio factum factus² possum volo¹ uter pervenio tempus quare potis lego² opprimo imperator sentio homo
Topic #3: multus possum superus multi multo² multa vivo habeo summus vita multa¹ unus virtus graecus sic
Topic #4: bellum bellus multus gero¹ multi multa multa¹ valeo multo² persequor facio dux paucus duco post
Topic #5: utor etiam solus¹ solus usus² solum¹ sol tantus possum uto atticus nullus bonus judico quisquam
Topic #6: atheniensis athenienses lacedaemonius lacedaemonii graecia alcibiades filius urbs potestas morus¹ peto morus² apud mos morus
Topic #7: exercitus² exerceo exercio superus hostis proelium apud summus summa copia¹ miles summum mitto interficio interfacio
Topic #8: publicus possum publicum publica unus castra sto castrum publico indo inde revorto populus² transeo oppugno²
Topic #9: rex locus locum rego volo¹ habeo regius loco vello video trado eumenes praeficio datames praefectus
Topic #10: primus navis dies talis prima dio navo divus quidem talus dius consilium possum modo modus
Topic #11: nam patrius¹ patrius² pario² patria capio par tamen capio¹ parus¹ pario³ nitor¹ nisi malus malus¹
Topic #12: proficiscor proficio mitto parvus profectus³ pervenio proficisco dico² tempus domus cognosco lego¹ redeo fallo puto
Topic #13: filius annus sero¹ pater natus¹ natus natus² nascor satum satis primus dico² relinquo duco magus²
Topic #14: ceterus adverro ceter adverto adversus amicus amicus¹ amicus² ceterum adversus² propter populus² populus¹ romanus enim

"""
