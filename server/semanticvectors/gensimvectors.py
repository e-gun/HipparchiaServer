# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import time

from flask import request, session

from server import hipparchia
from server.hipparchiaobjects.searchobjects import ProgressPoll
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.searching.searchfunctions import buildsearchobject, cleaninitialquery
from server.semanticvectors.gensimlsi import lsigenerateoutput
from server.semanticvectors.gensimnearestneighbors import generatenearestneighbordata
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.vectorhelpers import buildlemmatizesearchphrase, checkforstoredvector
from server.semanticvectors.vectorpseudoroutes import emptyvectoroutput
from server.startup import authordict, lemmatadict, listmapper, poll, workdict


@hipparchia.route('/findneighbors/<timestamp>', methods=['GET'])
def findnearestneighborvectors(timestamp):
	"""

	meant to be called via a click from a result from a prior search

	:param timestamp:
	:return:
	"""

	try:
		ts = str(int(timestamp))
	except ValueError:
		ts = str(int(time.time()))

	so = buildsearchobject(ts, request, session)
	so.seeking = ''
	so.proximate = ''
	so.proximatelemma = ''

	try:
		so.lemma = lemmatadict[cleaninitialquery(request.args.get('lem', ''))]
	except KeyError:
		so.lemma = None

	so.vectorquerytype = 'nearestneighborsquery'

	poll[ts] = ProgressPoll(ts)
	activepoll = poll[ts]
	activepoll.activate()
	activepoll.statusis('Preparing to search')

	output = executegensimsearch(activepoll, so)

	del poll[ts]

	return output


def executegensimsearch(activepoll, searchobject):
	"""

	use the searchlist to grab a collection of sentences

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	:param searchitem:
	:param vtype:
	:return:
	"""
	so = searchobject

	starttime = time.time()

	if so.vectorquerytype != 'nearestneighborsquery':
		outputfunction = lsigenerateoutput
		indextype = 'lsi'
		so.lemma = None
		so.tovectorize = buildlemmatizesearchphrase(so.seeking)
		if not so.tovectorize:
			reasons = ['unable to lemmatize the search term(s) [nb: whole words required and accents matter]']
			return emptyvectoroutput(so, reasons)
	else:
		outputfunction = generatenearestneighbordata
		indextype = 'nn'

	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'

	activecorpora = so.getactivecorpora()

	if (so.lemma or so.tovectorize) and activecorpora:
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
		vectorspace = checkforstoredvector(searchlist, indextype)

		if vectorspace == 'failed to build model':
			reasons = ['failed to build vector model (too few words?)']
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
			sentencestuples = vectorprepdispatcher(so, activepoll)
		else:
			sentencestuples = None

		output = outputfunction(sentencestuples, workssearched, so, activepoll, starttime, vectorspace)

	else:
		reasons = ['search list contained zero items']
		return emptyvectoroutput(so, reasons)

	return output


