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

from server import hipparchia
from server.dbsupport.dblinefunctions import dblineintolineobject, makeablankline, worklinetemplate
from server.dbsupport.miscdbfunctions import resultiterator
from server.dbsupport.tablefunctions import assignuniquename
from server.formatting.miscformatting import consolewarning, debugmessage
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.helperobjects import QueryCombinator
from server.hipparchiaobjects.searchobjects import SearchObject
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.searching.precomposesql import searchlistintosqldict, rewritesqlsearchdictforlemmata, \
    perparesoforsecondsqldict
from server.searching.searchhelperfunctions import rebuildsearchobjectviasearchorder, grableadingandlagging, \
    findleastcommonterm, findleastcommontermcount, lookoutsideoftheline
from server.threading.mpthreadcount import setthreadcount

"""
    OVERVIEW

[a] precomposedsqlsearch() picks a searchfnc: 
    [a1] basicprecomposedsqlsearcher ('simple' and 'single lemma' searching)
    [a2] precomposedsqlwithinxlinessearch ('proximity' by lines)
    [a3] precomposedsqlwithinxwords ('proximity' by words)
    [a4] precomposedsqlphrasesearch ('phrases' if the phrase contains an uncommon word)
    [a5] precomposedsqlsubqueryphrasesearch ('phrases' via a much more elaborate set of SQL queries)

[b] most of the searches nevertheless call basicprecomposedsqlsearcher()
    two-step searches will call basicprecomposedsqlsearcher() via  generatepreliminaryhitlist()

[c] eventually searching should either flow through a shared library or go through the in-house search code

[d] the in-house search code flow is: 
    [d1] precomposedsqlsearchmanager() - build a collection of MP workers who then workonprecomposedsqlsearch()
    [d2] workonprecomposedsqlsearch() - iterate through listofplacestosearch & execute precomposedsqlsearcher() on each item in the list
    [d3] precomposedsqlsearcher() - execute the basic sql query and return the hits
    
[e] the shared library is barely begun; but refactoring the search code has cleaned up some old crud

"""


def precomposedsqlsearch(so: SearchObject) -> List[dbWorkLine]:
    """

    flow control for searching governed by so.searchtype

    speed notes: the speed of these searches is consonant with that of the old search code; usu. <1s difference

    it is tempting to eliminate sqlphrasesearch() in order to keep the code base more streamlined: the savings are small
    for example:
        Sought »δοῦναι τοῦ καταϲκευάϲματοϲ«; Searched 236,835 texts and found 3 passages (6.26s)
    vs
        Sought »δοῦναι τοῦ καταϲκευάϲματοϲ«; Searched 236,835 texts and found 3 passages (9.01s)

    """

    assert so.searchtype in ['simple', 'simplelemma', 'proximity', 'phrase'], 'unknown searchtype sent to rawsqlsearches()'

    so.poll.statusis('Executing a {t} search...'.format(t=so.searchtype))

    so.searchsqldict = searchlistintosqldict(so, so.termone)
    if so.lemmaone:
        so.searchsqldict = rewritesqlsearchdictforlemmata(so)

    searchfnc = lambda x: list()

    if so.searchtype in ['simple', 'simplelemma']:
        searchfnc = basicprecomposedsqlsearcher
    elif so.searchtype == 'proximity':
        # search for the least common terms first: swap termone and termtwo if need be
        so = rebuildsearchobjectviasearchorder(so)
        if so.scope == 'lines':
            # this will hit rawdsqlsearchmanager() 2x
            searchfnc = precomposedsqlwithinxlinessearch
        else:
            searchfnc = precomposedsqlwithinxwords
    elif so.searchtype == 'phrase':
        so.phrase = so.termone
        so.leastcommon = findleastcommonterm(so.termone, so.accented)
        lccount = findleastcommontermcount(so.termone, so.accented)
        if 0 < lccount < 500:
            # debugmessage('searchfnc = sqlphrasesearch')
            searchfnc = precomposedsqlphrasesearch
        else:
            # debugmessage('searchfnc = sqlsubqueryphrasesearch')
            searchfnc = precomposedsqlsubqueryphrasesearch
    else:
        # should be hard to reach this because of "assert" above
        consolewarning('rawsqlsearches() does not support {t} searching'.format(t=so.searchtype), color='red')

    so.searchsqldict = searchlistintosqldict(so, so.termone)
    if so.lemmaone:
        so.searchsqldict = rewritesqlsearchdictforlemmata(so)

    hitlist = searchfnc(so)

    if so.onehit:
        # you might still have two hits from the same author; purge the doubles
        # use unique keys property of a dict() to do it
        uniqueauthors = {h.authorid: h for h in hitlist}
        hitlist = [uniqueauthors[a] for a in uniqueauthors]

    hitlist = hitlist[:so.cap]

    return hitlist


