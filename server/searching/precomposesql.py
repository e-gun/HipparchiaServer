# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List

from server import hipparchia
from server.dbsupport.dblinefunctions import worklinetemplate, worklinetemplatelist
from server.formatting.miscformatting import consolewarning
from server.formatting.wordformatting import wordlistintoregex
from server.hipparchiaobjects.searchobjects import SearchObject
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.listsandsession.whereclauses import wholeworktemptablecontents
from server.searching.searchhelperfunctions import buildbetweenwhereextension


def searchlistintosqldict(searchobject: SearchObject, seeking: str, subqueryphrasesearch=False) -> dict:
    """

    take a searchobject
    grab its searchlist and its exceptionlist and convert them into a collection of sql queries

    the old strategy would generate the queries as needed and on the fly: this version is slower can costs more memory
    by definition; it generates all possible queries and it holds them in memory; nevertheless the speed cost should be
    negligible relative to the total cost of a search; the memory cost can only get interesting if you have lots of
    users; but here too the overload problem should come from too much postgres and not too much prep

    in any case these lists of queries can be handed off to a simple MP-aware helper binary that can dodge MP
    forking in python; this binary can be in rust or go or ...

    { table1: {query: q, data: d, temptable: t},
    table2: {query: q, data: d, temptable: t},
    ... }

    note that a temptable is seldom used
    but something like searching inside a date range in an inscriptional corpus will trigger the need for one

    example: δηλοῖ in Aristotle + 3 works of Plato
    {
    'gr0086': {
        'temptable': '',
        'query': 'SELECT wkuniversalid, index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words, annotations FROM gr0086 WHERE  ( accented_line ~* %s )  LIMIT 200',
        'data': ('δηλοῖ',)
    },
    'gr0059': {
        'temptable': '',
        'query': 'SELECT wkuniversalid, index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words, annotations FROM gr0059 WHERE ( (index BETWEEN 40842 AND 52799) OR (index BETWEEN 2172 AND 4884) OR (index BETWEEN 1 AND 677) ) AND ( accented_line ~* %s )  LIMIT 200',
        'data': ('δηλοῖ',)
    }
    }

    """

    returndict = dict()

    so = searchobject
    searchlist = so.indexrestrictions.keys()

    # templimits are used by proximity searching but so.cap should have been temporarily swapped out
    lim = str(so.cap)

    if so.onehit:
        mylimit = ' LIMIT 1'
    else:
        mylimit = ' LIMIT {lim}'.format(lim=lim)

    mysyntax = '~*'

    # print(so.indexrestrictions)

    for authortable in searchlist:
        r = so.indexrestrictions[authortable]
        whereextensions = str()
        returndict[authortable] = dict()
        returndict[authortable]['temptable'] = str()

        if r['type'] == 'between':
            whereextensions = buildbetweenwhereextension(authortable, so)
            if not subqueryphrasesearch:
                whr = 'WHERE {xtn} ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax, xtn=whereextensions)
            else:
                # whereextensions will come back with an extraneous ' AND'
                whereextensions = whereextensions[:-4]
                whr = 'WHERE {xtn}'.format(xtn=whereextensions)
        elif r['type'] == 'unrestricted':
            if not subqueryphrasesearch:
                whr = 'WHERE {xtn} ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax, xtn=whereextensions)
            else:
                whr = str()
        elif r['type'] == 'temptable':
            # how to construct the table...
            # note that the temp table name can't be assigned yet because you can get collisions via lemmatization
            # since that will give you more than one query per author table: gr1001_0, gr1001_1, ...
            q = r['where']['tempquery']
            q = re.sub('_includelist', '_includelist_UNIQUENAME', q)
            returndict[authortable]['temptable'] = q

            # how to SELECT inside the table...
            wtempate = """
            EXISTS
                (SELECT 1 FROM {tbl}_includelist_UNIQUENAME incl WHERE incl.includeindex = {tbl}.index
            """
            whereextensions = wtempate.format(tbl=authortable)
            whr = 'WHERE {xtn} AND {au}.{col} {sy} %s)'.format(au=authortable, col=so.usecolumn, sy=mysyntax,
                                                               xtn=whereextensions)
        else:
            # should never see this
            consolewarning('error in substringsearch(): unknown whereclause type', r['type'])
            whr = 'WHERE ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax)

        if not subqueryphrasesearch:
            qtemplate = 'SELECT {wtmpl} FROM {db} {whr} {lm}'
            q = qtemplate.format(wtmpl=worklinetemplate, db=authortable, whr=whr, lm=mylimit)
        else:
            q = rewritequerystringforsubqueryphrasesearching(authortable, whr, so)
        d = (seeking,)
        returndict[authortable]['query'] = q
        returndict[authortable]['data'] = d

    return returndict


