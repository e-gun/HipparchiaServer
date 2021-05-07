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

from server.formatting.miscformatting import consolewarning
from server.dbsupport.vectordbfunctions import storevectorindatabase
from server.formatting.vectorformatting import analogiesgenerateoutput
from server.hipparchiaobjects.searchobjects import SearchObject
from server.threading.mpthreadcount import setthreadcount

try:
    from gensim.models import Word2Vec
except ImportError:
    from multiprocessing import current_process

    if current_process().name == 'MainProcess':
        print('gensim not available')
    Word2Vec = None

try:
    from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer, TfidfVectorizer
    from sklearn.linear_model import SGDClassifier
    from sklearn.model_selection import GridSearchCV
    from sklearn.pipeline import Pipeline
    from sklearn.decomposition import NMF, LatentDirichletAllocation, TruncatedSVD
except ImportError:
    if current_process().name == 'MainProcess':
        consolewarning('sklearn is unavailable', color='black')
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
        consolewarning('pyLDAvis is unavailable', color='black')
    pyLDAvis = None
    ldavis = None


JSON_STR = str
JSONDICT = str


def buildgensimmodel(so: SearchObject, bagsofwords: List[List[str]]) -> Word2Vec:
    """

    [a virtual clone of buildgensimmodel() in the old gensimmodels.py]

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

    [debugging] first bag is ['o', 'quantum', 'homo', 'beatus', 'edo¹', 'peto', 'amo', 'bonus', 'senex', 'idem', 'ego',
    'ille', 'conus', 'caelestis', 'in', 'limen', 'quatio', 'tergum', 'taurus³', 'ios', 'hymen', 'hymenaeus'] [debugging]

    :return:
    """

    typelabel = 'nn'

    vv = so.vectorvalues
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
        print('loss after {n} iterations was: {l}'.format(n=vv.trainingiterations,
                                                          l=gensimmodel.get_latest_training_loss()))

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

    # print(model.wv['puer'])

    storevectorindatabase(so, gensimmodel)

    return gensimmodel


def buildsklearnselectedworks(so: SearchObject, bagsofsentences: list):
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

    """

    activepoll = so.poll
    vv = so.vectorvalues

    settings = {
        'maxfeatures': vv.ldamaxfeatures,
        'components': vv.ldacomponents,  # topics
        'maxfreq': vv.ldamaxfreq,  # fewer than n% of sentences should have this word (i.e., purge common words)
        'minfreq': vv.ldaminfreq,  # word must be found >n times
        'iterations': vv.ldaiterations,
        'mustbelongerthan': vv.ldamustbelongerthan
    }

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
    storevectorindatabase(so, ldavishtmlandjs)

    return ldavishtmlandjs


def gensimgenerateanalogies(vectorspace: Word2Vec, so: SearchObject) -> JSON_STR:
    """

    most_similar(positive=None, negative=None, topn=10, restrict_vocab=None, indexer=None)
        [analogies; most_similar(positive=['woman', 'king'], negative=['man']) --> queen]

    most_similar_cosmul(positive=None, negative=None, topn=10)
    [analogy finder; most_similar_cosmul(positive=['baghdad', 'england'], negative=['london']) --> iraq]

    :param sentencetuples:
    :param searchobject:
    :param vectorspace:
    :return:
    """

    if so.session['baggingmethod'] != 'unlemmatized':
        a = so.lemmaone.dictionaryentry
        b = so.lemmatwo.dictionaryentry
        c = so.lemmathree.dictionaryentry
    else:
        a = so.lemmaone
        b = so.lemmatwo
        c = so.termthree

    positive = [a, b]
    negative = [c]

    # similarities are less interesting than cosimilarities
    # similarities = vectorspace.wv.most_similar(positive=positive, negative=negative, topn=4)

    try:
        similarities = vectorspace.wv.most_similar(positive=positive, negative=negative, topn=4)
    except KeyError as theexception:
        # KeyError: "word 'terra' not in vocabulary"
        # raise KeyError(f"Key '{key}' not present")
        missing = re.search(r'word \'(.*?)\'', str(theexception))
        try:
            similarities = [('"{m}" was missing from the vector space'.format(m=missing.group(1)), 0)]
        except AttributeError:
            similarities = [('[a term was missing from the vector space]', 0)]

    try:
        cosimilarities = vectorspace.wv.most_similar_cosmul(positive=positive, negative=negative, topn=5)
    except KeyError as theexception:
        # KeyError: "word 'terra' not in vocabulary"
        missing = re.search(r'word \'(.*?)\'', str(theexception))
        try:
            cosimilarities = [('"{m}" was missing from the vector space'.format(m=missing.group(1)), 0)]
        except AttributeError:
            cosimilarities = [('[a term was missing from the vector space]', 0)]

    simlabel = [('<b>similarities</b>', str())]
    cosimlabel = [('<b>cosimilarities</b>', str())]
    similarities = [(s[0], round(s[1], 3)) for s in similarities]
    cosimilarities = [(s[0], round(s[1], 3)) for s in cosimilarities]

    output = simlabel + similarities + cosimlabel + cosimilarities

    output = analogiesgenerateoutput(so, output)

    return output
