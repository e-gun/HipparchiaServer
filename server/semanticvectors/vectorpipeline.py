# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import json
import locale
import re
from string import punctuation
from typing import List

from server import hipparchia
from server.dbsupport.miscdbfunctions import resultiterator
from server.dbsupport.tablefunctions import assignuniquename
from server.dbsupport.vectordbfunctions import checkforstoredvector
from server.formatting.miscformatting import consolewarning, debugmessage
from server.formatting.vectorformatting import ldatopicsgenerateoutput
from server.formatting.wordformatting import elidedextrapunct
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.searchobjects import SearchObject
from server.listsandsession.genericlistfunctions import findsetofallwords
from server.listsandsession.searchlistmanagement import compilesearchlist
from server.routes.searchroute import updatesearchlistandsearchobject
from server.searching.precomposedsqlsearching import basicprecomposedsqlsearcher
from server.searching.precomposesql import searchlistintosqldict
from server.semanticvectors.gensimnearestneighbors import generatenearestneighbordata
from server.semanticvectors.modelbuilders import buildgensimmodel, buildsklearnselectedworks, \
    gensimgenerateanalogies
from server.semanticvectors.vectorhelpers import mostcommonwordsviaheadwords, removestopwords, cleanvectortext, \
    recursivesplit, convertmophdicttodict, emptyvectoroutput
from server.startup import listmapper, workdict
from server.textsandindices.textandindiceshelperfunctions import getrequiredmorphobjects

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


def pythonvectors(so: SearchObject) -> JSON_STR:
    """

    this is the matching function to golangvectors()

    [0] test to see what will happen:
        [a] scope problems? [jump away if so...]
        [b] already a model on file? ... [jump down to #5 if so]
    [1] generate a searchlist
    [2] do a searchlistintosqldict()
    [3] acquire and bag the words
        [a] grab db lines that are relevant to the search
        [b] turn them into a unified text block
        [c] do some preliminary cleanups
        [d] break the text into sentences and assemble []SentenceWithLocus (NB: these are "unlemmatized bags of words")
        [e] figure out all of the words used in the passage
        [f] find all of the parsing info relative to these words
        [g] figure out which headwords to associate with the collection of words
        [h] build the lemmatized bags of words ('unlemmatized' can skip [f] and [g]...)
    [4] hand the bags over to Word2Vec(), etc. [*]
    [5] run queries against the model and return the JSON results
    """
    debugmessage('pythonvectors()')
    assert so.vectorquerytype in ['analogies', 'nearestneighborsquery', 'topicmodel']

    # [0] is this really going to happen?
    so.poll.statusis('Checking for valid search')
    # [i] do we bail out before even getting started?
    # note that this can / will return independently and break here
    abortjson = checkneedtoabort(so)
    if abortjson:
        del so.poll
        return abortjson

    # [ii] do we actually have a model stored already?
    so.poll.statusis('Checking for stored search')
    # calculatewholeauthorsearches() + configurewhereclausedata()
    so = updatesearchlistandsearchobject(so)
    so.setsearchlistthumbprint()
    themodel = checkforstoredvector(so)

    if not themodel:
        # [1] generate a searchlist: use executesearch() as the template

        so.usecolumn = 'marked_up_line'
        so.cap = 199999999

        # [2] do a searchlistintosqldict() [this is killing lda...]
        so.searchsqldict = searchlistintosqldict(so, str(), vectors=True)

        bagsofwords = acquireandbagthewords(so)

        # [4] hand the bags over to Word2Vec(), etc.
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
    # [5] run queries against the model
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


