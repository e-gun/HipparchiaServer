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
from collections import defaultdict

try:
	from gensim import corpora, models, similarities
except ImportError:
	print('gensim not installed')

from flask import request, session

from server import hipparchia
from server.formatting.bibliographicformatting import bcedating
from server.formatting.jsformatting import generatevectorjs
from server.hipparchiaobjects.helperobjects import ProgressPoll
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions, \
	polytonicsort
from server.listsandsession.whereclauses import configurewhereclausedata
from server.searching.searchfunctions import buildsearchobject, cleaninitialquery
from server.semanticvectors.vectordispatcher import findheadwords, vectorsentencedispatching
from server.semanticvectors.vectorhelpers import findverctorenvirons, \
	findwordvectorset, tidyupmophdict
from server.semanticvectors.vectormath import buildvectorspace, caclulatecosinevalues
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


	:param headword:
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

	# nb: basically forcing so.session['cosdistbysentence'] == 'yes'
	# don't know how to enter executesearch() properly to handle the other option
	# print('cosdistbysentence')

	output = findvectorsbysentence(activepoll, so)

	del poll[ts]

	return output


def findvectorsbysentence(activepoll, searchobject):
	"""

	use the searchlist to grab a collection of sentences

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	:param searchitem:
	:param vtype:
	:return:
	"""

	starttime = time.time()

	so = searchobject

	# we are not really a route at the moment, but instead being called by execute search
	# when the δ option is checked; hence the commenting out of the following
	# lemma = cleaninitialquery(request.args.get('lem', ''))

	try:
		lemma = lemmatadict[so.lemma.dictionaryentry]
	except KeyError:
		lemma = None
	except AttributeError:
		# 'NoneType' object has no attribute 'dictionaryentry'
		lemma = None

	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c] == 'yes']

	if (lemma or so.seeking) and activecorpora:
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

	# Vergil
	# so.lemma = lemmatadict['flos']
	# searchlist = ['lt0690']

	if len(searchlist) > 0:
		searchlist = flagexclusions(searchlist, so.session)
		workssearched = len(searchlist)
		searchlist = calculatewholeauthorsearches(searchlist, authordict)
		so.searchlist = searchlist

		indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
		so.indexrestrictions = indexrestrictions

		# find all sentences
		activepoll.statusis('Finding all sentences')
		sentences = vectorsentencedispatching(so, activepoll)

		output = generatevectoroutput(sentences, workssearched, so, activepoll, starttime, 'sentences')
	else:
		return emptyvectoroutput(so)

	return output


def findvectorsfromhits(searchobject, hitdict, activepoll, starttime, workssearched):
	"""
	a pseudo-route: the Δ option was checked and executesearch() branced over to this function

	we searched for a word within N lines/words of another word

	we got some lineobjects that are our hits

	how we vectorize this

	:param searchobject:
	:param hitdict:
	:param activepoll:
	:param starttime:
	:param workssearched:
	:return:
	"""

	so = searchobject

	activepoll.statusis('Compiling proximite wordlists')
	environs = findverctorenvirons(hitdict, so)

	output = generatevectoroutput(environs, workssearched, so, activepoll, starttime, 'passages')

	return output


