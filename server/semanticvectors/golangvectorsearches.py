# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import json
import warnings
from typing import List
from server import hipparchia
from server.dbsupport.redisdbfunctions import establishredisconnection
from server.formatting.miscformatting import consolewarning, debugmessage
from server.hipparchiaobjects.searchobjects import SearchObject
from server.listsandsession.genericlistfunctions import flattenlistoflists
from server.listsandsession.searchlistmanagement import compilesearchlist
from server.routes.searchroute import updatesearchlistandsearchobject
from server.searching.precomposedsearchgolanginterface import golangclibinarysearcher, golangsharedlibrarysearcher
from server.searching.precomposesql import searchlistintosqldict, rewritesqlsearchdictforgolang
from server.searching.searchhelperfunctions import genericgolangcliexecution
from server.semanticvectors.vectorroutehelperfunctions import emptyvectoroutput
from server.semanticvectors.gensimnearestneighbors import generatenearestneighbordata
from server.startup import listmapper
from server.threading.mpthreadcount import setthreadcount
from server.dbsupport.vectordbfunctions import storevectorindatabase

try:
    from gensim.models import Word2Vec
except ImportError:
    from multiprocessing import current_process

    if current_process().name == 'MainProcess':
        print('gensim not available')
    Word2Vec = None

JSON_STR = str
JSONDICT = str


def golangvectors(so: SearchObject) -> JSON_STR:
    """

    the flow inside of go, but this overview is useful for refactoring hipparchia's python

    our paradigm case is going to be a nearest neighbors query; to do this you need to...

    [a] grab db lines that are relevant to the search
    [b] turn them into a unified text block
    [c] do some preliminary cleanups
    [d] break the text into sentences and assemble []SentenceWithLocus (NB: these are "unlemmatized bags of words")
    [e] figure out all of the words used in the passage
    [f] find all of the parsing info relative to these words
    [g] figure out which headwords to associate with the collection of words
    [h] build the lemmatized bags of words ('unlemmatized' can skip [f] and [g]...)
    [i] store the bags

    note that we are assuming you also have the golanggrabber available

    127.0.0.1:6379> spop 2b10de72_vectorresults 4
    1) "{\"Loc\":\"line/lt0472w001/615\",\"Sent\":\"acceptum facio reddo lesbia mius praesens malus\xc2\xb2 multus dico\xc2\xb2 non possum reticeo detondeo qui\xc2\xb9 ego in reor attulo\"}"
    2) "{\"Loc\":\"line/lt0472w001/1294\",\"Sent\":\"jacio hederiger quandoquidem fortuna meus atque tuus ego miser aspicio et si puriter ago qui\xc2\xb2 enim genus\xc2\xb9 figura curro duco subtemen curro fundo\xc2\xb9\"}"
    3) "{\"Loc\":\"line/lt0472w001/2296\",\"Sent\":\"qui\xc2\xb2 tu nunc chordus\xc2\xb9 quis\xc2\xb9 tu praepono nos possum\"}"
    4) "{\"Loc\":\"line/lt0472w001/1105\",\"Sent\":\"rasilis subeo foris\xc2\xb9\"}"

    """

    abort = lambda x: emptyvectoroutput(so, x)

    consolewarning('in progress; will not return results', color='red')

    # in order to meet the requirements of [a] above we need to
    #   [1] generate a searchlist
    #   [2] do a searchlistintosqldict()
    #   [3] store the searchlist to redis
    #   [4] run a search on that dict with the golang searcher
    #   [5] do nothing: leave those lines from #3 in redis

    # [1] generate a searchlist: use executesearch() as the template

    # print('so.vectorquerytype', so.vectorquerytype)

    so.poll.statusis('Preparing to search')
    so.usecolumn = 'marked_up_line'
    activecorpora = so.getactivecorpora()
    so.cap = 99999999

    # so.seeking should only be set via a fallback when session['baggingmethod'] == 'unlemmatized'
    if (so.lemmaone or so.tovectorize or so.seeking) and activecorpora:
        so.poll.statusis('Compiling the list of works to search')
        so.searchlist = compilesearchlist(listmapper, so.session)
    elif not activecorpora:
        return abort(['no active corpora'])
    elif not so.searchlist:
        return abort(['empty list of places to look'])
    else:
        # note that some vector queries do not need a term; fix this later...
        return abort(['there was no search term'])

    # calculatewholeauthorsearches() + configurewhereclausedata()
    so = updatesearchlistandsearchobject(so)

    # [2] do a searchlistintosqldict()
    so.searchsqldict = searchlistintosqldict(so, str(), vectors=True)
    so.searchsqldict = rewritesqlsearchdictforgolang(so)
    debugmessage('\nso.searchsqldict:\n{d}\n'.format(d=so.searchsqldict))

    # [3] store the searchlist to redis
    rc = establishredisconnection()
    debugmessage('storing search at "{r}"'.format(r=so.searchid))
    for s in so.searchsqldict:
        rc.sadd(so.searchid, json.dumps(so.searchsqldict[s]))

    # [4] run a search on that dict

    if hipparchia.config['GOLANGLOADING'] != 'cli':
        resultrediskey = golangsharedlibrarysearcher(so)
    else:
        resultrediskey = golangclibinarysearcher(so)

    # [5] we now have a collection of lines stored in redis
    # HipparchiaGoVectorHelper can be told to just collect  and work on those lines

    target = so.searchid + '_results'
    if resultrediskey == target:
        vectorresultskey = golangclibinaryvectorhelper(so)
    else:
        fail = 'search for lines failed to return a proper result key: {a} ≠ {b}'.format(a=resultrediskey, b=target)
        consolewarning(fail, color='red')
        vectorresultskey = str()

    # OK we are done: the bags of words are waiting for us on redis
    # these should be collected and then handed over to Word2Vec()

    debugmessage('golangvectors() reports that the vectorresultskey = {r}'.format(r=vectorresultskey))

    debugmessage('fetching search from "{r}"'.format(r=vectorresultskey))

    redisresults = list()
    while vectorresultskey:
        r = rc.spop(vectorresultskey)
        if r:
            redisresults.append(r)
        else:
            vectorresultskey = None

    hits = redishitintobagofwordsdict(redisresults)
    bagsofwords = [hits[k] for k in hits]
    debugmessage('first bag is {b}'.format(b=bagsofwords[0]))

    themodel = golangbuildgensimmodel(so, bagsofwords)

    jsonoutput = generatenearestneighbordata(None, len(so.searchlist), so, themodel)

    return jsonoutput


