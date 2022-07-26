# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-22
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""
import multiprocessing
import pickle
import re
from typing import List, Generator
from multiprocessing.managers import ListProxy

import psycopg2

from server import hipparchia
from server.dbsupport.dblinefunctions import worklinetemplate, dblineintolineobject, makeablankline, grablistoflines
from server.dbsupport.miscdbfunctions import resultiterator
from server.dbsupport.redisdbfunctions import establishredisconnection
from server.dbsupport.tablefunctions import assignuniquename
from server.formatting.miscformatting import consolewarning
from server.formatting.wordformatting import wordlistintoregex
from server.hipparchiaobjects.helperobjects import QueryCombinator
from server._deprecated.searchfunctionobjects import returnsearchfncobject
from server.hipparchiaobjects.searchobjects import SearchObject
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.listsandsession.genericlistfunctions import flattenlistoflists
from server.searching.miscsearchfunctions import lookoutsideoftheline, buildbetweenwhereextension, dblooknear, \
    grableadingandlagging

"""

BASIC STRING SEARCH

"""


def substringsearch(seeking: str, authortable: str, searchobject: SearchObject, cursor, templimit=None) -> Generator:
    """

    actually one of the most basic search types: look for a string/substring

    the whereclause is built conditionally:

    sample 'unrestricted':
        SELECT * FROM gr0059 WHERE  ( stripped_line ~* %s )  LIMIT 200 ('βαλλ',)
        [i.e, SELECT * FROM gr0059 WHERE  ( stripped_line ~* 'βαλλ') LIMIT 200;]
    sample 'between':
        SELECT * FROM gr0032 WHERE (index BETWEEN 1846 AND 2856) AND (index NOT BETWEEN 1846 AND 2061) AND ( stripped_line ~* %s )  LIMIT 200 ('βαλλ',)
    sample 'temptable':
        [create the temptable]
        SELECT * FROM in1204 WHERE EXISTS (SELECT 1 FROM in1204_includelist incl WHERE incl.includeindex = in1204.index AND in1204.accented_line ~* %s)  LIMIT 200 ('τούτου',)

    :param seeking:
    :param authortable:
    :param searchobject:
    :param cursor:
    :param templimit:
    :return:
    """

    so = searchobject

    if templimit:
        lim = str(templimit)
    else:
        lim = str(so.cap)

    if so.onehit:
        mylimit = ' LIMIT 1'
    else:
        mylimit = ' LIMIT {lim}'.format(lim=lim)

    mysyntax = '~*'
    found = list()

    r = so.indexrestrictions[authortable]
    whereextensions = str()

    if r['type'] == 'temptable':
        # make the table
        q = r['where']['tempquery']
        avoidcollisions = assignuniquename()
        q = re.sub('_includelist', '_includelist_{a}'.format(a=avoidcollisions), q)
        cursor.execute(q)
        # now you can work with it
        wtempate = """
		EXISTS
			(SELECT 1 FROM {tbl}_includelist_{a} incl WHERE incl.includeindex = {tbl}.index
		"""
        whereextensions = wtempate.format(a=avoidcollisions, tbl=authortable)
        whr = 'WHERE {xtn} AND {au}.{col} {sy} %s)'.format(au=authortable, col=so.usecolumn, sy=mysyntax,
                                                           xtn=whereextensions)
    elif r['type'] == 'between':
        whereextensions = buildbetweenwhereextension(authortable, so)
        whr = 'WHERE {xtn} ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax, xtn=whereextensions)
    elif r['type'] == 'unrestricted':
        whr = 'WHERE {xtn} ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax, xtn=whereextensions)
    else:
        # should never see this
        consolewarning('error in substringsearch(): unknown whereclause type', r['type'])
        whr = 'WHERE ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax)

    qtemplate = 'SELECT {wtmpl} FROM {db} {whr} {lm}'
    q = qtemplate.format(wtmpl=worklinetemplate, db=authortable, whr=whr, lm=mylimit)
    d = (seeking,)

    # print('q/d\nq:\t{q}\nd:\t{d}\n'.format(q=q, d=d))

    try:
        cursor.execute(q, d)
        found = resultiterator(cursor)
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
        consolewarning('DatabaseError for {c} @ {p}'.format(c=cursor, p=multiprocessing.current_process().name),
                       color='red')
        consolewarning('\tq, d', q, d)

    return found