def generatevectoroutput(listsofwords, workssearched, searchobject, activepoll, starttime, vtype):
	"""


	:return:
	"""
	so = searchobject
	dmin, dmax = bcedating(so.session)

	# find all words in use
	allwords = findwordvectorset(listsofwords)

	# find all possible forms of all the words we used
	# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
	activepoll.statusis('Finding headwords')
	morphdict = findheadwords(allwords)
	morphdict = tidyupmophdict(morphdict)

	# find all possible headwords of all of the forms in use
	# note that we will not know what we did not know: count unparsed words too and deliver that as info at the end?
	allheadwords = dict()
	for m in morphdict.keys():
		for h in morphdict[m]:
			allheadwords[h] = m

	if so.lemma:
		# set to none for now
		subtractterm = None
	else:
		subtractterm = so.seeking

	activepoll.statusis('Building vectors')
	vectorspace = buildvectorspace(allheadwords, morphdict, listsofwords, subtractterm=subtractterm)

	# for k in vectorspace.keys():
	# 	print(k, vectorspace[k])

	if so.lemma:
		focus = so.lemma.dictionaryentry
	else:
		focus = so.seeking

	activepoll.statusis('Calculating cosine distances')

	cosinevalues = caclulatecosinevalues(focus, vectorspace, allheadwords.keys())
	# cosinevalues = vectorcosinedispatching(focus, vectorspace, allheadwords.keys())

	# apply the threshold and drop the 'None' items
	threshold = 1.0 - hipparchia.config['VECTORDISTANCECUTOFF']
	falseidentity = .02
	cosinevalues = {c: cosinevalues[c] for c in cosinevalues if cosinevalues[c] and falseidentity < cosinevalues[c] < threshold}

	# now we have the relationship of everybody to our lemmatized word

	# print('CORE COSINE VALUES')
	# for v in polytonicsort(cosinevalues):
	# 	print(v, cosinevalues[v])
	ccv = [(cosinevalues[v], v) for v in cosinevalues]
	ccv = sorted(ccv, key=lambda t: t[0])
	ccv = ['\t{a}\t<lemmaheadword id="{b}">{b}</lemmaheadword>'.format(a=round(c[0], 3), b=c[1]) for c in ccv]
	ccv = '\n'.join(ccv)

	# next we look for the interrelationships of the words that are above the threshold
	activepoll.statusis('Calculating metacosine distances')
	metacosinevals = dict()
	metacosinevals[focus] = cosinevalues
	for v in cosinevalues:
		metac = caclulatecosinevalues(v, vectorspace, cosinevalues.keys())
		# metac = vectorcosinedispatching(v, vectorspace, cosinevalues.keys())
		metac = {c: metac[c] for c in metac if metac[c] and falseidentity < metac[c] < threshold}
		metacosinevals[v] = metac

	mcv = list(['\nrelationships of these terms to one another\n'])
	for headword in polytonicsort(metacosinevals.keys()):
		# print(headword)
		# for word in metacosinevals[headword]:
		# 	print('\t', word, metacosinevals[headword][word])
		if headword != focus:
			insetvals = [(metacosinevals[headword][word], word) for word in metacosinevals[headword]]
			insetvals = sorted(insetvals, key=lambda t: t[0])
			insetvals = ['\t{a}\t<lemmaheadword id="{b}">{b}</lemmaheadword>'.format(a=round(c[0], 3), b=c[1]) for c in insetvals]
			if insetvals:
				mcv.append('<lemmaheadword id="{h}">{h}</lemmaheadword>'.format(h=headword))
			mcv += insetvals
	if len(mcv) > 1:
		mcv = '\n'.join(mcv)
	else:
		mcv = ''

	findshtml = '<pre>{ccv}</pre>\n\n<pre>{mcv}</pre>'.format(ccv=ccv, mcv=mcv)

	findsjs = generatevectorjs()

	searchtime = time.time() - starttime
	searchtime = round(searchtime, 2)
	workssearched = locale.format('%d', workssearched, grouping=True)

	output = dict()
	output['title'] = 'Cosine distances to »{skg}«'.format(skg=focus)
	output['found'] = findshtml
	# ultimately the js should let you clock on any top word to find its associations...
	output['js'] = findsjs
	output['resultcount'] = '{c} related terms in {s} {t}'.format(c=len(cosinevalues), s=len(listsofwords), t=vtype)
	output['scope'] = workssearched
	output['searchtime'] = str(searchtime)
	output['proximate'] = ''
	if so.lemma:
		xtra = 'all forms of '
	else:
		xtra = ''
	output['thesearch'] = '{x}»{skg}«'.format(x=xtra, skg=focus)
	output['htmlsearch'] = '{x}<span class="sought">»{skg}«</span>'.format(x=xtra, skg=focus)
	output['hitmax'] = ''
	output['onehit'] = ''
	output['sortby'] = 'distance with a cutoff of {c}'.format(c=1 - hipparchia.config['VECTORDISTANCECUTOFF'])
	output['dmin'] = dmin
	output['dmax'] = dmax
	activepoll.deactivate()

	output = json.dumps(output)

	return output


