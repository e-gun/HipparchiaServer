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

from server import hipparchia
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.vectorhelpers import buildflatbagsofwords, buildbagsofwordswithalternates, convertmophdicttodict, mostcommonwords, findheadwords
from server.dbsupport.dblinefunctions import grablistoflines
from server.semanticvectors.vectorpseudoroutes import emptyvectoroutput
from server.formatting.vectorformatting import skformatmostimilar
from server.formatting.jsformatting import insertbrowserclickjs
from server.startup import authordict, listmapper, workdict
from server.formatting.bibliographicformatting import bcedating


def sklearnselectedworks(activepoll, searchobject):
	"""

	:param activepoll:
	:param searchobject:
	:return:
	"""

	skfunctiontotest = sklearntextfeatureextractionandevaluation
	skfunctiontotest = simplesktextcomparison
	# skfunctiontotest = ldatopicmodeling

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
		sentencetuples = vectorprepdispatcher(so, activepoll)
		if len(sentencetuples) > hipparchia.config['MAXSENTENCECOMPARISONSPACE']:
			reasons = ['scope of search exceeded allowed maximum: {a} > {b}'.format(a=len(sentencetuples), b=hipparchia.config['MAXSENTENCECOMPARISONSPACE'])]
			return emptyvectoroutput(so, reasons)
		similaritiesdict = skfunctiontotest(sentencetuples, activepoll)
		# similaritiesdict: {id: (scoreA, lindobjectA1, sentA1, lindobjectA2, sentA2), id2: (scoreB, lindobjectB1, sentB1, lindobjectB2, sentB2), ... }
		corehtml = skformatmostimilar(similaritiesdict)
		output = generatesimilarsentenceoutput(corehtml, so, activepoll, workssearched, len(similaritiesdict))
	else:
		return emptyvectoroutput(so)

	return output


def generatesimilarsentenceoutput(corehtml, searchobject, activepoll, workssearched, matches):
	"""

	:param corehtml:
	:param searchobject:
	:return:
	"""

	so = searchobject
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
		all = 'all forms of »{skg}«'.format(skg=so.lemma)
	else:
		all = ''
	if so.proximatelemma:
		near = ' all forms of »{skg}«'.format(skg=so.proximatelemma)
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

	and

	http://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction

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