"""

PROXIMITY SEARCHING

"""


def withinxlines(workdbname: str, searchobject: SearchObject, dbconnection) -> List[tuple]:
    """

    after finding x, look for y within n lines of x

    people who send phrases to both halves and/or a lot of regex will not always get what they want

    :param workdbname:
    :param searchobject:
    :return:
    """

    so = searchobject
    dbcursor = dbconnection.cursor()
    dbconnection.setautocommit()

    # you will only get session['maxresults'] back from substringsearch() unless you raise the cap
    # "Roman" near "Aetol" will get 3786 hits in Livy, but only maxresults will come
    # back for checking: but the Aetolians are likely not among those 200 or so passages...
    templimit = 2000000

    if so.lemma:
        chunksize = hipparchia.config['LEMMACHUNKSIZE']
        terms = so.lemma.formlist
        chunked = [terms[i:i + chunksize] for i in range(0, len(terms), chunksize)]
        chunked = [wordlistintoregex(c) for c in chunked]
        hitlist = list()
        for c in chunked:
            hitlist += list(substringsearch(c, workdbname, so, dbcursor, templimit))
    else:
        hitlist = list(substringsearch(so.termone, workdbname, so, dbcursor, templimit))

    # fullmatches = lemmatizedwithinxlines(searchobject, hitlist, dbcursor)

    if so.lemmaone or so.lemmatwo:
        fullmatches = lemmatizedwithinxlines(searchobject, hitlist, dbcursor)
    else:
        fullmatches = simplewithinxlines(searchobject, hitlist, dbcursor)

    return fullmatches


def lemmatizedwithinxlines(searchobject: SearchObject, hitlist: List[tuple], dbcursor):
    """

    BROKEN ATM: 1.7.4 (probably most/all of 1.7.x)

    the alternate way of doing withinxlines

    this will ask regex to do the heavy lifting

    nasty edge case 'fire' near 'burn' in Homer:

    simplewithinxlines()
      Sought all 5 known forms of »πῦρ« within 1 lines of all 359 known forms of »καίω«
      Searched 3 texts and found 24 passages (621.25s)

    lemmatizedwithinxlines()
       Sought all 5 known forms of »πῦρ« within 1 lines of all 359 known forms of »καίω«
       Searched 3 texts and found 24 passages (2.82s)

    note that this function is often slightly slower than simplewithinxlines(), but it does seem to be able
    to avoid the catastrophe

    lemmatized vs non-lemmatized is probably the key difference when it comes to speed

    :param hitlist:
    :return:
    """

    so = searchobject

    columconverter = {'marked_up_line': 'markedup', 'accented_line': 'polytonic', 'stripped_line': 'stripped'}
    col = columconverter[so.usecolumn]

    prox = int(so.session['proximity'])

    # note that at the moment we arrive here with a one-work per worker policy
    # that is all of the hits will come from the same table
    # this means extra/useless sifting below, but perhaps it is safer to be wasteful now lest we break later

    fullmatches = set()  # set to avoid duplicate hits
    hitlinelist = list()
    linesintheauthors = dict()

    hitlinelist = [dblineintolineobject(h) for h in hitlist]
    for l in hitlinelist:
        wkid = l.universalid
        # prox = 2
        # l = 100
        # list(range(l-prox, l+prox+1))
        # [98, 99, 100, 101, 102]
        environs = set(range(l.index - prox, l.index + prox + 1))
        environs = ['{w}_ln_{x}'.format(w=wkid, x=e) for e in environs]
        try:
            linesintheauthors[wkid[0:6]]
        except KeyError:
            linesintheauthors[wkid[0:6]] = set()
        linesintheauthors[wkid[0:6]].update(environs)

    # now grab all of the lines you might need
    linecollection = set()
    for l in linesintheauthors:
        if linesintheauthors[l]:
            # example: {'lt0803': {952, 953, 951}}
            linecollection = grablistoflines(l, list(linesintheauthors[l]), dbcursor)
            linecollection = {'{w}_ln_{x}'.format(w=l.wkuinversalid, x=l.index): l for l in linecollection}

    # then associate all of the surrounding words with those lines
    wordbundles = dict()
    for l in hitlinelist:
        wkid = l.universalid
        environs = set(range(l.index - prox, l.index + prox + 1))
        mylines = list()
        for e in environs:
            try:
                mylines.append(linecollection['{w}_ln_{x}'.format(w=wkid, x=e)])
            except KeyError:
                # you went out of bounds and tried to grab something that is not really there
                # KeyError: 'lt1515w001_ln_1175'
                # line 1175 is actually the first line of lt1515w002...
                pass

        mywords = [getattr(l, col) for l in mylines]
        mywords = [w.split(' ') for w in mywords if mywords]
        mywords = flattenlistoflists(mywords)
        mywords = ' '.join(mywords)
        wordbundles[l] = mywords

    # then see if we have any hits...
    while True:
        for provisionalhitline in wordbundles:
            if len(fullmatches) > so.cap:
                break
            if so.near and re.search(so.termtwo, wordbundles[provisionalhitline]):
                fullmatches.add(provisionalhitline)
            elif not so.near and not re.search(so.termtwo, wordbundles[provisionalhitline]):
                fullmatches.add(provisionalhitline)
        break

    fullmatches = [m.decompose() for m in fullmatches]

    return fullmatches