def acquireandbagthewords(so: SearchObject) -> List[List[str]]:
    """

    [3] acquire and bag the words
        [a] grab db lines that are relevant to the search
        [b] turn them into a unified text block
        [c] do some preliminary cleanups
        [d1] break the text into sentences (NB: these are "unlemmatized bags of words")
        [d2] [disabled option] and assemble sentences-with-locus
        [e] figure out all of the words used in the passage
        [f] find all of the parsing info relative to these words
        [g] figure out which headwords to associate with the collection of words
        [h] build the lemmatized bags of words ('unlemmatized' can skip [e] - [g]...)

    """

    # [a] grab db lines that are relevant to the search
    so.poll.statusis('Grabbing the required lines')
    linesweneed = basicprecomposedsqlsearcher(so)
    so.poll.allworkis(-1)  # this turns off the % completed notice in the JS
    so.poll.sethits(0)

    # return from an SPop will leave them out of order...
    # dbWorkLine has __eq__, __gt__, and __lt__
    so.poll.statusis('Sorting the lines')
    linesweneed = sorted(linesweneed)

    # kill off titles and salutations: dangerous if there is a body l1 value of 't' out there
    so.poll.statusis('Pruning the lines')
    linesweneed = [r for r in linesweneed if r.l1 not in ['t', 'sa']]

    # [b] turn them into a unified text block
    # note that we will shortly discard the getlineurl() info ...
    so.poll.statusis('Joining the lines')
    wholetext = ' '.join(['⊏{i}⊐{t}'.format(i=l.getlineurl(), t=l.markedup) for l in linesweneed])

    # [c] do some preliminary cleanups
    so.poll.statusis('Cleaning the lines')
    wholetext = re.sub(r'-\s{1,2}', str(), wholetext)
    wholetext = cleanvectortext(wholetext)  # this contains a de-abbreviator, html stripper, etc.
    wholetext = wholetext.lower()

    # [d1] break the text into sentences
    so.poll.statusis('Finding the sentences')
    terminations = ['.', '?', '!', '·', ';']
    allsentences = recursivesplit([wholetext], terminations)

    # do a little bit of extra cleaning that we could not do before
    punct = re.compile('[{s}]'.format(s=re.escape(punctuation + elidedextrapunct)))
    allsentences = [re.sub(punct, str(), s) for s in allsentences]

    if so.sentencebundlesize > 1:
        # https://stackoverflow.com/questions/44104729/grouping-every-three-items-together-in-list-python
        allsentences = [' '.join(bundle) for bundle in zip(*[iter(allsentences)] * so.sentencebundlesize)]

    # [d2] [disabled option] and assemble sentences-with-locus (NB: these are "unlemmatized bags of words")
    bll = False
    if bll:
        unusedlistofdicts = buildlineandlocus(linesweneed[0], allsentences)
        del unusedlistofdicts

    # we might be using a lot of memory...
    del linesweneed

    # clean out the location info
    allsentences = [re.sub(r'⊏.*?⊐', str(), s) for s in allsentences]
    # consolewarning('trimming sentences: remove next line of code later')
    # allsentences = allsentences[:20]

    morphdict = dict()
    if so.session['baggingmethod'] != 'unlemmatized':
        so.poll.statusis('Determining the set of words')
        # [e] figure out all of the words used in the passage
        allwords = findsetofallwords(allsentences)

        # [f] find all of the parsing info relative to these words
        so.poll.statusis('Building the parsing table')
        mo = getrequiredmorphobjects(allwords, furtherdeabbreviate=True)

        # [g] figure out which headwords to associate with the collection of words
        # {'θεῶν': {'θεόϲ', 'θέα', 'θεάω', 'θεά'}, 'πώ': {'πω'}, 'πολλά': {'πολύϲ'}, 'πατήρ': {'πατήρ'}, ... }
        morphdict = convertmophdicttodict(mo)

    # [h] build the lemmatized bags of words ('unlemmatized' can skip [e]-[g]...)
    wordbags = pythonpipelinewordbagbuilder(so, morphdict, allsentences)

    return wordbags


def buildlineandlocus(firstline, allsentences: List[str]) -> List[dict]:
    """

    build line-to-locus association:

    {'line/gr0014w002/233': 'μαϲτότεροϲ παρὰ πᾶϲι νομίζεται', 'line/gr0014w002/213': 'ὑμεῖϲ δ’ ὅϲῳ χεῖρον ἢ...', ...}

    there are (currently unused) vector styles that can require it

    note the possibility of collisions: short sentences on the same line; use tuples if you really do this...

    """

    previousid = firstline.getlineurl()
    idfinder = re.compile(r'⊏(.*?)⊐')
    taggedmatches = list()
    for s in allsentences:
        ids = re.findall(idfinder, s)
        if ids:
            taggedmatches.append({ids[0]: re.sub(idfinder, str(), s)})
            previousid = ids[-1]
        else:
            taggedmatches.append({previousid: s})

    return taggedmatches


def checkneedtoabort(so: SearchObject) -> str:
    """

    can/should we even do this?

    """

    if so.iamarobot:
        return str()

    abortjson = str()
    abort = lambda x: emptyvectoroutput(so, x)
    activecorpora = so.getactivecorpora()
    so.poll.statusis('Compiling the list of works to search')
    so.searchlist = compilesearchlist(listmapper, so.session)

    # so.seeking should only be set via a fallback when session['baggingmethod'] == 'unlemmatized'
    if (so.lemmaone or so.tovectorize or so.seeking) and activecorpora:
        pass
    elif not activecorpora:
        abortjson = abort(['no active corpora'])
    elif not so.searchlist:
        abortjson = abort(['empty list of places to look'])
    elif so.vectorquerytype == 'topicmodel':
        # we don't have and don't need a lemmaone, etc.
        pass
    elif so.vectorquerytype == 'analogies':
        if not so.lemmaone or not so.lemmatwo or not so.lemmathree:
            abortjson = abort('[did not have three lemmata]')
    else:
        # note that some vector queries do not need a term; fix this later...
        abortjson = abort(['there was no search term'])

    maxwords = hipparchia.config['MAXVECTORSPACE']
    wordstotal = 0
    for work in so.searchlist:
        work = work[:10]
        try:
            wordstotal += workdict[work].wordcount
        except TypeError:
            # TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'
            pass

    if wordstotal > maxwords:
        m = 'the vector scope max exceeded: {a} > {b} '
        abortjson = abort([m.format(a=locale.format_string('%d', wordstotal, grouping=True), b=locale.format_string('%d', maxwords, grouping=True))])

    return abortjson


