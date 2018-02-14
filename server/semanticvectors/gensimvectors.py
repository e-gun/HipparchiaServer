# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import json
import locale
import time
from copy import deepcopy

from gensim import corpora, models, similarities
from gensim.models import Word2Vec

from server import hipparchia
from server.dbsupport.dbfunctions import setthreadcount
from server.formatting.bibliographicformatting import bcedating
from server.formatting.jsformatting import generatevectorjs
from server.formatting.vectorformatting import formatlsimatches, formatnnmatches
from server.hipparchiaobjects.helperobjects import SemanticVectorCorpus
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.rudimentaryvectormath import buildbagsofwords
from server.semanticvectors.vectordispatcher import findheadwords, vectorsentencedispatching
from server.semanticvectors.vectorhelpers import convertmophdicttodict, finddblinefromsentence, findwordvectorset
from server.semanticvectors.vectorpseudoroutes import emptyvectoroutput
from server.startup import authordict, lemmatadict, listmapper, workdict


def findnearestneighbors(activepoll, searchobject):
	"""

	pass-through to findlatentsemanticindex()

	:param activepoll:
	:param searchobject:
	:return:
	"""

	return findlatentsemanticindex(activepoll, searchobject, nn=True)


def findlatentsemanticindex(activepoll, searchobject, nn=False):
	"""

	use the searchlist to grab a collection of sentences

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	:param searchitem:
	:param vtype:
	:return:
	"""

	if not nn:
		outputfunction = lsigenerateoutput
	else:
		outputfunction = nearestneighborgenerateoutput

	starttime = time.time()

	so = searchobject

	try:
		validlemma = lemmatadict[so.lemma.dictionaryentry]
	except KeyError:
		validlemma = None
	except AttributeError:
		# 'NoneType' object has no attribute 'dictionaryentry'
		validlemma = None

	so.lemma = validlemma

	try:
		validlemmatwo = lemmatadict[so.proximatelemma.dictionaryentry]
	except KeyError:
		validlemmatwo = None
	except AttributeError:
		# 'NoneType' object has no attribute 'dictionaryentry'
		validlemmatwo = None

	so.proximatelemma = validlemmatwo

	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c] == 'yes']

	if (so.lemma or so.seeking) and activecorpora:
		activepoll.statusis('Compiling the list of works to search')
		searchlist = compilesearchlist(listmapper, so.session)
	else:
		reasons = ['search list contained zero items']
		return emptyvectoroutput(so, reasons)

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
		reasons = ['the vector scope max exceeded: {a} > {b} '.format(a=locale.format('%d', wordstotal, grouping=True), b=locale.format('%d', maxwords, grouping=True))]
		return emptyvectoroutput(so, reasons)

	# DEBUGGING
	# Frogs and mice
	# so.lemma = lemmatadict['βάτραχοϲ']
	# searchlist = ['gr1220']

	# Euripides
	# so.lemma = lemmatadict['ἄτη']
	# print(so.lemma.formlist)
	# so.lemma.formlist = ['ἄτῃ', 'ἄταν', 'ἄτηϲ', 'ἄτηι']
	# searchlist = ['gr0006']

	if len(searchlist) > 0:
		searchlist = flagexclusions(searchlist, so.session)
		workssearched = len(searchlist)
		searchlist = calculatewholeauthorsearches(searchlist, authordict)
		so.searchlist = searchlist

		indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
		so.indexrestrictions = indexrestrictions

		if validlemma:
			# find all sentences
			activepoll.statusis('Finding all sentences')
			# blanking out the search term will really return every last sentence...
			# otherwise you only return sentences with the search term in them
			restorelemma = lemmatadict[so.lemma.dictionaryentry]
			so.lemma = None
			so.seeking = r'.'
			sentences = vectorsentencedispatching(so, activepoll)
			so.lemma = restorelemma
			output = outputfunction(sentences, workssearched, so, activepoll, starttime)
		else:
			return emptyvectoroutput(so)
	else:
		return emptyvectoroutput(so)

	return output


