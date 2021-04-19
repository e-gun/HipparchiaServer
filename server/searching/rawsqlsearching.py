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
from server.dbsupport.dblinefunctions import dblineintolineobject
from server.dbsupport.miscdbfunctions import resultiterator
from server.dbsupport.tablefunctions import assignuniquename
from server.formatting.miscformatting import consolewarning
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.searchobjects import SearchObject
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.listsandsession.searchlistintosql import searchlistintosqldict, rewritesqlsearchdictforlemmata, \
    perparesoforsecondsqldict
from server.searching.searchfunctions import rebuildsearchobjectviasearchorder, grableadingandlagging, \
    findleastcommonterm, findleastcommontermcount, lookoutsideoftheline
from server.threading.mpthreadcount import setthreadcount


def rawsqlsearches(so: SearchObject) -> List[dbWorkLine]:
    """

    flow control for searching governed by so.searchtype

    speed notes: [NB: linux is *way* faster than a virtualized big sur; vfio issues, I guess]
        simple: Sought »μετείληφεν« Searched 7,461 texts and found 132 passages (5.79s) [consonant w/ old]
        lemmatized: Sought all 28 known forms of »μακρόβιοϲ« Searched 7,461 texts and found 200 passages (29.56s) [faster?]
        withinxlines: Sought »μεγιστοσ« within 3 lines of »θαυμαστ« Searched 7,461 texts and found 20 passages (6.51s)  [consonant]
        winthinxwords: Sought »μακρόβιον« within 8 words of »γλῶτταν« Searched 7,461 texts and found 2 passages (6.87s) [consonant]
        sqlphrasesearch: Sought »ἡ φύϲιϲ μετείληφεν« Searched 7,461 texts and found 1 passage (6.63s) [consonant w/ old]

    consonant means <1s slower

    """

    assert so.searchtype in ['simple', 'simplelemma', 'proximity', 'phrase'], 'unknown searchtype sent to rawsqlsearches()'

    so.poll.statusis('Executing a {t} search...'.format(t=so.searchtype))

    so.searchsqldict = searchlistintosqldict(so, so.termone)
    if so.lemmaone:
        so.searchsqldict = rewritesqlsearchdictforlemmata(so)

    searchfnc = lambda x: list()

    if so.searchtype in ['simple', 'simplelemma']:
        searchfnc = rawsqlsearchmanager
    elif so.searchtype == 'proximity':
        # search for the least common terms first: swap termone and termtwo if need be
        so = rebuildsearchobjectviasearchorder(so)
        if so.scope == 'lines':
            # this will hit rawdsqlsearchmanager() 2x
            searchfnc = sqlwithinxlinessearch
        else:
            searchfnc = sqlwithinxwords
    elif so.searchtype == 'phrase':
        so.phrase = so.termone
        so.leastcommon = findleastcommonterm(so.termone, so.accented)
        lccount = findleastcommontermcount(so.termone, so.accented)
        if 0 < lccount < 500:
            # standard phrase search
            searchfnc = sqlphrasesearch
        else:
            # subqueryphrasesearch
            consolewarning('rawsqlsearches() cannot do a sql subqueryphrasesearch()', color='red')
            pass
    else:
        # should be hard to reach this because of "assert" above
        consolewarning('rawsqlsearches() does not support {t} searching'.format(t=so.searchtype), color='red')

    so.searchsqldict = searchlistintosqldict(so, so.termone)
    if so.lemmaone:
        so.searchsqldict = rewritesqlsearchdictforlemmata(so)

    hitlist = searchfnc(so)

    return hitlist


def rawsqlsearchmanager(so: SearchObject) -> List[dbWorkLine]:
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
            activepoll.remain(len(listofplacestosearch))
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


def generatepreliminaryhitlist(so: SearchObject) -> List[dbWorkLine]:
    """

    grab the hits for part one of a two part search

    """

    actualcap = so.cap
    so.cap = hipparchia.config['INTERMEDIATESEARCHCAP']

    so.poll.statusis('Part one: Searching for "{x}"'.format(x=so.termone))
    if so.lemmaone:
        so.poll.statusis('Part one: Searching for all forms of "{x}"'.format(x=so.lemmaone.dictionaryentry))

    hitlines = rawsqlsearchmanager(so)
    so.cap = actualcap

    return hitlines


def sqlwithinxlinessearch(so: SearchObject) -> List[dbWorkLine]:
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
    newhitlines = rawsqlsearchmanager(so)

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


def sqlwithinxwords(so: SearchObject) -> List[dbWorkLine]:
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


def sqlphrasesearch(so: SearchObject) -> List[dbWorkLine]:
    """

    you are searching for a relatively rare word: we will keep things simple-ish

    note that the second half of this is not yet MP and could/should be for speed

    """

    so.termone = so.leastcommon
    searchphrase = so.phrase
    phraselen = len(searchphrase.split(' '))

    initialhitlines = generatepreliminaryhitlist(so)

    so.poll.statusis('Part two: Searching among the initial hits for the full phrase "{p}"'.format(p=so.originalseeking))
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


def sqlsubqueryphrasesearch(so: SearchObject) -> List[dbWorkLine]:
    """

    use subquery syntax to grab multi-line windows of text for phrase searching

    line ends and line beginning issues can be overcome this way, but then you have plenty of
    bookkeeping to do to to get the proper results focussed on the right line

    tablestosearch:
        ['lt0400', 'lt0022', ...]

    a search inside of Ar., Eth. Eud.:

    SELECT secondpass.index, secondpass.accented_line
        FROM (SELECT firstpass.index, firstpass.linebundle, firstpass.accented_line FROM
            (SELECT index, accented_line,
                concat(accented_line, ' ', lead(accented_line) OVER (ORDER BY index ASC)) as linebundle
                FROM gr0086 WHERE ( (index BETWEEN 15982 AND 18745) ) ) firstpass
            ) secondpass
        WHERE secondpass.linebundle ~ %s  LIMIT 200

    a search in x., hell and x., mem less book 3 of hell and book 2 of mem:

    SELECT secondpass.index, secondpass.accented_line
        FROM (SELECT firstpass.index, firstpass.linebundle, firstpass.accented_line FROM
            (SELECT index, accented_line,
                concat(accented_line, ' ', lead(accented_line) OVER (ORDER BY index ASC)) as linebundle
                FROM gr0032 WHERE ( (index BETWEEN 1 AND 7918) OR (index BETWEEN 7919 AND 11999) ) AND ( (index NOT BETWEEN 1846 AND 2856) AND (index NOT BETWEEN 8845 AND 9864) ) ) firstpass
            ) secondpass
    WHERE secondpass.linebundle ~ %s  LIMIT 200

    """

    return list()