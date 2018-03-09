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

	poll[ts] = ProgressPoll(ts)
	activepoll = poll[ts]
	activepoll.activate()
	activepoll.statusis('Preparing to search')

	output = executegensimsearch(activepoll, so, nn=True)

	del poll[ts]

	return output


def executegensimsearch(activepoll, searchobject, nn=False):
	"""

	use the searchlist to grab a collection of sentences

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	:param searchitem:
	:param vtype:
	:return:
	"""
	so = searchobject

	starttime = time.time()

	if not nn:
		outputfunction = lsigenerateoutput
		indextype = 'lsi'
		so.vectortype = 'semanticvectorquery'
		so.lemma = buildlemmatizesearchphrase(so.seeking)
		if not so.lemma:
			reasons = ['unable to lemmatize the search term(s) [nb: whole words required and accents matter]']
			return emptyvectoroutput(so, reasons)
		else:
			validlemma = True
	else:
		outputfunction = generatenearestneighbordata
		indextype = 'nn'

		try:
			validlemma = lemmatadict[so.lemma.dictionaryentry]
		except KeyError:
			validlemma = None
		except AttributeError:
			# 'NoneType' object has no attribute 'dictionaryentry'
			validlemma = None

		so.lemma = validlemma

		try:
			validlemmatwo = lemmatadict[so.proximatelemma.dictionaryentry]
		except KeyError:
			validlemmatwo = None
		except AttributeError:
			# 'NoneType' object has no attribute 'dictionaryentry'
			validlemmatwo = None

		so.proximatelemma = validlemmatwo


	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c] == 'yes']

	if (so.lemma or so.seeking) and activecorpora:
		activepoll.statusis('Compiling the list of works to search')
		searchlist = compilesearchlist(listmapper, so.session)
	else:
		reasons = ['search list contained zero items']
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

		vectorspace = checkforstoredvector(searchlist, indextype)

		if validlemma:
			# find all sentences
			if not vectorspace:
				activepoll.statusis('No stored model for this search. Finding all sentences')
			else:
				activepoll.statusis('Finding neighbors')
			# blanking out the search term will really return every last sentence...
			# otherwise you only return sentences with the search term in them
			try:
				restorelemma = lemmatadict[so.lemma.dictionaryentry]
			except AttributeError:
				# we are doing an lsi search and actually holding a string in so.lemma
				restorelemma = so.lemma
			so.lemma = None
			so.seeking = r'.'
			if not vectorspace:
				sentencestuples = vectorprepdispatcher(so, activepoll)
			else:
				sentencestuples = None
			so.lemma = restorelemma
			output = outputfunction(sentencestuples, workssearched, so, activepoll, starttime, vectorspace)
		else:
			return emptyvectoroutput(so)
	else:
		return emptyvectoroutput(so)

	return output


def findnearestneighbors(activepoll, searchobject, req):
	"""

	pass-through to findlatentsemanticindex()

	:param activepoll:
	:param searchobject:
	:return:
	"""
	so = searchobject

	try:
		so.lemma = lemmatadict[cleaninitialquery(req.args.get('lem', ''))]
	except KeyError:
		so.lemma = None

	return executegensimsearch(activepoll, so, nn=True)