def lsigenerateoutput(listsofwords, workssearched, searchobject, activepoll, starttime):
	"""


	:return:
	"""

	so = searchobject
	dmin, dmax = bcedating(so.session)

	# find all words in use
	allwords = findwordvectorset(listsofwords)

	# find all possible forms of all the words we used
	# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
	wl = locale.format('%d', len(listsofwords), grouping=True)
	activepoll.statusis('Finding headwords for {n} sentences'.format(n=wl))

	morphdict = findheadwords(allwords)
	morphdict = convertmophdicttodict(morphdict)

	# find all possible headwords of all of the forms in use
	# note that we will not know what we did not know: count unparsed words too and deliver that as info at the end?
	allheadwords = dict()
	for m in morphdict.keys():
		for h in morphdict[m]:
			allheadwords[h] = m

	hw = locale.format('%d', len(allheadwords.keys()), grouping=True)
	activepoll.statusis('Building vectors for {h} headwords in {n} sentences'.format(h=hw, n=wl))

	# TESTING
	# mostsimilar = findapproximatenearestneighbors(so.lemma.dictionaryentry, morphdict, listsofwords)
	# print('mostsimilar',mostsimilar)
	# throwexception

	corpus = lsibuildspace(morphdict, listsofwords)
	c = corpus

	# print('tokens', c.lsidictionary)
	# print('cshape', c.lsicorpus)
	# for d in c.lsicorpus:
	# 	print('doc:', d)
	# print('10 topics', corpus.showtopics(10))

	try:
		vq = ' '.join([so.lemma.dictionaryentry, so.proximatelemma.dictionaryentry])
	except AttributeError:
		# there was no second lemma & you cant join None
		vq = so.lemma.dictionaryentry

	vectorquerylsi = c.findquerylsi(vq)

	vectorindex = similarities.MatrixSimilarity(c.semantics)

	similis = vectorindex[vectorquerylsi]
	# print('similis', similis)

	threshold = hipparchia.config['VECTORDISTANCECUTOFF']

	matches = list()
	sims = sorted(enumerate(similis), key=lambda item: -item[1])
	count = 0
	activepoll.statusis('Sifting results')
	subsearchobject = deepcopy(so)

	for s in sims:
		if s[1] > threshold:
			thissentence = c.sentences[s[0]]
			# this part is slow and needs MP refactoring?
			dblines = finddblinefromsentence(thissentence, subsearchobject)
			if dblines:
				if len(dblines) > 1:
					xtra = ' <span class="small">[1 of {n} occurrences]</span>'.format(n=len(dblines))
				else:
					xtra = ''
				dbline = dblines[0]
				count += 1
				thismatch = dict()
				thismatch['count'] = count
				thismatch['score'] = float(s[1])  # s[1] comes back as <class 'numpy.float32'>
				thismatch['line'] = dbline
				thismatch['sentence'] = '{s}{x}'.format(s=' '.join(thissentence), x=xtra)
				thismatch['words'] = c.bagsofwords[s[0]]
				matches.append(thismatch)

	findshtml = formatlsimatches(matches)

	findsjs = generatevectorjs()

	searchtime = time.time() - starttime
	searchtime = round(searchtime, 2)
	workssearched = locale.format('%d', workssearched, grouping=True)

	lm = so.lemma.dictionaryentry
	try:
		pr = so.proximatelemma.dictionaryentry
	except AttributeError:
		# proximatelemma is None
		pr = None

	output = dict()
	if lm and pr:
		output['title'] = 'Semantic index for all forms of »{skg}« and »{pr}«'.format(skg=lm, pr=pr)
	else:
		output['title'] = 'Semantic index for all forms of »{skg}«'.format(skg=lm, pr=pr)
	output['found'] = findshtml
	# ultimately the js should let you clock on any top word to find its associations...
	output['js'] = findsjs
	output['resultcount'] = '{n} sentences above the cutoff'.format(n=len(matches))
	output['scope'] = workssearched
	output['searchtime'] = str(searchtime)
	output['proximate'] = ''

	if so.lemma:
		all = 'all forms of »{skg}«'.format(skg=lm)
	else:
		all = ''
	if so.proximatelemma:
		near = ' all forms of »{skg}«'.format(skg=pr)
	else:
		near = ''
	output['thesearch'] = '{all}{near}'.format(all=all, near=near)

	if so.lemma:
		all = 'all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.lemma.formlist), skg=lm)
	else:
		all = ''
	if so.proximatelemma:
		near = ' and all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.proximatelemma.formlist), skg=pr)
	else:
		near = ''
	output['htmlsearch'] = '{all}{near}'.format(all=all, near=near)
	output['hitmax'] = ''
	output['onehit'] = ''
	output['sortby'] = 'proximity'
	output['dmin'] = dmin
	output['dmax'] = dmax
	activepoll.deactivate()

	output = json.dumps(output)

	return output