def emptyvectoroutput(searchobject, reasons=list()):
	"""

	no results; say as much

	:return:
	"""

	so = searchobject
	output = dict()
	dmin, dmax = bcedating(so.session)

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c] == 'yes']

	if not activecorpora:
		reasons.append('there are no active databases')
	if not (so.lemma or so.seeking):
		reasons.append('no search term was provided')

	output['title'] = '(empty query)'
	output['found'] = ''
	output['resultcount'] = 0
	output['scope'] = 0
	output['searchtime'] = '0.00'
	output['proximate'] = so.proximate
	output['thesearch'] = ''
	output['htmlsearch'] = '<span class="emph">nothing</span> (search not executed because {r})'.format(r=' and '.join(reasons))
	output['hitmax'] = 0
	output['dmin'] = dmin
	output['dmax'] = dmax
	output['sortby'] = so.session['sortorder']
	output['onehit'] = so.session['onehit']

	output = json.dumps(output)

	return output


##
## TESTING
##

def findlatentsemanticindex(activepoll, searchobject):
	"""

	use the searchlist to grab a collection of sentences

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	:param searchitem:
	:param vtype:
	:return:
	"""

	print('findlatentsemanticindex')
	searchobject.seeking = 'fortestingpurposes'

	starttime = time.time()

	so = searchobject

	# we are not really a route at the moment, but instead being called by execute search
	# when the δ option is checked; hence the commenting out of the following
	# lemma = cleaninitialquery(request.args.get('lem', ''))

	try:
		lemma = lemmatadict[so.lemma.dictionaryentry]
	except KeyError:
		lemma = None
	except AttributeError:
		# 'NoneType' object has no attribute 'dictionaryentry'
		lemma = None

	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c] == 'yes']

	if (lemma or so.seeking) and activecorpora:
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

	# catullus
	# searchlist = ['lt0472']

	# hdt
	searchlist = ['gr0016']

	# hippoc
	searchlist = ['gr0627']

	# nepos
	# searchlist = ['lt0588']

	if len(searchlist) > 0:
		searchlist = flagexclusions(searchlist, so.session)
		workssearched = len(searchlist)
		searchlist = calculatewholeauthorsearches(searchlist, authordict)
		so.searchlist = searchlist

		indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
		so.indexrestrictions = indexrestrictions

		# find all sentences
		activepoll.statusis('Finding all sentences')
		# blanking out the search term will really return every last sentence...
		# otherwise you only return sentences with the search term in them
		so.lemma = None
		so.seeking = r'.'
		sentences = vectorsentencedispatching(so, activepoll)
		output = lsigenerateoutput(sentences, workssearched, so, activepoll, starttime, 'sentences')
	else:
		return emptyvectoroutput(so)

	return output


