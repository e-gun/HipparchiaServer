# -*- coding: utf-8 -*-
from multiprocessing import Process, Manager

from server import hipparchia
from server.dbsupport.dbfunctions import setconnection, grabonelinefromwork, dblineintolineobject, makeablankline
from server.hipparchiaclasses import MPCounter
from server.searching.searchfunctions import concordancelookup
from server.textsandconcordnaces.textandconcordancehelperfunctions import concordancesorter, findwordsinaline


def compilewordlists(worksandboundaries, cursor):
	"""
	grab and return lots of lines
	this is very generic
	typical uses are
		one work + a line range (which may or may not be the whole work: {'work1: (start,stop)}
		multiple (whole) works: {'work1': (start,stop), 'work2': (start,stop), ...}
	but you could one day use this to mix-and-match:
		a concordance of Thuc + Hdt 3 + all Epic...
	this is, you could use aocompileauthorandworklist() to feed this function
	the resulting concorances would be massive
	
	:param worksandboundaries:
	:param cursor:
	:return:
	"""
	lineobjects = []
	
	for w in worksandboundaries:
		query = 'SELECT * FROM ' + w + ' WHERE (index >= %s AND index <= %s)'
		data = (worksandboundaries[w][0], worksandboundaries[w][1])
		cursor.execute(query, data)
		lines = cursor.fetchall()
		
		for l in lines:
			lineobjects.append(dblineintolineobject(w, l))
	
	return lineobjects


def buildconcordancefromwork(cdict, cursor):
	"""
	speed notes
		buildconcordancefromconcordance() seemed ineffecient for small chunks: it was; but it is also a lot slower for whole works...
		single threaded buildconcordancefromwork() is 3-4x faster than mp buildconcordancefromconcordance()
		a mp version of buildconcordancefromwork() is 50% *slower* than mp buildconcordancefromconcordance()
	top speed seems to be a single thread diving into a work and building the concordance line by line
	
	cdict = {wo.universalid: (startline, endline)}
	
	the ultimate output needs to look like
		(word, count, citations)
	:param work:
	:param startline:
	:param endline:
	:param cursor:
	:return:
	"""
	
	lineobjects = compilewordlists(cdict, cursor)
	
	#concordancedict = mpsingleworkfromworkconcordancedispatch(work, lineobjects)
	concordancedict = linesintoconcordance(lineobjects)
	# now you are looking at: { wordA: [(workid1, index1, locus1), (workid2, index2, locus2),..., wordB: ...]}
	
	unsortedoutput = []

	# test if you only compiled from a single author:
	onework = True
	testlist = [x[0][0] for x in concordancedict.values()]
	if len(set(testlist)) != 1:
		onework = False
	
	for c in concordancedict.keys():
		hits = concordancedict[c]
		count = str(len(hits))
		hits = sorted(hits)
		if onework == True:
			hits = [h[2] for h in hits]
			loci = ', '.join(hits)
		else:
			previouswork = hits[0][0]
			loci = '<span class="work">'+previouswork[6:10] + '</span>: '
			for hit in hits:
				if hit[0] == previouswork:
					loci += hit[2] + ', '
				else:
					loci = loci[:-2] + '; '
					previouswork = hit[0]
					loci += '<span class="work">'+previouswork[6:10] + '</span>: '
					loci += hit[2] + ', '
			loci = loci[:-2]
		
		unsortedoutput.append((c, count, loci))
	
	output = concordancesorter(unsortedoutput)
	
	return output


def linesintoconcordance(lineobjects):
	"""
	generate the condordance dictionary:
		{ wordA: [(workid1, index1, locus1), (workid2, index2, locus2),..., wordB: ...]}

	:return:
	"""
	
	defaultwork = lineobjects[0].wkuinversalid
	
	concordance = {}
	previous = makeablankline(defaultwork, lineobjects[0].index - 1)
	
	while len(lineobjects) > 0:
		try:
			line = lineobjects.pop()
		except:
			line = makeablankline(defaultwork, -1)
		
		if line.index != -1:
			# find all of the words in the line
			words = findwordsinaline(line.contents)
			# deal with the hyphens issue
			if previous.hyphenated['accented'] != '':
				words = words[1:]
			if line.hyphenated['accented'] != '':
				words = words[:-1] + [line.hyphenated['accented']]
			words = list(set(words))
			words[:] = [x.lower() for x in words]
			for w in words:
				try:
					# to forestall the problem of sorting the citation values later, include the index now
					# sp variant:
					concordance[w].append((line.wkuinversalid, line.index, line.locus()))
					# concordance[w].append() seems to have race condition problems in mp land: you will end up with 1 copy of each word
					# mp variant:
					# concordance[w] = concordance[w] + [(line.wkuinversalid, line.index, line.locus())]
				except:
					concordance[w] = [(line.wkuinversalid, line.index, line.locus())]
		previous = line
	
	return concordance