def nearestneighborgenerateoutput(listsofwords, workssearched, searchobject, activepoll, starttime):
	"""

	:param listsofwords:
	:param workssearched:
	:param searchobject:
	:param activepoll:
	:param starttime:
	:return:
	"""

	so = searchobject
	dmin, dmax = bcedating(so.session)

	# find all words in use
	allwords = findwordvectorset(listsofwords)

	# find all possible forms of all the words we used
	# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
	wl = locale.format('%d', len(listsofwords), grouping=True)
	activepoll.statusis('Finding headwords for {n} sentences'.format(n=wl))

	morphdict = findheadwords(allwords)
	morphdict = convertmophdicttodict(morphdict)

	# find all possible headwords of all of the forms in use
	# note that we will not know what we did not know: count unparsed words too and deliver that as info at the end?
	allheadwords = dict()
	for m in morphdict.keys():
		for h in morphdict[m]:
			allheadwords[h] = m

	hw = locale.format('%d', len(allheadwords.keys()), grouping=True)
	activepoll.statusis('Building vectors for {h} headwords in {n} sentences'.format(h=hw, n=wl))

	# TESTING
	termone = so.lemma.dictionaryentry
	try:
		termtwo = so.proximatelemma.dictionaryentry
	except AttributeError:
		termtwo = None

	if termone and termtwo:
		similarity = findword2vecsimilarities(termone, termtwo, morphdict, listsofwords)
		# print('similarity of {a} and {b} is {c}'.format(a=termone, b=termtwo, c=similarity))
		html = similarity
	else:
		mostsimilar = findapproximatenearestneighbors(termone, morphdict, listsofwords)
		# print('mostsimilar', mostsimilar)
		# [('εὕρηϲιϲ', 1.0), ('εὑρίϲκω', 0.6673248708248138), ('φυϲιάω', 0.5833806097507477), ('νόμοϲ', 0.5505017340183258), ...]
		html = formatnnmatches(mostsimilar)

	findshtml = '<pre>{h}</pre>'.format(h=html)

	findsjs = generatevectorjs()

	searchtime = time.time() - starttime
	searchtime = round(searchtime, 2)
	workssearched = locale.format('%d', workssearched, grouping=True)

	lm = so.lemma.dictionaryentry
	try:
		pr = so.proximatelemma.dictionaryentry
	except AttributeError:
		# proximatelemma is None
		pr = None

	output = dict()
	if lm and pr:
		output['title'] = '[TESTING] Word2Vec of »{skg}« and »{pr}«'.format(skg=lm, pr=pr)
	else:
		output['title'] = '[TESTING] Neighbors for all forms of »{skg}«'.format(skg=lm, pr=pr)
	output['found'] = findshtml
	# ultimately the js should let you clock on any top word to find its associations...
	output['js'] = findsjs
	output['resultcount'] = ''
	output['scope'] = workssearched
	output['searchtime'] = str(searchtime)
	output['proximate'] = ''

	if so.lemma:
		all = 'all forms of »{skg}«'.format(skg=lm)
	else:
		all = ''
	if so.proximatelemma:
		near = ' all forms of »{skg}«'.format(skg=pr)
	else:
		near = ''
	output['thesearch'] = '{all}{near}'.format(all=all, near=near)

	if so.lemma:
		all = 'all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.lemma.formlist), skg=lm)
	else:
		all = ''
	if so.proximatelemma:
		near = ' and all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.proximatelemma.formlist), skg=pr)
	else:
		near = ''
	output['htmlsearch'] = '{all}{near}'.format(all=all, near=near)
	output['hitmax'] = ''
	output['onehit'] = ''
	output['sortby'] = 'proximity'
	output['dmin'] = dmin
	output['dmax'] = dmax
	activepoll.deactivate()

	output = json.dumps(output)

	return output


