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
		session['cosdistbysentence'] = 'no'
		session['cosdistbylineorword'] = 'no'
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
		session['indexskipsknownwords'] = 'no'
		session['inscriptioncorpus'] = corpusisonandavailable('inscriptioncorpus')
		session['latestdate'] = hipparchia.config['DEFAULTLATESTDATE']
		session['latincorpus'] = corpusisonandavailable('latincorpus')
		session['linesofcontext'] = int(hipparchia.config['DEFAULTLINESOFCONTEXT'])
		session['maxresults'] = str(int(hipparchia.config['DEFAULTMAXRESULTS']))
		session['morphtables'] = 'yes'
		session['morphdialects'] = 'yes'
		session['morphduals'] = 'yes'
		session['morphemptyrows'] = 'yes'
		session['morphfinite'] = 'yes'
		session['morphimper'] = 'yes'
		session['morphinfin'] = 'yes'
		session['morphpcpls'] = 'yes'
		session['nearestneighborsquery'] = 'no'
		session['nearornot'] = 'T'
		session['onehit'] = hipparchia.config['DEFAULTONEHIT']
		session['papyruscorpus'] = corpusisonandavailable('papyruscorpus')
		session['principleparts'] = hipparchia.config['FINDPRINCIPLEPARTS']
		session['proximity'] = '1'
		session['psgexclusions'] = list()
		session['psgselections'] = list()
		session['quotesummary'] = hipparchia.config['DEFAULTSUMMARIZELEXICALQUOTES']
		session['searchscope'] = 'L'
		session['searchinsidemarkup'] = hipparchia.config['SEARCHMARKEDUPLINE']
		session['semanticvectorquery'] = 'no'
		session['sensesummary'] = hipparchia.config['DEFAULTSUMMARIZELEXICALSENSES']
		session['sentencesimilarity'] = 'no'
		session['simpletextoutput'] = hipparchia.config['SIMPLETEXTOUTPUT']
		session['showwordcounts'] = hipparchia.config['SHOWGLOBALWORDCOUNTS']
		session['sortorder'] = hipparchia.config['DEFAULTSORTORDER']
		session['spuria'] = hipparchia.config['DEFAULTSPURIA']
		session['suppresscolors'] = hipparchia.config['SUPPRESSCOLORS']
		session['tensorflowgraph'] = 'no'
		session['topicmodel'] = 'no'
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
		session.modified = True
	return