def simplewithinxlines(searchobject: SearchObject, hitlist: List[tuple], dbcursor) -> List[tuple]:
    """

    the older and potentially very slow way of doing withinxlines

    this will ask postgres to do the heavy lifting

    nasty edge case 'fire' near 'burn' in Homer:
      Sought all 5 known forms of »πῦρ« within 1 lines of all 359 known forms of »καίω«
      Searched 3 texts and found 24 passages (621.25s)

    170 initial hits in Homer then take *aeons* to find the rest
    as each of the 170 itself takes several seconds to check

    :param hitlist:
    :return:
    """

    so = searchobject

    fullmatches = set()  # set to avoid duplicate hits

    while True:
        for hit in hitlist:
            if len(fullmatches) > so.cap:
                break
            hitasline = dbWorkLine(*hit)
            # NB: the returned 'fullmatches' should look like a dbline [i.e., a tuple] and not a lineobject
            hitindex = hitasline.index
            uid = hitasline.universalid
            isnear = dblooknear(hitindex, so.distance, so.termtwo, uid, so.usecolumn, dbcursor)
            if so.near and isnear:
                fullmatches.add(hit)
            elif not so.near and not isnear:
                fullmatches.add(hit)
        break

    fullmatches = list(fullmatches)

    return fullmatches


def withinxwords(workdbname: str, searchobject: SearchObject, dbconnection) -> List[dbWorkLine]:
    """

    int(session['proximity']), searchingfor, proximate, curs, wkid, whereclauseinfo

    after finding x, look for y within n words of x

    getting to y:
        find the search term x and slice it out of its line
        then build forwards and backwards within the requisite range
        then see if you get a match in the range

    if looking for 'paucitate' near 'imperator' you will find:
        'romani paucitate seruorum gloriatos itane tandem ne'
    this will become:
        'romani' + 'seruorum gloriatos itane tandem ne'

    :param workdbname:
    :param searchobject:
    :return:
    """

    so = searchobject
    dbcursor = dbconnection.cursor()
    dbconnection.setautocommit()

    # you will only get session['maxresults'] back from substringsearch() unless you raise the cap
    # "Roman" near "Aetol" will get 3786 hits in Livy, but only maxresults will come
    # back for checking: but the Aetolians are likley not among those passages...
    templimit = 9999

    if so.lemma:
        chunksize = hipparchia.config['LEMMACHUNKSIZE']
        terms = so.lemma.formlist
        chunked = [terms[i:i + chunksize] for i in range(0, len(terms), chunksize)]
        chunked = [wordlistintoregex(c) for c in chunked]

        hits = list()
        for c in chunked:
            hits += list(substringsearch(c, workdbname, so, dbcursor, templimit))
        so.usewordlist = 'polytonic'
    else:
        hits = list(substringsearch(so.termone, workdbname, so, dbcursor, templimit))

    fullmatches = list()

    for hit in hits:
        hitline = dblineintolineobject(hit)

        leadandlag = grableadingandlagging(hitline, so, dbcursor)
        lagging = leadandlag['lag']
        leading = leadandlag['lead']
        # print(hitline.universalid, so.termtwo, '\n\t[lag] ', lagging, '\n\t[lead]', leading)

        if so.near and (re.search(so.termtwo, leading) or re.search(so.termtwo, lagging)):
            fullmatches.append(hit)
        elif not so.near and not re.search(so.termtwo, leading) and not re.search(so.termtwo, lagging):
            fullmatches.append(hit)

    return fullmatches