def lsigenerateoutput(listsofwords, workssearched, searchobject, activepoll, starttime, vtype):
	"""


	:return:
	"""

	so = searchobject
	dmin, dmax = bcedating(so.session)

	# find all words in use
	allwords = findwordvectorset(listsofwords)

	# find all possible forms of all the words we used
	# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
	activepoll.statusis('Finding headwords')
	morphdict = findheadwords(allwords)
	morphdict = tidyupmophdict(morphdict)

	# find all possible headwords of all of the forms in use
	# note that we will not know what we did not know: count unparsed words too and deliver that as info at the end?
	allheadwords = dict()
	for m in morphdict.keys():
		for h in morphdict[m]:
			allheadwords[h] = m

	if so.lemma:
		# set to none for now
		subtractterm = None
	else:
		subtractterm = so.seeking

	activepoll.statusis('Building vectors')

	vectorspace = lsibuildspace(allheadwords, morphdict, listsofwords)

	print('throwexception')
	throwexception

	# for k in vectorspace.keys():
	# 	print(k, vectorspace[k])

	if so.lemma:
		focus = so.lemma.dictionaryentry
	else:
		focus = so.seeking

	activepoll.statusis('Calculating cosine distances')

	cosinevalues = caclulatecosinevalues(focus, vectorspace, allheadwords.keys())
	# cosinevalues = vectorcosinedispatching(focus, vectorspace, allheadwords.keys())

	# apply the threshold and drop the 'None' items
	threshold = 1.0 - hipparchia.config['VECTORDISTANCECUTOFF']
	falseidentity = .02
	cosinevalues = {c: cosinevalues[c] for c in cosinevalues if cosinevalues[c] and falseidentity < cosinevalues[c] < threshold}

	# now we have the relationship of everybody to our lemmatized word

	# print('CORE COSINE VALUES')
	# for v in polytonicsort(cosinevalues):
	# 	print(v, cosinevalues[v])
	ccv = [(cosinevalues[v], v) for v in cosinevalues]
	ccv = sorted(ccv, key=lambda t: t[0])
	ccv = ['\t{a}\t<lemmaheadword id="{b}">{b}</lemmaheadword>'.format(a=round(c[0], 3), b=c[1]) for c in ccv]
	ccv = '\n'.join(ccv)

	# next we look for the interrelationships of the words that are above the threshold
	activepoll.statusis('Calculating metacosine distances')
	metacosinevals = dict()
	metacosinevals[focus] = cosinevalues
	for v in cosinevalues:
		metac = caclulatecosinevalues(v, vectorspace, cosinevalues.keys())
		# metac = vectorcosinedispatching(v, vectorspace, cosinevalues.keys())
		metac = {c: metac[c] for c in metac if metac[c] and falseidentity < metac[c] < threshold}
		metacosinevals[v] = metac

	mcv = list(['\nrelationships of these terms to one another\n'])
	for headword in polytonicsort(metacosinevals.keys()):
		# print(headword)
		# for word in metacosinevals[headword]:
		# 	print('\t', word, metacosinevals[headword][word])
		if headword != focus:
			insetvals = [(metacosinevals[headword][word], word) for word in metacosinevals[headword]]
			insetvals = sorted(insetvals, key=lambda t: t[0])
			insetvals = ['\t{a}\t<lemmaheadword id="{b}">{b}</lemmaheadword>'.format(a=round(c[0], 3), b=c[1]) for c in insetvals]
			if insetvals:
				mcv.append('<lemmaheadword id="{h}">{h}</lemmaheadword>'.format(h=headword))
			mcv += insetvals
	if len(mcv) > 1:
		mcv = '\n'.join(mcv)
	else:
		mcv = ''

	findshtml = '<pre>{ccv}</pre>\n\n<pre>{mcv}</pre>'.format(ccv=ccv, mcv=mcv)

	findsjs = generatevectorjs()

	searchtime = time.time() - starttime
	searchtime = round(searchtime, 2)
	workssearched = locale.format('%d', workssearched, grouping=True)

	output = dict()
	output['title'] = 'Cosine distances to »{skg}«'.format(skg=focus)
	output['found'] = findshtml
	# ultimately the js should let you clock on any top word to find its associations...
	output['js'] = findsjs
	output['resultcount'] = '{c} related terms in {s} {t}'.format(c=len(cosinevalues), s=len(listsofwords), t=vtype)
	output['scope'] = workssearched
	output['searchtime'] = str(searchtime)
	output['proximate'] = ''
	if so.lemma:
		xtra = 'all forms of '
	else:
		xtra = ''
	output['thesearch'] = '{x}»{skg}«'.format(x=xtra, skg=focus)
	output['htmlsearch'] = '{x}<span class="sought">»{skg}«</span>'.format(x=xtra, skg=focus)
	output['hitmax'] = ''
	output['onehit'] = ''
	output['sortby'] = 'distance with a cutoff of {c}'.format(c=1 - hipparchia.config['VECTORDISTANCECUTOFF'])
	output['dmin'] = dmin
	output['dmax'] = dmax
	activepoll.deactivate()

	output = json.dumps(output)

	return output


def lsibuildspace(allheadwords, morphdict, sentences):
	"""

	:param allheadwords:
	:param morphdict:
	:param sentences:
	:return:
	"""

	vectorspace = dict()
	vectormapper = dict()

	sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
	sentences = [s for s in sentences if s]

	bagsofwords = list()
	for s in sentences:
		lemattized = list()
		for word in s:
			try:
				# WARNING: we are treating homonymns as if 2+ words were there instead of just one
				# 'rectum' will give you 'rectus' and 'rego'; 'res' will give you 'reor' and 'res'
				# this necessarily distorts the vector space
				lemattized.append([item for item in morphdict[word]])
			except KeyError:
				pass
		# flatten
		bagsofwords.append([item for sublist in lemattized for item in sublist])

	prevalence = defaultdict(int)
	for bag in bagsofwords:
		for word in bag:
			prevalence[word] += 1

	bagsofwords = [[w for w in bag if prevalence[w] > 1] for bag in bagsofwords]

	lsidictionary = corpora.Dictionary(bagsofwords)
	print('lsidictionary', lsidictionary)

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

	print('10 topics', semanticindex.print_topics(10))

	corpussemanticindex = semanticindex[corpustfidf]

	vectorquery = 'εὕρηϲιϲ φύϲιϲ'
	vectorquerybag = lsidictionary.doc2bow(vectorquery.lower().split())
	vectorquerylsi = semanticindex[vectorquerybag]
	# print('vectorquerylsi', vectorquerylsi)

	vectorindex = similarities.MatrixSimilarity(semanticindex[lsicorpus])

	similis = vectorindex[vectorquerylsi]
	print('similis', similis)

	sims = sorted(enumerate(similis), key=lambda item: -item[1])
	for s in sims:
		if s[1] > .5:
			print(s, ' '.join(sentences[s[0]]), bagsofwords[s[0]])
			# print(s, ' '.join(sentences[s[0]]))

	return



