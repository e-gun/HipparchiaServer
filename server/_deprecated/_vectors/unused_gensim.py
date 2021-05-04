# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""
import re
import warnings
from typing import List

from gensim.models import Word2Vec

from server import hipparchia
from server.dbsupport.vectordbfunctions import checkforstoredvector, storevectorindatabase
from server.formatting.vectorformatting import analogiesgenerateoutput
from server.listsandsession.searchlistmanagement import compilesearchlist, flagexclusions, calculatewholeauthorsearches
from server.listsandsession.whereclauses import configurewhereclausedata
from server._deprecated._vectors.gensimlsi import lsigenerateoutput
from server.semanticvectors.gensimfunctions import Word2Vec, JSON_STR
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server._deprecated._vectors.misc_unused_vectors import tsnegraphofvectors, threejsgraphofvectors
from server.semanticvectors.vectorhelpers import buildlemmatizesearchphrase
from server.semanticvectors.vectorroutehelperfunctions import emptyvectoroutput
from server.semanticvectors.wordbaggers import buildwordbags
from server.startup import listmapper, workdict, authordict
from server.threading.mpthreadcount import setthreadcount


def executegensimlsi(searchobject):
	"""

	CURRENTLYUNUSED

	set yourself up for executegensimsearch()

	:param searchobject:
	:return:
	"""
	so = searchobject

	if so.vectorquerytype == 'CURRENTLYUNUSED':
		outputfunction = lsigenerateoutput
		indextype = 'lsi'
		so.lemma = None
		so.tovectorize = buildlemmatizesearchphrase(so.seeking)
		if not so.tovectorize:
			reasons = ['unable to lemmatize the search term(s) [nb: whole words required and accents matter]']
			return emptyvectoroutput(so, reasons)
		return executegensimsearch(searchobject, outputfunction, indextype)
	else:
		reasons = ['unknown vectorquerytype sent to executegensimsearch()']
		return emptyvectoroutput(searchobject, reasons)


def executegensimsearch(searchobject, outputfunction, indextype):
	"""

	use the searchlist to grab a collection of sentences

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	:param searchitem:
	:param vtype:
	:return:
	"""

	so = searchobject
	activepoll = so.poll

	# print('so.vectorquerytype', so.vectorquerytype)

	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'

	activecorpora = so.getactivecorpora()

	# so.seeking should only be set via a fallback when session['baggingmethod'] == 'unlemmatized'
	if (so.lemma or so.tovectorize or so.seeking) and activecorpora:
		activepoll.statusis('Compiling the list of works to search')
		searchlist = compilesearchlist(listmapper, so.session)
	elif not activecorpora:
		reasons = ['no active corpora']
		return emptyvectoroutput(so, reasons)
	else:
		reasons = ['there was no search term']
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
		wt = '{:,}'.format(wordstotal)
		mw = '{:,}'.format(maxwords)
		reasons = ['the vector scope max exceeded: {a} > {b} '.format(a=wt, b=mw)]
		return emptyvectoroutput(so, reasons)

	# DEBUGGING
	# Frogs and mice
	# so.lemma = lemmatadict['βάτραχοϲ']
	# searchlist = ['gr1220']

	# Euripides
	# so.lemma = lemmatadict['ἄτη']
	# print(so.lemma.formlist)
	# so.lemma.formlist = ['ἄτῃ', 'ἄταν', 'ἄτηϲ', 'ἄτηι']
	# searchlist = ['gr0006']

	if len(searchlist) > 0:
		searchlist = flagexclusions(searchlist, so.session)
		workssearched = len(searchlist)
		searchlist = calculatewholeauthorsearches(searchlist, authordict)
		so.searchlist = searchlist

		indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
		so.indexrestrictions = indexrestrictions

		# 'False' if there is no vectorspace; 'failed' if there can never be one; otherwise vectors
		vectorspace = checkforstoredvector(so, indextype)

		if not vectorspace and hipparchia.config['FORBIDUSERDEFINEDVECTORSPACES']:
			reasons = ['you are only allowed to fetch pre-stored vector spaces; <b>try a single author or corpus search using the default vector values</b>']
			return emptyvectoroutput(so, reasons)

		# find all sentences
		if not vectorspace:
			activepoll.statusis('No stored model for this search. Finding all sentences')
		else:
			activepoll.statusis('Finding neighbors')
		# blanking out the search term will return every last sentence...
		# otherwise you only return sentences with the search term in them (i.e. rudimentaryvectorsearch)
		if not vectorspace:
			so.seeking = r'.'
			sentencetuples = vectorprepdispatcher(so)
		else:
			sentencetuples = None

		output = outputfunction(sentencetuples, workssearched, so, vectorspace)

	else:
		reasons = ['search list contained zero items']
		return emptyvectoroutput(so, reasons)

	return output


def twodimensionalrepresentationofspace(searchobject):
	"""

	https://radimrehurek.com/gensim/auto_examples/tutorials/run_word2vec.html#sphx-glr-auto-examples-tutorials-run-word2vec-py

	see there: Visualising the Word Embeddings

	:return:
	"""

	if searchobject.vectorquerytype == 'vectortestfunction':
		outputfunction = tsnegraphofvectors
		indextype = 'nn'
		return executegensimsearch(searchobject, outputfunction, indextype)
	else:
		reasons = ['unknown vectorquerytype sent to executegensimsearch()']
		return emptyvectoroutput(searchobject, reasons)


def threedimensionalrepresentationofspace(searchobject):
	"""

	see https://github.com/tobydoig/3dword2vec

	:param searchobject:
	:return:
	"""

	if searchobject.vectorquerytype == 'vectortestfunction':
		outputfunction = threejsgraphofvectors
		indextype = 'nn'
		return executegensimsearch(searchobject, outputfunction, indextype)
	else:
		reasons = ['unknown vectorquerytype sent to executegensimsearch()']
		return emptyvectoroutput(searchobject, reasons)