"""

PHRASE SEARCHING

"""

def phrasesearch(wkid: str, searchobject: SearchObject, cursor) -> List[dbWorkLine]:
    """

    a whitespace might mean things are on a new line
    note how horrible something like και δη και is: you will search και first and then...
    subqueryphrasesearch() takes a more or less fixed amount of time; this function is
    faster if you call it with an uncommon word; if you call it with a common word, then
    you will likely search much more slowly than you would with subqueryphrasesearch()

    :param wkid:
    :param activepoll:
    :param searchobject:
    :param cursor:
    :return:
    """

    so = searchobject
    searchphrase = so.termone
    activepoll = so.poll

    # print('so.leastcommon', so.leastcommon)

    # need a high templimit because you can actually fool "leastcommon"
    # "πλῶϲ θανατώδη" will not find "ἁπλῶϲ θανατώδη": you really wanted the latter (presumably), but
    # "πλῶϲ" is going to be entered as leastcommon, and a search for it will find "ἁπλῶϲ" many, many times
    # as the latter is a common term...

    hits = substringsearch(so.leastcommon, wkid, so, cursor, templimit=999999)

    fullmatches = list()

    while True:
        # since hits is now a generator you can no longer pop til you drop
        for hit in hits:
            # print('hit', hit)
            if len(fullmatches) > so.cap:
                break
            phraselen = len(searchphrase.split(' '))
            # wordklinetemplate in dblinefunctions.py governs the order of things here...
            hitindex = hit[1]
            wordset = lookoutsideoftheline(hitindex, phraselen - 1, wkid, so, cursor)
            if not so.accented:
                wordset = re.sub(r'[.?!;:,·’]', str(), wordset)
            else:
                # the difference is in the apostrophe: δ vs δ’
                wordset = re.sub(r'[.?!;:,·]', str(), wordset)

            if so.near and re.search(searchphrase, wordset):
                fullmatches.append(hit)
                activepoll.addhits(1)
            elif not so.near and re.search(searchphrase, wordset) is None:
                fullmatches.append(hit)
                activepoll.addhits(1)
        break

    return fullmatches


