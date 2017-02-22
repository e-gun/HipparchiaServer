# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import asyncio
from multiprocessing import Pool
from server import hipparchia
from server.dbsupport.dbfunctions import dblineintolineobject, makeablankline
from server.formatting_helper_functions import cleanwords
from server.textsandconcordnaces.textandconcordancehelperfunctions import dictmerger



def compilewordlists(worksandboundaries, cursor):
	"""
	grab and return lots of lines
	this is very generic
	typical uses are
		one work + a line range (which may or may not be the whole work: {'work1: (start,stop)}
		multiple (whole) works: {'work1': (start,stop), 'work2': (start,stop), ...}
	but you could one day use this to mix-and-match:
		a concordance of Thuc + Hdt 3 + all Epic...
	this is, you could use compileauthorandworklist() to feed this function
	the resulting concorances would be massive
	
	:param worksandboundaries:
	:param cursor:
	:return:
	"""
	
	lineobjects = []
	
	for w in worksandboundaries:
		db = w[0:6]
		query = 'SELECT * FROM ' + db + ' WHERE (index >= %s AND index <= %s)'
		data = (worksandboundaries[w][0], worksandboundaries[w][1])
		cursor.execute(query, data)
		lines = cursor.fetchall()

		thiswork = [dblineintolineobject(l) for l in lines]
		lineobjects += thiswork

	return lineobjects


def buildconcordancefromwork(cdict, activepoll, cursor):
	"""
	speed notes
		a Manager() implementation was 50% slower than single-threaded: lock/unlock penalty on a shared dictionary
		single thread is quite fast: 52s for Eustathius, Commentarii ad Homeri Iliadem [1,099,422 wds]
		a Pool() is 2x as fast, but you cannot get polling data from inside the pool

	cdict = {wo.universalid: (startline, endline)}

	just caesar's bellum gallicum: cdict {'lt0448w001': (1, 6192)}
	all of casear's works: cdict {'lt0448w001': (1, 6192), 'lt0448w002': (6193, 10860), 'lt0448w003': (10861, 10891), 'lt0448w004': (10892, 10927), 'lt0448w005': (10928, 10933), 'lt0448w006': (10934, 10944), 'lt0448w007': (10945, 10997), 'lt0448w008': (10998, 11038)}

	the ultimate output needs to look like
		(word, count, citations)

	each item will hit the browser as something like:
		ἀβίωτον | 4 | w028: 246.d.6; w030: 407.a.5, 407.b.1; w034: 926.b.6

	:param work:
	:param startline:
	:param endline:
	:param cursor:
	:return:
	"""

	#print('cdict',cdict)

	onework = False
	if len(cdict) == 1:
		onework = True

	activepoll.allworkis(-1)
	
	lineobjects = compilewordlists(cdict, cursor)

	pooling = True
	if pooling:
		activepoll.statusis('Compiling the concordance')
		# 2x as fast to produce the final result; even faster inside the relevant loop
		# the drawback is the problem sending the poll object into the pool
		activepoll.allworkis(-1)
		activepoll.notes = '(progress information unavailable)'
		concordancedict = pooledconcordance(lineobjects)
	else:
		activepoll.statusis('Compiling the concordance')
		activepoll.allworkis(len(lineobjects))
		activepoll.remain(len(lineobjects))
		concordancedict = linesintoconcordance(lineobjects, activepoll)

	# concordancedict: { wordA: [(workid1, index1, locus1), (workid2, index2, locus2),..., wordB: ...]}
	# {'illic': [('lt0472w001', 2048, '68A.35')], 'carpitur': [('lt0472w001', 2048, '68A.35')], ...}

	unsortedoutput = []

	activepoll.statusis('Sifting the concordance')
	activepoll.notes = ''
	activepoll.allworkis(-1)
	
	for c in concordancedict.keys():
		hits = concordancedict[c]
		count = str(len(hits))
		hits = sorted(hits)
		if onework == True:
			hits = [h[2] for h in hits]
			loci = ', '.join(hits)
		else:
			previouswork = hits[0][0]
			loci = '<span class="work">%(w)s</span>: ' % {'w': previouswork[6:10]}
			for hit in hits:
				if hit[0] == previouswork:
					loci += hit[2] + ', '
				else:
					loci = loci[:-2] + '; '
					previouswork = hit[0]
					loci += '<span class="work">%(w)s</span>: ' % {'w': previouswork[6:10]}
					loci += hit[2] + ', '
			loci = loci[:-2]

		unsortedoutput.append((c, count, loci))
	
	return unsortedoutput


def linesintoconcordance(lineobjects, activepoll):
	"""
	generate the condordance dictionary:
		{ wordA: [(workid1, index1, locus1), (workid2, index2, locus2),..., wordB: ...]}
		{'illic': [('lt0472w001', 2048, '68A.35')], 'carpitur': [('lt0472w001', 2048, '68A.35')], ...}

	:return:
	"""

	defaultwork = lineobjects[0].wkuinversalid
	
	concordance = {}
	
	while len(lineobjects) > 0:
		try:
			line = lineobjects.pop()
			if activepoll:
				activepoll.remain(len(lineobjects))
		except:
			line = makeablankline(defaultwork, -1)
		
		if line.index != -1:
			words = line.wordlist('polytonic')
			words = [cleanwords(w).lower() for w in words]
			words = list(set(words))
			for w in words:
				try:
					concordance[w].append((line.wkuinversalid, line.index, line.locus()))
				except:
					concordance[w] = [(line.wkuinversalid, line.index, line.locus())]
	
	return concordance


def pooledconcordance(lineobjects):
	"""

	split up the line objects and dispatch them into an mp pool

	each thread will generate a dict

	then merge the result dicts into a master dict

	return the masterdict

	:param lineobjects:
	:return: masterdict
	"""

	workers = hipparchia.config['WORKERS']

	if len(lineobjects) > 100 * workers:
		# if you have only 2 lines of an author and 5 workers how will you divide the author up?
		chunksize = int(len(lineobjects)/workers)+1
		chunklines = [lineobjects[i:i + chunksize] for i in range(0, len(lineobjects), chunksize)]
	else:
		chunklines = [lineobjects]

	# polling does not really work
	# RuntimeError: Synchronized objects should only be shared between processes through inheritance
	# Manager() can do this but Pool() can't
	thereisapoll = False

	argmap = [(c, thereisapoll) for c in chunklines]

	with Pool(processes=int(workers)) as pool:
		listofconcordancedicts = pool.starmap(linesintoconcordance, argmap)

	masterdict = listofconcordancedicts.pop()

	while listofconcordancedicts:
		tomerge = listofconcordancedicts.pop()
		masterdict = dictmerger(masterdict, tomerge)

	return masterdict