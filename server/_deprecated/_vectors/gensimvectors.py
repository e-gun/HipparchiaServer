# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from server._deprecated._vectors.unused_gensim import executegensimsearch, generateanalogies
from server.semanticvectors.gensimnearestneighbors import generatenearestneighbordata
from server.semanticvectors.vectorroutehelperfunctions import emptyvectoroutput


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

	# print('searchobject.vectorquerytype', searchobject.vectorquerytype)

	if searchobject.vectorquerytype == 'analogies':
		outputfunction = generateanalogies
		indextype = 'nn'
		return executegensimsearch(searchobject, outputfunction, indextype)
	else:
		reasons = ['unknown vectorquerytype sent to executegensimsearch()']
		return emptyvectoroutput(searchobject, reasons)