def ldatopicmodeling(sentencetuples, activepoll):
	"""

	see:
		http://scikit-learn.org/stable/auto_examples/applications/plot_topics_extraction_with_nmf_lda.html#sphx-glr-auto-examples-applications-plot-topics-extraction-with-nmf-lda-py

	CountVectorizer:
	max_df : float in range [0.0, 1.0] or int, default=1.0
	    When building the vocabulary ignore terms that have a document frequency strictly higher than the given threshold (corpus-specific stop words).

	min_df : float in range [0.0, 1.0] or int, default=1
	    When building the vocabulary ignore terms that have a document frequency strictly lower than the given threshold. This value is also called cut-off in the literature.

	:param sentencetuples:
	:param activepoll:
	:return:
	"""

	maxfeatures = 1000
	components = 10
	topwords = 10


	mustbelongerthan = 2

	sentencetuples = [s for s in sentencetuples if len(s[1].strip().split(' ')) > mustbelongerthan]
	sentences = [s[1] for s in sentencetuples]

	sentencesaslists = [s.split(' ') for s in sentences]
	allwordsinorder = [item for sublist in sentencesaslists for item in sublist if item]

	morphdict = findheadwords(set(allwordsinorder))
	morphdict = convertmophdicttodict(morphdict)

	# going forward we we need a list of lists of headwords
	# there are two ways to do this:
	#   'ϲυγγενεύϲ ϲυγγενήϲ' vs 'ϲυγγενεύϲ·ϲυγγενήϲ'

	bagofwordsfunction = buildflatbagsofwords
	# bagofwordsfunction = buildbagsofwordswithalternates

	bagsofwordlists = bagofwordsfunction(morphdict, sentencesaslists)
	bagsofsentences = [' '.join(b) for b in bagsofwordlists]

	# Use tf (raw term count) features for LDA.
	ldavectorizer = CountVectorizer(max_df=0.95,
	                             min_df=2,
	                             max_features=maxfeatures)

	ldavectorized = ldavectorizer.fit_transform(bagsofsentences)

	lda = LatentDirichletAllocation(n_components=components,
	                                max_iter=5,
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
	nmf = NMF(n_components=components, random_state=1,
	          alpha=.1, l1_ratio=.5).fit(tfidf)

	print("\nTopics in NMF model (Frobenius norm):")
	tfidffeaturenames = tfidfvectorizer.get_feature_names()
	print_top_words(nmf, tfidffeaturenames, topwords)

	# Fit the NMF model
	print("Fitting the NMF model (generalized Kullback-Leibler divergence) with "
	      "tf-idf features, n_samples=%d and n_features=%d..."
	      % (len(sentences), maxfeatures))

	nmf = NMF(n_components=components, random_state=1,
	          beta_loss='kullback-leibler', solver='mu', max_iter=1000, alpha=.1,
	          l1_ratio=.5).fit(tfidf)

	print("\nTopics in NMF model (generalized Kullback-Leibler divergence):")
	tfidffeaturenames = tfidfvectorizer.get_feature_names()
	print_top_words(nmf, tfidffeaturenames, topwords)

	"""
	Cornelius Nepos
	Topics in LDA model:
	Topic #0: suus suum sua suo possum patrius² patrius¹ nam sus patria
	Topic #1: superus summus tantus omnis summum summa utor omnes atticus sero¹
	Topic #2: parvus liber¹ lego¹ alius¹ liberi legatus volo¹ pars video mitto
	Topic #3: malus malus¹ malus² malus³ malum malum² nisi nitor¹ fides¹ fides²
	Topic #4: proficiscor proficisco forum¹ forum forus forus¹ noster statua setius exeo
	Topic #5: modus modo magis magus² magis² vita do vivo quidem tantus
	Topic #6: multus possum rex publicus multi multa rego publica multa¹ publicum
	Topic #7: capio¹ capio primus interficio interfacio prima mille dico² milium possum
	Topic #8: bellus bellum facio exercitus² exerceo exercio factum atheniensis athenienses adverto
	Topic #9: facio locum locus habeo dies proficio proficiscor divus dius profectus³
	
	
	Topics in NMF model (Frobenius norm):
	Topic #0: nam possum rex habeo enim rego lacedaemonius atheniensis lacedaemonii athenienses
	Topic #1: suus suum sua suo sus civis adventus advenio pars video
	Topic #2: facio factum factus² timor opprimo tempus brevis celer¹ classis imprudens
	Topic #3: multus multa multi multa¹ multo² valeo plurimus post bonum tamen
	Topic #4: bellus bellum gero¹ athenienses atheniensis pax pario³ pario² persequor indico²
	Topic #5: exercitus² exerceo exercio mitto praesum apud miles praetor filius occaedes
	Topic #6: solus¹ solus solum¹ sol etiam timor plurimus efficio defendo princeps
	Topic #7: adverto adverro adversus adversus² adversum² datames copia¹ fortuna miles italia
	Topic #8: patrius² patrius¹ patria patrium fero nam libero tamen tyrannus possum
	Topic #9: locum locus loco hostis dies castrum castra rogo castro uno
	
	Fitting the NMF model (generalized Kullback-Leibler divergence) with tf-idf features, n_samples=1560 and n_features=1000...
	done in 0.599s.
	
	Topics in NMF model (generalized Kullback-Leibler divergence):
	Topic #0: nam tempus omnis utor tantus enim omnes tum rex gero¹
	Topic #1: suus suum sua suo enim sus possum amicus¹ amicus civis
	Topic #2: facio factum factus² pervenio quare volo¹ tempus possum uter licet
	Topic #3: multus possum tamen unus parvus puto consilium virtus nam pater
	Topic #4: multus bellum bellus multo² multa multa¹ multi gero¹ valeo post
	Topic #5: exercitus² rex exerceo proficiscor mitto exercio apud nam interfacio rego
	Topic #6: atheniensis athenienses lacedaemonius lacedaemonii superus etiam summus solus¹ solus solum¹
	Topic #7: adverro adverto adversus adversus² hostis copia¹ volo¹ castrum eumenes arma
	Topic #8: publicus patrius² patrius¹ possum patria publicum publica dico² populus¹ populus²
	Topic #9: locus locum possum habeo primus loco video prima urbs sero¹
	
	
	Julius Caesar
	Topics in LDA model:
	Topic #0: reliquus relinquo legio cohors reliquum caesar praesidium cohorto facio reliqua
	Topic #1: primus noster prima mille milium acies signum hostis circito circiter
	Topic #2: multus pompejus multi proficiscor multa caesar totus² totus¹ gallius² gallia
	Topic #3: mitto caesar bellus bellum equitatus¹ equitatus² lego¹ equito legatus omnis
	Topic #4: navis oppidum navo opus¹ pars murus porta portus miles reliquus
	Topic #5: castra castrum suus locum locus sua suum suo castro utor
	Topic #6: interficio interfacio animus publicus pompejus cado publica animo aliquis casus¹
	Topic #7: superus summus video summa summum miles caesar dico² habeo enim
	Topic #8: eques proelium facio alius¹ caesar proelior proelio equito factum equio
	Topic #9: exercitus² exerceo exercio arma conficio confacio capio capio¹ milito miles
	
	Topics in NMF model (Frobenius norm):
	Topic #0: caesar possum facio miles bellum bellus omnis navis omnes pars
	Topic #1: suus sua suum suo sus finis salus copia¹ habeo auxilium
	Topic #2: castra castrum castro legio pono munitio hostis relinquo copia¹ passus³
	Topic #3: locum locus loco natura iniquus pugno superus noster idoneus deligo¹
	Topic #4: exercitus² exerceo exercio traduco copia¹ dimitto copis¹ duco incolumis caesar
	Topic #5: equito equitatus¹ equitatus² eques mitto noster proelium caesar jubeo omnis
	Topic #6: lego¹ legatus legatum mitto lego² missum caesar legio fabius praeficio
	Topic #7: reliquus reliquum reliqua relinquo fuga civitas paro¹ paro² pars fugo
	Topic #8: dies dius divus posterus postero paucus pauci pauca dico² nox
	Topic #9: superus summus summa summum imperium voluntas trado uter contendo habeo
	
	Fitting the NMF model (generalized Kullback-Leibler divergence) with tf-idf features, n_samples=4490 and n_features=1000...
	
	Topics in NMF model (generalized Kullback-Leibler divergence):
	Topic #0: caesar facio tempus cognosco utor possum causa per video uto
	Topic #1: suus suum sua suo sus romanus habeo populus² populus¹ civitas
	Topic #2: castra castrum castro munitio vallus¹ vallus² vallum copia¹ suus pono
	Topic #3: locus locum possum multus loco video multi multa noster pugno
	Topic #4: exercitus² exerceo exercio gallius² gallia proficiscor consilium totus¹ totus² bellus
	Topic #5: equito eques proelium equitatus² equitatus¹ omnis hostis omnes proelior proelio
	Topic #6: mitto caesar lego¹ legatus legio pompejus legatum missum pompeji praeficio
	Topic #7: reliquus navis reliquum relinquo reliqua interficio interfacio navo paucus numerus
	Topic #8: miles dies milito mille primus oppidum milium divus dius passus³
	Topic #9: pars superus unus summus noster summa summum pario² fero hostis
	
	"""

	return