def pythonpipelinewordbagbuilder(so: SearchObject, morphdict, allsentences):
    """

    return the bags after picking which bagging method to use

    the old baggers do not work with the new pipeline

        for word in string.split(' ')  VS for word in string

    otherwise these are basically identical

    """
    so.poll.statusis('Filling the bags of words')

    baggingmethods = {'flat': flatbagger,
                      'alternates': alternatesbagger,
                      'winnertakesall': winnertakesallbagger,
                      'unlemmatized': unlemmatizedbagger}

    bagofwordsfunction = baggingmethods[so.session['baggingmethod']]

    bagsofwords = bagofwordsfunction(morphdict, allsentences)

    debugmessage('pythonpipelinewordbagbuilder() bagsofwords[0:2]:\n\t{b}'.format(b=bagsofwords[0:2]))

    return bagsofwords


def flatbagger(morphdict: dict, allsentences: [List[str]]) -> List[List[str]]:
    """
    turn a list of sentences into a list of list of headwords

    alternate possibilities listed next to one another: ϲυγγενεύϲ ϲυγγενήϲ

    WARNING: we are treating homonymns as if 2+ words were there instead of just one
    this necessarily distorts the vector space

    """

    bagsofwords = list()
    for thissentence in allsentences:
        lemmatizedsentence = list()
        for word in thissentence.split(' '):
            try:
                lemmatizedsentence.append([item for item in morphdict[word]])
            except KeyError:
                pass
        # append the flattened version
        bagsofwords.append([item for sublist in lemmatizedsentence for item in sublist])

    return bagsofwords


def alternatesbagger(morphdict: dict, allsentences: [List[str]]) -> List[List[str]]:
    """
    turn a list of sentences into a list of list of headwords

    alternate possibilities yoked to one another: ϲυγγενεύϲ·ϲυγγενήϲ

    """
    bagsofwords = list()
    for thissentence in allsentences:
        lemmatizedsentence = list()
        for word in thissentence.split(' '):
            try:
                lemmatizedsentence.append('·'.join(morphdict[word]))
            except KeyError:
                pass
        bagsofwords.append(lemmatizedsentence)

    return bagsofwords


def winnertakesallbagger(morphdict: dict, allsentences: [List[str]]) -> List[List[str]]:
    """

    turn a list of sentences into a list of list of headwords

    here we figure out which headword is the dominant homonym

    then we just use that term

    """

    # PART ONE: figure out who the "winners" are going to be

    # [a] determine the full set of headwords we are accessing

    allheadwords = {item for x in morphdict for item in morphdict[x]}

    dbconnection = ConnectionObject(readonlyconnection=False)
    dbconnection.setautocommit()
    dbcursor = dbconnection.cursor()
    rnd = assignuniquename(6)

    tqtemplate = """
    CREATE TEMPORARY TABLE temporary_headwordlist_{rnd} AS
    	SELECT headwords AS hw FROM unnest(ARRAY[{allwords}]) headwords
    """

    qtemplate = """
    SELECT entry_name, total_count FROM {db} 
    	WHERE EXISTS 
    		(SELECT 1 FROM temporary_headwordlist_{rnd} temptable WHERE temptable.hw = {db}.entry_name)
    """

    tempquery = tqtemplate.format(rnd=rnd, allwords=list(allheadwords))
    dbcursor.execute(tempquery)
    # https://www.psycopg.org/docs/extras.html#psycopg2.extras.execute_values
    # third parameter is

    query = qtemplate.format(rnd=rnd, db='dictionary_headword_wordcounts')
    dbcursor.execute(query)
    results = resultiterator(dbcursor)

    randkedheadwords = {r[0]: r[1] for r in results}

    # PART TWO: let the winners take all

    bagsofwords = list()
    for thissentence in allsentences:
        lemmatizedsentence = list()
        for word in thissentence.split(' '):
            # [('x', 4), ('y', 5), ('z', 1)]
            try:
                possibilities = sorted([(item, randkedheadwords[item]) for item in morphdict[word]], key=lambda x: x[1])
                # first item of last tuple is the winner
                lemmatizedsentence.append(possibilities[-1][0])
            except KeyError:
                pass
        if lemmatizedsentence:
            bagsofwords.append(lemmatizedsentence)

    return bagsofwords


def unlemmatizedbagger(morphdict: dict, allsentences: [List[str]]) -> List[List[str]]:
    """

    return the split version of the original:
        ['cui dono lepidum nouum libellum..', 'corneli tibi namque..., ]

    """

    bagsofwords = [s.split(' ') for s in allsentences]

    return bagsofwords


