# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from typing import List

import warnings

from server.dbsupport.vectordbfunctions import storevectorindatabase
from server.semanticvectors.wordbaggers import buildwordbags
from server.threading.mpthreadcount import setthreadcount

try:
	from gensim.models import Word2Vec
except ImportError:
	from multiprocessing import current_process
	if current_process().name == 'MainProcess':
		print('gensim not available')
	Word2Vec = None


def buildgensimmodel(searchobject, morphdict: dict, sentences: List[str]) -> Word2Vec:
	"""

	returns a Word2Vec model

	then you use one of the many ill-documented class functions that come with
	the model to make queries against it

	WordEmbeddingsKeyedVectors in keyedvectors.py is your friend here for learning what you can really do
		most_similar(positive=None, negative=None, topn=10, restrict_vocab=None, indexer=None)
			[analogies; most_similar(positive=['woman', 'king'], negative=['man']) --> queen]

		similar_by_word(word, topn=10, restrict_vocab=None)
			[the top-N most similar words]

		similar_by_vector(vector, topn=10, restrict_vocab=None)

		similarity_matrix(dictionary, tfidf=None, threshold=0.0, exponent=2.0, nonzero_limit=100, dtype=REAL)

		wmdistance(document1, document2)
			[Word Mover's Distance between two documents]

		most_similar_cosmul(positive=None, negative=None, topn=10)
			[analogy finder; most_similar_cosmul(positive=['baghdad', 'england'], negative=['london']) --> iraq]

		cosine_similarities(vector_1, vectors_all)

		distances(word_or_vector, other_words=())

		distance(w1, w2)
			[distance('woman', 'man')]

		similarity(w1, w2)
			[similarity('woman', 'man')]

		n_similarity(ws1, ws2)
			[sets of words: n_similarity(['sushi', 'shop'], ['japanese', 'restaurant'])]


	FYI: Doc2VecKeyedVectors
		doesnt_match(docs)
			[Which doc from the given list doesn't go with the others?]

	note that Word2Vec will hurl out lots of DeprecationWarnings; we are blocking them
	one hopes that this does not yield a surprise some day... [surprise: it did...]

	this code is a candidate for refactoring because of the gensim 3.8 vs 4.0 API difference
	a drop down from model to model.wv requires refactoring dependent functions

	:return:
	"""

	vv = searchobject.vectorvalues

	sentences = [[w for w in words.lower().split() if w] for words in sentences if words]
	sentences = [s for s in sentences if s]

	bagsofwords = buildwordbags(searchobject, morphdict, sentences)

	workers = setthreadcount()

	computeloss = False

	# Note that for a fully deterministically-reproducible run, you must also limit the model to a single worker thread
	# (workers=1), to eliminate ordering jitter from OS thread scheduling.
	try:
		with warnings.catch_warnings():
			warnings.filterwarnings("ignore", category=DeprecationWarning)
			try:
				gensimmodel = Word2Vec(bagsofwords,
							min_count=vv.minimumpresence,
							seed=1,
							iter=vv.trainingiterations,
							size=vv.dimensions,
							sample=vv.downsample,
							sg=1,  # the results seem terrible if you say sg=0
							window=vv.window,
							workers=workers,
							compute_loss=computeloss)
			except TypeError:
				# TypeError: __init__() got an unexpected keyword argument 'iter'
				# i.e., gensim 4.0.0 changed the API
				# see: https://radimrehurek.com/gensim/models/word2vec.html
				#
				# class gensim.models.word2vec.Word2Vec(sentences=None, corpus_file=None, vector_size=100, alpha=0.025,
				# window=5, min_count=5, max_vocab_size=None, sample=0.001, seed=1, workers=3, min_alpha=0.0001, sg=0,
				# hs=0, negative=5, ns_exponent=0.75, cbow_mean=1, hashfxn=<built-in function hash>, epochs=5,
				# null_word=0, trim_rule=None, sorted_vocab=1, batch_words=10000, compute_loss=False, callbacks=(),
				# comment=None, max_final_vocab=None)
				#
				# epochs (int, optional) – Number of iterations (epochs) over the corpus. (Formerly: iter)
				# vector_size (int, optional) – Dimensionality of the word vectors.
				gensimmodel = Word2Vec(bagsofwords,
							min_count=vv.minimumpresence,
							seed=1,
							epochs=vv.trainingiterations,
							vector_size=vv.dimensions,
							sample=vv.downsample,
							sg=1,  # the results seem terrible if you say sg=0
							window=vv.window,
							workers=workers,
							compute_loss=computeloss)

	except RuntimeError:
		# RuntimeError: you must first build vocabulary before training the model
		# this will happen if you have a tiny author with too few words
		gensimmodel = None

	if computeloss:
		print('loss after {n} iterations was: {l}'.format(n=vv.trainingiterations, l=gensimmodel.get_latest_training_loss()))

	reducedmodel = None

	if gensimmodel:
		with warnings.catch_warnings():
			warnings.filterwarnings("ignore", category=DeprecationWarning)
			try:
				gensimmodel.delete_temporary_training_data(replace_word_vectors_with_normalized=True)
			except AttributeError:
				# AttributeError: 'Word2Vec' object has no attribute 'delete_temporary_training_data'
				# i.e., gensim 4.0.0 changed the API
				# see: https://radimrehurek.com/gensim/models/word2vec.html
				# 	If you’re finished training a model (i.e. no more updates, only querying), you can switch to the KeyedVectors instance:
				# 	word_vectors = model.wv
				# 	del model
				# this complicates our backwards-compatible-life, though.
				# we want to return a Word2Vec and not a KeyedVectors instance
				# gensimmodel = gensimmodel.wv
				reducedmodel = Word2Vec([["cat", "say", "meow"], ["dog", "say", "woof"]], min_count=1)
				reducedmodel.wv = gensimmodel.wv

	if reducedmodel:
		gensimmodel = reducedmodel

	# print(model.wv['puer'])

	storevectorindatabase(searchobject, 'nn', gensimmodel)

	return gensimmodel


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