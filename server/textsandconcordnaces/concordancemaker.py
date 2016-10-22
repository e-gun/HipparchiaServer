# -*- coding: utf-8 -*-

from server.dbsupport.dbfunctions import dblineintolineobject, makeablankline
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
	this is, you could use compileauthorandworklist() to feed this function
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
			words = findwordsinaline(line.accented)
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



