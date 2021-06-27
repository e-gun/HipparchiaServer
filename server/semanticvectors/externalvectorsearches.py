# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import json

from server import hipparchia
from server.dbsupport.redisdbfunctions import establishredisconnection, redisfetch
from server.dbsupport.vectordbfunctions import checkforstoredvector
from server.formatting.miscformatting import consolewarning, debugmessage
from server.formatting.vectorformatting import ldatopicsgenerateoutput
from server.hipparchiaobjects.searchobjects import SearchObject
from server.listsandsession.genericlistfunctions import flattenlistoflists
from server.routes.searchroute import updatesearchlistandsearchobject
from server.searching.miscsearchfunctions import genericexternalcliexecution
from server.searching.precomposesql import searchlistintosqldict, rewritesqlsearchdictforexternalhelper
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


def externalvectors(so: SearchObject) -> JSON_STR:
    """

    the flow inside of go, but this overview is useful for looking at hipparchia's python

    our paradigm case is going to be a nearest neighbors query; to do this you need to...

    [a] grab db lines that are relevant to the search
    [b] turn them into a unified text block
    [c] do some preliminary cleanups
    [d] break the text into sentences and assemble []BagWithLocus (NB: these are "unlemmatized bags of words")
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
      [3] run a search on that dict with the golang helper in order to acquire the lines that will become bags
      [4] tell HipparchiaGoVectorHelper can be told to just collect and work on those lines

      then after [a]-[i] happens....

      [5] collect the bags of words and hand them over to Word2Vec(), etc. [*]
      [6] run queries against the model and return the JSON results

    NB: we are assuming you also have the golanggrabber available

    at the moment only the cli binary will search: the module version has not been configured yet...

    n6:
        127.0.0.1:6379> spop 2b10de72_vectorresults 4
        1) "{\"Loc\":\"line/lt0472w001/615\",\"Bag\":\"acceptum facio reddo lesbia mius praesens malus\xc2\xb2 multus dico\xc2\xb2 non possum reticeo detondeo qui\xc2\xb9 ego in reor attulo\"}"
        2) "{\"Loc\":\"line/lt0472w001/1294\",\"Bag\":\"jacio hederiger quandoquidem fortuna meus atque tuus ego miser aspicio et si puriter ago qui\xc2\xb2 enim genus\xc2\xb9 figura curro duco subtemen curro fundo\xc2\xb9\"}"
        3) "{\"Loc\":\"line/lt0472w001/2296\",\"Bag\":\"qui\xc2\xb2 tu nunc chordus\xc2\xb9 quis\xc2\xb9 tu praepono nos possum\"}"
        4) "{\"Loc\":\"line/lt0472w001/1105\",\"Bag\":\"rasilis subeo foris\xc2\xb9\"}"

    """

    # debugmessage('golangvectors()')
    assert so.vectorquerytype in ['analogies', 'nearestneighborsquery', 'topicmodel']

    # [0] is this really going to happen?

    # [i] do we bail out before even getting started?
    so.poll.statusis('Checking for valid search')

    abortjson = checkneedtoabort(so)
    if abortjson:
        so.poll.deleteredispoll()
        return abortjson

    # [ii] do we actually have a model stored already?
    so.poll.statusis('Checking for stored search')
    # calculatewholeauthorsearches() + configurewhereclausedata()
    so = updatesearchlistandsearchobject(so)
    so.setsearchlistthumbprint()
    so.poll.allworkis(-1)  # this turns off the % completed notice in the JS
    so.poll.sethits(0)

    themodel = checkforstoredvector(so)

    if not themodel:
        # [1] generate a searchlist: use executesearch() as the template

        so.poll.statusis('Preparing to search')
        so.usecolumn = 'marked_up_line'

        so.cap = 199999999

        # [2] do a searchlistintosqldict()
        so.searchsqldict = searchlistintosqldict(so, str(), vectors=True)
        so.searchsqldict = rewritesqlsearchdictforexternalhelper(so)

        # [3] store the searchlist to redis
        so.poll.statusis('Dispatching the search instructions to the searcher')
        rc = establishredisconnection()
        # debugmessage('storing search at "{r}"'.format(r=so.searchid))

        for s in so.searchsqldict:
            rc.sadd(so.searchid, json.dumps(so.searchsqldict[s]))

        # [4] run a search for the lines we need on that dict with the golang helper
        # don't use golangsharedlibrarysearcher() because the round trip kills you:
        #   grab lines; store lines; fetch lines; process lines...
        # instead run the search that grabs the lines internally to the helper
        # that then hands these off to the bagger

        so.poll.statusis('Grabbing a collection of lines')
        vectorresultskey = externalclibinaryvectorhelper(so)
        so.poll.allworkis(-1)
        so.poll.sethits(0)

        # this means that [a]-[i] has now happened....

        # [5] collect the sentences and hand them over to Word2Vec(), etc.
        so.poll.statusis('Fetching the bags of words')

        redisresults = redisfetch(vectorresultskey)
        debugmessage('fetched {r} bags from {k}'.format(k=vectorresultskey, r=len(redisresults)))

        # results results are in dict form...
        js = [json.loads(r) for r in redisresults]
        hits = {j['Loc']: j['Bag'] for j in js}

        # note that we are about to toss the 'Loc' info that we compiled (and used as a k in k/v pairs...)
        # there are (currently unused) vector styles that can require it
        bagsofsentences = [hits[k] for k in hits]

        # do this inside the module...
        # stops = list(mostcommonwordsviaheadwords())
        # bagsofsentences = [removestopwords(s, stops) for s in bagsofsentences]

        bagsofwords = [b.split(' ') for b in bagsofsentences]

        # try:
        #     debugmessage('10-100th bags are {b}'.format(b=bagsofwords[10:100]))
        #     debugmessage('# of bags is {b}'.format(b=len(bagsofwords)))
        # except IndexError:
        #     debugmessage('you have a problem: there were no bags of words')

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
    elif so.iamarobot:
        # there is a model and the bot is attempting to build something that has already been build
        return '<!-- MODEL EXISTS -->'

    # so we have a model one way or the other by now...
    # [6] run queries against the model and return the JSON results
    if so.iamarobot:
        return '<!-- MODEL BUILT -->'

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


