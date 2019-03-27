# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
from flask import session

from server import hipparchia
from server.dbsupport.miscdbfunctions import probefordatabases
from server.listsandsession.corpusavailability import corpusisonandavailable


def probeforsessionvariables():
	"""

	check to see if there is a session, if not populate all of the keyed values with their defaults

	:return:
	"""

	try:
		session['greekcorpus']
	except KeyError:
		# print('resetting session variables')
		session['agnexclusions'] = list()
		session['agnselections'] = list()
		session['alocexclusions'] = list()
		session['alocselections'] = list()
		session['auexclusions'] = list()
		session['auselections'] = list()
		session['authorssummary'] = hipparchia.config['DEFAULTSUMMARIZELEXICALAUTHORS']
		session['available'] = probefordatabases()
		session['bracketangled'] = hipparchia.config['DEFAULTHIGHLIGHTANGLEDBRACKETS']
		session['bracketcurly'] = hipparchia.config['DEFAULTHIGHLIGHTCURLYBRACKETS']
		session['bracketround'] = hipparchia.config['DEFAULTHIGHLIGHTROUNDBRACKETS']
		session['bracketsquare'] = hipparchia.config['DEFAULTHIGHLIGHTSQUAREBRACKETS']
		session['browsercontext'] = str(int(hipparchia.config['DEFAULTBROWSERLINES']))
		session['christiancorpus'] = corpusisonandavailable('christiancorpus')
		session['collapseattic'] = True
		session['cosdistbysentence'] = False
		session['cosdistbylineorword'] = False
		session['debugdb'] = hipparchia.config['DBDEBUGMODE']
		session['debuglex'] = hipparchia.config['LEXDEBUGMODE']
		session['debugparse'] = hipparchia.config['PARSERDEBUGMODE']
		session['debughtml'] = hipparchia.config['HTMLDEBUGMODE']
		session['debugparse'] = hipparchia.config['PARSERDEBUGMODE']
		session['earliestdate'] = hipparchia.config['DEFAULTEARLIESTDATE']
		session['fontchoice'] = hipparchia.config['HOSTEDFONTFAMILY']
		session['greekcorpus'] = corpusisonandavailable('greekcorpus')
		session['headwordindexing'] = hipparchia.config['DEFAULTINDEXBYHEADWORDS']
		session['incerta'] = hipparchia.config['DEFAULTINCERTA']
		session['indexbyfrequency'] = hipparchia.config['DEFAULTINDEXBYFREQUENCY']
		session['indexskipsknownwords'] = False
		session['inscriptioncorpus'] = corpusisonandavailable('inscriptioncorpus')
		session['latestdate'] = hipparchia.config['DEFAULTLATESTDATE']
		session['latincorpus'] = corpusisonandavailable('latincorpus')
		session['linesofcontext'] = int(hipparchia.config['DEFAULTLINESOFCONTEXT'])
		session['maxresults'] = str(int(hipparchia.config['DEFAULTMAXRESULTS']))
		session['morphtables'] = True
		session['morphdialects'] = True
		session['morphduals'] = True
		session['morphemptyrows'] = True
		session['morphfinite'] = True
		session['morphimper'] = True
		session['morphinfin'] = True
		session['morphpcpls'] = True
		session['nearestneighborsquery'] = False
		session['nearornot'] = 'near'
		session['onehit'] = hipparchia.config['DEFAULTONEHIT']
		session['papyruscorpus'] = corpusisonandavailable('papyruscorpus')
		session['principleparts'] = hipparchia.config['FINDPRINCIPLEPARTS']
		session['proximity'] = '1'
		session['psgexclusions'] = list()
		session['psgselections'] = list()
		session['quotesummary'] = hipparchia.config['DEFAULTSUMMARIZELEXICALQUOTES']
		session['searchscope'] = 'lines'
		session['searchinsidemarkup'] = hipparchia.config['SEARCHMARKEDUPLINE']
		session['semanticvectorquery'] = False
		session['sensesummary'] = hipparchia.config['DEFAULTSUMMARIZELEXICALSENSES']
		session['sentencesimilarity'] = False
		session['simpletextoutput'] = hipparchia.config['SIMPLETEXTOUTPUT']
		session['showwordcounts'] = hipparchia.config['SHOWGLOBALWORDCOUNTS']
		session['sortorder'] = hipparchia.config['DEFAULTSORTORDER']
		session['spuria'] = hipparchia.config['DEFAULTSPURIA']
		session['suppresscolors'] = hipparchia.config['SUPPRESSCOLORS']
		session['tensorflowgraph'] = False
		session['topicmodel'] = False
		session['varia'] = hipparchia.config['DEFAULTVARIA']
		session['vdim'] = hipparchia.config['VECTORDIMENSIONS']
		session['vwindow'] = hipparchia.config['VECTORWINDOW']
		session['viterat'] = hipparchia.config['VECTORTRAININGITERATIONS']
		session['vminpres'] = hipparchia.config['VECTORMINIMALPRESENCE']
		session['vdsamp'] = hipparchia.config['VECTORDOWNSAMPLE']
		session['vcutloc'] = hipparchia.config['VECTORDISTANCECUTOFFLOCAL']
		session['vcutneighb'] = hipparchia.config['VECTORDISTANCECUTOFFNEARESTNEIGHBOR']
		session['vcutlem'] = hipparchia.config['VECTORDISTANCECUTOFFLEMMAPAIR']
		session['vnncap'] = hipparchia.config['NEARESTNEIGHBORSCAP']
		session['vsentperdoc'] = hipparchia.config['SENTENCESPERDOCUMENT']
		session['ldamaxfeatures'] = hipparchia.config['LDAMAXFEATURES']
		session['ldacomponents'] = hipparchia.config['LDACOMPONENTS']
		session['ldamaxfreq'] = hipparchia.config['LDAMAXFREQ']
		session['ldaminfreq'] = hipparchia.config['LDAMINFREQ']
		session['ldaiterations'] = hipparchia.config['LDAITERATIONS']
		session['ldamustbelongerthan'] = hipparchia.config['LDAMUSTBELONGERTHAN']
		session['wkexclusions'] = list()
		session['wkgnexclusions'] = list()
		session['wkgnselections'] = list()
		session['wkselections'] = list()
		session['wlocexclusions'] = list()
		session['wlocselections'] = list()
		session['xmission'] = 'Any'
		session['zaplunates'] = hipparchia.config['RESTOREMEDIALANDFINALSIGMA']
		convertyesnototruefalse()
		session.modified = True
	return