def rewritesqlsearchdictforlemmata(so: SearchObject) -> dict:
    """

    you have
    { table1: {query: q, data: d, temptable: t},
    table2: {query: q, data: d, temptable: t},
    ... }

    but the 'data' needs to be swapped out

    { ...,
    'gr0059_20': {
        'data': '(^|\\s)δηλώϲητε(\\s|$)|(^|\\s)δηλώϲωϲι(\\s|$)|(^|\\s)δεδηλωμένην(\\s|$)|(^|\\s)δηλωθε[ίὶ]ϲ(\\s|$)|(^|\\s)δεδήλωκεν(\\s|$)|(^|\\s)δηλώϲαντα(\\s|$)|(^|\\s)δηλώϲῃϲ(\\s|$)|(^|\\s)δηλώϲουϲαν(\\s|$)|(^|\\s)δηλωϲάϲηϲ(\\s|$)|(^|\\s)δηλοῖμεν(\\s|$)',
        'query': 'SELECT wkuniversalid, index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words, annotations FROM gr0059 WHERE ( (index BETWEEN 2172 AND 4884) OR (index BETWEEN 40842 AND 52799) OR (index BETWEEN 1 AND 677) ) AND ( accented_line ~* %s )  LIMIT 200',
        'temptable': ''
    },
    'gr0059_21': {
        'data': '(^|\\s)ἐδηλώϲαντο(\\s|$)|(^|\\s)δεδηλωμένοϲ(\\s|$)|(^|\\s)δήλουϲ(\\s|$)|(^|\\s)δηλούϲαϲ(\\s|$)|(^|\\s)δηλώϲειεν(\\s|$)|(^|\\s)δηλωθ[έὲ]ν(\\s|$)|(^|\\s)δηλώϲειϲ(\\s|$)|(^|\\s)δηλουμένων(\\s|$)|(^|\\s)δηλώϲαϲαν(\\s|$)|(^|\\s)δηλώϲετε(\\s|$)',
        'query': 'SELECT wkuniversalid, index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words, annotations FROM gr0059 WHERE ( (index BETWEEN 2172 AND 4884) OR (index BETWEEN 40842 AND 52799) OR (index BETWEEN 1 AND 677) ) AND ( accented_line ~* %s )  LIMIT 200',
        'temptable': ''
    }
    }

    """

    searchdict = so.searchsqldict

    terms = so.lemmaone.formlist

    chunksize = hipparchia.config['LEMMACHUNKSIZE']
    newtablenames = '{t}_{c}'

    chunked = [terms[i:i + chunksize] for i in range(0, len(terms), chunksize)]
    chunked = [wordlistintoregex(c) for c in chunked]
    modifieddict = dict()
    for authortable in searchdict:
        count = -1
        for c in chunked:
            count += 1
            modifieddict[newtablenames.format(t=authortable, c=count)] = dict()
            target = modifieddict[newtablenames.format(t=authortable, c=count)]
            target['data'] = c
            target['query'] = searchdict[authortable]['query']
            target['temptable'] = searchdict[authortable]['temptable']

    return modifieddict


def perparesoforsecondsqldict(so: SearchObject, initialhitlines: List[dbWorkLine], usebetweensyntax=True) -> SearchObject:
    """

    after finding initialhitlines sqlwithinxlinessearch() will run a second query

    it needs a new sqldict

    """

    so.indexrestrictions = dict()
    authorsandlines = dict()

    if not usebetweensyntax:
        # consolewarning('sqlwithinxlinessearch(): temptable')
        # time trials...
        # Sought all 13 known forms of »ὕβριϲ« within 4 lines of all 230 known forms of »φεύγω«
        # Searched 7,873 texts and found 9 passages (11.87s)
        # Searched between 400 B.C.E. and 350 B.C.E.

        # Sought all 230 known forms of »φεύγω« within 4 lines of all 16 known forms of »κρίϲιϲ«
        # Searched 7,873 texts and found 12 passages (14.64s)
        # Searched between 400 B.C.E. and 350 B.C.E.

        for hl in initialhitlines:
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
    else:
        # Sought all 13 known forms of »ὕβριϲ« within 4 lines of all 230 known forms of »φεύγω«
        # Searched 7,873 texts and found 9 passages (9.35s)
        # Searched between 400 B.C.E. and 350 B.C.E.

        # Sought all 230 known forms of »φεύγω« within 4 lines of all 16 known forms of »κρίϲιϲ«
        # Searched 7,873 texts and found 12 passages (11.35s)
        # Searched between 400 B.C.E. and 350 B.C.E.

        # consolewarning('sqlwithinxlinessearch(): between')
        for hl in initialhitlines:
            boundiaries = (hl.index - so.distance, hl.index + so.distance)
            try:
                authorsandlines[hl.authorid].append(boundiaries)
            except KeyError:
                authorsandlines[hl.authorid] = [boundiaries]
        for a in authorsandlines:
            so.searchlist = list(authorsandlines.keys())
            so.indexrestrictions[a] = dict()
            so.indexrestrictions[a]['where'] = dict()
            so.indexrestrictions[a]['type'] = 'between'
            so.indexrestrictions[a]['where']['listofboundaries'] = authorsandlines[a]
            so.indexrestrictions[a]['where']['listofomissions'] = list()

    return so


