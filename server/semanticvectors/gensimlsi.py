# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from gensim import corpora
from gensim.models import LsiModel, TfidfModel
from gensim.similarities import MatrixSimilarity

from server import hipparchia
from server.dbsupport.vectordbfunctions import storevectorindatabase
from server.formatting.vectorformatting import formatlsimatches, lsiformatoutput
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.helperobjects import LSIVectorCorpus
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.vectorhelpers import buildflatbagsofwords, convertmophdicttodict, finddblinesfromsentences, \
	findheadwords, findwordvectorset


def lsigenerateoutput(sentencestuples, workssearched, searchobject, activepoll, lsispace):
	"""

	:param sentencestuples:
	:param workssearched:
	:param searchobject:
	:param activepoll:
	:param starttime:
	:param lsispace:
	:return:
	"""

	matches = lsifindmatches(sentencestuples, searchobject, activepoll, lsispace)

	findshtml = formatlsimatches(matches)

	output = lsiformatoutput(findshtml, workssearched, matches, searchobject, activepoll)

	return output


def lsifindmatches(sentencestuples, searchobject, activepoll, lsispace):
	"""


	:return:
	"""

	so = searchobject

	makespace = lsibuildspace

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

		lsispace = makespace(morphdict, listsofwords)
		storevectorindatabase(so, 'lsi', lsispace)

	vectorquerylsi = lsispace.findquerylsi(so.tovectorize)

	vectorindex = MatrixSimilarity(lsispace.semantics)

	similis = vectorindex[vectorquerylsi]
	# print('similis', similis)

	threshold = hipparchia.config['VECTORDISTANCECUTOFFLEMMAPAIR']

	matches = list()
	sims = sorted(enumerate(similis), key=lambda item: -item[1])
	count = 0
	activepoll.statusis('Sifting results')

	if not sentencestuples:
		sentencestuples = vectorprepdispatcher(so, activepoll)

	dbconnection = ConnectionObject('autocommit')
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

	dbconnection.connectioncleanup()

	matches = [m for m in matches if len(m['sentence'].split(' ')) > 2]

	return matches


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
