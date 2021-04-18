# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import multiprocessing
import re
from multiprocessing import Manager
from multiprocessing.context import Process
from multiprocessing.managers import ListProxy
from typing import List, Generator

import psycopg2

from server.dbsupport.dblinefunctions import dblineintolineobject
from server.dbsupport.miscdbfunctions import resultiterator
from server.dbsupport.tablefunctions import assignuniquename
from server.formatting.miscformatting import consolewarning
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.searchobjects import SearchObject
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.threading.mpthreadcount import setthreadcount
from server.listsandsession.searchlistintosql import searchlistintosqldict, rewritesqlsearchdictforlemmata
from server.listsandsession.whereclauses import wholeworktemptablecontents
from server import hipparchia


def rawsqlsearches(so: SearchObject) -> List[dbWorkLine]:
    """

    flow control for searching governed by so.searchtype

    """

    assert so.searchtype in ['simple', 'simplelemma', 'proximity', 'phrase'], 'unknown searchtype sent to rawsqlsearches()'

    so.searchsqldict = prepsearchsqldict(so)

    hitlist = list()

    if so.searchtype in ['simple', 'simplelemma']:
        hitlist = rawdsqlsearchmanager(so)
    elif so.searchtype == 'proximity':
        # can't do proximate lemmata yet
        if so.scope == 'lines':
            # this will hit rawdsqlsearchmanager() 2x
            hitlist = sqlwithinxlinessearch(so)
        else:
            consolewarning('unable to do within-x-words ATM', color='red')
    else:
        consolewarning('rawsqlsearches() not yet supporting {t} searching'.format(t=so.searchtype), color='red')

    return hitlist


def prepsearchsqldict(searchobject: SearchObject, forcelemmata=False) -> dict:
    """

    should the searchsqldict be lemmatized or not?

    """
    so = searchobject
    searchsqldict = searchlistintosqldict(so, so.termone)

    if so.lemma or forcelemmata:
        searchsqldict = rewritesqlsearchdictforlemmata(so)

    return searchsqldict


def rawdsqlsearchmanager(so: SearchObject) -> List[dbWorkLine]:
    """

    quick and dirty dispatcher: not polished

    note that you need so.searchsqldict to be properly configured before you get here

    fix this up last...

    """

    activepoll = so.poll

    workers = setthreadcount()

    manager = Manager()
    foundlineobjects = manager.list()

    searchsqlbyauthor = [so.searchsqldict[k] for k in so.searchsqldict.keys()]
    searchsqlbyauthor = manager.list(searchsqlbyauthor)

    activepoll.allworkis(len(so.searchlist))
    activepoll.remain(len(so.indexrestrictions.keys()))
    activepoll.sethits(0)

    argumentuple = [foundlineobjects, searchsqlbyauthor, so]

    oneconnectionperworker = {i: ConnectionObject() for i in range(workers)}
    argumentswithconnections = [tuple([i] + list(argumentuple) + [oneconnectionperworker[i]]) for i in range(workers)]

    jobs = [Process(target=workonrawsqlsearch, args=argumentswithconnections[i]) for i in range(workers)]

    for j in jobs:
        j.start()
    for j in jobs:
        j.join()

    # generator needs to turn into a list
    foundlineobjects = list(foundlineobjects)

    for c in oneconnectionperworker:
        oneconnectionperworker[c].connectioncleanup()

    return foundlineobjects


def workonrawsqlsearch(workerid: int, foundlineobjects: ListProxy, listofplacestosearch: ListProxy,
                       searchobject: SearchObject, dbconnection) -> ListProxy:
    """

    iterate through listofplacestosearch

    execute rawsqlsearcher() on each item in the list

    gather the results...

    """


    so = searchobject
    activepoll = so.poll
    dbconnection.setreadonly(False)
    dbcursor = dbconnection.cursor()
    commitcount = 0
    getnetxitem = listofplacestosearch.pop
    remainder = listofplacestosearch
    emptyerror = IndexError
    remaindererror = TypeError

    while listofplacestosearch and activepoll.gethits() <= so.cap:
        commitcount += 1
        dbconnection.checkneedtocommit(commitcount)

        try:
            querydict = getnetxitem(0)
        except emptyerror:
            querydict = None
            listofplacestosearch = None

        if querydict:
            foundlines = rawsqlsearcher(querydict, dbcursor)
            lineobjects = [dblineintolineobject(f) for f in foundlines]
            foundlineobjects.extend(lineobjects)

            if lineobjects:
                # print(authortable, len(lineobjects))
                numberoffinds = len(lineobjects)
                activepoll.addhits(numberoffinds)
        else:
            listofplacestosearch = None

        try:
            activepoll.remain(len(remainder))
        except remaindererror:
            pass

    # print('workonrawsqlsearch() worker #{i} finished'.format(i=workerid))

    return foundlineobjects


