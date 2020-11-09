# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
from collections import deque

from server.dbsupport.miscdbfunctions import resultiterator
from server.dbsupport.tablefunctions import assignuniquename
from server.hipparchiaobjects.connectionobject import ConnectionObject


def buildwordbags(searchobject, morphdict: dict, sentences: list) -> deque:
	"""

	return the bags after picking which bagging method to use

	:param searchobject:
	:param morphdict:
	:param sentences:
	:return:
	"""

	searchobject.poll.statusis('Building bags of words')

	baggingmethods = {'flat': buildflatbagsofwords,
	                  'alternates': buildbagsofwordswithalternates,
	                  'winnertakesall': buildwinnertakesallbagsofwords,
	                  'unlemmatized': buidunlemmatizedbagsofwords}

	bagofwordsfunction = baggingmethods[searchobject.session['baggingmethod']]

	bagsofwords = bagofwordsfunction(morphdict, sentences)

	return bagsofwords


def buildwinnertakesallbagsofwords(morphdict, sentences) -> deque:
	"""

	turn a list of sentences into a list of list of headwords

	here we figure out which headword is the dominant homonym

	then we just use that term

		esse ===> sum
		esse =/=> edo

	assuming that it is faster to do this 2x so you can do a temp table query rather than iterate into DB

	not tested/profiled, though...

	:param morphdict:
	:param sentences:
	:return:
	"""

	# PART ONE: figure out who the "winners" are going to be

	bagsofwords = buildflatbagsofwords(morphdict, sentences)

	allheadwords = {w for bag in bagsofwords for w in bag}

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

	bagsofwords = deque()
	for s in sentences:
		lemattized = deque()
		for word in s:
			# [('x', 4), ('y', 5), ('z', 1)]
			try:
				possibilities = sorted([(item, randkedheadwords[item]) for item in morphdict[word]], key=lambda x: x[1])
				# first item of last tuple is the winner
				lemattized.append(possibilities[-1][0])
			except KeyError:
				pass
		if lemattized:
			bagsofwords.append(lemattized)

	return bagsofwords


def buidunlemmatizedbagsofwords(morphdict, sentences) -> deque:
	"""

	you wasted a bunch of cycles generating the morphdict, now you will fail to use it...

	what you see is what you get...

	:param morphdict:
	:param sentences:
	:return:
	"""

	bagsofwords = sentences

	return bagsofwords


def buildflatbagsofwords(morphdict, sentences) -> deque:
	"""
	turn a list of sentences into a list of list of headwords

	here we put homonymns next to one another:
		ϲυγγενεύϲ ϲυγγενήϲ

	in buildbagsofwordswithalternates() we have one 'word':
		ϲυγγενεύϲ·ϲυγγενήϲ

	:param morphdict:
	:param sentences:
	:return:
	"""

	bagsofwords = deque()
	for s in sentences:
		lemattized = deque()
		for word in s:
			try:
				# WARNING: we are treating homonymns as if 2+ words were there instead of just one
				# 'rectum' will give you 'rectus' and 'rego'; 'res' will give you 'reor' and 'res'
				# this necessarily distorts the vector space
				lemattized.append([item for item in morphdict[word]])
			except KeyError:
				pass
		# flatten
		bagsofwords.append([item for sublist in lemattized for item in sublist])

	return bagsofwords


def buildbagsofwordswithalternates(morphdict, sentences) -> deque:
	"""

	buildbagsofwords() in rudimentaryvectormath.py does this but flattens rather than
	joining multiple possibilities

	here we have one 'word':
		ϲυγγενεύϲ·ϲυγγενήϲ

	there we have two:
		ϲυγγενεύϲ ϲυγγενήϲ

	:param morphdict:
	:param sentences:
	:return:
	"""

	bagsofwords = deque()
	for s in sentences:
		lemmatizedsentence = deque()
		for word in s:
			try:
				lemmatizedsentence.append('·'.join(morphdict[word]))
			except KeyError:
				pass
		bagsofwords.append(lemmatizedsentence)

	return bagsofwords
