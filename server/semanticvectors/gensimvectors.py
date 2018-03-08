# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import json
import time

from flask import request, session
from gensim import corpora
from gensim.models import LogEntropyModel, LsiModel, TfidfModel, Word2Vec
from gensim.similarities import MatrixSimilarity

from server import hipparchia
from server.dbsupport.dbfunctions import setconnection, setthreadcount
from server.formatting.bibliographicformatting import bcedating
from server.formatting.jsformatting import generatevectorjs, insertbrowserclickjs
from server.formatting.vectorformatting import formatlsimatches, formatnnmatches, formatnnsimilarity
from server.hipparchiaobjects.helperobjects import LSIVectorCorpus, LogEntropyVectorCorpus
from server.hipparchiaobjects.searchobjects import OutputObject, ProgressPoll
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.searching.searchfunctions import buildsearchobject, cleaninitialquery
from server.semanticvectors.vectordispatcher import findheadwords, vectorsentencedispatching
from server.semanticvectors.vectorgraphing import graphnnmatches
from server.semanticvectors.vectorhelpers import buildflatbagsofwords, checkforstoredvector, convertmophdicttodict, \
	finddblinesfromsentences, findwordvectorset, storevectorindatabase
from server.semanticvectors.vectorpseudoroutes import emptyvectoroutput
from server.startup import authordict, lemmatadict, listmapper, poll, workdict


@hipparchia.route('/findneighbors/<timestamp>', methods=['GET'])
def findnearestneighborvectors(timestamp):
	"""

	meant to be called via a click from a result from a prior search

	:param timestamp:
	:return:
	"""

	try:
		ts = str(int(timestamp))
	except ValueError:
		ts = str(int(time.time()))

	so = buildsearchobject(ts, request, session)
	so.seeking = ''
	so.proximate = ''
	so.proximatelemma = ''

	try:
		so.lemma = lemmatadict[cleaninitialquery(request.args.get('lem', ''))]
	except KeyError:
		so.lemma = None

	poll[ts] = ProgressPoll(ts)
	activepoll = poll[ts]
	activepoll.activate()
	activepoll.statusis('Preparing to search')

	output = findlatentsemanticindex(activepoll, so, nn=True)

	del poll[ts]

	return output


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
	so = searchobject

	if not nn:
		outputfunction = lsigenerateoutput
		indextype = 'lsi'
		so.vectortype = 'semanticvectorquery'
	else:
		outputfunction = nearestneighborgenerateoutput
		indextype = 'nn'

	starttime = time.time()

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
		wt = '{:,}'.format(wordstotal)
		mw = '{:,}'.format(maxwords)
		reasons = ['the vector scope max exceeded: {a} > {b} '.format(a=wt, b=mw)]
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

		vectorspace = checkforstoredvector(searchlist, indextype)

		if validlemma:
			# find all sentences
			if not vectorspace:
				activepoll.statusis('No stored model for this search. Finding all sentences')
			else:
				activepoll.statusis('Finding neighbors')
			# blanking out the search term will really return every last sentence...
			# otherwise you only return sentences with the search term in them
			restorelemma = lemmatadict[so.lemma.dictionaryentry]
			so.lemma = None
			so.seeking = r'.'
			if not vectorspace:
				sentencestuples = vectorsentencedispatching(so, activepoll)
			else:
				sentencestuples = None
			so.lemma = restorelemma
			output = outputfunction(sentencestuples, workssearched, so, activepoll, starttime, vectorspace)
		else:
			return emptyvectoroutput(so)
	else:
		return emptyvectoroutput(so)

	return output