def convertyesnototruefalse():
	"""

	anything that is y/n in the config file needs to be t/f in the session

	:return:
	"""

	trueorfalse = [
		'authorssummary',
		'bracketangled',
		'bracketcurly',
		'bracketround',
		'bracketsquare',
		'christiancorpus',
		'collapseattic',
		'cosdistbylineorword',
		'cosdistbysentence',
		'debugdb',
		'debughtml',
		'debuglex',
		'debugparse',
		'greekcorpus',
		'headwordindexing',
		'incerta',
		'indexbyfrequency',
		'indexskipsknownwords',
		'inscriptioncorpus',
		'latincorpus',
		'morphdialects',
		'morphduals',
		'morphemptyrows',
		'morphimper',
		'morphinfin',
		'morphfinite',
		'morphpcpls',
		'morphtables',
		'nearestneighborsquery',
		'onehit',
		'papyruscorpus',
		'principleparts',
		'quotesummary',
		'searchinsidemarkup',
		'semanticvectorquery',
		'sensesummary',
		'sentencesimilarity',
		'showwordcounts',
		'simpletextoutput',
		'spuria',
		'suppresscolors',
		'topicmodel',
		'varia',
		'zaplunates',
	]

	for k in session.keys():
		if k in trueorfalse and session[k] in ['yes', 'no']:
			if session[k] == 'yes':
				session[k] = True
			else:
				session[k] = False

	session.modified = True

	return
