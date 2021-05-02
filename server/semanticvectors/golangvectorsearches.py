# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

from server.hipparchiaobjects.searchobjects import SearchObject
from server.formatting.miscformatting import consolewarning, debugmessage


def golangvectors(so: SearchObject):
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

    """
    consolewarning('in progress; will not return results', color='red')
    return str()