def rewritequerystringforsubqueryphrasesearching(authortable: str, whereclause: str, so: SearchObject) -> str:
    """

        you have
    { table1: {query: q, data: d, temptable: t},
    table2: {query: q, data: d, temptable: t},
    ... }

    but the 'queries' needs to be swapped out

    notes on lead and lag: examining the next row and the previous row

    lead and lag example
        https://fle.github.io/detect-value-changes-between-successive-lines-with-postgresql.html

    partitions: [over clauses]
        http://tapoueh.org/blog/2013/08/20-Window-Functions

    hipparchiaDB=# SELECT secondpass.index, secondpass.accented_line FROM
                            (SELECT firstpass.index, firstpass.linebundle, firstpass.accented_line FROM
                                            (SELECT index, accented_line, concat(accented_line, ' ', lead(accented_line) OVER (ORDER BY index ASC)) AS linebundle
                                                    FROM gr0014 WHERE ( (index BETWEEN 4897 AND 7556) OR (index BETWEEN 7557 AND 10317) ) ) firstpass
                            ) secondpass
                    WHERE secondpass.linebundle ~ 'λαβόντα παρ ὑμῶν';
     index |                       accented_line
    -------+------------------------------------------------------------
      7485 | τὴν πρὸϲ τοὺϲ τετελευτηκόταϲ εὔνοιαν ὑπάρχουϲαν προλαβόντα
      9795 | χρηϲτὸν εἶναι δεῖ τὸν τὰ τηλικαῦτα διοικεῖν ἀξιοῦντα οὐδὲ
      9796 | τὸ πιϲτευθῆναι προλαβόντα παρ ὑμῶν εἰϲ τὸ μείζω δύναϲθαι

    BUT, workonrawsqlsearch() is going to call dblineintolineobject() on the results, so you want something that will fit that...

    SELECT second.wkuniversalid, second.index, second.level_05_value, second.level_04_value, second.level_03_value, second.level_02_value, second.level_01_value, second.level_00_value, second.marked_up_line, second.accented_line, second.stripped_line, second.hyphenated_words, second.annotations FROM
        (SELECT * FROM
            (SELECT wkuniversalid, index, level_05_value, level_04_value, level_03_value, level_02_value, level_01_value, level_00_value, marked_up_line, accented_line, stripped_line, hyphenated_words, annotations, concat(accented_line, ' ', lead(accented_line) OVER (ORDER BY index ASC)) AS linebundle
                FROM gr0014  ) first
        ) second
    WHERE second.linebundle ~ 'λαβόντα παρ ὑμῶν' LIMIT 200;

    """

    sp = ['second.{x}'.format(x=x) for x in worklinetemplatelist]
    sp = ', '.join(sp)
    wl = ', '.join(worklinetemplatelist)

    if not so.onehit:
        lim = ' LIMIT {c}'.format(c=so.cap)
    else:
        # the windowing problem means that '1' might be something that gets discarded
        lim = ' LIMIT 5'

    qtemplate = """
    SELECT {sp} FROM
        ( SELECT * FROM
            ( SELECT {wl}, concat({co}, ' ', lead({co}) OVER (ORDER BY index ASC) ) AS linebundle
                FROM {db} {whr} ) first
        ) second
    WHERE second.linebundle ~ %s {lim}"""

    query = qtemplate.format(sp=sp, wl=wl, co=so.usecolumn, db=authortable, whr=whereclause, lim=lim)

    return query


def rewritesqlsearchdictforgolang(so: SearchObject) -> dict:
    """

    you presently have
    { table1: {query: q, data: d, temptable: t},
    table2: {query: q, data: d, temptable: t},
    ... }

    the following modifications to the searchdict are required to feed the golang module
    [a] the keys need to be renamed: temptable -> TempTable; query -> PsqlQuery; data -> PsqlData
    [b] the tuple inside of 'data' needs to come out and up: ('x',) -> 'x'
    [c] the '%s' in the 'query' needs to become '$1' for string substitution

    """

    ssq = so.searchsqldict
    newdict = dict()
    for s in ssq:
        newdict[s] = dict()
        newdict[s]['TempTable'] = ssq[s]['temptable']
        newdict[s]['PsqlQuery'] = re.sub(r'%s', r'$1', ssq[s]['query'])
        if isinstance(ssq[s]['data'], tuple):
            newdict[s]['PsqlData'] = ssq[s]['data'][0]
        else:
            newdict[s]['PsqlData'] = ssq[s]['data']
    return newdict
