# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import json
from os import path

from server import hipparchia
from server.formatting.miscformatting import consolewarning, debugmessage
from server.hipparchiaobjects.searchobjects import SearchObject
from server.listsandsession.genericlistfunctions import flattenlistoflists
from server.listsandsession.searchlistmanagement import compilesearchlist
from server.routes.searchroute import updatesearchlistandsearchobject
from server.searching.searchhelperfunctions import genericgolangcliexecution
from server.searching.precomposedsearchgolanginterface import golangclibinarysearcher, golangsharedlibrarysearcher
from server.searching.precomposesql import searchlistintosqldict, rewritesqlsearchdictforgolang
from server.semanticvectors.vectorroutehelperfunctions import emptyvectoroutput
from server.startup import listmapper

JSON_STR = str


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

    """

    abort = lambda x: emptyvectoroutput(so, x)

    consolewarning('in progress; will not return results', color='red')

    # in order to meet the requirements of [a] above we need to
    #   [1] generate a searchlist
    #   [2] do a searchlistintosqldict()
    #   [3] run a search on that dict with the golang searcher
    #   [4] do nothing: leave those lines from #3 in redis

    # [1] generate a searchlist: use executesearch() as the template

    # print('so.vectorquerytype', so.vectorquerytype)

    so.poll.statusis('Preparing to search')
    so.usecolumn = 'marked_up_line'
    activecorpora = so.getactivecorpora()

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

    # [3] run a search on that dict

    if hipparchia.config['GOLANGLOADING'] != 'cli':
        resultrediskey = golangsharedlibrarysearcher(so)
    else:
        resultrediskey = golangclibinarysearcher(so)

    # [4] we now have a collection of lines stored in redis
    # HipparchiaGoVectorHelper can be told to just collect those lines

    target = so.searchid + '_results'
    if resultrediskey == target:
        vectorresultskey = golangclibinaryvectorhelper(resultrediskey, so)
    else:
        fail = 'search for lines failed to return a proper result key: {a} ≠ {b}'.format(a=resultrediskey, b=target)
        consolewarning(fail, color='red')
        vectorresultskey = str()

    debugmessage('golangvectors() vectorresultskey = {r}'.format(r=vectorresultskey))
    return str()


def golangclibinaryvectorhelper(resultrediskey: str, so: SearchObject) -> str():
    """

    use the cli interface to HipparchiaGoVectorHelper to execute [a]-[i]
    as outlined in golangvectors() above

    """

    return genericgolangcliexecution(hipparchia.config['GOLANGVECTORBINARYNAME'], formatgolangvectorhelperarguments, so)


def formatgolangvectorhelperarguments(command: str, searchkey: str, so: SearchObject) -> list:
    """

    Usage of ./HipparchiaGoVectorHelper:
    -k string
        the search key
    -l int
        logging level: 0 is silent; 4 is very noisy (default 4)
    -p string
        psql logon information (as a JSON string) (default "{\"Host\": \"localhost\", \"Port\": 5432, \"User\": \"hippa_wr\", \"Pass\": \"\", \"DBName\": \"hipparchiaDB\"}")
    -r string
        redis logon information (as a JSON string) (default "{\"Addr\": \"localhost:6379\", \"Password\": \"\", \"DB\": 0}")
    -v	print version and exit
    -xb string
        [for manual debugging] db to grab from (default "lt0448")
    -xe int
        [for manual debugging] last line to grab (default 26)
    -xs int
        [for manual debugging] first line to grab

    """

    arguments = dict()

    arguments['k'] = searchkey
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