"""
herodotus

10 topics [(0, '0.516*"λέγω³" + 0.514*"λέγω¹" + 0.495*"λέγω²" + 0.215*"ὅδε" + 0.173*"ἔλεγοϲ" + 0.102*"λέγοϲ" + 0.095*"ϲφεῖϲ" + 0.095*"ποιέω" + 0.084*"νῦν" + 0.079*"λόγοϲ"'), (1, '-0.405*"ποιέω" + -0.252*"ἔχω" + -0.214*"ποιόω" + 0.212*"λέγω¹" + 0.211*"λέγω³" + -0.204*"ϲφεῖϲ" + 0.203*"λέγω²" + -0.151*"νῦν" + -0.123*"ὅδε" + -0.118*"πρότεροϲ"'), (2, '0.784*"εἶπον" + 0.533*"εἶποϲ" + -0.208*"ποιέω" + -0.127*"ποιόω" + -0.121*"ὅδε" + 0.079*"ἔχω" + -0.050*"ἀμείβω" + 0.042*"χόω" + -0.030*"νῦν" + 0.027*"χάω"'), (3, '0.635*"ὅδε" + 0.351*"ποιέω" + 0.276*"ἀμείβω" + -0.250*"ἔχω" + 0.210*"ποιόω" + 0.191*"εἶπον" + -0.148*"ναῦϲ" + 0.140*"εἶποϲ" + -0.137*"νέα" + -0.137*"νεάω"'), (4, '-0.568*"ὅδε" + 0.539*"ποιέω" + 0.346*"ποιόω" + -0.292*"ἀμείβω" + -0.235*"ἔχω" + -0.110*"χάω" + -0.093*"ἔχιϲ" + 0.093*"εἶπον" + -0.092*"χέω" + 0.080*"λέγω²"'), (5, '0.401*"ναῦϲ" + -0.392*"ἔχω" + 0.389*"νέα" + 0.389*"νεάω" + 0.309*"νέοϲ" + -0.202*"χάω" + -0.181*"ἔχιϲ" + -0.177*"χέω" + 0.139*"νεάζω" + 0.139*"νεόω"'), (6, '-0.450*"ἔχω" + 0.263*"ϲφεῖϲ" + -0.243*"ποιέω" + -0.243*"χάω" + -0.218*"ἔχιϲ" + -0.214*"χέω" + -0.194*"νέα" + -0.194*"νεάω" + -0.194*"ναῦϲ" + -0.161*"ποιόω"'), (7, '-0.762*"νῦν" + -0.359*"καλέω" + 0.300*"ϲφεῖϲ" + 0.121*"δέω²" + 0.110*"δέω¹" + 0.109*"ἔχω" + 0.091*"δέομαι" + -0.082*"πόλιϲ" + -0.078*"χώρα" + 0.073*"χάω"'), (8, '-0.893*"οὔτε" + 0.200*"καλέω" + 0.159*"ϲφεῖϲ" + 0.110*"ὄνομα" + -0.092*"οὔτιϲ" + -0.091*"οὔτι" + 0.085*"δέω²" + 0.085*"δέω¹" + 0.084*"πρότεροϲ" + 0.068*"πρῶτοϲ"'), (9, '0.500*"νῦν" + -0.434*"καλέω" + -0.330*"ὄνομα" + 0.242*"ϲφεῖϲ" + 0.241*"δέω¹" + 0.240*"δέω²" + -0.204*"πόλιϲ" + 0.189*"δέομαι" + 0.151*"δεῖ" + -0.081*"ἀφικνέομαι"')]


"""