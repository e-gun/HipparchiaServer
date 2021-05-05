# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import json

from server import hipparchia
from server.dbsupport.redisdbfunctions import establishredisconnection
from server.dbsupport.vectordbfunctions import checkforstoredvector
from server.formatting.miscformatting import consolewarning, debugmessage
from server.formatting.vectorformatting import ldatopicsgenerateoutput
from server.hipparchiaobjects.searchobjects import SearchObject
from server.listsandsession.genericlistfunctions import flattenlistoflists
from server.routes.searchroute import updatesearchlistandsearchobject
from server.searching.precomposedsearchgolanginterface import golangclibinarysearcher, golangsharedlibrarysearcher
from server.searching.precomposesql import searchlistintosqldict, rewritesqlsearchdictforgolang
from server.searching.searchhelperfunctions import genericgolangcliexecution
from server.semanticvectors.gensimnearestneighbors import generatenearestneighbordata
from server.semanticvectors.modelbuilders import buildgensimmodel, buildsklearnselectedworks, \
    gensimgenerateanalogies
from server.semanticvectors.vectorhelpers import mostcommonwordsviaheadwords, removestopwords
from server.semanticvectors.vectorpipeline import checkneedtoabort

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


def golangvectors(so: SearchObject) -> JSON_STR:
    """

    the flow inside of go, but this overview is useful for looking at hipparchia's python

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

    in order to meet the requirements of [a] above we need to
      [0] test to see what will happen:
        [a] scope problems? [jump away if so...]
        [b] already a model on file? ... [jump down to #7 if so]
      [1] generate a searchlist
      [2] do a searchlistintosqldict()
      [3] store the searchlist to redis
      [4] run a search on that dict with the golang helper in order to acquire the lines that will become bags
      [5] tell HipparchiaGoVectorHelper can be told to just collect and work on those lines

      then after [a]-[i] happens....

      [6] collect the bags of words and hand them over to Word2Vec(), etc. [*]
      [7] run queries against the model and return the JSON results

    NB: we are assuming you also have the golanggrabber available

    n6:
        127.0.0.1:6379> spop 2b10de72_vectorresults 4
        1) "{\"Loc\":\"line/lt0472w001/615\",\"Sent\":\"acceptum facio reddo lesbia mius praesens malus\xc2\xb2 multus dico\xc2\xb2 non possum reticeo detondeo qui\xc2\xb9 ego in reor attulo\"}"
        2) "{\"Loc\":\"line/lt0472w001/1294\",\"Sent\":\"jacio hederiger quandoquidem fortuna meus atque tuus ego miser aspicio et si puriter ago qui\xc2\xb2 enim genus\xc2\xb9 figura curro duco subtemen curro fundo\xc2\xb9\"}"
        3) "{\"Loc\":\"line/lt0472w001/2296\",\"Sent\":\"qui\xc2\xb2 tu nunc chordus\xc2\xb9 quis\xc2\xb9 tu praepono nos possum\"}"
        4) "{\"Loc\":\"line/lt0472w001/1105\",\"Sent\":\"rasilis subeo foris\xc2\xb9\"}"

    """
    debugmessage('golangvectors()')
    assert so.vectorquerytype in ['analogies', 'nearestneighborsquery', 'topicmodel']

    # [0] is this really going to happen?

    # [i] do we bail out before even getting started?
    so.poll.statusis('Checking for valid search')
    abortjson = checkneedtoabort(so)
    if abortjson:
        del so.poll
        return abortjson

    # [ii] do we actually have a model stored already?
    so.poll.statusis('Checking for stored search')
    themodel = checkforstoredvector(so)

    if not themodel:
        # [1] generate a searchlist: use executesearch() as the template

        so.poll.statusis('Preparing to search')
        so.usecolumn = 'marked_up_line'
        so.cap = 199999999

        # calculatewholeauthorsearches() + configurewhereclausedata()
        so = updatesearchlistandsearchobject(so)

        # [2] do a searchlistintosqldict()
        so.searchsqldict = searchlistintosqldict(so, str(), vectors=True)
        so.searchsqldict = rewritesqlsearchdictforgolang(so)

        # [3] store the searchlist to redis
        so.poll.statusis('Dispatching the search instructions to the searcher')
        rc = establishredisconnection()
        debugmessage('storing search at "{r}"'.format(r=so.searchid))
        for s in so.searchsqldict:
            rc.sadd(so.searchid, json.dumps(so.searchsqldict[s]))

        # [4] run a search on that dict with the golang helper in order to acquire the lines that will become bags
        so.poll.statusis('Grabbing a collection of lines')
        if hipparchia.config['GOLANGLOADING'] != 'cli':
            resultrediskey = golangsharedlibrarysearcher(so)
        else:
            resultrediskey = golangclibinarysearcher(so)

        # [5] tell HipparchiaGoVectorHelper can be told to just collect and work on those lines
        so.poll.statusis('Preparing and bagging the collection of sentences')
        so.poll.allworkis(-1)  # this turns off the % completed notice in the JS
        so.poll.sethits(0)
        target = so.searchid + '_results'
        if resultrediskey == target:
            vectorresultskey = golangclibinaryvectorhelper(so)
        else:
            fail = 'search for lines failed to return a proper result key: {a} ≠ {b}'.format(a=resultrediskey, b=target)
            consolewarning(fail, color='red')
            vectorresultskey = str()

        # this means that [a]-[i] has now happened....

        # [6] collect the sentences and hand them over to Word2Vec(), etc.
        so.poll.statusis('Fetching the bags of words')
        debugmessage('golangvectors() reports that the vectorresultskey = {r}'.format(r=vectorresultskey))
        debugmessage('fetching search from "{r}"'.format(r=vectorresultskey))

        redisresults = list()
        while vectorresultskey:
            r = rc.spop(vectorresultskey)
            if r:
                redisresults.append(r)
            else:
                vectorresultskey = None

        js = [json.loads(r) for r in redisresults]
        hits = {j['Loc']: j['Sent'] for j in js}
        # note that we are about to toss the 'Loc' info that we compiled (and used as a k in k/v pairs...)
        # there are (currently unused) vector styles that can require it
        bagsofwords = [hits[k].split(' ') for k in hits]
        debugmessage('first bag is {b}'.format(b=bagsofwords[0]))
        debugmessage('# of bags is {b}'.format(b=len(bagsofwords)))

        so.poll.statusis('Building the model')
        if so.vectorquerytype == 'nearestneighborsquery':
            themodel = buildgensimmodel(so, bagsofwords)
        elif so.vectorquerytype == 'analogies':
            # the same gensim model can serve both analogies and neighbors
            themodel = buildgensimmodel(so, bagsofwords)
        elif so.vectorquerytype == 'topicmodel':
            stops = list(mostcommonwordsviaheadwords())
            bagsofsentences = [' '.join(b) for b in bagsofwords]
            bagsofsentences = [removestopwords(s, stops) for s in bagsofsentences]
            themodel = buildsklearnselectedworks(so, bagsofsentences)
        else:
            pass

    # so we have a model one way or the other by now...
    # [7] run queries against the model and return the JSON results

    if so.vectorquerytype == 'nearestneighborsquery':
        jsonoutput = generatenearestneighbordata(None, len(so.searchlist), so, themodel)
    elif so.vectorquerytype == 'analogies':
        jsonoutput = gensimgenerateanalogies(themodel, so)
    elif so.vectorquerytype == 'topicmodel':
        # def ldatopicsgenerateoutput(ldavishtmlandjs: str, workssearched: int, settings: dict, searchobject: SearchObject):
        jsonoutput = ldatopicsgenerateoutput(themodel, so)
    else:
        jsonoutput = json.dumps('golang cannot execute {s} queries'.format(s=so.vectorquerytype))
    return jsonoutput


def golangclibinaryvectorhelper(so: SearchObject) -> str:
    """

    use the cli interface to HipparchiaGoVectorHelper to execute [a]-[i]
    as outlined in golangvectors() above

    """

    bin = hipparchia.config['GOLANGVECTORBINARYNAME']

    vectorresultskey = genericgolangcliexecution(bin, formatgolangvectorhelperarguments, so)
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