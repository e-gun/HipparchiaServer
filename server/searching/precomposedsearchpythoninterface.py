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


def precomposedsqlsearchmanager(so: SearchObject) -> List[dbWorkLine]:
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

    activepoll.allworkis(len(searchsqlbyauthor))
    activepoll.remain(len(searchsqlbyauthor))
    activepoll.sethits(0)

    argumentuple = [foundlineobjects, searchsqlbyauthor, so]

    oneconnectionperworker = {i: ConnectionObject() for i in range(workers)}
    argumentswithconnections = [tuple([i] + list(argumentuple) + [oneconnectionperworker[i]]) for i in range(workers)]

    jobs = [Process(target=workonprecomposedsqlsearch, args=argumentswithconnections[i]) for i in range(workers)]

    for j in jobs:
        j.start()
    for j in jobs:
        j.join()

    # generator needs to turn into a list
    foundlineobjects = list(foundlineobjects)

    for c in oneconnectionperworker:
        oneconnectionperworker[c].connectioncleanup()

    return foundlineobjects


def workonprecomposedsqlsearch(workerid: int, foundlineobjects: ListProxy, listofplacestosearch: ListProxy,
                               searchobject: SearchObject, dbconnection) -> ListProxy:
    """

    iterate through listofplacestosearch

    execute precomposedsqlsearcher() on each item in the list

    gather the results...

    listofplacestosearch elements are dicts and the whole looks like:

        [{'temptable': '', 'query': 'SELECT ...', 'data': ('ὕβριν',)},
        {'temptable': '', 'query': 'SELECT ...', 'data': ('ὕβριν',)} ...]

    this is supposed to give you one query per hipparchiaDB table unless you are lemmatizing

    """

    # if workerid == 0:
    #     print('{w} - listofplacestosearch'.format(w=workerid), listofplacestosearch)
    so = searchobject
    activepoll = so.poll
    dbconnection.setreadonly(False)
    dbcursor = dbconnection.cursor()
    commitcount = 0
    getnetxitem = listofplacestosearch.pop
    emptyerror = IndexError
    remaindererror = TypeError

    while listofplacestosearch and activepoll.gethits() <= so.cap:
        # if workerid == 0:
        #     print('remain:', len(listofplacestosearch))
        commitcount += 1
        dbconnection.checkneedtocommit(commitcount)

        try:
            querydict = getnetxitem(0)
        except emptyerror:
            querydict = None
            listofplacestosearch = None

        if querydict:
            foundlines = precomposedsqlsearcher(querydict, dbcursor)
            lineobjects = [dblineintolineobject(f) for f in foundlines]
            foundlineobjects.extend(lineobjects)

            if lineobjects:
                numberoffinds = len(lineobjects)
                activepoll.addhits(numberoffinds)
        else:
            listofplacestosearch = None

        try:
            activepoll.remain(len(listofplacestosearch))
        except remaindererror:
            pass

    return foundlineobjects


def precomposedsqlsearcher(querydict, dbcursor) -> Generator:
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

    # debugmessage('precomposedsqlsearcher() querydict = {q}'.format(q=querydict))
    # debugmessage('precomposedsqlsearcher() q:\n\t{q}\nd:\n\t{d}'.format(q=q, d=d))

    warnings = {
        1: 'DataError; cannot search for »{d}«\n\tcheck for unbalanced parentheses and/or bad regex',
        2: 'psycopg2.InternalError; did not execute query="{q}" and data="{d}',
        3: 'precomposedsqlsearcher() DatabaseError for {c} @ {p}'
    }

    try:
        dbcursor.execute(q, d)
        found = resultiterator(dbcursor)
    except psycopg2.DataError:
        # e.g., invalid regular expression: parentheses () not balanced
        consolewarning(warnings[1].format(d=d[0]), color='red')
    except psycopg2.InternalError:
        # current transaction is aborted, commands ignored until end of transaction block
        consolewarning(warnings[2].format(q=q, d=d), color='red')
    except psycopg2.DatabaseError:
        # psycopg2.DatabaseError: error with status PGRES_TUPLES_OK and no message from the libpq
        # added to track PooledConnection threading issues
        # will see: 'DatabaseError for <cursor object at 0x136bab520; closed: 0> @ Process-4'
        consolewarning(warnings[3].format(c=dbcursor, p=multiprocessing.current_process().name), color='red')
        consolewarning('\tq, d: {q}, {d}'.format(q=q, d=q))

    return found