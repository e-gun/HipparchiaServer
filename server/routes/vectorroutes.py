# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import time

from flask import request, session

from server import hipparchia
from server.formatting.wordformatting import removegravity
from server.hipparchiaobjects.helperobjects import ProgressPoll, SearchObject
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.sessionfunctions import sessionvariables
from server.listsandsession.whereclauses import configurewhereclausedata
from server.searching.searchfunctions import cleaninitialquery
from server.semanticvectors.vectordispatcher import findheadwords, vectordispatching
from server.semanticvectors.vectorhelpers import buildvectorspace, caclulatecosinevalues, mostcommonwords
from server.startup import authordict, lemmatadict, listmapper, poll, workdict

"""
	THE MATH

	http://www.puttypeg.net/papers/vector-chapter.pdf

	see esp pp. 155-58 on cosine similarity:
	
		cos(α,β) = α · β / ||α|| ||β||
	
	||α|| = sqrt(α · α)
	
	and α = sum([a1, a2, ... ai])

	1 = most related
	0 = unrelated

"""

"""	
	OVERVIEW OF THE IDEAL PROCESS
	
	[a] find all forms of X
	[b] find all words in the same sentence as X
	[c] calculate values for the most common neighbors of X where these values describe the degree of relatedness
	[d] calculate similar values that relate those same neighbors to one another
	[e] graph the results.
	
"""


@hipparchia.route('/findvectors/<timestamp>', methods=['GET'])
def findvectors(timestamp):
	"""

	use the searchlist to grab a collection of passages

	[or is it better to do this via the text boxes...? you will never be able to do "all of medicine" that way, though]

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	:param timestamp:
	:return:
	"""
	starttime = time.time()

	try:
		ts = str(int(timestamp))
	except:
		ts = str(int(time.time()))

	lemma = cleaninitialquery(request.args.get('lem', ''))

	try:
		lemma = lemmatadict[lemma]
	except KeyError:
		lemma = None

	poll[ts] = ProgressPoll(ts)
	activepoll = poll[ts]
	activepoll.activate()
	activepoll.statusis('Preparing to search')

	searchlist = list()
	output = ''
	nosearch = True

	seeking = ''
	proximate = ''
	proximatelemma = ''
	sessionvariables()
	frozensession = session.copy()

	so = SearchObject(ts, seeking, proximate, lemma, proximatelemma, frozensession)
	so.usecolumn = 'marked_up_line'

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if frozensession[c] == 'yes']

	if lemma and activecorpora:
		activepoll.statusis('Compiling the list of works to search')
		searchlist = compilesearchlist(listmapper, frozensession)

	# make sure you don't go nuts
	maxwords = hipparchia.config['MAXVECTORSPACE']
	wordstotal = 0
	for work in searchlist:
		work = work[:10]
		try:
			wordstotal += workdict[work].wordcount
		except TypeError:
			# TypeError: unsupported operand type(s) for +=: 'int' and 'NoneType'
			pass

	if wordstotal > maxwords:
		searchlist = list()
		print('aborted vectorization: too many words {a} > {b}'.format(a=wordstotal, b=maxwords))
	else:
		print('wordstotal', wordstotal)

	# DEBUGGING
	# Frogs and mice
	so.lemma = lemmatadict['βάτραχοϲ']
	searchlist = ['gr1220']

	# Hippocrates
	"""
	Sought all 6 known forms of »εὕρηϲιϲ«
	Searched 57 texts and found 35 passages (0.25s)
	Sorted by name
	"""
	so.lemma = lemmatadict['εὕρηϲιϲ']
	searchlist = ['gr0627']

	# Galen
	"""
	Sought all 6 known forms of »εὕρηϲιϲ«
	Searched 110 texts and found 296 passages (0.93s)
	Sorted by name
	"""
	so.lemma = lemmatadict['εὕρηϲιϲ']
	searchlist = ['gr0057']


	if len(searchlist) > 0:
		nosearch = False
		searchlist = flagexclusions(searchlist, frozensession)
		workssearched = len(searchlist)
		searchlist = calculatewholeauthorsearches(searchlist, authordict)
		so.searchlist = searchlist

		indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
		so.indexrestrictions = indexrestrictions

		# find all sentences
		sentences = vectordispatching(so, activepoll)

		# find all words in use
		allwords = [s.split(' ') for s in sentences]
		# flatten
		allwords = [item for sublist in allwords for item in sublist]
		allwords = [removegravity(w) for w in allwords]
		allwords = set(allwords) - {''}

		# find all possible forms of all the words we used
		# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
		morphdict = findheadwords(allwords, activepoll)
		morphdict = {k: v for k, v in morphdict.items() if v is not None}
		morphdict = {k: set([p.getbaseform() for p in morphdict[k].getpossible()]) for k in morphdict.keys()}

		# {'θεῶν': {'θεόϲ', 'θέα', 'θεάω', 'θεά'}, 'πώ': {'πω'}, 'πολλά': {'πολύϲ'}, 'πατήρ': {'πατήρ'}, ... }

		# over-aggressive? more thought/care might be required here
		delenda = mostcommonwords()
		morphdict = {k: v for k, v in morphdict.items() if v - delenda == v}

		# find all possible headwords of all of the forms in use
		allheadwords = dict()
		for m in morphdict.keys():
			for h in morphdict[m]:
				allheadwords[h] = m

		vectorspace = buildvectorspace(allheadwords, morphdict, sentences, delenda)

		# for k in vectorspace.keys():
		# 	print(k, vectorspace[k])

		cosinevalues = caclulatecosinevalues(so.lemma.dictionaryentry, vectorspace, allheadwords.keys())

		# apply the threshold and drop the 'None' items
		threshold = 1.0 - hipparchia.config['VECTORDISTANCECUTOFF']
		cosinevalues = {c: cosinevalues[c] for c in cosinevalues if cosinevalues[c] and cosinevalues[c] < threshold}

		# now we have the relationship of everybody to our lemmatized word

		# print('CORE COSINE VALUES')
		# for v in polytonicsort(cosinevalues):
		# 	print(v, cosinevalues[v])

		# next we look for the interrelationships of the words that are above the threshold
		metacosinevals = dict()
		metacosinevals[so.lemma.dictionaryentry] = cosinevalues
		for v in cosinevalues:
			metac = caclulatecosinevalues(v, vectorspace, cosinevalues.keys())
			metac = {c: metac[c] for c in metac if metac[c] and metac[c] < threshold}
			metacosinevals[v] = metac

		# for headword in polytonicsort(metacosinevals.keys()):
		# 	print(headword)
		# 	for word in metacosinevals[headword]:
		# 		print('\t',word, metacosinevals[headword][word])


	return