def subqueryphrasesearch(workerid, foundlineobjects: ListProxy, searchphrase: str, listofplacestosearch: ListProxy,
                         searchobject: SearchObject, dbconnection) -> ListProxy:
    """

    foundlineobjects, searchingfor, searchlist, commitcount, whereclauseinfo, activepoll

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

    :return:
    """
    # print('subqueryphrasesearch()')
    so = searchobject
    activepoll = so.poll

    # build incomplete sfo that will handle everything other than iteratethroughsearchlist()
    sfo = returnsearchfncobject(workerid, foundlineobjects, listofplacestosearch, so, dbconnection, None)

    querytemplate = """
		SELECT secondpass.index, secondpass.{co} FROM 
			(SELECT firstpass.index, firstpass.linebundle, firstpass.{co} FROM
					(SELECT index, {co}, concat({co}, ' ', lead({co}) OVER (ORDER BY index ASC)) AS linebundle
						FROM {db} {whr} ) firstpass
			) secondpass
		WHERE secondpass.linebundle ~ %s {lim}"""

    wheretempate = """
	WHERE EXISTS
		(SELECT 1 FROM {tbl}_includelist_{a} incl WHERE incl.includeindex = {tbl}.index)
	"""

    # substringsearch() needs ability to CREATE TEMPORARY TABLE
    sfo.dbconnection.setreadonly(False)
    dbcursor = sfo.dbconnection.cursor()

    qcomb = QueryCombinator(searchphrase)
    # the last item is the full phrase:  ('one two three four five', '')
    combinations = qcomb.combinations()
    combinations.pop()
    # lines start/end
    sp = re.sub(r'^\s', r'(^|\\s)', searchphrase)
    sp = re.sub(r'\s$', r'(\\s|$)', sp)
    # on the reasoning behind the following substitution see 'DEBUGGING notes: SQL oddities' above
    # sp = re.sub(r' ', r'\\s', sp)

    if not so.onehit:
        lim = ' LIMIT ' + str(so.cap)
    else:
        # the windowing problem means that '1' might be something that gets discarded
        lim = ' LIMIT 5'

    if so.redissearchlist:
        listofplacestosearch = True

    while listofplacestosearch and activepoll.gethits() <= so.cap:
        # sfo.getnextfnc() also takes care of the commitcount
        authortable = sfo.getnextfnc()
        sfo.updatepollremaining()

        if authortable:
            whr = str()
            r = so.indexrestrictions[authortable]
            if r['type'] == 'between':
                indexwedwhere = buildbetweenwhereextension(authortable, so)
                if indexwedwhere != '':
                    # indexwedwhere will come back with an extraneous ' AND'
                    indexwedwhere = indexwedwhere[:-4]
                    whr = 'WHERE {iw}'.format(iw=indexwedwhere)
            elif r['type'] == 'temptable':
                avoidcollisions = assignuniquename()
                q = r['where']['tempquery']
                q = re.sub('_includelist', '_includelist_{a}'.format(a=avoidcollisions), q)
                dbcursor.execute(q)
                whr = wheretempate.format(tbl=authortable, a=avoidcollisions)

            query = querytemplate.format(db=authortable, co=so.usecolumn, whr=whr, lim=lim)
            data = (sp,)
            # print('subqueryphrasesearch() find indices() q,d:\n\t',query, data)
            dbcursor.execute(query, data)
            indices = [i[0] for i in dbcursor.fetchall()]
            # this will yield a bunch of windows: you need to find the centers; see 'while...' below

            locallineobjects = list()
            if indices:
                for i in indices:
                    query = 'SELECT {wtmpl} FROM {tb} WHERE index=%s'.format(wtmpl=worklinetemplate, tb=authortable)
                    data = (i,)
                    # print('subqueryphrasesearch() iterate through indices() q,d:\n\t', query, data)
                    dbcursor.execute(query, data)
                    locallineobjects.append(dblineintolineobject(dbcursor.fetchone()))

            locallineobjects.reverse()
            # debugging
            # for l in locallineobjects:
            #	print(l.universalid, l.locus(), getattr(l,so.usewordlist))

            gotmyonehit = False
            while locallineobjects and activepoll.gethits() <= so.cap and not gotmyonehit:
                # windows of indices come back: e.g., three lines that look like they match when only one matches [3131, 3132, 3133]
                # figure out which line is really the line with the goods
                # it is not nearly so simple as picking the 2nd element in any run of 3: no always runs of 3 + matches in
                # subsequent lines means that you really should check your work carefully; this is not an especially costly
                # operation relative to the whole search and esp. relative to the speed gains of using a subquery search
                lineobject = locallineobjects.pop()
                if re.search(sp, getattr(lineobject, so.usewordlist)):
                    sfo.addnewfindstolistoffinds([lineobject])
                    activepoll.addhits(1)
                    if so.onehit:
                        gotmyonehit = True
                else:
                    try:
                        nextline = locallineobjects[0]
                    except IndexError:
                        nextline = makeablankline('gr0000w000', -1)

                    if lineobject.wkuinversalid != nextline.wkuinversalid or lineobject.index != (nextline.index - 1):
                        # you grabbed the next line on the pile (e.g., index = 9999), not the actual next line (e.g., index = 101)
                        # usually you won't get a hit by grabbing the next db line, but sometimes you do...
                        query = 'SELECT {wtmpl} FROM {tb} WHERE index=%s'.format(wtmpl=worklinetemplate, tb=authortable)
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
                            sfo.addnewfindstolistoffinds([lineobject])
                            activepoll.addhits(1)
                            if so.onehit:
                                gotmyonehit = True
        else:
            # redis will return None for authortable if the set is now empty
            listofplacestosearch = None

    sfo.listcleanup()

    if sfo.needconnectioncleanup:
        sfo.dbconnection.connectioncleanup()

    return foundlineobjects