def basicprecomposedsqlsearcher(so: SearchObject) -> List[dbWorkLine]:
    """

    give me sql and I will search

    this is hollow at the moment because precomposedsqlsearchmanager() is a candidate for a rust library that will
    allow MP without triggering python's MP

    the same library would need to offer internally the same functionality as workonprecomposedsqlsearch()
    and precomposedsqlsearcher()

    """

    usesharedlibrary = hipparchia.config['GOLANGTHREADING']


    nosharedlibrary = True

    if nosharedlibrary:
        hits = precomposedsqlsearchmanager(so)
        return hits
    else:
        # potential flow:
        # [1] send the searchdict to redis as a list of json.dups(items) (keyed to the searchid)
        # [2a] invoke the external function by sending it the searchid
        # [2b] you will also need to send things like the cap value, psql login info, and redis login info
        # [3] wait for the function to (a) gather; (b) search; (c) store
        # [4] pull the results back from redis via the searchid
        # redis makes sense because the activity poll is going to have to be done via redis anyway...

        # the following modifications to the searchdict are required to feed the golang module
        # [a] the keys need to be renamed: temptable -> TempTable; query -> PsqlQuery; data -> PsqlData
        # [b] the tuple inside of 'data' needs to come out and up: ('x',) -> 'x'
        # [c] the '%s' in the 'query' needs to become '$1' for string substitution

        # the searched items are stored under the redis key 'searchid_results'
        # json.loads() will leave you with a dictionary of k/v pairs that can be turned into a dbWorkLine

        consolewarning('basicsqlsearcher() does not support shared library searching'.format(t=so.searchtype), color='red')
        return list()


def generatepreliminaryhitlist(so: SearchObject, recap=hipparchia.config['INTERMEDIATESEARCHCAP']) -> List[dbWorkLine]:
    """

    grab the hits for part one of a two part search

    """

    actualcap = so.cap
    so.cap = recap

    so.poll.statusis('Part one: Searching for "{x}"'.format(x=so.termone))
    if so.lemmaone:
        so.poll.statusis('Part one: Searching for all forms of "{x}"'.format(x=so.lemmaone.dictionaryentry))

    hitlines = basicprecomposedsqlsearcher(so)
    so.cap = actualcap

    return hitlines


def precomposedsqlwithinxlinessearch(so: SearchObject) -> List[dbWorkLine]:
    """

    after finding x, look for y within n lines of x

    people who send phrases to both halves and/or a lot of regex will not always get what they want

    note that this implementations is significantly slower than the standard withinxlines() + simplewithinxlines()

    """

    initialhitlines = generatepreliminaryhitlist(so)

    # we are going to need a new searchsqldict w/ a new temptable
    # sq = { table1: {query: q, data: d, temptable: t},
    #         table2: {query: q, data: d, temptable: t}, ...

    # this means refeeding searchlistintosqldict() and priming it for a 'temptable' search
    # the temptable follows the paradigm of wholeworktemptablecontents()
    # r {'type': 'temptable', 'where': {'tempquery': '\n\tCREATE TEMPORARY TABLE in0f08_includelist AS \n\t\tSELECT values \n\t\t\tAS includeindex FROM unnest(ARRAY[768,769,770,771,772,773,774,775,776,777,778,779,780,781,782,783,784,785,786,787,788,789,790,791,792,793,794,795,796,797,798,799,800,801,802,803,804,805,806,807,808,809,810,763,764,765,766,767]) values\n\t'}}

    so = perparesoforsecondsqldict(so, initialhitlines)

    so.searchsqldict = searchlistintosqldict(so, so.termtwo)
    if so.lemmatwo:
        so.lemmaone = so.lemmatwo
        so.searchsqldict = rewritesqlsearchdictforlemmata(so)

    so.poll.statusis('Part two: Searching among the initial hits for "{x}"'.format(x=so.termtwo))
    if so.lemmaone:
        so.poll.statusis('Part two: Searching among the initial hits for all forms of "{x}"'.format(x=so.lemmaone.dictionaryentry))

    so.poll.sethits(0)
    newhitlines = basicprecomposedsqlsearcher(so)

    # newhitlines will contain, e.g., in0001w0ig_493 and in0001w0ig_492, i.e., 2 lines that are part of the same 'hit'
    # so we need can't use newhitlines directly but have to check it against the initial hits
    # that's fine since "not near" would push us in this direction in any case

    initialhitlinedict = {hl.uniqueid: hl for hl in initialhitlines}
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


