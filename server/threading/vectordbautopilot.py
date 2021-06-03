# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import multiprocessing
import threading
import time
from typing import List

from server import hipparchia
from server.commandlineoptions import getcommandlineargs
from server.formatting.miscformatting import consolewarning, debugmessage
from server.hipparchiaobjects.progresspoll import NullProgressPoll
from server.hipparchiaobjects.searchobjects import SearchObject
from server.semanticvectors.externalvectorsearches import externalvectors
from server.semanticvectors.vectorpipeline import pythonvectors
from server.startup import authordict, listmapper, progresspolldict


def startvectorizing():
	"""

	figure out what vectors are not available in the db

	calculate and add them in the background

	exit when there are none that are out of date or blank

	macOS is currently doing something strange if you run searches while the vectorbot is active

		libc++abi.dylib: terminating with uncaught exception of type std::runtime_error: Couldn't close file
		Traceback (most recent call last):
			File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.7/lib/python3.7/threading.py", line 917, in _bootstrap_inner
			...
			File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.7/lib/python3.7/multiprocessing/connection.py", line 383, in _recv
			raise EOFError
		EOFError

	searching is safe when the vectorbot finishes

	this is fairly 'new' and perhaps emerged via an OS update [it has been known but not documented for a while]

	linux does not seem to have this problem

	:return:
	"""

	workpile = None

	commandlineargs = getcommandlineargs()

	if hipparchia.config['AUTOVECTORIZE'] and not commandlineargs.disablevectorbot:
		workpile = determinevectorworkpile()

	# [(['gr2062'], 4182615), (['gr0057'], 2594166), (['gr4090'], 2202504), ...]

	if hipparchia.config['EXTERNALVECTORHELPER']:
		vectorfunction = externalvectors
	else:
		vectorfunction = pythonvectors

	emptypoll = NullProgressPoll(None)
	modeltype = 'nearestneighborsquery'

	minwords = 500

	while workpile:
		if len(progresspolldict.keys()) != 0:
			# consolewarning('vectorbot pausing to make way for a search')
			time.sleep(30)

		# the typical searchlist is one item: ['lt1414']
		searching = workpile.pop()
		searchlist = searching[0]
		wordcount = searching[1]

		if wordcount > minwords:
			so = buildfakesearchobject()
			so.searchlist = searchlist
			so.poll = emptypoll
			so.vectorquerytype = modeltype
			so.termone = 'FAKESEARCH'

			for c in hipparchia.config['CORPORATOAUTOVECTORIZE']:
				so.session[c] = True

			jsonmessage = vectorfunction(so)

			if jsonmessage == '<!-- MODEL BUILT -->':
				built = True
			else:
				built = False

			if '<!-- MODEL FAILED -->' in jsonmessage:
				consolewarning('vectorbot failed on {s} and will be shutting down'.format(s=searchlist), color='red')
				workpile = list()
				jsonmessage = None

			if '<!-- MODEL EXISTS -->' in jsonmessage:
				# debugmessage('startvectorizing() says that {i} has already been built'.format(i=searchlist[0]))
				pass

			if built and len(searchlist) > 1:
				v = '{i}+ {n} more items vectorized ({w} words)'
			else:
				v = '{i} vectorized ({w} words)'

			if built and wordcount > 5000:
				consolewarning(v.format(i=searchlist[0], w=wordcount, n=len(searchlist) - 1), color='green',
							   isbold=False)

			if built and len(workpile) % 25 == 0:
				consolewarning('{n} items remain to vectorize'.format(n=len(workpile)), color='green', isbold=False)

	if hipparchia.config['AUTOVECTORIZE'] and not commandlineargs.disablevectorbot and multiprocessing.current_process().name == 'MainProcess':
		consolewarning('only short authors remain (fewer than {min} words in the corpus...)'.format(min=minwords), color='green')
		consolewarning('vectorbot shutting down', color='green')

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

	if multiprocessing.current_process().name == 'MainProcess':
		consolewarning('the vectorbot is active and searching for items that need to be vectorized', color='green')
		consolewarning('bagging method has been set to: {b}'.format(b=hipparchia.config['DEFAULTBAGGINGMETHOD']))

	authors = [(authordict[a].universalid, authordict[a].countwordsinworks()) for a in authordict]
	authorsbylength = sorted(authors, key=lambda x: x[1])
	# note that we are turning these into one-item lists: genre lists, etc are multi-author lists
	authortuples = [([a[0]], a[1]) for a in authorsbylength]

	# print('authortuples[-10:]', authortuples[-10:])
	# [(['gr2042'], 1145288), (['gr4013'], 1177392), (['lt0474'], 1207760), (['gr2018'], 1271700), (['gr4089'], 1343587), (['gr4015'], 1422513), (['gr4083'], 1765800), (['gr4090'], 2202504), (['gr0057'], 2594166), (['gr2062'], 4182615)]

	activelists = [l for l in listmapper if len(listmapper[l]['a']) > 0]

	corpustuples = list()
	for item in activelists:
		corpustuples.append(([authordict[a].universalid for a in authordict if authordict[a].universalid[:2] == item], sum([authordict[a].countwordsinworks() for a in authordict if authordict[a].universalid[:2] == item])))

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
	frozensession['baggingmethod'] = hipparchia.config['DEFAULTBAGGINGMETHOD']

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

	for x in ['agnexclusions', 'agnselections', 'alocexclusions', 'alocselections', 'analogyfinder', 'auexclusions',
			  'auselections']:
		frozensession[x] = list()

	for s in ['wkexclusions', 'wkgnexclusions', 'wkgnselections', 'wkselections', 'wlocexclusions',
			  'wlocselections']:
		frozensession[s] = list()

	for p in ['psgexclusions', 'psgselections']:
		frozensession[p] = list()

	for c in ['christiancorpus', 'latincorpus', 'greekcorpus', 'inscriptioncorpus']:
		frozensession[c] = True

	frozensession['latestdate'] = 1500
	frozensession['earliestdate'] = -850

	so = SearchObject('vectorbot', str(), str(), None, None, frozensession)

	# parsevectorsentences() needs the following:
	so.vectorquerytype = qtype
	so.usecolumn = 'marked_up_line'
	so.sortorder = 'shortname'
	so.iamarobot = True

	return so


vectorbot = threading.Thread(target=startvectorizing, name='vectorbot', args=tuple())
vectorbot.start()
