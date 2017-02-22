# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import asyncio
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
		buildconcordancefromconcordance() seemed ineffecient for small chunks: it was; but it is also a lot slower for whole works...
		single threaded buildconcordancefromwork() is 3-4x faster than mp buildconcordancefromconcordance()
		a mp version of buildconcordancefromwork() is 50% *slower* than mp buildconcordancefromconcordance()
	top speed seems to be a single thread diving into a work and building the concordance line by line: endless lock/unlock on the shared dictionary is too costly
	
	cdict = {wo.universalid: (startline, endline)}

	just caesar's bellum gallicum: cdict {'lt0448w001': (1, 6192)}
	all of casear's works: cdict {'lt0448w001': (1, 6192), 'lt0448w002': (6193, 10860), 'lt0448w003': (10861, 10891), 'lt0448w004': (10892, 10927), 'lt0448w005': (10928, 10933), 'lt0448w006': (10934, 10944), 'lt0448w007': (10945, 10997), 'lt0448w008': (10998, 11038)}

	the ultimate output needs to look like
		(word, count, citations)
		
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

	activepoll.statusis('Compiling the concordance')
	concordancedict = linesintoconcordance(lineobjects, activepoll)
	# now you are looking at: { wordA: [(workid1, index1, locus1), (workid2, index2, locus2),..., wordB: ...]}

	# functional but no faster: alas
	# loop = asyncio.new_event_loop()
	# asyncio.set_event_loop(loop)
	# concordancedict = loop.run_until_complete(test(lineobjects, activepoll))

	unsortedoutput = []

	activepoll.statusis('Sifting the concordance')
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

	:return:
	"""

	defaultwork = lineobjects[0].wkuinversalid
	
	concordance = {}
	
	while len(lineobjects) > 0:
		try:
			line = lineobjects.pop()
			activepoll.remain(len(lineobjects))
		except:
			line = makeablankline(defaultwork, -1)
		
		if line.index != -1:
			words = line.wordlist('polytonic')
			words = [cleanwords(w).lower() for w in words]
			words = list(set(words))
			for w in words:
				try:
					# to forestall the problem of sorting the citation values later, include the index now
					concordance[w].append((line.wkuinversalid, line.index, line.locus()))
					# concordance[w].append() seems to have race condition problems in mp land: you will end up with 1 copy of each word
					# mp variant:
					# concordance[w] = concordance[w] + [(line.wkuinversalid, line.index, line.locus())]
				except:
					concordance[w] = [(line.wkuinversalid, line.index, line.locus())]
	
	return concordance


# testing alternative implementations
# this does not speed things up over the simple version:
# no matter how you slice it it is hard to beat
# 52s for Concordance to Eustathius, Commentarii ad Homeri Iliadem

async def lic(a,b):
	return linesintoconcordance(a, b)

@asyncio.coroutine
async def test(lineobjects, activepoll):
	workers = hipparchia.config['WORKERS']

	if len(lineobjects) > 100 * workers:
		# if you have only 2 lines of an author and 5 workers how will you divide the author up?
		chunksize = int(len(lineobjects)/workers)+1
		chunklines = [lineobjects[i:i + chunksize] for i in range(0, len(lineobjects), chunksize)]
	else:
		chunklines = [lineobjects]

	dictofdicts = {}
	piles = min(len(chunklines), workers)

	for i in range(0,piles):
		dictofdicts[i] = await lic(chunklines[i], activepoll)

	masterdict = dictofdicts.pop(0)

	if dictofdicts:
		for k in dictofdicts:
			masterdict = dictmerger(masterdict, dictofdicts[k])

	return masterdict