def nearestneighborgenerateoutput(sentencetuples, workssearched, searchobject, activepoll, starttime, vectorspace):
	"""

	:param listsofwords:
	:param workssearched:
	:param searchobject:
	:param activepoll:
	:param starttime:
	:return:
	"""

	so = searchobject
	output = OutputObject(so, so.session)
	imagename = ''
	termone = so.lemma.dictionaryentry

	try:
		termtwo = so.proximatelemma.dictionaryentry
	except AttributeError:
		termtwo = None

	if not vectorspace:
		vectorspace = buildnnvectorspace(sentencetuples, activepoll, so)
		if vectorspace == 'failed to build model':
			reasons = [vectorspace]
			return emptyvectoroutput(so, reasons)

	if termone and termtwo:
		similarity = findword2vecsimilarities(termone, termtwo, vectorspace)
		similarity = formatnnsimilarity(termone, termtwo, similarity)
		mostsimilar = ['placeholder']
		html = similarity
	else:
		activepoll.statusis('Calculating the nearest neighbors')
		mostsimilar = findapproximatenearestneighbors(termone, vectorspace)
		# [('εὕρηϲιϲ', 1.0), ('εὑρίϲκω', 0.6673248708248138), ('φυϲιάω', 0.5833806097507477), ('νόμοϲ', 0.5505017340183258), ...]
		if mostsimilar:
			html = formatnnmatches(mostsimilar)
			activepoll.statusis('Building the graph')
			mostsimilar = mostsimilar[:hipparchia.config['NEARESTNEIGHBORSCAP']]
			imagename = graphnnmatches(termone, mostsimilar, vectorspace, so.searchlist)
		else:
			html = '<pre>["{t}" was not found in the vector space]</pre>'.format(t=termone)

	findshtml = '{h}'.format(h=html)

	findsjs = generatevectorjs('findneighbors')

	lm = so.lemma.dictionaryentry
	try:
		pr = so.proximatelemma.dictionaryentry
	except AttributeError:
		# proximatelemma is None
		pr = None

	if lm and pr:
		output.title = '[TESTING] Word2Vec of »{skg}« and »{pr}«'.format(skg=lm, pr=pr)
	else:
		output.title = 'Neighbors for all forms of »{skg}«'.format(skg=lm, pr=pr)
	output.found = findshtml
	output.js = findsjs
	try:
		output.setresultcount(len(mostsimilar), 'proximate terms to graph')
	except TypeError:
		pass
	output.setscope(workssearched)
	output.searchtime = str(round(time.time() - starttime, 2))

	if so.lemma:
		all = 'all forms of »{skg}«'.format(skg=lm)
	else:
		all = ''
	if so.proximatelemma:
		near = ' all forms of »{skg}«'.format(skg=pr)
	else:
		near = ''
	output.thesearch = thesearch = '{all}{near}'.format(all=all, near=near)

	if so.lemma:
		all = 'all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.lemma.formlist), skg=lm)
	else:
		all = ''
	if so.proximatelemma:
		near = ' and all {n} known forms of <span class="sought">»{skg}«</span>'.format(n=len(so.proximatelemma.formlist), skg=pr)
	else:
		near = ''
	output.htmlsearch = '{all}{near}'.format(all=all, near=near)

	if lm and pr:
		output.sortby = ''
	else:
		output.sortby = 'proximity'

	output.image = imagename
	activepoll.deactivate()

	jsonoutput = json.dumps(output.generateoutput())

	return jsonoutput


def buildnnvectorspace(sentencetuples, activepoll, searchobject):
	"""

	:return:
	"""

	# find all words in use
	listsofwords = [s[1] for s in sentencetuples]
	allwords = findwordvectorset(listsofwords)

	# find all possible forms of all the words we used
	# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
	wl = '{:,}'.format(len(listsofwords))
	activepoll.statusis(
		'No stored model for this search. Generating a new one.<br />Finding headwords for {n} sentences'.format(n=wl))

	morphdict = findheadwords(allwords)
	morphdict = convertmophdicttodict(morphdict)
	# morphdict = {t: '·'.join(morphdict[t]) for t in morphdict}

	activepoll.statusis(
		'No stored model for this search. Generating a new one.<br />Building vectors for the headwords in the {n} sentences'.format(
			n=wl))
	vectorspace = buildgensimmodel(searchobject, morphdict, listsofwords)

	return vectorspace


def findapproximatenearestneighbors(query, mymodel):
	"""

	search for points in space that are close to a given query point

	the query should be a dictionary headword

	this returns a list of tuples: (word, distance)

	:param query:
	:param morphdict:
	:param sentences:
	:return:
	"""

	explore = max(2500, hipparchia.config['NEARESTNEIGHBORSCAP'])

	try:
		mostsimilar = mymodel.most_similar(query, topn=explore)
		mostsimilar = [s for s in mostsimilar if s[1] > hipparchia.config['VECTORDISTANCECUTOFFNEARESTNEIGHBOR']]
	except KeyError:
		# keyedvectors.py: raise KeyError("word '%s' not in vocabulary" % word)
		mostsimilar = None
	except AttributeError:
		# 'NoneType' object has no attribute 'most_similar'
		mostsimilar = None

	#print('mostsimilar', mostsimilar)

	return mostsimilar