"""

PHRASE SEARCHING NOTES

notes on lead and lag: examining the next row and the previous row

lead and lag example
	https://fle.github.io/detect-value-changes-between-successive-lines-with-postgresql.html

partitions: [over clauses]
	http://tapoueh.org/blog/2013/08/20-Window-Functions


[a] a span is generated by the subquery clause SQ
select SQ.index, SQ.stripped_line, SQ.nextline
from
	(
	select index, stripped_line,
	lead(stripped_line) over (ORDER BY index asc) as nextline
	from lt1212
	where (index > 9000 and index < 9010)
	) SQ

[b] searching within it
select SQ.index, SQ.stripped_line, SQ.nextline
from
	(
	select index, stripped_line,
	lead(stripped_line) over (ORDER BY index asc) as nextline
	from lt1212
	where (index > 9000 and index < 9010)
	) SQ
where SQ.stripped_line ~ 'quidam' and SQ.nextline ~ 'ae '

[c] returning a linebundle before and after a hit:

select SQ.index, concat(SQ.prevline, SQ.stripped_line, SQ.nextline) as linebundle
from
	(
	select index, stripped_line,
	lead(stripped_line) over (ORDER BY index asc) as nextline,
    lag(stripped_line) over (ORDER BY index asc) as prevline
	from lt1212
	where (index > 0)
	) SQ
where SQ.stripped_line ~ 'et tamen'

[d] peeking at the windows: ﻿
	119174 is where you will find:
		index: 119174
		linebundle: ἆρά γ ἄξιον τῇ χάριτι ταύτῃ παραβαλεῖν τὰϲ τρίτον ἔφη τῷ φίλῳ μου τούτῳ χαριζόμενοϲ πόλεωϲ καὶ διὰ τὸν οἰκιϲτὴν ἀλέξανδρον καὶ
		accented_line: τρίτον ἔφη τῷ φίλῳ μου τούτῳ χαριζόμενοϲ

				SELECT firstpass.index, firstpass.linebundle, firstpass.accented_line FROM
					(SELECT index, accented_line,
						concat(lag(accented_line) OVER (ORDER BY index ASC), ' ', accented_line, ' ', lead(accented_line) OVER (ORDER BY index ASC)) as linebundle
						FROM gr0007 WHERE ( wkuniversalid ~ 'gr0007' ) ) firstpass
				where firstpass.index < 119176 and firstpass.index > 119172


[e] putting it all together and dispensing with lag:

SELECT secondpass.index, secondpass.accented_line
				FROM (SELECT firstpass.index, firstpass.linebundle, firstpass.accented_line FROM
					(SELECT index, accented_line,
						concat(accented_line, ' ', lead(accented_line) OVER (ORDER BY index ASC)) as linebundle
						FROM gr0007 WHERE ( wkuniversalid ~ 'gr0007' ) ) firstpass
					) secondpass
				WHERE secondpass.linebundle ~ 'τῷ φίλῳ μου' LIMIT 3000


"""

"""

ADDITONAL SEARCH NOTES

"""


