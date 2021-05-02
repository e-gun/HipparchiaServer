# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import json
import subprocess
from os import path
from typing import List

from server import hipparchia
from server.dbsupport.redisdbfunctions import establishredisconnection
from server.formatting.miscformatting import debugmessage, consolewarning
from server.hipparchiaobjects.searchobjects import SearchObject
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.searching.precomposesql import rewritesqlsearchdictforgolang
from server.searching.precomposedsearchpythoninterface import precomposedsqlsearchmanager
from server.searching.searchhelperfunctions import redishitintodbworkline, formatgolanggrabberarguments, \
    genericgolangcliexecution
from server.threading.mpthreadcount import setthreadcount

gosearch = None
try:
    from server.golangmodule import hipparchiagolangsearching as gosearch
except ImportError as e:
    debugmessage('golang search module unavailable:\n\t"{e}"'.format(e=e))

if gosearch:
    goredislogin = gosearch.NewRedisLogin('{h}:{p}'.format(h=hipparchia.config['REDISHOST'],
                                          p=hipparchia.config['REDISPORT']), str(), hipparchia.config['REDISDBID'])
    gopsqlloginro = gosearch.NewPostgresLogin(hipparchia.config['DBHOST'], hipparchia.config['DBPORT'],
                                            hipparchia.config['DBUSER'], hipparchia.config['DBPASS'],
                                            hipparchia.config['DBNAME'])
    gopsqlloginrw = gosearch.NewPostgresLogin(hipparchia.config['DBHOST'], hipparchia.config['DBPORT'],
                                            hipparchia.config['DBWRITEUSER'], hipparchia.config['DBWRITEPASS'],
                                            hipparchia.config['DBNAME'])

try:
    import redis
    c = establishredisconnection()
    c.ping()
    canuseredis = True
    del c
except ImportError:
    canuseredis = False
except redis.exceptions.ConnectionError:
    canuseredis = False


def precomposedgolangsearcher(so: SearchObject) -> List[dbWorkLine]:
    """

    you are using golang to do the search

    [1] send the searchdict to redis as a list of json.dumps(items) (keyed to the searchid)
    [2] send the external fnc the searchid, cap value, worker #, psql login info, redis login info
    [3] wait for the function to (a) gather; (b) search; (c) store
    [4] pull the results back from redis via the searchid
    NB: redis makes sense because the activity poll is going to have to be done via redis anyway...

    the searched items are stored under the redis key 'searchid_results'
    json.loads() will leave you with a dictionary of k/v pairs that can be turned into a dbWorkLine

    """

    warning = 'attempted to search via golang but {x} is not available using precomposedsqlsearchmanager() instead'

    if not gosearch:
        consolewarning(warning.format(x='golang'), color='red')
        return precomposedsqlsearchmanager(so)

    if not canuseredis:
        consolewarning(warning.format(x='redis'), color='red')
        return precomposedsqlsearchmanager(so)

    rc = establishredisconnection()

    so.searchsqldict = rewritesqlsearchdictforgolang(so)
    debugmessage('storing search at "{r}"'.format(r=so.searchid))
    for s in so.searchsqldict:
        rc.sadd(so.searchid, json.dumps(so.searchsqldict[s]))

    if hipparchia.config['GOLANGLOADING'] != 'cli':
        resultrediskey = golangsharedlibrarysearcher(so)
    else:
        resultrediskey = golangclibinarysearcher(so)

    redisresults = list()

    while resultrediskey:
        r = rc.spop(resultrediskey)
        if r:
            redisresults.append(r)
        else:
            resultrediskey = None

    hits = [redishitintodbworkline(r) for r in redisresults]

    return hits


def golangclibinarysearcher(so: SearchObject) -> str:
    """

    you have decided to call the "golanggrabber" binary

    invoke it by telling it the search id, etc.

    then wait for it to finish and report that the results are ready

    """

    debugmessage('calling {e}'.format(e=hipparchia.config['GOLANGCLIBINARYNAME']))

    return genericgolangcliexecution(hipparchia.config['GOLANGCLIBINARYNAME'], formatgolanggrabberarguments, so)


def golangsharedlibrarysearcher(so: SearchObject) -> str:
    """

    use the shared library to do the golang search

    at the moment the progress polls will not update; it seems that the module locks python up

    the cli version can read set the poll data and have it get read by wscheckpoll()
    the module is setting the poll data, but it is not getting read by wscheckpoll()
        wscheckpoll() will loop 0-2 times: wscheckpoll() {'total': -1, 'remaining': -1, 'hits': -1, ...}
        then it locks during the search
        then it unlocks after the search is over: wscheckpoll() {'total': 776, 'remaining': 0, 'hits': 18, ... }

        conversely if the cli app is searching wscheckpoll() will update every .4s, as expected

    """

    debugmessage('calling golang via the golang module')
    searcher = gosearch.HipparchiaGolangSearcher
    resultrediskey = searcher(so.searchid, so.cap, setthreadcount(), hipparchia.config['GOLANGMODLOGLEVEL'],
                              goredislogin, gopsqlloginrw)
    debugmessage('search completed and stored at "{r}"'.format(r=resultrediskey))

    return resultrediskey