def findword2vecsimilarities(termone, termtwo, mymodel):
	"""

	:param query:
	:param morphdict:
	:param sentences:
	:return:
	"""

	similarity = mymodel.wv.similarity(termone, termtwo)

	return similarity


def buildgensimmodel(searchobject, morphdict, sentences):
	"""


	:return:
	"""

	sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
	sentences = [s for s in sentences if s]

	# going forward we we need a list of lists of headwords
	# there are two ways to do this:
	#   'ϲυγγενεύϲ ϲυγγενήϲ' vs 'ϲυγγενεύϲ·ϲυγγενήϲ'
	# the former seems less bad than the latter
	# if might be possible to vectorize in unlemmatized form and then to search via the lemma
	# here you would need to invoke mymodel.wv.n_similarity(self, ws1, ws2) where ws is a list of words
	bagofwordsfunction = buildflatbagsofwords
	# bagofwordsfunction = buildbagsofwordswithalternates

	bagsofwords = bagofwordsfunction(morphdict, sentences)

	workers = setthreadcount()

	dimensions = hipparchia.config['VECTORDIMENSIONS']
	window = hipparchia.config['VECTORWINDOW']
	trainingiterations = hipparchia.config['VECTORTRAININGITERATIONS']
	minimumnumberofhits = hipparchia.config['VECTORMINIMALPRESENCE']
	downsample = hipparchia.config['VECTORDOWNSAMPLE']
	computeloss = False

	# Note that for a fully deterministically-reproducible run, you must also limit the model to a single worker thread (workers=1), to eliminate ordering jitter from OS thread scheduling.
	try:
		model = Word2Vec(bagsofwords,
						min_count=minimumnumberofhits,
						seed=1,
						iter=trainingiterations,
						size=dimensions,
						sample=downsample,
						sg=1,  # the results seem terrible if you say sg=0
						window=window,
						workers=workers,
						compute_loss=computeloss)
	except RuntimeError:
		# RuntimeError: you must first build vocabulary before training the model
		# this will happen if you have a tiny author with too few words
		model = None

	if computeloss:
		print('loss after {n} iterations was: {l}'.format(n=trainingiterations, l=model.get_latest_training_loss()))

	if model:
		model.delete_temporary_training_data(replace_word_vectors_with_normalized=True)

	# print(model.wv['puer'])

	storevectorindatabase(searchobject.searchlist, 'nn', model)

	return model


def lsigenerateoutput(sentencestuples, workssearched, searchobject, activepoll, starttime, lsispace):
	"""


	:return:
	"""

	so = searchobject
	dmin, dmax = bcedating(so.session)

	if not lsispace:
		# find all words in use
		listsofwords = [s[1] for s in sentencestuples]
		allwords = findwordvectorset(listsofwords)

		# find all possible forms of all the words we used
		# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
		wl = '{:,}'.format(len(listsofwords))
		activepoll.statusis('Finding headwords for {n} sentences'.format(n=wl))

		morphdict = findheadwords(allwords)
		morphdict = convertmophdicttodict(morphdict)

		# find all possible headwords of all of the forms in use
		# note that we will not know what we did not know: count unparsed words too and deliver that as info at the end?
		allheadwords = dict()
		for m in morphdict.keys():
			for h in morphdict[m]:
				allheadwords[h] = m

		hw = '{:,}'.format(len(allheadwords.keys()))
		activepoll.statusis('Building vectors for {h} headwords in {n} sentences'.format(h=hw, n=wl))

		lsispace = lsibuildspace(morphdict, listsofwords)
		storevectorindatabase(so.searchlist, 'lsi', lsispace)

	try:
		vq = ' '.join([so.lemma.dictionaryentry, so.proximatelemma.dictionaryentry])
	except AttributeError:
		# there was no second lemma & you cant join None
		vq = so.lemma.dictionaryentry

	vectorquerylsi = lsispace.findquerylsi(vq)

	vectorindex = MatrixSimilarity(lsispace.semantics)

	similis = vectorindex[vectorquerylsi]
	# print('similis', similis)

	threshold = hipparchia.config['VECTORDISTANCECUTOFFLEMMAPAIR']

	matches = list()
	sims = sorted(enumerate(similis), key=lambda item: -item[1])
	count = 0
	activepoll.statusis('Sifting results')

	dbconnection = setconnection('autocommit')
	cursor = dbconnection.cursor()
	for s in sims:
		if s[1] > threshold:
			thissentence = lsispace.sentences[s[0]]
			# this part is slow and needs MP refactoring?
			# dblines = finddblinefromsentence(thissentence, subsearchobject)
			dblines = finddblinesfromsentences(thissentence, sentencestuples, cursor)
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
				thismatch['words'] = lsispace.bagsofwords[s[0]]
				matches.append(thismatch)

	cursor.close()
	del dbconnection

	matches = [m for m in matches if len(m['sentence'].split(' ')) > 2]
	findshtml = formatlsimatches(matches)

	# findsjs = generatevectorjs('therewillbenoreclicks')
	findsjs = insertbrowserclickjs('browser')

	searchtime = time.time() - starttime
	searchtime = round(searchtime, 2)
	workssearched = '{:,}'.format(workssearched)

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


