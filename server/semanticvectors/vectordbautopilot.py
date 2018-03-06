# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import threading
import time

from server import hipparchia
from server.dbsupport.dbfunctions import resultiterator, setconnection
from server.hipparchiaobjects.helperobjects import ProgressPoll, SearchObject
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.gensimvectors import buildnnvectorspace
from server.semanticvectors.vectordispatcher import vectorsentencedispatching
from server.semanticvectors.vectorhelpers import checkforstoredvector
from server.startup import poll, workdict


def startvectorizing():
	"""

	:return:
	"""

	workpile = None

	if hipparchia.config['AUTOVECTORIZE'] == 'yes':
		workpile = determinevectorworkpile()

	# [(['gr2062'], 4182615), (['gr0057'], 2594166), (['gr4090'], 2202504), ...]
	emptypoll = ProgressPoll(1)
	indextype = 'nn'

	while workpile:
		if len(poll.keys()) > 1:
			print('vectorbot pausing to make way for a search')
			time.sleep(30)

		# the typical searchlist is one item: ['lt1414']
		searching = workpile.pop()
		searchlist = searching[0]
		wordcount = searching[1]
		so = buildfakesearchobject()
		vectorspace = checkforstoredvector(searchlist, indextype)
		if not vectorspace:
			so.searchlist = searchlist
			indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
			so.indexrestrictions = indexrestrictions
			sentencetuples = vectorsentencedispatching(so, emptypoll)
			vectorspace = buildnnvectorspace(sentencetuples, emptypoll, so)
			# the vectorspace is stored in the db at the end of the call to buildnnvectorspace()
			if len(searchlist) > 1:
				v = '{i}+ {n} more items vectorized ({w} words)'
			else:
				v = '{i} vectorized ({w} words)'
			print(v.format(i=searchlist[0], w=wordcount))
			del vectorspace
			if len(workpile) % 25 == 0:
				print('{n} items remain to vectorize'.format(n=len(workpile)))

	print('vectorbot finished')

	return


def determinevectorworkpile():
	"""

	:return:
	"""

	print('the vectorbot is active\n\tdetermining which vectors we might need to calculate\n')

	dbconnection = setconnection('autocommit')
	cursor = dbconnection.cursor()

	workquery = """
	SELECT universalid, wordcount FROM works ORDER BY universalid
	"""

	cursor.execute(workquery)
	results = resultiterator(cursor)

	authors = dict()
	for r in results:
		au = r[0][:6]
		wd = r[1]
		try:
			authors[au] += wd
		except KeyError:
			authors[au] = wd

	authorsbylength = sorted(authors.keys(), key=lambda x: authors[x])
	# note that we are turning these into one-item lists: genre lists, etc are multi-author lists
	authortuples = [([a], authors[a]) for a in authorsbylength]

	# print('authortuples[:10]', authortuples[:10])
	# [(['gr2062'], 4182615), (['gr0057'], 2594166), (['gr4090'], 2202504), ...]
	cursor.close()
	del dbconnection

	workpile = authortuples
	workpile = [w for w in workpile if w[1] < hipparchia.config['MAXVECTORSPACE']]
	return workpile


def buildfakesearchobject():
	"""

	do what it takes to build a hollow searchobject

	:return:
	"""

	frozensession = dict()
	blanks = ['searchscope', 'nearornot', 'onehit']
	for b in blanks:
		frozensession[b] = None

	nulls = ['psgselections', 'psgexclusions']
	for n in nulls:
		frozensession[n] = list()

	zeroes = ['proximity', 'maxresults', 'linesofcontext']
	for z in zeroes:
		frozensession[z] = 0

	so = SearchObject(1, '', '', None, None, frozensession)

	return so


vectorbot = threading.Thread(target=startvectorizing, args=())
vectorbot.start()
