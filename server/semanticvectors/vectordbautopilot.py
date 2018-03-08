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
from server.hipparchiaobjects.searchobjects import ProgressPoll, SearchObject
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.gensimnearestneighbors import buildnnvectorspace
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.vectorhelpers import checkforstoredvector
from server.startup import poll, workdict


def startvectorizing():
	"""

	figure out what vectors are not available in the db

	calculate and add them in the background

	exit when there are none that are out of date or blank

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
			sentencetuples = vectorprepdispatcher(so, emptypoll)
			vectorspace = buildnnvectorspace(sentencetuples, emptypoll, so)
			# the vectorspace is stored in the db at the end of the call to buildnnvectorspace()

			if vectorspace and len(searchlist) > 1:
				v = '{i}+ {n} more items vectorized ({w} words)'
			else:
				v = '{i} vectorized ({w} words)'
			if vectorspace and wordcount > 5000:
				print(v.format(i=searchlist[0], w=wordcount))

			if vectorspace and len(workpile) % 25 == 0:
				print('{n} items remain to vectorize'.format(n=len(workpile)))

			if not vectorspace and len(workpile) % 100 == 0:
				print('{n} items remain to vectorize, but vectors are not returned with shorter authors'.format(n=len(workpile)))
				print('aborting vectorization')
				workpile = list()
			del vectorspace

	if hipparchia.config['AUTOVECTORIZE'] == 'yes':
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

	corporasizes = dict()
	for r in results:
		c = r[0][:2]
		wd = r[1]
		try:
			corporasizes[c] += wd
		except KeyError:
			corporasizes[c] = wd

	corpustuples = list()
	for k in corporasizes.keys():
		authors = [a for a in authorsbylength if a[:2] == k]
		corpustuples.append((authors, corporasizes[k]))

	# print('authortuples[:10]', authortuples[:10])
	# [(['gr2062'], 4182615), (['gr0057'], 2594166), (['gr4090'], 2202504), ...]
	cursor.close()
	del dbconnection

	workpile = authortuples + corpustuples
	workpile = [w for w in workpile if w[1] < hipparchia.config['MAXVECTORSPACE']]

	# test caesar
	# workpile = [(['lt0448'], 999)]

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

	yn = ['onehit', 'icandodates']
	for n in yn:
		frozensession[n] = 'no'

	so = SearchObject(1, '', '', None, None, frozensession)

	# parsevectorsentences() needs the following:
	so.vectortype = 'semanticvectorquery'
	so.usecolumn = 'marked_up_line'
	so.sortorder = 'shortname'

	return so


vectorbot = threading.Thread(target=startvectorizing, args=())
vectorbot.start()