def lsibuildspace(morphdict, sentences):
	"""

	:param allheadwords:
	:param morphdict:
	:param sentences:
	:return:
	"""

	sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
	sentences = [s for s in sentences if s]

	bagsofwords = buildbagsofwords(morphdict, sentences)

	lsidictionary = corpora.Dictionary(bagsofwords)

	lsicorpus = [lsidictionary.doc2bow(bag) for bag in bagsofwords]

	termfreqinversedocfreq = models.TfidfModel(lsicorpus)

	corpustfidf = termfreqinversedocfreq[lsicorpus]

	semanticindex = models.LsiModel(corpustfidf, id2word=lsidictionary, num_topics=350)

	"""	
	"An empirical study of required dimensionality for large-scale latent semantic indexing applications"
	Bradford 2008
	
	For a term-document matrix that has been decomposed via SVD with a non-zero diagonal... 
	
	Dimensionality is reduced by deleting all but the k largest values on 
	this diagonal, together with the corresponding columns in the
	other two matrices. This truncation process is used to generate a
	k-dimensional vector space. Both terms and documents are represented
	by k-dimensional vectors in this vector space.
	
	Landauer and Dumais in 1997: They found that the degree of match 
	between cosine measures in the LSI space and human judgment
	was strongly dependent on k, with a maximum for k = 300
	
	It is clear that there will be a growing degradation of representational
	fidelity as the dimensionality is increased beyond 400. Depending
	upon the application, such behavior may preclude use of
	dimensionality greater than 400.  
	
	recommendations:
	300: thousands to 10s of thousands

	"""

	corpus = SemanticVectorCorpus(semanticindex, corpustfidf, lsidictionary, lsicorpus, bagsofwords, sentences)

	return corpus


def findapproximatenearestneighbors(query, morphdict, sentences):
	"""

	search for points in space that are close to a given query point

	the query should be a dictionary headword

	:param query:
	:param morphdict:
	:param sentences:
	:return:
	"""

	sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
	sentences = [s for s in sentences if s]

	bagsofwords = buildbagsofwords(morphdict, sentences)

	workers = setthreadcount()
	dimensions = 300
	window = 10
	trainingiterations = 12
	minimumnumberofhits = 5
	downsample = 0.05

	# Note that for a fully deterministically-reproducible run, you must also limit the model to a single worker thread (workers=1), to eliminate ordering jitter from OS thread scheduling.
	mymodel = Word2Vec(bagsofwords,
						min_count=minimumnumberofhits,
						seed=1,
						iter=trainingiterations,
						sample=downsample,
						size=dimensions,
						sg=1,
						window=window,
						workers=workers)

	# indexer = AnnoyIndexer(mymodel, 2)
	# mostsimilar = mymodel.most_similar(query, topn=10, indexer=indexer)

	# needed if you will graph
	# thewords = mymodel[mymodel.wv.vocab]

	mostsimilar = mymodel.most_similar(query)

	return mostsimilar


def findword2vecsimilarities(termone, termtwo, morphdict, sentences):
	"""

	:param query:
	:param morphdict:
	:param sentences:
	:return:
	"""

	# print('findword2vecsimilarities()')

	sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
	sentences = [s for s in sentences if s]

	bagsofwords = buildbagsofwords(morphdict, sentences)

	workers = setthreadcount()

	dimensions = 300
	window = 10
	trainingiterations = 12
	minimumnumberofhits = 1
	downsample = 0.05

	# Note that for a fully deterministically-reproducible run, you must also limit the model to a single worker thread (workers=1), to eliminate ordering jitter from OS thread scheduling.
	model = Word2Vec(bagsofwords,
					min_count=minimumnumberofhits,
					seed=1,
					iter=trainingiterations,
					size=dimensions,
					sample=downsample,
					sg=1,
					window=window,
					workers=workers)

	similarity = model.wv.similarity(termone, termtwo)

	return similarity