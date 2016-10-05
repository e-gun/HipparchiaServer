# -*- coding: utf-8 -*-
from multiprocessing import Process, Manager
from server import formatting_helper_functions
from server.searching.searchfunctions import concordancelookup
from server.formatting_helper_functions import polytonicsort
from server.dbsupport.dbfunctions import setconnection
from server.hipparchiaclasses import MPCounter
from server import hipparchia


def buildconcordance(work, mode, cursor):
	"""
	build a concordance; mp aware, but the bottleneck is the db itself: you can go 2x faster here but 3-4x faster in a search
	modes:
		0 - of this work
		1 - of words unique to this work in this author
		2 - of this author
	at the moment supplenda like '⟪marcent⟫' will wind up at the end under '⟪⟫': is this a good or a bad thing?
	:param work:
	:param mode:
	:param cursor:
	:return:
	"""
	
	concordancewords = []
	
	if mode == 0:
		query = 'SELECT word, loci FROM ' + work
		cursor.execute(query)
		results = cursor.fetchall()
		concordancewords = results
	if mode == 1:
		# find all works
		query = 'SELECT universalid FROM works WHERE universalid LIKE %s'
		data = (work[0:7]+'%',)
		cursor.execute(query,data)
		results = cursor.fetchall()
		otherworks = []
		for r in results:
			if r[0]+'_conc' != work:
				otherworks.append(r[0]+'_conc')

		# gather their vocab lists
		otherwords = []
		for other in otherworks:
			query = 'SELECT word FROM '+other
			cursor.execute(query)
			results = cursor.fetchall()
			for r in results:
				otherwords.append(r[0])
		otherwords = list(set(otherwords))

		# collect this work
		query = 'SELECT word, loci FROM ' + work
		cursor.execute(query)
		results = cursor.fetchall()
		
		# drop dupes
		uniquewords = []
		for word in results:
			if word[0] in otherwords:
				pass
			else:
				uniquewords.append(word)
		concordancewords = uniquewords
	
	output = []
	if len(concordancewords) > 0:
		unsortedoutput = mpsingleworkconcordancedispatch(work, concordancewords)
		output = concordancesorter(unsortedoutput)
	
	# note that you should zip right here if mode==2 because in that case concordancewords = [] and output remains []
	if mode == 2:
		# find all works
		query = 'SELECT universalid FROM works WHERE universalid LIKE %s'
		data = (work[0:7]+'%',)
		cursor.execute(query,data)
		results = cursor.fetchall()
		works = []
		for r in results:
			works.append(r[0] + '_conc')
		
		# gather vocab lists
		wordset = {}
		for w in works:
			query = 'SELECT word, loci FROM ' + w
			cursor.execute(query)
			results = cursor.fetchall()
			for item in results:
				if item[0] not in wordset:
					wordset[item[0]] = [[w,item[1]]]
				else:
					wordset[item[0]].append([w,item[1]])
		
		unsortedwords = list(wordset)
		unsortedoutput = mpauthorconcordancedispatch(wordset,unsortedwords)
		output = concordancesorter(unsortedoutput)
		
	return output