def externalclibinaryvectorhelper(so: SearchObject) -> str:
    """

    use the cli interface to HipparchiaGoVectorHelper to execute [a]-[i]
    as outlined in golangvectors() above

    note that it is possible to use the module to do the vectors:

    [ hipparchia_venv/HipparchiaServer/ % python3 ]

        import server.externalmodule.hipparchiagolangsearching as gs
        r = gs.NewRedisLogin('localhost:6379', '', 0)
        p = gs.NewPostgresLogin('localhost', 5432, 'hippa_rd', 'MYPASSWORD', 'hipparchiaDB')
        b = gs.HipparchiaBagger
        b('x', 'winnertakesall', 5, 'lt0448', 1, 26, 3, '', '', r, p)

    but we are currently not implementing that

    note the two "missing" parameters: these are stopword strings that *must* be supplied by
    module users: 'one two three...'

    """

    bin = hipparchia.config['EXTERNALBINARYNAME']
    vectorresultskey = genericexternalcliexecution(bin, formatexternalappvectorhelperarguments, so)

    return vectorresultskey


def formatexternalappvectorhelperarguments(command: str, so: SearchObject) -> list:
    """
    Hipparchia Golang Helper CLI Debugging Interface (v.1.3.0)

    Usage of ./HipparchiaGoDBHelper:
      -c int
            [searches] max hit count (default 200)
      -k string
            [searches] redis key to use
      -l int
            [common] logging level: 0 is silent; 5 is very noisy (default 1)
      -p string
            [common] psql logon information (as a JSON string) (default "{\"Host\": \"localhost\", \"Port\": 5432, \"User\": \"hippa_wr\", \"Pass\": \"\", \"DBName\": \"hipparchiaDB\"}")
      -r string
            [common] redis logon information (as a JSON string) (default "{\"Addr\": \"localhost:6379\", \"Password\": \"\", \"DB\": 0}")
      -sv
            [vectors] assert that this is a vectorizing run
      -svb string
            [vectors] the bagging method: choices are alternates, flat, unlemmatized, winnertakesall (default "winnertakesall")
      -svbs int
            [vectors] number of sentences per bag (default 1)
      -svdb string
            [vectors][for manual debugging] db to grab from (default "lt0448")
      -sve int
            [vectors][for manual debugging] last line to grab (default 26)
      -svhw string
            [vectors] provide a string of headwords to skip 'one two three...' (default "(suppressed owing to length)")
      -svin string
            [vectors][provide a string of inflected forms to skip 'one two three...' (default "(suppressed owing to length)")
      -svs int
            [vectors][for manual debugging] first line to grab (default 1)
      -t int
            [common] number of goroutines to dispatch (default 5)
      -v	[common] print version and exit
      -ws
            [websockets] assert that you are requesting the websocket server
      -wsf int
            [websockets] fail threshold before messages stop being sent (default 3)
      -wsp int
            [websockets] port on which to open the websocket server (default 5010)
      -wss int
            [websockets] save the polls instead of deleting them: 0 is no; 1 is yes

      note that "-svhw" and "-svin" are currently uncalled: the built-in defaults are the only option

    """

    if 'Rust' not in hipparchia.config['EXTERNALBINARYNAME']:
        # irritating '--x' vs '-x' issue...
        prefix = '-'
    else:
        prefix = '--'

    arguments = dict()

    arguments['svb'] = so.session['baggingmethod']
    arguments['svbs'] = so.session['vsentperdoc']
    arguments['k'] = so.searchid
    arguments['l'] = hipparchia.config['EXTERNAVECTORLOGLEVEL']

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

    if hipparchia.config['EXTERNALBINARYKNOWSLOGININFO']:
        pass
    else:
        arguments['p'] = json.dumps(psd)

    argumentlist = [['{x}{k}'.format(k=k, x=prefix), '{v}'.format(v=arguments[k])] for k in arguments]
    argumentlist.append(['{x}sv'.format(x=prefix)])
    argumentlist = flattenlistoflists(argumentlist)
    commandandarguments = [command] + argumentlist

    return commandandarguments