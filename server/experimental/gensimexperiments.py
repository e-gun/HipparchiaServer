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
from server.semanticvectors.vectorhelpers import buildflatbagsofwords


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