def precomposedsqlwithinxwords(so: SearchObject) -> List[dbWorkLine]:
    """

    after finding x, look for y within n words of x

    note that the second half of this is not yet MP and could/should be for speed

    """

    initialhitlines = generatepreliminaryhitlist(so)

    fullmatches = list()

    so.poll.statusis('Part two: Searching among the initial hits for "{x}"'.format(x=so.termtwo))
    if so.lemmatwo:
        so.poll.statusis('Part two: Searching among the initial hits for all forms of "{x}"'.format(x=so.lemmatwo.dictionaryentry))

    so.poll.sethits(0)
    commitcount = 0

    dbconnection = ConnectionObject()
    dbcursor = dbconnection.cursor()

    while initialhitlines and len(fullmatches) < so.cap:
        commitcount += 1
        if commitcount == hipparchia.config['MPCOMMITCOUNT']:
            dbconnection.commit()
            commitcount = 0
        hit = initialhitlines.pop()
        leadandlag = grableadingandlagging(hit, so, dbcursor)
        # print('leadandlag for {h}: {l}'.format(h=hit.uniqueid, l=leadandlag))
        lagging = leadandlag['lag']
        leading = leadandlag['lead']

        if so.near and (re.search(so.termtwo, leading) or re.search(so.termtwo, lagging)):
            fullmatches.append(hit)
            so.poll.addhits(1)
        elif not so.near and not re.search(so.termtwo, leading) and not re.search(so.termtwo, lagging):
            fullmatches.append(hit)
            so.poll.addhits(1)

    dbconnection.connectioncleanup()

    return fullmatches


def precomposedsqlphrasesearch(so: SearchObject) -> List[dbWorkLine]:
    """

    you are searching for a relatively rare word: we will keep things simple-ish

    note that the second half of this is not MP: but searches already only take 6s; so clean code probably wins here

    """

    so.termone = so.leastcommon
    searchphrase = so.phrase
    phraselen = len(searchphrase.split(' '))

    initialhitlines = generatepreliminaryhitlist(so)

    m = 'Part two: Searching among the {h} initial hits for the full phrase "{p}"'
    so.poll.statusis(m.format(h=so.poll.gethits(), p=so.originalseeking))
    so.poll.sethits(0)

    fullmatches = list()

    dbconnection = ConnectionObject()
    dbcursor = dbconnection.cursor()
    commitcount = 0
    while initialhitlines and len(fullmatches) <= so.cap:
        commitcount += 1
        if commitcount == hipparchia.config['MPCOMMITCOUNT']:
            dbconnection.commit()
            commitcount = 0

        hit = initialhitlines.pop()

        wordset = lookoutsideoftheline(hit.index, phraselen - 1, hit.authorid, so, dbcursor)

        if not so.accented:
            wordset = re.sub(r'[.?!;:,·’]', str(), wordset)
        else:
            # the difference is in the apostrophe: δ vs δ’
            wordset = re.sub(r'[.?!;:,·]', str(), wordset)

        if so.near and re.search(searchphrase, wordset):
            fullmatches.append(hit)
            so.poll.addhits(1)
        elif not so.near and re.search(searchphrase, wordset) is None:
            fullmatches.append(hit)
            so.poll.addhits(1)

    dbconnection.connectioncleanup()

    return fullmatches