def redishitintobagofwordsdict(redisresults: List[JSONDICT]) -> dict:
    """

    convert a golang struct stored as json in the redis server into a dict

    type SentenceWithLocus struct {
        Loc  string
        Sent string
    }

    """

    js = [json.loads(r) for r in redisresults]

    d = {j['Loc']: j['Sent'] for j in js}

    return d


def golangclibinaryvectorhelper(so: SearchObject) -> str:
    """

    use the cli interface to HipparchiaGoVectorHelper to execute [a]-[i]
    as outlined in golangvectors() above

    """

    vectorresultskey = genericgolangcliexecution(hipparchia.config['GOLANGVECTORBINARYNAME'], formatgolangvectorhelperarguments, so)
    return vectorresultskey


def formatgolangvectorhelperarguments(command: str, so: SearchObject) -> list:
    """

    Usage of ./HipparchiaGoVectorHelper:
      -b string
            the bagging method: choices are [alternates], [flat], unlemmatized, [winntertakesall] (default "unlemmatized")
      -k string
            the search key
      -l int
            logging level: 0 is silent; 4 is very noisy (default 4)
      -p string
            psql logon information (as a JSON string) (default "{\"Host\": \"localhost\", \"Port\": 5432, \"User\": \"hippa_wr\", \"Pass\": \"\", \"DBName\": \"hipparchiaDB\"}")
      -r string
            redis logon information (as a JSON string) (default "{\"Addr\": \"localhost:6379\", \"Password\": \"\", \"DB\": 0}")
      -v    print version and exit
      -xb string
            [for manual debugging] db to grab from (default "lt0448")
      -xe int
            [for manual debugging] last line to grab (default 26)
      -xs int
            [for manual debugging] first line to grab (default 1)

    """

    arguments = dict()

    arguments['b'] = so.session['baggingmethod']
    arguments['k'] = so.searchid + '_results'
    arguments['l'] = hipparchia.config['GOLANGVECTORLOGLEVEL']

    rld = {'Addr': '{a}:{b}'.format(a=hipparchia.config['REDISHOST'], b=hipparchia.config['REDISPORT']),
           'Password': str(),
           'DB': hipparchia.config['REDISDBID']}
    arguments['r'] = json.dumps(rld)

    # rw user by default atm; can do this smarter...
    psd = {'Host': hipparchia.config['DBHOST'],
           'Port': hipparchia.config['DBPORT'],
           'User': hipparchia.config['DBWRITEUSER'],
           'Pass': hipparchia.config['DBWRITEPASS'],
           'DBName': hipparchia.config['DBNAME']}

    if hipparchia.config['GOLANGBINARYKNOWSLOGININFO']:
        pass
    else:
        arguments['p'] = json.dumps(psd)

    argumentlist = [['-{k}'.format(k=k), '{v}'.format(v=arguments[k])] for k in arguments]
    argumentlist = flattenlistoflists(argumentlist)
    commandandarguments = [command] + argumentlist

    return commandandarguments


def golangbuildgensimmodel(so: SearchObject, bagsofwords: list) -> Word2Vec:
    """

    [a virtual clone of buildgensimmodel() in gensimmodels.py]

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

    storevectorindatabase(so, typelabel, gensimmodel)

    return gensimmodel
