# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import json

from server import hipparchia
from server.dbsupport.tablefunctions import assignuniquename
from server.dbsupport.vectordbfunctions import checkforstoredvector
from server.dbsupport.vectordbfunctions import createstoredimagestable
from server.formatting.jsformatting import generatevectorjs
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.searchobjects import SearchOutputObject
from server.listsandsession.searchlistmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.gensimanalogies import generateanalogies
from server.semanticvectors.gensimlsi import lsigenerateoutput
from server.semanticvectors.gensimnearestneighbors import generatenearestneighbordata
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.vectorhelpers import buildlemmatizesearchphrase, reducetotwodimensions
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
	Visualising the Word Embeddings


	:return:
	"""

	if searchobject.vectorquerytype == 'vectortestfunction':
		outputfunction = tsnegraphofvectors
		indextype = 'nn'
		return executegensimsearch(searchobject, outputfunction, indextype)
	else:
		reasons = ['unknown vectorquerytype sent to executegensimsearch()']
		return emptyvectoroutput(searchobject, reasons)


def tsnegraphofvectors(sentencetuples, workssearched, so, vectorspace):
	"""

	lifted from https://radimrehurek.com/gensim/auto_examples/tutorials/run_word2vec.html#sphx-glr-auto-examples-tutorials-run-word2vec-py


	:param sentencetuples:
	:param workssearched:
	:param so:
	:param vectorspace:
	:return:
	"""

	import random

	random.seed(0)

	plotdict = reducetotwodimensions(vectorspace)
	xvalues = plotdict['xvalues']
	yvalues = plotdict['yvalues']
	labels = plotdict['labels']

	import matplotlib.pyplot as plt
	import random
	from io import BytesIO

	random.seed(0)

	plt.figure(figsize=(12, 12))
	plt.scatter(xvalues, yvalues)


	# Label randomly subsampled 25 data points
	#
	indices = list(range(len(labels)))
	selected_indices = random.sample(indices, 25)
	for i in selected_indices:
		plt.annotate(labels[i], (xvalues[i], yvalues[i]))

	graphobject = BytesIO()
	plt.savefig(graphobject)
	plt.clf()
	plt.close()

	graphobject = graphobject.getvalue()

	imagename = svg(graphobject)

	print('http://localhost:5000/getstoredfigure/{i}'.format(i=imagename))

	output = SearchOutputObject(so)
	output.image = imagename

	findsjs = generatevectorjs()

	output.found = str()
	output.js = findsjs

	jsonoutput = json.dumps(output.generateoutput())

	# print('jsonoutput', jsonoutput)
	return jsonoutput


# temp fnc: delete later
def svg(figureasbytes):
	"""

	store a graph in the image table so that you can subsequently display it in the browser

	note that images get deleted after use

	also note that we hand the data to the db and then immediatel grab it out of the db because of
	constraints imposed by the way flask works

	:param figureasbytes:
	:return:
	"""

	dbconnection = ConnectionObject(ctype='rw')
	dbconnection.setautocommit()
	cursor = dbconnection.cursor()

	# avoid psycopg2.DataError: value too long for type character varying(12)
	randomid = assignuniquename(12)

	q = """
	INSERT INTO public.storedvectorimages 
		(imagename, imagedata)
		VALUES (%s, %s)
	"""

	d = (randomid, figureasbytes)
	try:
		cursor.execute(q, d)
	except psycopg2.ProgrammingError:
		# psycopg2.ProgrammingError: relation "public.storedvectorimages" does not exist
		createstoredimagestable()
		cursor.execute(q, d)

	# print('stored {n} in vector image table'.format(n=randomid))

	dbconnection.connectioncleanup()

	return randomid