def precomposedsqlsubqueryphrasesearch(so: SearchObject) -> List[dbWorkLine]:
    """

    use subquery syntax to grab multi-line windows of text for phrase searching

    line ends and line beginning issues can be overcome this way, but then you have plenty of
    bookkeeping to do to to get the proper results focussed on the right line

    these searches take linear time: same basic time for any given scope regardless of the query

    """

    # rebuild the searchsqldict but this time pass through rewritequerystringforsubqueryphrasesearching()
    so.searchsqldict = searchlistintosqldict(so, so.phrase, subqueryphrasesearch=True)

    # the windowed collection of lines; you will need to work to find the centers
    # windowing will increase the number of hits: 2+ lines per actual find
    initialhitlines = generatepreliminaryhitlist(so, recap=so.cap * 3)

    m = 'Part two: Searching among the {h} initial hits for the full phrase "{p}"'
    so.poll.statusis(m.format(h=so.poll.gethits(), p=so.originalseeking))
    so.poll.sethits(0)

    sp = re.sub(r'^\s', r'(^|\\s)', so.phrase)
    sp = re.sub(r'\s$', r'(\\s|$)', sp)

    combinations = QueryCombinator(so.phrase)
    # the last item is the full phrase and it will have already been searched:  ('one two three four five', '')
    combinations = combinations.combinations()
    combinations.pop()

    listoffinds = list()

    dbconnection = ConnectionObject()
    dbcursor = dbconnection.cursor()

    setofhits = set()

    # print('initialhitlines')
    # for i in initialhitlines:
    #     print(i.index, i.markedup)

    while initialhitlines:
        # windows of indices come back: e.g., three lines that look like they match when only one matches [3131, 3132, 3133]
        # figure out which line is really the line with the goods
        # it is not nearly so simple as picking the 2nd element in any run of 3: no always runs of 3 + matches in
        # subsequent lines means that you really should check your work carefully; this is not an especially costly
        # operation relative to the whole search and esp. relative to the speed gains of using a subquery search
        lineobject = initialhitlines.pop()
        if not so.onehit or lineobject.authorid not in setofhits:
            if re.search(sp, getattr(lineobject, so.usewordlist)):
                listoffinds.append(lineobject)
                so.poll.addhits(1)
                setofhits.add(lineobject.authorid)
            else:
                try:
                    nextline = initialhitlines[0]
                except IndexError:
                    nextline = makeablankline('gr0000w000', -1)

                if lineobject.wkuinversalid != nextline.wkuinversalid or lineobject.index != (nextline.index - 1):
                    # you grabbed the next line on the pile (e.g., index = 9999), not the actual next line (e.g., index = 101)
                    # usually you won't get a hit by grabbing the next db line, but sometimes you do...
                    query = 'SELECT {wtmpl} FROM {tb} WHERE index=%s'.format(wtmpl=worklinetemplate, tb=lineobject.authorid)
                    data = (lineobject.index + 1,)
                    # print('subqueryphrasesearch() "while locallineobjects..." loop q,d:\n\t', query, data)
                    dbcursor.execute(query, data)
                    try:
                        nextline = dblineintolineobject(dbcursor.fetchone())
                    except:
                        nextline = makeablankline('gr0000w000', -1)

                for c in combinations:
                    tail = c[0] + '$'
                    head = '^' + c[1]
                    # debugging
                    # print('re',getattr(lo,so.usewordlist),tail, head, getattr(next,so.usewordlist))

                    t = False
                    h = False
                    try:
                        t = re.search(tail, getattr(lineobject, so.usewordlist))
                    except re.error:
                        pass
                    try:
                        h = re.search(head, getattr(nextline, so.usewordlist))
                    except re.error:
                        pass

                    if t and h:
                        listoffinds.append(lineobject)
                        so.poll.addhits(1)
                        setofhits.add(lineobject.authorid)

    dbconnection.connectioncleanup()
    return listoffinds


"""

    THE IN-HOUSE SEARCH CODE

"""


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
                # print(authortable, len(lineobjects))
                numberoffinds = len(lineobjects)
                activepoll.addhits(numberoffinds)
        else:
            listofplacestosearch = None

        try:
            activepoll.remain(len(listofplacestosearch))
        except remaindererror:
            pass

    # print('workonrawsqlsearch() worker #{i} finished'.format(i=workerid))

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
