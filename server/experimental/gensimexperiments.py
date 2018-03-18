# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
from gensim import corpora
from gensim.models import LogEntropyModel, LsiModel

from server.hipparchiaobjects.helperobjects import LogEntropyVectorCorpus
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.vectorhelpers import buildflatbagsofwords
from server.semanticvectors.vectorhelpers import convertmophdicttodict, findheadwords, findwordvectorset
from server.startup import authordict, listmapper


def gensimexperiment(so):
	"""

	:param activepoll:
	:param so:
	:return:
	"""

	activepoll = so.poll

	activecorpora = so.getactivecorpora()
	searchlist = flagexclusions(searchlist, so.session)
	workssearched = len(searchlist)
	searchlist = compilesearchlist(listmapper, so.session)
	searchlist = calculatewholeauthorsearches(searchlist, authordict)
	so.searchlist = searchlist
	sentencetuples = vectorprepdispatcher(so)
	# find all words in use
	listsofwords = [s[1] for s in sentencetuples]
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

	vectorspace = logentropybuildspace(morphdict, listsofwords)

	return output


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