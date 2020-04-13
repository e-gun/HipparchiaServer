# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from server import hipparchia
from server.dbsupport.vectordbfunctions import checkforstoredvector
from server.listsandsession.searchlistmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.gensimanalogies import generateanalogies
from server.semanticvectors.gensimlsi import lsigenerateoutput
from server.semanticvectors.gensimnearestneighbors import generatenearestneighbordata
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.vectorgraphing import threejsgraphofvectors, tsnegraphofvectors
from server.semanticvectors.vectorhelpers import buildlemmatizesearchphrase
from server.semanticvectors.vectorroutehelperfunctions import emptyvectoroutput
from server.startup import authordict, listmapper, workdict


def executenearestneighborsquery(searchobject):
	"""

	set yourself up for executegensimsearch()

	:param searchobject:
	:return:
	"""

	if searchobject.vectorquerytype == 'nearestneighborsquery':
		outputfunction = generatenearestneighbordata
		indextype = 'nn'
		return executegensimsearch(searchobject, outputfunction, indextype)
	else:
		reasons = ['unknown vectorquerytype sent to executegensimsearch()']
		return emptyvectoroutput(searchobject, reasons)


def executegenerateanalogies(searchobject):
	"""

	set yourself up for executegensimsearch()

	:param searchobject:
	:return:
	"""

	if searchobject.vectorquerytype == 'analogyfinder':
		outputfunction = generateanalogies
		indextype = 'nn'
		return executegensimsearch(searchobject, outputfunction, indextype)
	else:
		reasons = ['unknown vectorquerytype sent to executegensimsearch()']
		return emptyvectoroutput(searchobject, reasons)


def executegensimlsi(searchobject):
	"""

	CURRENTLYUNUSED

	set yourself up for executegensimsearch()

	:param searchobject:
	:return:
	"""
	so = searchobject

	if so.vectorquerytype == 'CURRENTLYUNUSED':
		outputfunction = lsigenerateoutput
		indextype = 'lsi'
		so.lemma = None
		so.tovectorize = buildlemmatizesearchphrase(so.seeking)
		if not so.tovectorize:
			reasons = ['unable to lemmatize the search term(s) [nb: whole words required and accents matter]']
			return emptyvectoroutput(so, reasons)
		return executegensimsearch(searchobject, outputfunction, indextype)
	else:
		reasons = ['unknown vectorquerytype sent to executegensimsearch()']
		return emptyvectoroutput(searchobject, reasons)


def executegensimsearch(searchobject, outputfunction, indextype):
	"""

	use the searchlist to grab a collection of sentences

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	:param searchitem:
	:param vtype:
	:return:
	"""

	so = searchobject
	activepoll = so.poll

	# print('so.vectorquerytype', so.vectorquerytype)

	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'

	activecorpora = so.getactivecorpora()

	# so.seeking should only be set via a fallback when session['baggingmethod'] == 'unlemmatized'
	if (so.lemma or so.tovectorize or so.seeking) and activecorpora:
		activepoll.statusis('Compiling the list of works to search')
		searchlist = compilesearchlist(listmapper, so.session)
	elif not activecorpora:
		reasons = ['no active corpora']
		return emptyvectoroutput(so, reasons)
	else:
		reasons = ['there was no search term']
		return emptyvectoroutput(so, reasons)

	# make sure you don't go nuts
	maxwords = hipparchia.config['MAXVECTORSPACE']
	wordstotal = 0
	for work in searchlist:
		work = work[:10]
		try:
			wordstotal += workdict[work].wordcount
		except TypeError:
			# TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'
			pass

	if wordstotal > maxwords:
		wt = '{:,}'.format(wordstotal)
		mw = '{:,}'.format(maxwords)
		reasons = ['the vector scope max exceeded: {a} > {b} '.format(a=wt, b=mw)]
		return emptyvectoroutput(so, reasons)

	# DEBUGGING
	# Frogs and mice
	# so.lemma = lemmatadict['βάτραχοϲ']
	# searchlist = ['gr1220']

	# Euripides
	# so.lemma = lemmatadict['ἄτη']
	# print(so.lemma.formlist)
	# so.lemma.formlist = ['ἄτῃ', 'ἄταν', 'ἄτηϲ', 'ἄτηι']
	# searchlist = ['gr0006']

	if len(searchlist) > 0:
		searchlist = flagexclusions(searchlist, so.session)
		workssearched = len(searchlist)
		searchlist = calculatewholeauthorsearches(searchlist, authordict)
		so.searchlist = searchlist

		indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
		so.indexrestrictions = indexrestrictions

		# 'False' if there is no vectorspace; 'failed' if there can never be one; otherwise vectors
		vectorspace = checkforstoredvector(so, indextype)

		if not vectorspace and hipparchia.config['FORBIDUSERDEFINEDVECTORSPACES']:
			reasons = ['you are only allowed to fetch pre-stored vector spaces; <b>try a single author or corpus search using the default vector values</b>']
			return emptyvectoroutput(so, reasons)

		# find all sentences
		if not vectorspace:
			activepoll.statusis('No stored model for this search. Finding all sentences')
		else:
			activepoll.statusis('Finding neighbors')
		# blanking out the search term will return every last sentence...
		# otherwise you only return sentences with the search term in them (i.e. rudimentaryvectorsearch)
		if not vectorspace:
			so.seeking = r'.'
			sentencetuples = vectorprepdispatcher(so)
		else:
			sentencetuples = None

		output = outputfunction(sentencetuples, workssearched, so, vectorspace)

	else:
		reasons = ['search list contained zero items']
		return emptyvectoroutput(so, reasons)

	return output


def twodimensionalrepresentationofspace(searchobject):
	"""

	https://radimrehurek.com/gensim/auto_examples/tutorials/run_word2vec.html#sphx-glr-auto-examples-tutorials-run-word2vec-py

	see there: Visualising the Word Embeddings

	:return:
	"""

	if searchobject.vectorquerytype == 'vectortestfunction':
		outputfunction = tsnegraphofvectors
		indextype = 'nn'
		return executegensimsearch(searchobject, outputfunction, indextype)
	else:
		reasons = ['unknown vectorquerytype sent to executegensimsearch()']
		return emptyvectoroutput(searchobject, reasons)


def threedimensionalrepresentationofspace(searchobject):
	"""

	see https://github.com/tobydoig/3dword2vec

	:param searchobject:
	:return:
	"""

	if searchobject.vectorquerytype == 'vectortestfunction':
		outputfunction = threejsgraphofvectors
		indextype = 'nn'
		return executegensimsearch(searchobject, outputfunction, indextype)
	else:
		reasons = ['unknown vectorquerytype sent to executegensimsearch()']
		return emptyvectoroutput(searchobject, reasons)
