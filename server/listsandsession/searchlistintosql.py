# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import re

from server import hipparchia
from server.dbsupport.dblinefunctions import worklinetemplate
from server.formatting.miscformatting import consolewarning
from server.formatting.wordformatting import wordlistintoregex
from server.hipparchiaobjects.searchobjects import SearchObject
from server.searching.searchfunctions import buildbetweenwhereextension


def searchlistintosqldict(searchobject: SearchObject, seeking: str) -> dict:
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
            whr = 'WHERE {xtn} ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax, xtn=whereextensions)
        elif r['type'] == 'unrestricted':
            whr = 'WHERE {xtn} ( {c} {sy} %s )'.format(c=so.usecolumn, sy=mysyntax, xtn=whereextensions)
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

        qtemplate = 'SELECT {wtmpl} FROM {db} {whr} {lm}'
        q = qtemplate.format(wtmpl=worklinetemplate, db=authortable, whr=whr, lm=mylimit)
        d = (seeking,)
        returndict[authortable]['query'] = q
        returndict[authortable]['data'] = d

    return returndict


def rewritesqlsearchdictforlemmata(searchobject: SearchObject) -> dict:
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
    so = searchobject
    searchdict = searchobject.searchsqldict

    terms = so.lemma.formlist

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