def rawsqlsearcher(querydict, dbcursor) -> Generator:
    """

    as per substringsearchintosqldict():
        sq = { table1: {query: q, data: d, temptable: t},
        table2: {query: q, data: d, temptable: t},
        ... }

    only sent the dict at sq[tableN]

    """

    t = querydict['temptable']
    q = querydict['query']
    d = (querydict['data'],)

    if t:
        unique = assignuniquename()
        t = re.sub('UNIQUENAME', unique, t)
        q = re.sub('UNIQUENAME', unique, q)
        dbcursor.execute(t)

    found = list()

    try:
        dbcursor.execute(q, d)
        found = resultiterator(dbcursor)
    except psycopg2.DataError:
        # e.g., invalid regular expression: parentheses () not balanced
        consolewarning(
            'DataError; cannot search for »{d}«\n\tcheck for unbalanced parentheses and/or bad regex'.format(d=d[0]),
            color='red')
    except psycopg2.InternalError:
        # current transaction is aborted, commands ignored until end of transaction block
        consolewarning('psycopg2.InternalError; did not execute query="{q}" and data="{d}'.format(q=q, d=d),
                       color='red')
    except psycopg2.DatabaseError:
        # psycopg2.DatabaseError: error with status PGRES_TUPLES_OK and no message from the libpq
        # added to track PooledConnection threading issues
        # will see: 'DatabaseError for <cursor object at 0x136bab520; closed: 0> @ Process-4'
        consolewarning('DatabaseError for {c} @ {p}'.format(c=dbcursor, p=multiprocessing.current_process().name),
                       color='red')
        consolewarning('\tq, d', q, d)

    # print('rawsqlsearcher() q:\n\t{q}\nd:\n\t{d}'.format(q=q, d=d))

    return found


def sqlwithinxlinessearch(searchobject: SearchObject) -> List[dbWorkLine]:
    """

    after finding x, look for y within n lines of x

    people who send phrases to both halves and/or a lot of regex will not always get what they want

    """

    so = searchobject
    actualcap = so.cap
    so.cap = hipparchia.config['INTERMEDIATESEARCHCAP']

    hitlines = rawdsqlsearchmanager(so)
    so.cap = actualcap

    # we are going to need a new searchsqldict w/ a new temptable
    # sq = { table1: {query: q, data: d, temptable: t},
    #         table2: {query: q, data: d, temptable: t}, ...

    # this means refeeding searchlistintosqldict() and priming it for a 'temptable' search
    # the temptable follows the paradigm of wholeworktemptablecontents()
    # r {'type': 'temptable', 'where': {'tempquery': '\n\tCREATE TEMPORARY TABLE in0f08_includelist AS \n\t\tSELECT values \n\t\t\tAS includeindex FROM unnest(ARRAY[768,769,770,771,772,773,774,775,776,777,778,779,780,781,782,783,784,785,786,787,788,789,790,791,792,793,794,795,796,797,798,799,800,801,802,803,804,805,806,807,808,809,810,763,764,765,766,767]) values\n\t'}}

    # originalrestrictions = so.indexrestrictions
    # originalsearchlist = so.searchlist

    so.indexrestrictions = dict()
    authorsandlines = dict()

    # first build up { table1: [listoflinesweneed], table2: [listoflinesweneed], ...}
    for hl in hitlines:
        linestosearch = list(range(hl.index - so.distance, hl.index + so.distance + 1))
        try:
            authorsandlines[hl.authorid].extend(linestosearch)
        except KeyError:
            authorsandlines[hl.authorid] = linestosearch

    so.searchlist = list(authorsandlines.keys())

    for a in authorsandlines:
        so.indexrestrictions[a] = dict()
        so.indexrestrictions[a]['type'] = 'temptable'
        so.indexrestrictions[a]['where'] = wholeworktemptablecontents(a, set(authorsandlines[a]))
        # print("so.indexrestrictions[a]['where']", so.indexrestrictions[a]['where'])

    so.searchsqldict = searchlistintosqldict(so, so.termtwo)
    newhitlines = rawdsqlsearchmanager(so)

    # newhitlines will contain, e.g., in0001w0ig_493 and in0001w0ig_492, i.e., 2 lines that are part of the same 'hit'
    # so we need can't use newhitlines directly but have to check it against the initial hits
    # that's fine since "not near" would push us in this direction in any case

    initialhitlinedict = {hl.uniqueid: hl for hl in hitlines}
    newhitlineids = set()
    for nhl in newhitlines:
        indices = list(range(nhl.index - so.distance, nhl.index + so.distance + 1))
        ids = ['{a}_{b}'.format(a=nhl.wkuinversalid, b=i) for i in indices]
        newhitlineids.update(ids)

    finalhitlines = list()
    if so.near:
        # "is near"
        finalhitlines = [initialhitlinedict[hl] for hl in initialhitlinedict if hl in newhitlineids]
    elif not so.near:
        # "is not near"
        finalhitlines = [initialhitlinedict[hl] for hl in initialhitlinedict if hl not in newhitlineids]

    return finalhitlines