# DEAD CODE KEPT AROUND SO THAT A BAD WHEEL IS NOT REINVENTED
#
# if so.searchtype == 'zz_never_meet_condition_simplelemma':
# 	# lemmatized searching gets very slow if the number of forms is large
# 	# faster to use arrays? nope...: see below
# 	# mix and match? [array of items that look like ['a|b|c', 'd|e|f', ...] nope...
#
# 	# Sample SQL:
# 	# CREATE TEMPORARY TABLE lemmatizedforms AS SELECT term FROM unnest(ARRAY['hospitium', 'hospitio']) term;
# 	# SELECT index, stripped_line FROM lt1212 WHERE stripped_line ~* ANY (SELECT term FROM lemmatizedforms);
#
# 	"""
# 	ARRAYS + TEMP TABLE VERSION
#
# 	Sought all 12 known forms of »hospitium«
# 	Searched 7,461 texts and found 250 passages (31.64s)
# 	Sorted by name
# 	[Search suspended: result cap reached.]
#
# 	"""
#
# 	"""
# 	MIXANDMATCH: ARRAYS of REREGEX
#
# 	Sought all 12 known forms of »hospitium«
# 	Searched 7,461 texts and found 250 passages (15.73s)
# 	Sorted by name
# 	[Search suspended: result cap reached.]
#
# 	"""
#
# 	"""
# 	GIANTREGEX VERSION
#
# 	Sought all 12 known forms of »hospitium«
# 	Searched 7,461 texts and found 250 passages (1.72s)
# 	Sorted by name
# 	[Search suspended: result cap reached.]
# 	"""
#
# 	forms = so.lemma.formlist
# 	# MIXANDMATCH if the next three lines are enabled
# 	n = 3
# 	forms = [forms[i:i + n] for i in range(0, len(forms), n)]
# 	forms = [wordlistintoregex(f) for f in forms]
#
# 	qtemplate = """
# 	DROP TABLE IF EXISTS lemmatizedforms_{wd};
# 	CREATE TEMPORARY TABLE IF NOT EXISTS lemmatizedforms_{wd} AS
# 		SELECT term FROM unnest(%s) term
# 	"""
# 	q = qtemplate.format(wd=so.lemma.dictionaryentry)
# 	d = (forms,)
# 	cursor.execute(q, d)
#
# 	# now modify the '%s' that we have from above
# 	whr = re.sub(r'%s', 'ANY (SELECT term FROM lemmatizedforms_{wd})'.format(wd=so.lemma.dictionaryentry), whr)


