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
from server.semanticvectors.gensimlsi import lsigenerateoutput
from server.semanticvectors.gensimnearestneighbors import generatenearestneighbordata
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.vectorhelpers import buildlemmatizesearchphrase
from server.semanticvectors.vectorroutehelperfunctions import emptyvectoroutput
from server.startup import authordict, listmapper, workdict


def executegensimsearch(searchobject):
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