def logentropybuildspace(morphdict, sentences):
	"""

	currently unused

	:param allheadwords:
	:param morphdict:
	:param sentences:
	:return:
	"""

	sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
	sentences = [s for s in sentences if s]

	# going forward we we need a list of lists of headwords
	# homonymns are adjacent, not joined: 'ϲυγγενεύϲ ϲυγγενήϲ' vs 'ϲυγγενεύϲ·ϲυγγενήϲ'
	bagsofwords = buildflatbagsofwords(morphdict, sentences)

	logentropydictionary = corpora.Dictionary(bagsofwords)
	logentropycorpus = [logentropydictionary.doc2bow(bag) for bag in bagsofwords]
	logentropyxform = LogEntropyModel(logentropycorpus)
	lsixform = LsiModel(corpus=logentropycorpus,
						id2word=logentropydictionary,
						onepass=False,
						num_topics=400)

	corpus = LogEntropyVectorCorpus(lsixform, logentropyxform, logentropydictionary, logentropycorpus, bagsofwords, sentences)


	return corpus


def lsibuildspace(morphdict, sentences):
	"""

	:param allheadwords:
	:param morphdict:
	:param sentences:
	:return:
	"""

	sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
	sentences = [s for s in sentences if s]

	# going forward we we need a list of lists of headwords
	# homonymns are adjacent, not joined: 'ϲυγγενεύϲ ϲυγγενήϲ' vs 'ϲυγγενεύϲ·ϲυγγενήϲ'
	bagsofwords = buildflatbagsofwords(morphdict, sentences)

	lsidictionary = corpora.Dictionary(bagsofwords)
	lsicorpus = [lsidictionary.doc2bow(bag) for bag in bagsofwords]
	termfreqinversedocfreq = TfidfModel(lsicorpus)
	corpustfidf = termfreqinversedocfreq[lsicorpus]
	semanticindex = LsiModel(corpustfidf, id2word=lsidictionary, num_topics=250)

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

	corpus = LSIVectorCorpus(semanticindex, corpustfidf, lsidictionary, lsicorpus, bagsofwords, sentences)

	return corpus


def doc2vecbuildspace(morphdict, sentences):
	"""

	hollow shell for testing...

	https://github.com/RaRe-Technologies/gensim/blob/develop/docs/notebooks/doc2vec-lee.ipynb

	https://rare-technologies.com/word2vec-in-python-part-two-optimizing/

	:param morphdict:
	:param sentences:
	:return:
	"""

	return


