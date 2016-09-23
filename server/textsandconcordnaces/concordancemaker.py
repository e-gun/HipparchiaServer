# -*- coding: utf-8 -*-
from server import formatting_helper_functions
from server.searching.searchfunctions import concordancelookup


def buildconcordance(work, mode, cursor):
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
	for result in concordancewords:
		citations = []
		loci = result[1].split(' ')
		count = str(len(loci))
		for locus in loci:
			citation = concordancelookup(work[:-5], locus, cursor)
			citations.append(citation)
		citations = ', '.join(citations)
		output.append([result[0], count, citations])
	
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
			# time to run through this is 0.15s for Ovid (who takes 142s to build): the bottleneck is in the monster number of calls to concordancelookup()
			query = 'SELECT word, loci FROM ' + w
			cursor.execute(query)
			results = cursor.fetchall()
			for item in results:
				if item[0] not in wordset:
					wordset[item[0]] = [[w,item[1]]]
				else:
					wordset[item[0]].append([w,item[1]])
		
		unsortedwords = list(wordset)
		sortedwords = formatting_helper_functions.polytonicsort(unsortedwords)

		for word in sortedwords:
			count = 0
			citations = []
			for hit in range(0,len(wordset[word])):
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