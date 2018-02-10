# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import locale
import math
import os
import time

import numpy as np
import tensorflow as tf
from sklearn.manifold import TSNE

from server import hipparchia
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.vectordispatcher import findheadwords, vectorsentencedispatching
from server.semanticvectors.vectorhelpers import convertmophdicttodict, tfbuilddataset, tfgeneratetrainingbatch, \
	tfplotwithlabels
from server.semanticvectors.vectorpseudoroutes import emptyvectoroutput
from server.startup import authordict, lemmatadict, listmapper, workdict


def tensorgraphelectedworks(activepoll, searchobject):
	"""

	adapted from https://raw.githubusercontent.com/tensorflow/tensorflow/r1.5/tensorflow/examples/tutorials/word2vec/word2vec_basic.py

	:param activepoll:
	:param searchobject:
	:return:
	"""

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
			output = tftrainondata(sentences, activepoll)
		else:
			return emptyvectoroutput(so)
	else:
		return emptyvectoroutput(so)

	return output


def tftrainondata(sentences, activepoll):
	"""

	adapted from the tensorflow tutorial

	sentences = ['the first sentence', 'the next sentence', ...]

	:param sentences:
	:return:
	"""

	sentencesaslists = [s.split(' ') for s in sentences]
	allwordsinorder = [item for sublist in sentencesaslists for item in sublist if item]

	morphdict = findheadwords(set(allwordsinorder))
	morphdict = convertmophdicttodict(morphdict)

	headwordsinorder = list()
	for w in allwordsinorder:
		try:
			hwds = [item for item in morphdict[w]]
			headwordsinorder.append('·'.join(hwds))
		except TypeError:
			pass
		except KeyError:
			pass

	vocabularysize = min(10000, len(set(headwordsinorder)))

	activepoll.statusis('Constructing dataset')
	dataset = tfbuilddataset(headwordsinorder, vocabularysize)

	batchsize = 8
	skipwindow = 1
	numberofskips = 2

	# print('dataset', dataset)
	activepoll.statusis('Constructing training batch')
	trainingbatch = tfgeneratetrainingbatch(batchsize, numberofskips, skipwindow, dataset['listofcodes'], 0)

	batchsize = 128
	embeddingsize = 128
	numsampled = 64

	# We pick a random validation set to sample nearest neighbors. Here we limit the
	# validation samples to the words that have a low numeric ID, which by
	# construction are also the most frequent. These 3 variables are used only for
	# displaying model accuracy, they don't affect calculation.

	validsize = 16
	validwindow = 100
	validexamples = np.random.choice(validwindow, validsize, replace=False)

	graph = tf.Graph()

	with graph.as_default():
		# Input data.
		traininputs = tf.placeholder(tf.int32, shape=[batchsize])
		trainlabels = tf.placeholder(tf.int32, shape=[batchsize, 1])
		validdataset = tf.constant(validexamples, dtype=tf.int32)

		# Ops and variables pinned to the CPU because of missing GPU implementation
		with tf.device('/cpu:0'):
			# Look up embeddings for inputs.
			embeddings = tf.Variable(tf.random_uniform([vocabularysize, embeddingsize], -1.0, 1.0))
			embed = tf.nn.embedding_lookup(embeddings, traininputs)

			# Construct the variables for the NCE loss
			nce_weights = tf.Variable(
				tf.truncated_normal([vocabularysize, embeddingsize], stddev=1.0 / math.sqrt(embeddingsize)))
			nce_biases = tf.Variable(tf.zeros([vocabularysize]))

		# Compute the average NCE loss for the batch.
		# tf.nce_loss automatically draws a new sample of the negative labels each
		# time we evaluate the loss.
		# Explanation of the meaning of NCE loss:
		#   http://mccormickml.com/2016/04/19/word2vec-tutorial-the-skip-gram-model/
		loss = tf.reduce_mean(
			tf.nn.nce_loss(weights=nce_weights,
			               biases=nce_biases,
			               labels=trainlabels,
			               inputs=embed,
			               num_sampled=numsampled,
			               num_classes=vocabularysize))

		# Construct the SGD optimizer using a learning rate of 1.0.
		optimizer = tf.train.GradientDescentOptimizer(1.0).minimize(loss)

		# Compute the cosine similarity between minibatch examples and all embeddings.
		norm = tf.sqrt(tf.reduce_sum(tf.square(embeddings), 1, keepdims=True))
		normalizedembeddings = embeddings / norm
		validembeddings = tf.nn.embedding_lookup(normalizedembeddings, validdataset)
		similarity = tf.matmul(validembeddings, normalizedembeddings, transpose_b=True)

		# Add variable initializer.
		init = tf.global_variables_initializer()

	# Step 5: Begin training.
	numsteps = 100001
	numsteps = 50001

	activepoll.statusis('Training on the data')
	with tf.Session(graph=graph) as tensorflowsession:
		# We must initialize all variables before we use them.
		init.run()
		thedata = trainingbatch['data']
		theindex = trainingbatch['dataindex']
		averageloss = 0
		for step in range(numsteps):
			newbatch = tfgeneratetrainingbatch(batchsize, numberofskips, skipwindow, thedata, theindex)
			thedata = newbatch['data']
			theindex = newbatch['dataindex']
			feeddict = {traininputs: newbatch['batch'], trainlabels: newbatch['labels']}

			# We perform one update step by evaluating the optimizer op (including it
			# in the list of returned values for session.run()
			_, lossval = tensorflowsession.run([optimizer, loss], feed_dict=feeddict)
			averageloss += lossval

			if step % 10000 == 0:
				activepoll.statusis('At step {s} of {n} training runs'.format(s=step, n=numsteps))

			# if step % 2000 == 0:
			# 	if step > 0:
			# 		averageloss /= 2000
			# 	# The average loss is an estimate of the loss over the last 2000 batches.
			# 	print('Average loss at step ', step, ': ', averageloss)
			# 	averageloss = 0
			#
			# # print('codesmappedtowords', dataset['codesmappedtowords'])
			# # Note that this is expensive (~20% slowdown if computed every 500 steps)
			# if step % 10000 == 0:
			# 	sim = similarity.eval()
			# 	for i in range(max(validsize, len(dataset['codesmappedtowords'].keys()))):
			# 		try:
			# 			valid_word = dataset['codesmappedtowords'][validexamples[i]]
			# 		except IndexError as x:
			# 			print('ve', validexamples)
			# 			print(x)
			# 		top_k = 8  # number of nearest neighbors
			# 		nearest = (-sim[i, :]).argsort()[1:top_k + 1]
			# 		log_str = 'Nearest to %s:' % valid_word
			# 		for k in range(top_k):
			# 			close_word = dataset['codesmappedtowords'][nearest[k]]
			# 			log_str = '%s %s,' % (log_str, close_word)
			# 		print(log_str)

		finalembeddings = normalizedembeddings.eval()

	activepoll.statusis('Graphing the data')
	tsne = TSNE(perplexity=30, n_components=2, init='pca', n_iter=5000, method='exact')
	plotonly = min(500, vocabularysize)
	lowdimembs = tsne.fit_transform(finalembeddings[:plotonly, :])
	labels = [dataset['codesmappedtowords'][i] for i in range(plotonly)]
	tfplotwithlabels(lowdimembs, labels, os.path.join('.', 'testplot.png'))

	return