def mpsingleworkconcordancedispatch(work, concordancewords):
	"""
	a multiprocessor aware version of the concordance lookup routine
	:param work: a work looks like 'gr0032w001_conc'
	:param concordancewords: for a mere work it is word + locations; looks like ('ὥρμων', '5701 6830')
	:return:
	"""
	
	manager = Manager()
	output = manager.list()
	memory = manager.dict()
	concordancewords = manager.list(concordancewords)
	commitcount = MPCounter()
	
	workers = hipparchia.config['WORKERS']
	jobs = [Process(target=mpconcordanceworker, args=(work, concordancewords, output, memory, commitcount)) for i in range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()
	
	return output


def mpconcordanceworker(work, concordancewords, output, memory, commitcount):
	"""
	a multiprocessors aware function that hands off bits of a concordance search to multiple searchers
	the memory function is supposed to save you the trouble of looking up the same line more than once
	this offers a radical speedup in someone like thucydides
	:param
	:return: output is a list of items of the form [word, count, citations]
	"""
	
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()
	
	while len(concordancewords) > 0:
		try: result = concordancewords.pop()
		except: result = ('null', '-1')
		# a work looks like 'gr0032w001_conc', hence work[:-5] below
		# a result looks like ('ὥρμων', '5701 6830')
		citations = []
		word = result[0]
		loci = result[1].split(' ')
		count = str(len(loci))
		for locus in loci:
			if locus not in memory:
				citation = concordancelookup(work[:-5], locus, curs)
				citations.append(citation)
				commitcount.increment()
				if commitcount.value % 5000 == 0:
					dbconnection.commit()
				memory[locus] = citation
			else:
				citations.append(memory[locus])
		citations = ', '.join(citations)
		output.append((word, count, citations))

	curs.close()
	del dbconnection
	
	return output


def mpauthorconcordancedispatch(wordset, unsortedwords):
	"""
	a multiprocessor aware version of the concordance lookup routine designed for whole authors
	:param wordset: itmes look like {word1: [[w001, 100], [w001,222], [w002,555]], word2: [[w005,666]]}
	:param sortedwords: [word1, word2, ...]
	:return:
	"""
	
	manager = Manager()
	output = manager.list()
	wordset = manager.dict(wordset)
	unsortedwords = manager.list(unsortedwords)
	memory = manager.dict()
	commitcount = MPCounter()
	
	workers = hipparchia.config['WORKERS']
	jobs = [Process(target=mpauthorconcordanceworker, args=(wordset, unsortedwords, output, memory, commitcount)) for i in range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()
	
	output
	
	return output


def mpauthorconcordanceworker(wordset, unsortedwords, output, memory, commitcount):
	"""
	a multiprocessors aware function that hands off bits of a concordance search to multiple searchers
	:param
	:return:
	"""
	
	dbconnection = setconnection('not_autocommit')
	curs = dbconnection.cursor()
	
	while len(unsortedwords) > 0:
		try: word = unsortedwords.pop()
		except: word = None
		
		if word is not None:
			count = 0
			citations = []
			for hit in range(0,len(wordset[word])):
				work = wordset[word][hit][0]
				loci = wordset[word][hit][1].split(' ')
				count += len(loci)
				wcitations = []
				for locus in loci:
					if locus not in memory:
						citation = concordancelookup(work[:-5], locus, curs)
						wcitations.append(citation)
						commitcount.increment()
						if commitcount.value % 5000 == 0:
							dbconnection.commit()
						memory[locus] = citation
					else:
						wcitations.append(memory[locus])
				wcitations = ', '.join(wcitations)
				wcitations = work[6:10] + ': ' + wcitations
				citations.append(wcitations)
			citations = '; '.join(citations)
			output.append([word, str(count), citations])

	curs.close()
	del dbconnection
	
	return output


def concordancesorter(unsortedoutput):
	"""
	you can't sort the list and then send it to a mp function where it will get unsorted
	so you have to jump through a hoop before you can jump through a hoop:
	make keys -> polytonicsort keys -> use keys to sort the list
	
	:param unsortedoutput:
	:return:
	"""
	
	# now you sort
	sortkeys = []
	outputdict = {}
	for o in unsortedoutput:
		sortkeys.append(o[0])
		outputdict[o[0]] = o
	
	sortkeys = polytonicsort(sortkeys)
	del unsortedoutput
	
	sortedoutput = []
	for k in sortkeys:
		sortedoutput.append(outputdict[k])
	
	return sortedoutput

#
# slated for removal
#

def singlethreadedbuildconcordance(work, mode, cursor):
	"""
	build a concordance
	modes:
		0 - of this work
		1 - of words unique to this work in this author
		2 - of this author
	:param work:
	:param mode:
	:param cursor:
	:return:
	"""
	
	concordancewords = []
	
	if mode == 0:
		query = 'SELECT word, loci FROM ' + work
		cursor.execute(query)
		results = cursor.fetchall()
		concordancewords = results
	if mode == 1:
		# find all works
		query = 'SELECT universalid FROM works WHERE universalid LIKE %s'
		data = (work[0:7] + '%',)
		cursor.execute(query, data)
		results = cursor.fetchall()
		otherworks = []
		for r in results:
			if r[0] + '_conc' != work:
				otherworks.append(r[0] + '_conc')
		
		# gather their vocab lists
		otherwords = []
		for other in otherworks:
			query = 'SELECT word FROM ' + other
			cursor.execute(query)
			results = cursor.fetchall()
			for r in results:
				otherwords.append(r[0])
		otherwords = list(set(otherwords))
		
		# collect this work
		query = 'SELECT word, loci FROM ' + work
		cursor.execute(query)
		results = cursor.fetchall()
		
		# drop dupes
		uniquewords = []
		for word in results:
			if word[0] in otherwords:
				pass
			else:
				uniquewords.append(word)
		concordancewords = uniquewords
	
	output = []
	for result in concordancewords:
		citations = []
		loci = result[1].split(' ')
		count = str(len(loci))
		# citations = mpconcordancedispatch(work, loci)
		for locus in loci:
			citation = concordancelookup(work[:-5], locus, cursor)
			citations.append(citation)
		citations = ', '.join(citations)
		output.append([result[0], count, citations])
	
	# note that you should zip right here if mode==2 because in that case concordancewords = [] and output remains []
	if mode == 2:
		# find all works
		query = 'SELECT universalid FROM works WHERE universalid LIKE %s'
		data = (work[0:7] + '%',)
		cursor.execute(query, data)
		results = cursor.fetchall()
		works = []
		for r in results:
			works.append(r[0] + '_conc')
		
		# gather vocab lists
		wordset = {}
		for w in works:
			# time to run through this is 0.15s for Ovid (who takes 142s to build): the bottleneck is in the monster number of calls to concordancelookup()
			query = 'SELECT word, loci FROM ' + w
			cursor.execute(query)
			results = cursor.fetchall()
			for item in results:
				if item[0] not in wordset:
					wordset[item[0]] = [[w, item[1]]]
				else:
					wordset[item[0]].append([w, item[1]])
		
		unsortedwords = list(wordset)
		sortedwords = formatting_helper_functions.polytonicsort(unsortedwords)
		
		for word in sortedwords:
			count = 0
			citations = []
			for hit in range(0, len(wordset[word])):
				work = wordset[word][hit][0]
				loci = wordset[word][hit][1].split(' ')
				count += len(loci)
				wcitations = []
				for locus in loci:
					citation = concordancelookup(work[:-5], locus, cursor)
					wcitations.append(citation)
				wcitations = ', '.join(wcitations)
				wcitations = work[6:10] + ': ' + wcitations
				citations.append(wcitations)
			citations = '; '.join(citations)
			output.append([word, str(count), citations])
	
	return output