"""
what a vector looks like...: 'puer' in caesar

[-0.07297496  0.1021654   0.03902959 -0.06689005  0.06367909 -0.08757351
 -0.0523007  -0.11700287 -0.06473643 -0.00216301 -0.04626903 -0.01550784
  0.0027577   0.05436178 -0.03622846  0.00093686  0.00973313  0.05469589
 -0.00484871  0.00853434 -0.00158172 -0.03580923 -0.07040348  0.00514191
 -0.04269573  0.0322229   0.02511295  0.11392887  0.00155903 -0.12464628
  0.03248475  0.00103343 -0.05620911  0.00382355  0.03891547 -0.04813525
  0.03882799  0.02826695 -0.00742884 -0.00357546 -0.02199934  0.02696464
  0.04004842  0.06254423  0.02879605  0.10324359 -0.03014274 -0.11210016
  0.00968658  0.07737652  0.0407063   0.01084703  0.03501635 -0.02285282
 -0.04080134  0.04386326  0.00078081  0.07206082 -0.09055281 -0.05264669
  0.04823256  0.01139497  0.05356287  0.09972883 -0.10292753  0.0778084
  0.03374154  0.02001307 -0.06033748  0.02714802  0.04452373  0.01173801
  0.08178856  0.01452065 -0.08290357 -0.03336409  0.09365007 -0.02081515
 -0.01616011 -0.0436631  -0.01192146  0.0971348  -0.01700965  0.047299
 -0.01956504 -0.03132216  0.04062452  0.05193596 -0.05685377 -0.03426539
 -0.0798387   0.0124453  -0.00955153  0.10101608  0.07797857 -0.05096063
 -0.07479604 -0.06234599 -0.05146498  0.0646603   0.08042667 -0.03302623
 -0.12186483 -0.03927034 -0.04969952  0.00105887  0.01894625  0.03772362
 -0.04696564 -0.06553476 -0.00934369  0.04645333  0.16495237 -0.01679634
 -0.0270997   0.01074857  0.04416994 -0.01331279  0.07085373  0.03512502
 -0.03597013  0.00072314 -0.03618126 -0.03249335 -0.04864321 -0.00091682
  0.02537548  0.02039542  0.03645486  0.01620385 -0.08862805  0.04040209
  0.12594098  0.03382703  0.04096643 -0.01572719  0.08885124  0.03318303
 -0.07438245 -0.0045597  -0.06566253 -0.03402666  0.04529983  0.00623911
 -0.03887329  0.12033626 -0.09388069 -0.04694028  0.02385728 -0.09738193
 -0.04089219  0.00273871  0.10862171 -0.03906664 -0.00087924 -0.02840637
 -0.08476509  0.04045922 -0.04407904  0.04918951 -0.04190287 -0.00049112
  0.09223717 -0.05879653 -0.01897216 -0.06497809 -0.05233913  0.07363557
  0.07741539  0.01593467  0.00569672 -0.06206178  0.00433147  0.02171708
 -0.04640922 -0.0392371   0.02420822  0.04259672 -0.13040288  0.0314232
  0.06681944  0.11744206 -0.02891444 -0.0201632   0.13967474  0.04557661
  0.11426584 -0.14583017 -0.02780947 -0.05890822  0.05594346  0.03217001
  0.02301606 -0.09076256 -0.02302598 -0.03244444 -0.11855584 -0.00460188
 -0.12163572  0.01065659 -0.04216166 -0.03426995  0.00936757 -0.08329219
 -0.01904839 -0.04498264  0.08040194 -0.05082183 -0.01129342 -0.03196287
  0.03953067  0.05667811  0.00109137  0.00468812 -0.0156208   0.04485156
  0.07992603  0.06708687 -0.02643748 -0.04021865  0.0367011  -0.00063396
  0.01714563  0.0586605  -0.04950646 -0.04359532  0.01542643  0.01353163
  0.03810446  0.07859109 -0.02517567  0.0248144  -0.08303869 -0.00522078
  0.09192681  0.03473615 -0.08826447  0.01213564  0.03064479 -0.05914807
 -0.06412902 -0.03452161  0.05555919  0.0444692   0.1389127  -0.11375115
 -0.02018013 -0.00082195 -0.1359317  -0.04003034 -0.02197042 -0.14613378
  0.08986787 -0.01037686  0.02959959  0.04603588 -0.01767985  0.06179699
 -0.03251902  0.04959809 -0.03610322  0.09182888 -0.02485723 -0.03208145
  0.10082986  0.02195905 -0.00160256  0.0371495  -0.05574754  0.05765224
 -0.1472714  -0.07408118 -0.01696561  0.07447409 -0.00626733 -0.03708688
 -0.07174284  0.02687856 -0.02598816  0.05963796  0.06249622 -0.04382812
  0.01569738 -0.03013863 -0.03567049 -0.01609015 -0.05017817 -0.07182983
  0.02449209 -0.04341337 -0.01197475 -0.04028719  0.01373828 -0.08293446
  0.01628143 -0.06926829 -0.08556946  0.05673709 -0.02611384 -0.01855229]

 """