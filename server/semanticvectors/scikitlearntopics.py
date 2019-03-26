# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import locale
from multiprocessing import current_process

from server import hipparchia
from server.formatting.vectorformatting import ldatopicsgenerateoutput
from server.listsandsession.searchlistmanagement import compilesearchlist, flagexclusions, calculatewholeauthorsearches
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.vectorhelpers import convertmophdicttodict, buildflatbagsofwords
from server.semanticvectors.vectorpseudoroutes import emptyvectoroutput
from server.startup import listmapper, workdict, authordict
from server.textsandindices.textandindiceshelperfunctions import getrequiredmorphobjects
from server.dbsupport.vectordbfunctions import storevectorindatabase, checkforstoredvector

try:
	from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer, TfidfVectorizer
	from sklearn.linear_model import SGDClassifier
	from sklearn.model_selection import GridSearchCV
	from sklearn.pipeline import Pipeline
	from sklearn.decomposition import NMF, LatentDirichletAllocation, TruncatedSVD
except ImportError:
	if current_process().name == 'MainProcess':
		print('sklearn is unavailable')
	CountVectorizer = None
	TfidfTransformer = None
	SGDClassifier = None
	GridSearchCV = None
	Pipeline = None

try:
	# will hurl out a bunch of DeprecationWarning messages at the moment...
	# lib/python3.6/re.py:191: DeprecationWarning: bad escape \s
	import pyLDAvis
	import pyLDAvis.sklearn as ldavis
except ImportError:
	if current_process().name == 'MainProcess':
		print('pyLDAvis is not available')
	pyLDAvis = None
	ldavis = None

from server.semanticvectors.vectorhelpers import mostcommonwordsviaheadwords, removestopwords, mostcommoninflectedforms


def sklearnselectedworks(searchobject):
	"""

	:param activepoll:
	:param searchobject:
	:return:
	"""

	if not ldavis or not CountVectorizer:
		reasons = ['requisite software not installed: sklearn and/or ldavis is unavailable']
		return emptyvectoroutput(searchobject, reasons)

	skfunctiontotest = ldatopicgraphing

	so = searchobject
	activepoll = so.poll

	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'
	so.vectortype = 'topicmodel'

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c]]

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
		reasons = ['the vector scope max exceeded: {a} > {b} '.format(a=locale.format_string('%d', wordstotal, grouping=True), b=locale.format_string('%d', maxwords, grouping=True))]
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

		sentencetuples = vectorprepdispatcher(so)
		if len(sentencetuples) > hipparchia.config['MAXSENTENCECOMPARISONSPACE']:
			reasons = ['scope of search exceeded allowed maximum: {a} > {b}'.format(a=len(sentencetuples), b=hipparchia.config['MAXSENTENCECOMPARISONSPACE'])]
			return emptyvectoroutput(so, reasons)
		output = skfunctiontotest(sentencetuples, workssearched, so)

	else:
		return emptyvectoroutput(so)

	return output


def ldatopicgraphing(sentencetuples, workssearched, searchobject, headwordstops=True):
	"""

	a sentence tuple looks like:
		('gr2397w001_ln_42', 'ποίῳ δὴ τούτων ἄξιον τὸν κόϲμον φθείρεϲθαι φάναι')

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

	if headwordstops:
		stops = mostcommonwordsviaheadwords()
	else:
		stops = mostcommoninflectedforms()

	sentencetuples = [(a, removestopwords(b, stops)) for a, b in sentencetuples]

	activepoll = searchobject.poll
	vv = searchobject.vectorvalues

	settings = {
		'maxfeatures': vv.ldamaxfeatures,
		'components': vv.ldacomponents,     # topics
		'maxfreq': vv.ldamaxfreq,           # fewer than n% of sentences should have this word (i.e., purge common words)
		'minfreq': vv.ldaminfreq,           # word must be found >n times
		'iterations': vv.ldaiterations,
		'mustbelongerthan': vv.ldamustbelongerthan
	}

	# not easy to store/fetch since you need both ldavectorizer and ldamodel
	# so we just store the actual graph...
	ldavishtmlandjs = checkforstoredvector(searchobject, 'lda')

	if not ldavishtmlandjs:
		sentencetuples = [s for s in sentencetuples if len(s[1].strip().split(' ')) > settings['mustbelongerthan']]
		sentences = [s[1] for s in sentencetuples]

		sentencesaslists = [s.split(' ') for s in sentences]
		allwordsinorder = [item for sublist in sentencesaslists for item in sublist if item]

		activepoll.statusis('Finding all headwords')
		morphdict = getrequiredmorphobjects(set(allwordsinorder), furtherdeabbreviate=True)
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
		ldavectorizer = CountVectorizer(max_df=settings['maxfreq'],
										min_df=settings['minfreq'],
										max_features=settings['maxfeatures'])

		ldavectorized = ldavectorizer.fit_transform(bagsofsentences)

		ldamodel = LatentDirichletAllocation(n_components=settings['components'],
											max_iter=settings['iterations'],
											learning_method='online',
											learning_offset=50.,
											random_state=0)

		ldamodel.fit(ldavectorized)

		visualisation = ldavis.prepare(ldamodel, ldavectorized, ldavectorizer)
		# pyLDAvis.save_html(visualisation, 'ldavis.html')

		ldavishtmlandjs = pyLDAvis.prepared_data_to_html(visualisation)
		storevectorindatabase(searchobject, 'lda', ldavishtmlandjs)

	jsonoutput = ldatopicsgenerateoutput(ldavishtmlandjs, workssearched, settings, searchobject)

	return jsonoutput
