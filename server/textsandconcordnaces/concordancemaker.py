# -*- coding: utf-8 -*-
from multiprocessing import Process, Manager

from server import formatting_helper_functions
from server import hipparchia
from server.dbsupport.dbfunctions import setconnection, grabonelinefromwork, dblineintolineobject
from server.hipparchiaclasses import MPCounter
from server.searching.searchfunctions import concordancelookup
from server.textsandconcordnaces.textandconcordancehelperfunctions import concordancesorter


def multipleworkwordlist(listofworks, cursor):
	"""
	give me an author, i will give you all the words he uses
	:param authorobject:
	:param cursor:
	:return: {'word1': ['workN', lineN], 'word2': ['workM', lineM], 'word3': ['workN', lineN], ...}
	"""

	works = []
	for w in listofworks:
		works.append(w+'_conc')
	
	# gather vocab lists
	wordset = {}
	for w in works:
		query = 'SELECT word, loci FROM ' + w
		cursor.execute(query)
		results = cursor.fetchall()
		for item in results:
			if item[0] not in wordset:
				wordset[item[0]] = [[w, item[1]]]
			else:
				wordset[item[0]].append([w, item[1]])
				
	return wordset
	
	
def buildconcordance(work, startline, endline, cursor):
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
	

	concdb = work+'_conc'
	
	query = 'SELECT word, loci FROM ' + concdb
	cursor.execute(query)
	results = cursor.fetchall()
	concordancewords = results
		
	output = []
	if len(concordancewords) > 0:
		unsortedoutput = mpsingleworkconcordancedispatch(work, concordancewords, startline, endline)
		output = concordancesorter(unsortedoutput)
	
	return output


def mpsingleworkconcordancedispatch(work, concordancewords, startline, endline):
	"""
	a multiprocessor aware version of the concordance lookup routine
	:param work: a work looks like 'gr0032w001_conc'
	:param concordancewords: for a mere work it is word + locations; looks like ('ὥρμων', '5701 6830')
	:return:
	"""
	
	manager = Manager()
	output = manager.list()
	startandstop = manager.list([startline, endline])
	memory = manager.dict()
	concordancewords = manager.list(concordancewords)
	commitcount = MPCounter()
	
	workers = hipparchia.config['WORKERS']
	jobs = [Process(target=mpconcordanceworker, args=(work, concordancewords, output, memory, commitcount, startandstop)) for i in range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()
	
	return output


def mpconcordanceworker(work, concordancewords, output, memory, commitcount, startandstop):
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
		citations = []
		word = result[0]
		loci = result[1].split(' ')
		count = 0
		for linenumber in loci:
			if int(linenumber) >= startandstop[0] and int(linenumber) <= startandstop[1]:
				count += 1
				if linenumber not in memory:
					line = grabonelinefromwork(work, linenumber, curs)
					lo = dblineintolineobject(work, line)
					citations.append(lo.locus())
					commitcount.increment()
					if commitcount.value % 5000 == 0:
						dbconnection.commit()
					memory[linenumber] = lo.locus()
				else:
					citations.append(memory[linenumber])
		if len(citations) > 0:
			citations = ', '.join(citations)
			output.append((word, str(count), citations))

	curs.close()
	del dbconnection
	
	return output


def mpmultipleworkcordancedispatch(wordset):
	"""
	a multiprocessor aware version of the concordance lookup routine designed for whole authors, but could be used
	with lists derived from multiple authors or segments within authors since you have univesalids here
	:param wordset: itmes look like {word1: [[w001, 100], [w001,222], [w002,555]], word2: [[w005,666]]}
	:param sortedwords: [word1, word2, ...]
	:return:
	"""
	
	unsortedwords = list(wordset)
	manager = Manager()
	output = manager.list()
	wordset = manager.dict(wordset)
	unsortedwords = manager.list(unsortedwords)
	memory = manager.dict()
	commitcount = MPCounter()
	
	workers = hipparchia.config['WORKERS']
	jobs = [Process(target=mpmultipleworkconcordanceworker, args=(wordset, unsortedwords, output, memory, commitcount)) for i in range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()
	
	return output


def mpmultipleworkconcordanceworker(wordset, unsortedwords, output, memory, commitcount):
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

