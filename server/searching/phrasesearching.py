# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

from flask import session

from server.dbsupport.dbfunctions import setconnection, makeablankline, dblineintolineobject
from server.searching.searchformatting import cleansearchterm
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion, whereclauses, \
	lookoutsideoftheline


def phrasesearch(leastcommon, searchphrase, cursor, wkid, authorswheredict, activepoll):
	"""
	a whitespace might mean things are on a new line
	note how horrible something like και δη και is: you will search και first and then...
	that's why we have shortphrasesearch() which is mighty slow too

	:param searchphrase:
	:param cursor:
	:param wkid:
	:param authorswheredict:
	:param activepoll:
	:return:
	"""

	if 'x' not in wkid:
		hits = substringsearch(leastcommon, cursor, wkid, authorswheredict)
	else:
		wkid = re.sub('x', 'w', wkid)
		hits = simplesearchworkwithexclusion(leastcommon, wkid, authorswheredict, cursor)
	
	fullmatches = []
	for hit in hits:
		phraselen = len(searchphrase.split(' '))
		wordset = lookoutsideoftheline(hit[0], phraselen - 1, wkid, cursor)
		if session['accentsmatter'] == 'no':
			wordset = re.sub(r'[\.\?\!;:,·’]', r'', wordset)
		else:
			# the difference is in the apostrophe: δ vs δ’
			wordset = re.sub(r'[\.\?\!;:,·]', r'', wordset)

		if session['nearornot'] == 'T' and re.search(searchphrase, wordset) is not None:
			fullmatches.append(hit)
			activepoll.addhits(1)
		elif session['nearornot'] == 'F' and re.search(searchphrase, wordset) is None:
			fullmatches.append(hit)
			activepoll.addhits(1)
	
	return fullmatches


def shortphrasesearch(count, foundlineobjects, searchphrase, workstosearch, authorswheredict, activepoll):
	"""
	mp aware search for runs of short words

	workstosearch:
		['lt0400', 'lt0022', 'lt0914w001_AT_1', 'lt0474w001']

	authorswheredict: [every author that needs to have a where-clause built because you asked for an '_AT_']
		{'lt0914': <server.hipparchiaclasses.dbAuthor object at 0x108b5d8d0>}

	seeking:
		'si tu non'

	:return:
	"""
	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	while len(workstosearch) > 0 and count.value <= int(session['maxresults']):
		try:
			wkid = workstosearch.pop()
			activepoll.remain(len(workstosearch))
		except:
			wkid = 'gr0000w000'

		if wkid != 'gr0000w000':
			matchobjects = []
			db = wkid[0:6]
			# check for exclusions
			if re.search(r'x', wkid) is not None:
				wkid = re.sub(r'x', 'w', wkid)
				restrictions = []
				for p in session['psgexclusions']:
					if wkid in p:
						restrictions.append(whereclauses(p, '<>', authorswheredict))
			
				whr = ''
				data = [wkid[0:10]]

				for r in restrictions:
					for i in range(0, len(r)):
						whr += r[i][0] + 'OR '
						data.append(r[i][1])
					# drop the trailing ' OR'
					whr = whr[0:-4] + ') AND ('
				# drop the trailing ') AND ('
				whr = whr[0:-6]
			
				query = 'SELECT * FROM ' + db + ' WHERE ( wkuniversalid = %s) AND ('+ whr + ' ORDER BY index ASC'
				curs.execute(query, tuple(data))
			else:
				if '_AT_' not in wkid:
					wkid = re.sub(r'x', 'w', wkid)
					if len(wkid) == 6:
						# we are searching the whole author
						data = (wkid+'%',)
					else:
						# we are searching an individual work
						data = (wkid[0:10],)
					query = 'SELECT * FROM ' + db + ' WHERE ( wkuniversalid LIKE %s) ORDER BY index'
					curs.execute(query, data)
				else:
					whr = ''
					data = [wkid[0:10]]
					w = whereclauses(wkid, '=', authorswheredict)
					for i in range(0, len(w)):
						whr += 'AND (' + w[i][0] + ') '
						data.append(w[i][1])
					# strip extra ANDs
					whr = whr[4:]
					wkid = re.sub(r'x', 'w', wkid)
					query = 'SELECT * FROM ' + db + ' WHERE ( wkuniversalid = %s) AND ( '+whr+' ORDER BY index'
					curs.execute(query, data)

			fulltext = curs.fetchall()
			
			previous = makeablankline(wkid, -1)
			lineobjects = [dblineintolineobject(f) for f in fulltext]
			lineobjects.append(makeablankline(wkid, -9999))
			del fulltext
			
			if session['accentsmatter'] == 'no':
				acc = 'stripped'
			else:
				acc = 'accented'
			
			searchphrase = cleansearchterm(searchphrase)
			searchterms = searchphrase.split(' ')
			searchterms = [x for x in searchterms if x]
			contextneeded = len(searchterms) - 1

			for i in range(0, len(lineobjects) - 1):
				if count.value <= int(session['maxresults']):
					if previous.hashyphenated == True and lineobjects[i].hashyphenated == True:
						core = lineobjects[i].allbutfirstandlastword(acc)
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[1:contextneeded + 1]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					elif previous.hashyphenated == False and lineobjects[i].hashyphenated == True:
						core = lineobjects[i].allbutlastword(acc)
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[0:contextneeded]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					elif previous.hashyphenated == True and lineobjects[i].hashyphenated == False:
						core = lineobjects[i].allbutfirstword(acc)
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[0:contextneeded]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					else:
						# previous.hashyphenated == False and lineobjects[i].hashyphenated == False
						if session['accentsmatter'] == 'no':
							core = lineobjects[i].stripped
						else:
							core = lineobjects[i].unformattedline()
						try:
							supplement = lineobjects[i + 1].wordlist(acc)[0:contextneeded]
						except:
							supplement = lineobjects[i + 1].wordlist(acc)
					
					try:
						prepend = previous.wordlist(acc)[-1 * contextneeded:]
					except:
						prepend = previous.wordlist(acc)
					
					prepend = ' '.join(prepend)
					supplement = ' '.join(supplement)
					searchzone = prepend + ' ' + core + ' ' + supplement
					searchzone = re.sub(r'\s\s', r' ', searchzone)
					
					if re.search(searchphrase, searchzone) is not None:
						count.increment(1)
						activepoll.sethits(count.value)
						matchobjects.append(lineobjects[i])
					previous = lineobjects[i]

			foundlineobjects += matchobjects


	curs.close()
	del dbconnection
	
	return foundlineobjects