def buildgensimmodel(searchobject, morphdict: dict, sentences: List[str]) -> Word2Vec:
    """

    returns a Word2Vec model

    then you use one of the many ill-documented class functions that come with
    the model to make queries against it

    WordEmbeddingsKeyedVectors in keyedvectors.py is your friend here for learning what you can really do
        most_similar(positive=None, negative=None, topn=10, restrict_vocab=None, indexer=None)
            [analogies; most_similar(positive=['woman', 'king'], negative=['man']) --> queen]

        similar_by_word(word, topn=10, restrict_vocab=None)
            [the top-N most similar words]

        similar_by_vector(vector, topn=10, restrict_vocab=None)

        similarity_matrix(dictionary, tfidf=None, threshold=0.0, exponent=2.0, nonzero_limit=100, dtype=REAL)

        wmdistance(document1, document2)
            [Word Mover's Distance between two documents]

        most_similar_cosmul(positive=None, negative=None, topn=10)
            [analogy finder; most_similar_cosmul(positive=['baghdad', 'england'], negative=['london']) --> iraq]

        cosine_similarities(vector_1, vectors_all)

        distances(word_or_vector, other_words=())

        distance(w1, w2)
            [distance('woman', 'man')]

        similarity(w1, w2)
            [similarity('woman', 'man')]

        n_similarity(ws1, ws2)
            [sets of words: n_similarity(['sushi', 'shop'], ['japanese', 'restaurant'])]


    FYI: Doc2VecKeyedVectors
        doesnt_match(docs)
            [Which doc from the given list doesn't go with the others?]

    note that Word2Vec will hurl out lots of DeprecationWarnings; we are blocking them
    one hopes that this does not yield a surprise some day... [surprise: it did...]

    this code is a candidate for refactoring because of the gensim 3.8 vs 4.0 API difference
    a drop down from model to model.wv requires refactoring dependent functions

    :return:
    """

    vv = searchobject.vectorvalues

    sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
    sentences = [s for s in sentences if s]

    bagsofwords = buildwordbags(searchobject, morphdict, sentences)
    # debugmessage('first bag is {b}'.format(b=bagsofwords[0]))
    # debugmessage('# of bags is {b}'.format(b=len(bagsofwords)))

    workers = setthreadcount()

    computeloss = False

    # Note that for a fully deterministically-reproducible run, you must also limit the model to a single worker thread
    # (workers=1), to eliminate ordering jitter from OS thread scheduling.
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                gensimmodel = Word2Vec(bagsofwords,
                            min_count=vv.minimumpresence,
                            seed=1,
                            iter=vv.trainingiterations,
                            size=vv.dimensions,
                            sample=vv.downsample,
                            sg=1,  # the results seem terrible if you say sg=0
                            window=vv.window,
                            workers=workers,
                            compute_loss=computeloss)
            except TypeError:
                # TypeError: __init__() got an unexpected keyword argument 'iter'
                # i.e., gensim 4.0.0 changed the API
                # see: https://radimrehurek.com/gensim/models/word2vec.html
                #
                # class gensim.models.word2vec.Word2Vec(sentences=None, corpus_file=None, vector_size=100, alpha=0.025,
                # window=5, min_count=5, max_vocab_size=None, sample=0.001, seed=1, workers=3, min_alpha=0.0001, sg=0,
                # hs=0, negative=5, ns_exponent=0.75, cbow_mean=1, hashfxn=<built-in function hash>, epochs=5,
                # null_word=0, trim_rule=None, sorted_vocab=1, batch_words=10000, compute_loss=False, callbacks=(),
                # comment=None, max_final_vocab=None)
                #
                # epochs (int, optional) – Number of iterations (epochs) over the corpus. (Formerly: iter)
                # vector_size (int, optional) – Dimensionality of the word vectors.
                gensimmodel = Word2Vec(bagsofwords,
                            min_count=vv.minimumpresence,
                            seed=1,
                            epochs=vv.trainingiterations,
                            vector_size=vv.dimensions,
                            sample=vv.downsample,
                            sg=1,  # the results seem terrible if you say sg=0
                            window=vv.window,
                            workers=workers,
                            compute_loss=computeloss)

    except RuntimeError:
        # RuntimeError: you must first build vocabulary before training the model
        # this will happen if you have a tiny author with too few words
        gensimmodel = None

    if computeloss:
        print('loss after {n} iterations was: {l}'.format(n=vv.trainingiterations, l=gensimmodel.get_latest_training_loss()))

    reducedmodel = None

    if gensimmodel:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                gensimmodel.delete_temporary_training_data(replace_word_vectors_with_normalized=True)
            except AttributeError:
                # AttributeError: 'Word2Vec' object has no attribute 'delete_temporary_training_data'
                # i.e., gensim 4.0.0 changed the API
                # see: https://radimrehurek.com/gensim/models/word2vec.html
                # 	If you’re finished training a model (i.e. no more updates, only querying), you can switch to the KeyedVectors instance:
                # 	word_vectors = model.wv
                # 	del model
                # this complicates our backwards-compatible-life, though.
                # we want to return a Word2Vec and not a KeyedVectors instance
                # gensimmodel = gensimmodel.wv
                reducedmodel = Word2Vec([["cat", "say", "meow"], ["dog", "say", "woof"]], min_count=1)
                reducedmodel.wv = gensimmodel.wv

    if reducedmodel:
        gensimmodel = reducedmodel

    # print(gensimmodel.wv['ludo'])

    storevectorindatabase(searchobject, 'nn', gensimmodel)

    return gensimmodel


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
        if vectorspace == 'there is no model: but there should be one...':
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