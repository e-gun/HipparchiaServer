import re

from flask import session

from server.dbsupport.dbfunctions import setconnection, makeablankline, dblineintolineobject
from server.searching.searchformatting import cleansearchterm
from server.searching.searchfunctions import substringsearch, simplesearchworkwithexclusion, whereclauses, \
	lookoutsideoftheline


def phrasesearch(searchphrase, cursor, wkid, authors, activepoll):
	"""
	a whitespace might mean things are on a new line
	note how horrible something like και δη και is: you will search και first and then...

	:param searchphrase:
	:param cursor:
	:param authorobject:
	:param worknumber:
	:return: db lines that match the search criterion
	"""
	searchphrase = cleansearchterm(searchphrase)
	searchterms = searchphrase.split(' ')
	searchterms = [x for x in searchterms if x]
	
	longestterm = searchterms[0]
	for term in searchterms:
		if len(term) > len(longestterm):
			longestterm = term
	
	if 'x' not in wkid:
		hits = substringsearch(longestterm, cursor, wkid, authors)
	else:
		wkid = re.sub('x', 'w', wkid)
		hits = simplesearchworkwithexclusion(longestterm, wkid, authors, cursor)
	
	fullmatches = []
	for hit in hits:
		phraselen = len(searchphrase.split(' '))
		wordset = lookoutsideoftheline(hit[0], phraselen - 1, wkid, cursor)
		if session['accentsmatter'] == 'N':
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


def shortphrasesearch(count, hits, searchphrase, workstosearch, authors, activepoll):
	"""
	mp aware search for runs of short words
	:return:
	"""
	dbconnection = setconnection('autocommit')
	curs = dbconnection.cursor()

	
	while len(workstosearch) > 0 and count.value <= int(session['maxresults']):
		try:
			w = workstosearch.pop()
			activepoll.remain(len(workstosearch))
		except: w = (-1, 'gr0000w000')
		index = w[0]
		if index != -1:
			matchobjects = []
			wkid = w[1]
			# echeck for exclusions
			if re.search(r'x', wkid) is not None:
				wkid = re.sub(r'x', 'w', wkid)
				restrictions = []
				for p in session['psgexclusions']:
					if wkid in p:
						restrictions.append(whereclauses(p, '<>', authors))
			
				whr = ''
				data = []
				for r in restrictions:
					for i in range(0, len(r)):
						whr += r[i][0] + 'OR '
						data.append(r[i][1])
					# drop the trailing ' OR'
					whr = whr[0:-4] + ') AND ('
				# drop the trailing ') AND ('
				whr = whr[0:-6]
			
				query = 'SELECT * FROM ' + wkid[0:10] + ' WHERE ('+ whr + ' ORDER BY index ASC'
				curs.execute(query, tuple(data))
			else:
				if '_AT_' not in wkid:
					wkid = re.sub(r'x', 'w', wkid)
					query = 'SELECT * FROM ' + wkid + ' ORDER BY index'
					curs.execute(query)
				else:
					whr = ''
					data = []
					w = whereclauses(wkid, '=', authors)
					for i in range(0, len(w)):
						whr += 'AND (' + w[i][0] + ') '
						data.append(w[i][1])
					# strip extra ANDs
					whr = whr[4:]
					wkid = re.sub(r'x', 'w', wkid)
					query = 'SELECT * FROM ' + wkid[0:10] + ' WHERE '+whr+' ORDER BY index'
					curs.execute(query, data)
					
			fulltext = curs.fetchall()
			
			previous = makeablankline(wkid, -1)
			lineobjects = []
			for dbline in fulltext:
				lineobjects.append(dblineintolineobject(wkid, dbline))
			lineobjects.append(makeablankline(wkid, -9999))
			del fulltext
			
			if session['accentsmatter'] == 'N':
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
						if session['accentsmatter'] == 'N':
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
					
			# note that each work generates one set of matchobjects (but they are internally sorted)
			hits[index] = (wkid, matchobjects)
	
	curs.close()
	del dbconnection
	
	return hits