# slated for removal

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
	jobs = [
		Process(target=mpconcordanceworker, args=(work, concordancewords, output, memory, commitcount, startandstop))
		for i in range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()
	
	return output


def mpsingleworkfromworkconcordancedispatch(work, lineobjects):
	"""
	buildconcordancefromwork() will send a collection of lines: dispatch them
	the ultimate output needs to look like
		(word, count, citations)
	the intermediate output that this will generate is:
		concordance = { wordA: [(index1, locus1), (index2, locus2),..., wordB: ...]}
	:param collectionoflines:
	:return:
	"""
	
	manager = Manager()
	concordance = manager.dict()
	lines = manager.list(lineobjects)
	
	previousfinder = {}
	previousfinder[lineobjects[0].index - 1] = makeablankline(work, lineobjects[0].index - 1)
	for l in lineobjects:
		previousfinder[l.index] = l
	previouslines = manager.dict(previousfinder)
	
	workers = hipparchia.config['WORKERS']
	jobs = [
		Process(target=mpconcorfromworkdanceworker, args=(work, lines, previouslines, concordance))
		for i in range(workers)]
	for j in jobs: j.start()
	for j in jobs: j.join()
	
	return concordance


def mpconcorfromworkdanceworker(work, lines, previouslines, concordance):
	"""
	generate the condordance dictionary:
		{ wordA: [(index1, locus1), (index2, locus2),..., wordB: ...]}

	:return:
	"""
	
	while len(lines) > 0:
		try:
			line = lines.pop()
		except:
			line = makeablankline(work, -1)
		
		if line.index != -1:
			# find all of the words in the line
			words = findwordsinaline(line.contents)
			# deal with the hyphens issue
			previous = previouslines[line.index - 1]
			if previous.hyphenated['accented'] != '':
				words = words[1:]
			if line.hyphenated['accented'] != '':
				words = words[:-1] + [line.hyphenated['accented']]
			words = list(set(words))
			words[:] = [x.lower() for x in words]
			
			for w in words:
				try:
					# to forestall the problem of sorting the citation values later, include the index now
					# concordance[w].append() seems to have race condition problems in mp land: you will end up with 1 copy of each word
					concordance[w] = concordance[w] + [(line.index, line.locus())]
				except:
					concordance[w] = [(line.index, line.locus())]
	
	return concordance


def multipleworkwordlist(listofworks, cursor):
	"""
	give me an author, i will give you all the words he uses
	:param authorobject:
	:param cursor:
	:return: {'word1': ['workN', lineN], 'word2': ['workM', lineM], 'word3': ['workN', lineN], ...}
	"""
	
	works = []
	for w in listofworks:
		works.append(w + '_conc')
	
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


def buildconcordancefromconcordance(work, startline, endline, cursor):
	"""
	build a concordance; mp aware, but the bottleneck is the db itself: you can go 2x faster here but 3-4x faster in a search
	at the moment supplenda like '⟪marcent⟫' will wind up at the end under '⟪⟫': is this a good or a bad thing?
	and yet buildconcordancefromwork() is way faster than this version: it seems DB calls are very costly indeed
	:param work:
	:param mode:
	:param cursor:
	:return:
	"""
	
	concdb = work + '_conc'
	
	query = 'SELECT word, loci FROM ' + concdb
	cursor.execute(query)
	results = cursor.fetchall()
	concordancewords = results
	
	unsortedoutput = []
	if len(concordancewords) > 0:
		unsortedoutput = mpsingleworkconcordancedispatch(work, concordancewords, startline, endline)
	
	return unsortedoutput


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
		try:
			result = concordancewords.pop()
		except:
			result = ('null', '-1')
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
	jobs = [Process(target=mpmultipleworkconcordanceworker, args=(wordset, unsortedwords, output, memory, commitcount))
	        for i in range(workers)]
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
		try:
			word = unsortedwords.pop()
		except:
			word = None
		
		if word is not None:
			count = 0
			citations = []
			for hit in range(0, len(wordset[word])):
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