"""

	ANOTHER DEAD END...

	you can use psql's to_tsvector() and to_tsquery() functions

	what you do via substringsearch()

	q:	SELECT * FROM lt1020 WHERE ( (index BETWEEN 9768 AND 13860) ) AND ( stripped_line ~* %s )  LIMIT 200
	d:	('(^|\\s)precatae(\\s|$)|(^|\\s)precor(\\s|$)|(^|\\s)precamini(\\s|$)|(^|\\s)precand[uv]m(\\s|$)|(^|\\s)precer(\\s|$)|(^|\\s)precat[uv]s(\\s|$)|(^|\\s)precor[uv]e(\\s|$)|(^|\\s)precam[uv]rq[uv]e(\\s|$)|(^|\\s)precabor(\\s|$)|(^|\\s)precanda(\\s|$)',)

	sample 'tsvector' search:
		SELECT * FROM lt1020 WHERE to_tsvector(accented_line) @@ to_tsquery('precor | ...');

	results:

		substringsearch()
			Sought all 64 known forms of »preco«
			Searched 836 texts and found 1,385 passages (3.98s)
			Sorted by name

		tsvectorsearch()
			Sought all 64 known forms of »preco«
			Searched 836 texts and found 1,629 passages (58.39s)
			Sorted by name

	to_tsvector() is way slower: presumably substringsearch() has access to the line indices while to_tsvector()
	is effectively reindexing everything

	AND there is also a mismatch in the results...

	the difference between the two sets of results:

		{'line/lt1017w012/19950', 'line/lt0959w007/22909',
			'line/lt0959w002/2874', 'line/lt1512w001/3715',
			'line/lt0975w001/1614', 'line/lt1017w016/44879',
			'line/lt1020w001/1939', 'line/lt0893w001/2382',
			'line/lt0959w006/13769', 'line/lt0959w007/26242',
			'line/lt0893w005/6467', 'line/lt0959w008/27102',
			'line/lt1254w001/7396', 'line/lt1017w008/8356',
			'line/lt1017w001/1020', 'line/lt0893w001/66',
			'line/lt1035w001/4642', 'line/lt1017w003/3010',
			'line/lt0959w006/10283', 'line/lt0975w001/918',
			'line/lt1017w009/10632', 'line/lt0959w007/23294',
			'line/lt0959w002/2651', 'line/lt0474w057/133448',
			'line/lt1017w001/575', 'line/lt1345w001/2081',
			'line/lt0893w003/3828', 'line/lt0890w001/45',
			'line/lt0550w001/5916', 'line/lt0959w006/14092',
			'line/lt1020w002/12520', 'line/lt1345w001/4984',
			'line/lt0660w002/1331', 'line/lt1017w004/4069',
			'line/lt1017w002/2055', 'line/lt0472w001/2079',
			'line/lt1017w009/9248', 'line/lt0893w001/2786',
			'line/lt0474w036/51672', 'line/lt2028w001/31',
			'line/lt0893w001/559', 'line/lt0959w006/21359',
			'line/lt1512w006/11520', 'line/lt0893w001/818',
			'line/lt2349w005/13128', 'line/lt0620w001/3045',
			'line/lt0890w001/84', 'line/lt0893w006/7923',
			'line/lt0893w004/5690', 'line/lt2349w005/11351',
			'line/lt0690w003/5038', 'line/lt1017w008/7966',
			'line/lt2349w005/13129', 'line/lt0893w005/7484',
			'line/lt0972w001/4066', 'line/lt0893w005/7175',
			'line/lt0959w002/3429', 'line/lt1017w003/2858',
			'line/lt0893w005/6609', 'line/lt0893w005/6625',
			'line/lt1351w005/17121', 'line/lt0400w003/810',
			'line/lt2349w005/29263', 'line/lt0660w002/1444',
			'line/lt0959w004/7028', 'line/lt2349w005/12243',
			'line/lt0959w006/15468', 'line/lt0969w001/155',
			'line/lt1017w003/2985', 'line/lt1017w007/7342',
			'line/lt1017w007/6802', 'line/lt0959w006/16035',
			'line/lt0690w003/10534', 'line/lt1017w006/6551'}

		'prece' seems to be the issue

		NOTE that it is NOT on the formlist

		terms ['precatae', 'precor', 'precamini', 'precandum', 'precer',
			'precatus', 'precorue', 'precamurque', 'precabor', 'precanda',
			'precando', 'precantia', 'precareris', 'precaturque',
			'precesque', 'precetur', 'precabaturque', 'precaretur',
			'precatu', 'precare', 'precata', 'precatusque', 'precentur',
			'precantibusque', 'precanti', 'precarentur', 'precem', 'preces',
			'precaturi', 'precaturus', 'precabuntur', 'precandi',
			'precantem', 'precabatur', 'precorque', 'precantemque',
			'precabantur', 'precabar', 'precemur', 'precaremur', 'precatam',
			'precandam', 'precans', 'precantes', 'precarer', 'precantur',
			'precabare', 'precarere', 'precaris', 'precatur', 'precatum',
			'precamur', 'precarique', 'precantique', 'precantium',
			'precabamur', 'precatique', 'precari', 'precante',
			'precabanturque', 'precantis', 'preceris', 'precantibus',
			'precati']

	it does not seem like it is worth the trouble to figure out how 'prece' gets found by a first draft that 
	was 20x slower than the current implementation

"""


def loadredisresults(searchid):
	"""

	search results were passed to redis

	grab and return them

	:param searchid:
	:return:
	"""

	redisfindsid = '{id}_findslist'.format(id=searchid)
	rc = establishredisconnection()
	finds = rc.lrange(redisfindsid, 0, -1)
	# foundlineobjects = [dblineintolineobject(pickle.loads(f)) for f in finds]
	foundlineobjects = [pickle.loads(f) for f in finds]
	return foundlineobjects