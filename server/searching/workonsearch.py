# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016
	License: GPL 3 (see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server.dbsupport.dbfunctions import setconnection
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion
from server.searching.phrasesearching import phrasesearch
from server.searching.proximitysearching import withinxlines, withinxwords

def workonsimplesearch(count, hits, seeking, searching, commitcount, authors, activepoll):
	"""
	a multiprocessors aware function that hands off bits of a simple search to multiple searchers
	you need to pick the right style of search for each work you search, though
	:param count:
	:param hits:
	:param seeking:
	:param searching:
	:return: a collection of hits
	"""
	
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()
	
	while len(searching) > 0 and count.value <= int(session['maxresults']):
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		# that's not supposed to happen with the pool, but somehow it does
		try:
			i = searching.pop()
			activepoll.remain(len(searching))
		except: i = (-1,'gr0000w000')
		commitcount.increment()
		if commitcount.value % 750 == 0:
			dbconnection.commit()
		wkid = i[1]
		index = i[0]
		if index != -1:
			if '_AT_' in wkid:
				hits[index] = (wkid, substringsearch(seeking, curs, wkid, authors))
			elif 'x' in wkid:
				wkid = re.sub('x', 'w', wkid)
				hits[index] = (wkid, simplesearchworkwithexclusion(seeking, wkid, authors, curs))
			else:
				hits[index] = (wkid, substringsearch(seeking, curs, wkid, authors))
				
			if len(hits[index][1]) == 0:
				del hits[index]
			else:
				count.increment(len(hits[index][1]))
				activepoll.addhits(len(hits[index][1]))
				
	dbconnection.commit()
	curs.close()
	del dbconnection
	
	return hits


def workonphrasesearch(hits, seeking, searching, commitcount, authors, activepoll):
	"""
	a multiprocessors aware function that hands off bits of a phrase search to multiple searchers
	you need to pick temporarily reassign max hits so that you do not stop searching after one item in the phrase hits the limit

	:param hits:
	:param seeking:
	:param searching:
	:return:
	"""
	tmp = session['maxresults']
	session['maxresults'] = 19999
	
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()
	
	while len(searching) > 0:
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		try:
			i = searching.pop()
			activepoll.remain(len(searching))
		except: i = (-1,'gr0001w001')
		commitcount.increment()
		if commitcount.value % 750 == 0:
			dbconnection.commit()
		wkid = i[1]
		index = i[0]
		hits[index] = (wkid, phrasesearch(seeking, curs, wkid, authors, activepoll))
		
	session['maxresults'] = tmp
	dbconnection.commit()
	curs.close()
	del dbconnection
	
	return hits


def workonproximitysearch(count, hits, seeking, proximate, searching, commitcount, authors, activepoll):
	"""
	a multiprocessors aware function that hands off bits of a proximity search to multiple searchers
	note that exclusions are handled deeper down in withinxlines() and withinxwords()
	:param count:
	:param hits:
	:param seeking:
	:param proximate:
	:param searching:
	:return: a collection of hits
	"""
	
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()
	
	if len(proximate) > len(seeking) and session['nearornot'] != 'F' and ' ' not in seeking and ' ' not in proximate:
		# look for the longest word first since that is probably the quicker route
		# but you cant swap seeking and proximate this way in a 'is not near' search without yielding the wrong focus
		tmp = proximate
		proximate = seeking
		seeking = tmp
	
	while len(searching) > 0 and count.value <= int(session['maxresults']):
		# pop rather than iterate lest you get several sets of the same results as each worker grabs the whole search pile
		# the pop() will fail if somebody else grabbed the last available work before it could be registered
		try:
			i = searching.pop()
			activepoll.remain(len(searching))
		except: i = (-1,'gr0001w001')
		commitcount.increment()
		if commitcount.value % 750 == 0:
			dbconnection.commit()
		wkid = i[1]
		index = i[0]
		if session['searchscope'] == 'L':
			hits[index] = (wkid, withinxlines(int(session['proximity']), seeking, proximate, curs, wkid, authors))
		else:
			hits[index] = (wkid, withinxwords(int(session['proximity']), seeking, proximate, curs, wkid, authors))
		
		if len(hits[index][1]) == 0:
			del hits[index]
		else:
			count.increment(len(hits[index][1]))
			activepoll.addhits(len(hits[index][1]))
	
	dbconnection.commit()
	curs.close()
	del dbconnection
	
	return hits