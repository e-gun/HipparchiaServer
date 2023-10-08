# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-22
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import multiprocessing
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
    if multiprocessing.current_process().name == 'MainProcess':
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


    Parameters [https://radimrehurek.com/gensim/models/word2vec.html]

        sentences (iterable of iterables, optional) – The sentences iterable can be simply a list of lists of tokens, but for larger corpora, consider an iterable that streams the sentences directly from disk/network. See BrownCorpus, Text8Corpus or LineSentence in word2vec module for such examples. See also the tutorial on data streaming in Python. If you don’t supply sentences, the model is left uninitialized – use if you plan to initialize it in some other way.

        corpus_file (str, optional) – Path to a corpus file in LineSentence format. You may use this argument instead of sentences to get performance boost. Only one of sentences or corpus_file arguments need to be passed (or none of them, in that case, the model is left uninitialized).

        vector_size (int, optional) – Dimensionality of the word vectors.

        window (int, optional) – Maximum distance between the current and predicted word within a sentence.

        min_count (int, optional) – Ignores all words with total frequency lower than this.

        workers (int, optional) – Use these many worker threads to train the model (=faster training with multicore machines).

        sg ({0, 1}, optional) – Training algorithm: 1 for skip-gram; otherwise CBOW.

        hs ({0, 1}, optional) – If 1, hierarchical softmax will be used for model training. If 0, and negative is non-zero, negative sampling will be used.

        negative (int, optional) – If > 0, negative sampling will be used, the int for negative specifies how many “noise words” should be drawn (usually between 5-20). If set to 0, no negative sampling is used.

        ns_exponent (float, optional) – The exponent used to shape the negative sampling distribution. A value of 1.0 samples exactly in proportion to the frequencies, 0.0 samples all words equally, while a negative value samples low-frequency words more than high-frequency words. The popular default value of 0.75 was chosen by the original Word2Vec paper. More recently, in https://arxiv.org/abs/1804.04212, Caselles-Dupré, Lesaint, & Royo-Letelier suggest that other values may perform better for recommendation applications.

        cbow_mean ({0, 1}, optional) – If 0, use the sum of the context word vectors. If 1, use the mean, only applies when cbow is used.

        alpha (float, optional) – The initial learning rate.

        min_alpha (float, optional) – Learning rate will linearly drop to min_alpha as training progresses.

        seed (int, optional) – Seed for the random number generator. Initial vectors for each word are seeded with a hash of the concatenation of word + str(seed). Note that for a fully deterministically-reproducible run, you must also limit the model to a single worker thread (workers=1), to eliminate ordering jitter from OS thread scheduling. (In Python 3, reproducibility between interpreter launches also requires use of the PYTHONHASHSEED environment variable to control hash randomization).

        max_vocab_size (int, optional) – Limits the RAM during vocabulary building; if there are more unique words than this, then prune the infrequent ones. Every 10 million word types need about 1GB of RAM. Set to None for no limit.

        max_final_vocab (int, optional) – Limits the vocab to a target vocab size by automatically picking a matching min_count. If the specified min_count is more than the calculated min_count, the specified min_count will be used. Set to None if not required.

        sample (float, optional) – The threshold for configuring which higher-frequency words are randomly downsampled, useful range is (0, 1e-5).

        hashfxn (function, optional) – Hash function to use to randomly initialize weights, for increased training reproducibility.

        epochs (int, optional) – Number of iterations (epochs) over the corpus. (Formerly: iter)

        trim_rule (function, optional) –

        Vocabulary trimming rule, specifies whether certain words should remain in the vocabulary, be trimmed away, or handled using the default (discard if word count < min_count). Can be None (min_count will be used, look to keep_vocab_item()), or a callable that accepts parameters (word, count, min_count) and returns either gensim.utils.RULE_DISCARD, gensim.utils.RULE_KEEP or gensim.utils.RULE_DEFAULT. The rule, if given, is only used to prune vocabulary during build_vocab() and is not stored as part of the model.

        The input parameters are of the following types:

                word (str) - the word we are examining

                count (int) - the word’s frequency count in the corpus

                min_count (int) - the minimum count threshold.

        sorted_vocab ({0, 1}, optional) – If 1, sort the vocabulary by descending frequency before assigning word indexes. See sort_by_descending_frequency().

        batch_words (int, optional) – Target size (in words) for batches of examples passed to worker threads (and thus cython routines).(Larger batches will be passed if individual texts are longer than 10000 words, but the standard cython code truncates to that maximum.)

        compute_loss (bool, optional) – If True, computes and stores loss value which can be retrieved using get_latest_training_loss().

        callbacks (iterable of CallbackAny2Vec, optional) – Sequence of callbacks to be executed at specific stages during training.

    [debugging] first bag is ['o', 'quantum', 'homo', 'beatus', 'edo¹', 'peto', 'amo', 'bonus', 'senex', 'idem', 'ego',
    'ille', 'conus', 'caelestis', 'in', 'limen', 'quatio', 'tergum', 'taurus³', 'ios', 'hymen', 'hymenaeus'] [debugging]

    :return:
    """

    vv = so.vectorvalues
    workers = setthreadcount()

    computeloss = False

    # Note that for a fully deterministically-reproducible run, you must also limit the model to a single worker thread
    # (workers=1), to eliminate ordering jitter from OS thread scheduling.
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            try:
                # gensim 4 API
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
            except TypeError:
                # gensim 3.8.3 API
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
