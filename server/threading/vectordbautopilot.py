# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import threading
import time
from typing import List

from click import secho

from server import hipparchia
from server.commandlineoptions import getcommandlineargs
from server.dbsupport.vectordbfunctions import checkforstoredvector
from server.hipparchiaobjects.progresspoll import ProgressPoll
from server.hipparchiaobjects.searchobjects import SearchObject
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.gensimnearestneighbors import buildnnvectorspace
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.startup import authordict, listmapper, poll, workdict


def startvectorizing():
	"""

	figure out what vectors are not available in the db

	calculate and add them in the background

	exit when there are none that are out of date or blank

	:return:
	"""

	workpile = None

	commandlineargs = getcommandlineargs()

	if hipparchia.config['AUTOVECTORIZE'] and not commandlineargs.disablevectorbot:
		workpile = determinevectorworkpile()

	# [(['gr2062'], 4182615), (['gr0057'], 2594166), (['gr4090'], 2202504), ...]
	emptypoll = ProgressPoll(1)
	indextype = 'nn'

	while workpile:
		if len(poll.keys()) != 0:
			secho('vectorbot pausing to make way for a search', fg='red')
			time.sleep(30)

		# the typical searchlist is one item: ['lt1414']
		searching = workpile.pop()
		searchlist = searching[0]
		wordcount = searching[1]
		so = buildfakesearchobject()
		so.searchlist = searchlist
		so.poll = emptypoll

		vectorspace = checkforstoredvector(so, indextype)

		if not vectorspace:
			indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
			so.indexrestrictions = indexrestrictions
			sentencetuples = vectorprepdispatcher(so)
			vectorspace = buildnnvectorspace(sentencetuples, so)
			# the vectorspace is stored in the db at the end of the call to buildnnvectorspace()

			if vectorspace and len(searchlist) > 1:
				v = '{i}+ {n} more items vectorized ({w} words)'
			else:
				v = '{i} vectorized ({w} words)'
			if vectorspace and wordcount > 5000:
				secho(v.format(i=searchlist[0], w=wordcount, n=len(searchlist)-1), fg='green')

			if vectorspace and len(workpile) % 25 == 0:
				secho('{n} items remain to vectorize'.format(n=len(workpile)), fg='green')

			if not vectorspace and len(workpile) % 100 == 0:
				secho('{n} items remain to vectorize, but vectors are not returned with shorter authors'.format(n=len(workpile)), fg='green')
				secho('aborting vectorization', fg='green')
				workpile = list()
			del vectorspace

	if hipparchia.config['AUTOVECTORIZE'] and not commandlineargs.disablevectorbot:
		secho('vectorbot finished', fg='green', bold=True)

	return


def determinevectorworkpile(tempcap=False) -> List[tuple]:
	"""

	probe the db for potential vectorization targets

	:return:
	"""

	if not tempcap:
		cap = hipparchia.config['MAXVECTORSPACE']
	else:
		# real number is just over 93596456
		cap = 94000000

	secho('the vectorbot is active and searching for items that need to be vectorized', fg='green', bold=True)

	authors = [(authordict[a].universalid, authordict[a].countwordsinworks()) for a in authordict]
	authorsbylength = sorted(authors, key=lambda x: x[1])
	# note that we are turning these into one-item lists: genre lists, etc are multi-author lists
	authortuples = [([a[0]], a[1]) for a in authorsbylength]

	# print('authortuples[-10:]', authortuples[-10:])
	# [(['gr2042'], 1145288), (['gr4013'], 1177392), (['lt0474'], 1207760), (['gr2018'], 1271700), (['gr4089'], 1343587), (['gr4015'], 1422513), (['gr4083'], 1765800), (['gr4090'], 2202504), (['gr0057'], 2594166), (['gr2062'], 4182615)]

	activelists = [l for l in listmapper if len(listmapper[l]['a']) > 0]

	corpustuples = list()
	for item in activelists:
		corpustuples.append(([authordict[a].universalid for a in authordict if authordict[a].universalid[:2] == item],
		                     sum([authordict[a].countwordsinworks() for a in authordict if authordict[a].universalid[:2] == item])))

	# gk 75233496
	# lt 7548164
	# db 4276074
	# in 5485166
	# ch 1053646

	# you can do the same exercise for genres and time slices
	# gr up to 300BCE: 13,518,315

	workpile = authortuples + corpustuples
	workpile = [w for w in workpile if w[1] < cap]

	# test: just caesar
	# workpile = [(['lt0448'], 999)]

	return workpile


def buildfakesearchobject(qtype='nearestneighborsquery') -> SearchObject:
	"""

	do what it takes to build a hollow searchobject

	:return:
	"""

	frozensession = dict()
	
	frozensession['vdim'] = hipparchia.config['VECTORDIMENSIONS']
	frozensession['vwindow'] = hipparchia.config['VECTORWINDOW']
	frozensession['viterat'] = hipparchia.config['VECTORTRAININGITERATIONS']
	frozensession['vminpres'] = hipparchia.config['VECTORMINIMALPRESENCE']
	frozensession['vdsamp'] = hipparchia.config['VECTORDOWNSAMPLE']
	frozensession['vcutloc'] = hipparchia.config['VECTORDISTANCECUTOFFLOCAL']
	frozensession['vcutneighb'] = hipparchia.config['VECTORDISTANCECUTOFFNEARESTNEIGHBOR']
	frozensession['vcutlem'] = hipparchia.config['VECTORDISTANCECUTOFFLEMMAPAIR']
	frozensession['vnncap'] = hipparchia.config['NEARESTNEIGHBORSCAP']
	frozensession['vsentperdoc'] = hipparchia.config['SENTENCESPERDOCUMENT']
	frozensession['ldamaxfeatures'] = hipparchia.config['LDAMAXFEATURES']
	frozensession['ldacomponents'] = hipparchia.config['LDACOMPONENTS']
	frozensession['ldamaxfreq'] = hipparchia.config['LDAMAXFREQ']
	frozensession['ldaminfreq'] = hipparchia.config['LDAMINFREQ']
	frozensession['ldaiterations'] = hipparchia.config['LDAITERATIONS']
	frozensession['ldamustbelongerthan'] = hipparchia.config['LDAMUSTBELONGERTHAN']
	
	blanks = ['searchscope', 'nearornot', 'onehit']
	for b in blanks:
		frozensession[b] = None

	nulls = ['psgselections', 'psgexclusions']
	for n in nulls:
		frozensession[n] = list()

	zeroes = ['proximity', 'maxresults', 'linesofcontext']
	for z in zeroes:
		frozensession[z] = 0

	trueorfalse = ['onehit', 'icandodates', 'nearestneighborsquery', 'searchinsidemarkup']
	for x in trueorfalse:
		frozensession[x] = False

	so = SearchObject(1, str(), str(), None, None, frozensession)

	# parsevectorsentences() needs the following:
	so.vectorquerytype = qtype
	so.usecolumn = 'marked_up_line'
	so.sortorder = 'shortname'

	return so


vectorbot = threading.Thread(target=startvectorizing, name='vectorbot', args=tuple())
vectorbot.start()
