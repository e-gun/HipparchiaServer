# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""
import collections
import locale
import math
import os
import random
import time

import numpy as np
from matplotlib import pyplot as plt

try:
	import tensorflow as tf
except ModuleNotFoundError:
	print('tensorflow unavailable')
	tf = None
try:
	from sklearn.manifold import TSNE
except ModuleNotFoundError:
	print('sklearn unavailable')
	TSNE = None

from random import randint

from server import hipparchia
from server.listsandsession.listmanagement import calculatewholeauthorsearches, compilesearchlist, flagexclusions
from server.listsandsession.whereclauses import configurewhereclausedata
from server.semanticvectors.preparetextforvectorization import vectorprepdispatcher
from server.semanticvectors.vectorhelpers import convertmophdicttodict, findheadwords
from server.semanticvectors.vectorpseudoroutes import emptyvectoroutput
from server.startup import authordict, listmapper, workdict


def tensorgraphelectedworks(activepoll, searchobject):
	"""

	adapted from https://raw.githubusercontent.com/tensorflow/tensorflow/r1.5/tensorflow/examples/tutorials/word2vec/word2vec_basic.py

	:param activepoll:
	:param searchobject:
	:return:
	"""

	starttime = time.time()

	tffunctiontocall = tftrainondata
	tffunctiontocall = tfnlptraining

	so = searchobject

	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c] == 'yes']

	if activecorpora:
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

	if len(searchlist) > 0:
		searchlist = flagexclusions(searchlist, so.session)
		workssearched = len(searchlist)
		searchlist = calculatewholeauthorsearches(searchlist, authordict)
		so.searchlist = searchlist

		indexrestrictions = configurewhereclausedata(searchlist, workdict, so)
		so.indexrestrictions = indexrestrictions

		# find all sentences
		activepoll.statusis('Finding all sentences')
		so.seeking = r'.'
		sentences = vectorprepdispatcher(so, activepoll)
		output = tffunctiontocall(sentences, activepoll)
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
	dataset = builddatasetdict(headwordsinorder, vocabularysize)

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
	# numsteps = 50001

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


def builddatasetdict(words, vocabularysize):
	"""

	adapted from the tensorflow tutorial

	:param words:
	:param vocabularysize:
	:return:
	"""

	count = [['UNK', -1]]
	count.extend(collections.Counter(words).most_common(vocabularysize - 1))
	dictionary = dict()
	for word, _ in count:
		dictionary[word] = len(dictionary)

	data = list()
	unk_count = 0
	for word in words:
		index = dictionary.get(word, 0)
		if index == 0:  # dictionary['UNK']
			unk_count += 1
		data.append(index)
	count[0][1] = unk_count
	reverseddictionary = dict(zip(dictionary.values(), dictionary.keys()))

	dataset = dict()
	dataset['listofcodes'] = data
	dataset['wordsandoccurrences'] = count
	dataset['wordsmappedtocodes'] = dictionary
	dataset['codesmappedtowords'] = reverseddictionary

	return dataset


def tfgeneratetrainingbatch(batchsize, numberofskips, skipwindow, thedata, dataindex):
	"""

	adapted from the tensorflow tutorial

	:param batchsize:
	:param numberofskips:
	:param skipwindow:
	:return:
	"""

	assert batchsize % numberofskips == 0
	assert numberofskips <= 2 * skipwindow
	batch = np.ndarray(shape=(batchsize), dtype=np.int32)
	labels = np.ndarray(shape=(batchsize, 1), dtype=np.int32)
	span = 2 * skipwindow + 1  # [ skipwindow target skipwindow ]
	buffer = collections.deque(maxlen=span)
	if dataindex + span > len(thedata):
		dataindex = 0
	buffer.extend(thedata[dataindex:dataindex + span])
	dataindex += span
	for i in range(batchsize // numberofskips):
		context_words = [w for w in range(span) if w != skipwindow]
		words_to_use = random.sample(context_words, numberofskips)
		for j, context_word in enumerate(words_to_use):
			batch[i * numberofskips + j] = buffer[skipwindow]
			labels[i * numberofskips + j, 0] = buffer[context_word]
		if dataindex == len(thedata):
			# buffer[:] = thedata[:span]
			# TypeError: sequence index must be integer, not 'slice'
			buffer = collections.deque(thedata[:span], maxlen=span)
			dataindex = span
		else:
			buffer.append(thedata[dataindex])
			dataindex += 1
	# Backtrack a little bit to avoid skipping words in the end of a batch
	dataindex = (dataindex + len(thedata) - span) % len(thedata)

	trainingbatch = dict()
	trainingbatch['batch'] = batch
	trainingbatch['labels'] = labels
	trainingbatch['data'] = thedata
	trainingbatch['dataindex'] = dataindex

	return trainingbatch


def tfplotwithlabels(low_dim_embs, labels, filename):
	"""

	also lifted from the tensorflow example code

	:param low_dim_embs:
	:param labels:
	:param filename:
	:return:
	"""
	assert low_dim_embs.shape[0] >= len(labels), 'More labels than embeddings'
	plt.figure(figsize=(18, 18))  # in inches
	for i, label in enumerate(labels):
		x, y = low_dim_embs[i, :]
		plt.scatter(x, y)
		plt.annotate(label,
		             xy=(x, y),
		             xytext=(5, 2),
		             textcoords='offset points',
		             ha='right',
		             va='bottom')

	plt.savefig(filename)

	return


## see: https://github.com/nfmcclure/tensorflow_cookbook/blob/master/07_Natural_Language_Processing/04_Working_With_Skip_Gram_Embeddings/04_working_with_skipgram.py


# acquire data

# normalize text

# build dictionary of words: {integerindex0: word0, integerindex1: word1, ...}

def tfnlptraining(sentences, activepoll):
	"""


	:param sentences:
	:param activepoll:
	:return:
	"""

	sentencesaslists = [s[1].split(' ') for s in sentences]
	allwordsinorder = [item for sublist in sentencesaslists for item in sublist if item]

	setofallwords = set(allwordsinorder)
	morphdict = findheadwords(setofallwords)
	morphdict = convertmophdicttodict(morphdict)

	setofallheadwords = list()
	joined = True
	if not joined:
		# FLATTENED lemmata
		for w in setofallwords:
			# note that we are warping the shape of the sentences by doing this
			# an alternative is to '·'.join() the items
			try:
				setofallheadwords.extend([w for w in morphdict[w]])
			except KeyError:
				pass
	else:
		# JOINED lemmata
		for w in setofallwords:
			# note that we are warping the shape of the sentences by doing this
			# an alternative is to '·'.join() the items
			try:
				setofallheadwords.append('·'.join(morphdict[w]))
			except KeyError:
				pass

	vocabularysize = min(10000, len(setofallheadwords))

	activepoll.statusis('Constructing dataset')
	dataset = builddatasetdict(setofallheadwords, vocabularysize)

	integermorphdict = dict()
	for wordform in morphdict:
		try:
			integermorphdict[wordform] = {dataset['wordsmappedtocodes'][w] for w in morphdict[wordform]}
		except KeyError:
			pass

	# integermorphdict looks like: {'lepidum': {33, 34}, 'habe': {32}, 'tum': {31}, ...}

	activepoll.statusis('Converting sentences to lists of integers')
	textasvals = converttexttoinexvalues(sentencesaslists, integermorphdict)
	textasvals = [t for t in textasvals if t]

	activepoll.statusis('Starting tensorflow work')
	similarities = tfnlpwork(textasvals, dataset['wordsmappedtocodes'], dataset['codesmappedtowords'], activepoll)

	print('similarities', similarities)

	return


def converttexttoinexvalues(sentences, morphdict):
	"""

	Turn text data into lists of integers from dictionary

	:param sentences:
	:param wordsmappedtocodes:
	:return:
	"""

	returndata = list()

	for s in sentences:
		newsentence = list()
		for word in s:
			try:
				hwds = [item for item in morphdict[word]]
				# NOTE: there is a big difference between adding all the possibilities and adding a joined version: '·'.join(hwds)
				newsentence.extend(hwds)
			except TypeError:
				pass
			except KeyError:
				pass
		# newsentence looks something like: [40, 39, 33, 34, 20, 21, 22, 2, 18, 19, 49, 50, 27, 5]
		returndata.append(newsentence)

	return returndata

# Generate data randomly (N words behind, target, N words ahead)


def generatetfbatch(sentences, batchsize, windowsize, method='cbow'):
	"""

	:param sentences:
	:param batchsize:
	:param windowsize:
	:param method:
	:return:
	"""

	batchdata = list()
	labeldata = list()

	while len(batchdata) < batchsize:
		randomsentence = np.random.choice(sentences)
		windowsequences = [randomsentence[max((n-windowsize), 0):(n+windowsize+1)] for n, m in enumerate(randomsentence)]
		itemsofinterest = [n if n < windowsize else windowsize for n, m in enumerate(windowsequences)]

		# Pull out center word of interest for each window and create a tuple for each window
		if method == 'skipgram':
			batchandlabels = [(x[y], x[:y] + x[(y+1):]) for x, y in zip(windowsequences, itemsofinterest)]
			# Make it in to a big list of tuples (target word, surrounding word)
			# e.g.: [(505, 78), (505, 597), (78, 505), (78, 597), (78, 328), (597, 505), (597, 78), (597, 328), (597, 366), (328, 78), (328, 597), (328, 366), (366, 597), (366, 328)]
			tupledata = [(x, y_) for x, y in batchandlabels for y_ in y]
		elif method == 'cbow':
			batchandlabels = [(x[:y] + x[(y + 1):], x[y]) for x, y in zip(windowsequences, itemsofinterest)]
			# Make it in to a big list of tuples (target word, surrounding word)
			tupledata = [(x_, y) for x, y in batchandlabels for x_ in x]
		else:
			raise ValueError('Method {m} not implemented yet.'.format(m=method))

		# extract batch and labels
		try:
			batch, labels = [list(x) for x in zip(*tupledata)]
		except ValueError:
			# tupledata was empty
			batch = list()
			labels = list()
		batchdata.extend(batch[:batchsize])
		labeldata.extend(labels[:batchsize])

	# Trim batch and label at the end
	batchdata = batchdata[:batchsize]
	labeldata = labeldata[:batchsize]

	# Convert to numpy array
	batchdata = np.array(batchdata)
	labeldata = np.transpose(np.array([labeldata]))

	thebatch = dict()
	thebatch['batchdata'] = batchdata
	thebatch['labeldata'] = labeldata

	return thebatch


def tfnlpwork(textasvals, wordsmappedtocodes, codesmappedtowords, activepoll):
	"""

	:return:
	"""

	valid_words = list()
	for i in range(0, min(len(textasvals), 5)):
		valid_words.append(codesmappedtowords[randint(0, len(codesmappedtowords))])

	valid_examples = [wordsmappedtocodes[x] for x in valid_words]
	print(valid_words)

	# Declare model parameters: first value is taken from the example code
	# An embedding is a mapping from discrete objects, such as words, to vectors of real numbers. For example, a 300-dimensional embedding for English words could include:...
	batchsize = 100
	batchsize = 50
	embeddingsize = 200
	vocabularysize = min(10000, len(codesmappedtowords))
	generations = 100000
	generations = 25000
	print_loss_every = 2000
	print_valid_every = 5000
	learning_rate = 1.0
	learning_rate = 0.1

	numsampled = int(batchsize / 2)  # Number of negative examples to sample.
	windowsize = 3  # How many words to consider left and right.
	
	# Define Embeddings:
	embeddings = tf.Variable(tf.random_uniform([vocabularysize, embeddingsize], -1.0, 1.0))

	# NCE loss parameters
	nceweights = tf.Variable(tf.truncated_normal([vocabularysize, embeddingsize], stddev=1.0 / np.sqrt(embeddingsize)))
	ncebiases = tf.Variable(tf.zeros([vocabularysize]))

	# Create data/target placeholders
	x_inputs = tf.placeholder(tf.int32, shape=[batchsize])
	y_target = tf.placeholder(tf.int32, shape=[batchsize, 1])
	valid_dataset = tf.constant(valid_examples, dtype=tf.int32)

	# Lookup the word embedding:
	embed = tf.nn.embedding_lookup(embeddings, x_inputs)

	# Get loss from prediction
	loss = tf.reduce_mean(tf.nn.nce_loss(weights=nceweights,
	                                     biases=ncebiases,
	                                     labels=y_target,
	                                     inputs=embed,
	                                     num_sampled=numsampled,
	                                     num_classes=vocabularysize))

	# Create optimizer
	optimizer = tf.train.GradientDescentOptimizer(learning_rate=learning_rate).minimize(loss)

	# Cosine similarity between words
	norm = tf.sqrt(tf.reduce_sum(tf.square(embeddings), 1, keepdims=True))
	normalizedembeddings = embeddings / norm
	valid_embeddings = tf.nn.embedding_lookup(normalizedembeddings, valid_dataset)
	similarity = tf.matmul(valid_embeddings, normalizedembeddings, transpose_b=True)

	# Add variable initializer.
	init = tf.global_variables_initializer()
	sess = tf.Session()
	sess.run(init)

	# Run the skip gram model.
	loss_vec = list()
	loss_x_vec = list()
	feeddict = dict()

	activepoll.statusis('Starting model: this could take a long time')
	for i in range(generations):
		mybatch = generatetfbatch(textasvals, batchsize, windowsize)
		feeddict = {x_inputs: mybatch['batchdata'], y_target: mybatch['labeldata']}

		# Run the train step
		sess.run(optimizer, feed_dict=feeddict)

		# Return the loss
		if (i + 1) % print_loss_every == 0:
			loss_val = sess.run(loss, feed_dict=feeddict)
			loss_vec.append(loss_val)
			loss_x_vec.append(i + 1)
			activepoll.statusis('Loss at step {} of {}: {}'.format(i + 1, generations, loss_val))

		# Validation: Print some random words and top 5 related words
		if (i + 1) % print_valid_every == 0:
			sim = sess.run(similarity, feed_dict=feeddict)
			for j in range(len(valid_words)):
				valid_word = codesmappedtowords[valid_examples[j]]
				top_k = 5  # number of nearest neighbors
				nearest = (-sim[j, :]).argsort()[1:top_k + 1]
				log_str = "Nearest to {}:".format(valid_word)
				for k in range(top_k):
					try:
						close_word = codesmappedtowords[nearest[k]]
						log_str = "%s %s," % (log_str, close_word)
					except KeyError:
						print('failed to find key for', k)
				print(log_str)

	similiarities = sess.run(similarity, feed_dict=feeddict)

	return similiarities

""""
Caesar, Civil War

['praestolor', 'consul', 'persuasus', 'depello', 'profecto']
2018-02-17 22:55:18.193969: I tensorflow/core/platform/cpu_feature_guard.cc:137] Your CPU supports instructions that this TensorFlow binary was not compiled to use: SSE4.2 AVX
Loss at step 2000 : 23.363452911376953
Loss at step 4000 : 2.2036380767822266
Nearest to praestolor: flumen, angustia, sumo, ina, forus,
Nearest to consul: praecipio, divinus, moratus², studium, muto¹,
Nearest to persuasus: angustum, tabernaculum, certo², praeacuo, legatio,
Nearest to depello: optume, mos, exposita, vestigium, gestus²,
Nearest to profecto: tela, liber¹, circus, causa, altum,
Loss at step 6000 : 1.556607723236084
Loss at step 8000 : 1.8531787395477295
Loss at step 10000 : 1.554192304611206
Nearest to praestolor: flumen, angustia, sumo, ina, forus,
Nearest to consul: divinus, praecipio, moratus², incitatio, conventus²,
Nearest to persuasus: angustum, tabernaculum, certo², praeacuo, legatio,
Nearest to depello: optume, mos, vestigium, gestus², mercenarius,
Nearest to profecto: tela, liber¹, circus, altum, alienatio,
Loss at step 12000 : 1.147690773010254
Loss at step 14000 : 2.003476619720459
Nearest to praestolor: flumen, forus, accipio, ina, angustia,
Nearest to consul: divinus, incitatio, praecipio, praeacuo, conventus²,
Nearest to persuasus: angustum, tabernaculum, certo², praeacuo, stativa,
Nearest to depello: mos, optume, vestigium, princeps, mercenarius,
Nearest to profecto: tela, altum, circus, liber¹, alienatio,
Loss at step 16000 : 1.7950029373168945
Loss at step 18000 : 1.3299369812011719
Loss at step 20000 : 1.9105793237686157
Nearest to praestolor: flumen, forus, ina, angustia, accipio,
Nearest to consul: divinus, incitatio, praecipio, captus², praeacuo,
Nearest to persuasus: angustum, praeacuo, tabernaculum, certo², stativa,
Nearest to depello: mos, vestigium, optume, legumen, mercenarius,
Nearest to profecto: tela, altum, liber¹, circus, divinus,
Loss at step 22000 : 1.388378620147705
Loss at step 24000 : 1.5698777437210083
Nearest to praestolor: flumen, forus, ina, allia, angustia,
Nearest to consul: divinus, incitatio, praeacuo, captus², obtrectatio,
Nearest to persuasus: angustum, praeacuo, tabernaculum, certo², stativa,
Nearest to depello: mos, vestigium, centurio¹, legumen, mercenarius,
Nearest to profecto: tela, altum, liber¹, divinus, alienatio,
similarities [[ 0.00406308  0.07302343  0.26531526 ... -0.00309991  0.0608354
  -0.04981409]
 [ 0.04587912  0.22984187  0.20147403 ...  0.03316061  0.13324411
  -0.0632373 ]
 [-0.02504043  0.15474978  0.16405106 ... -0.03804818  0.07038476
  -0.04413786]
 [-0.00551757  0.09003554  0.13273172 ... -0.16479288  0.01701138
   0.02178349]
 [ 0.01733876  0.29187733  0.062559   ... -0.05043877 -0.04319561
   0.07311901]]


BUT, gensim says the following of the neighborhood of consul:

0.963 	consulo 	
0.882 	senatus
0.882 	publico
0.867 	plebs
0.853 	publicum
0.851 	lex
0.851 	privo
0.85 	inimicus
0.844 	libet
0.842 	pleo
0.841 	oratio
0.837 	vox
0.833 	tribuo
0.829 	imperium
0.82 	lego²


a JOINED run:

['aedifico', 'adversarius·adversaria', 'quidem', 'coagmento·coagmentum', 'circumvenio']
Loss at step 2000 : 3.7477598190307617
Loss at step 4000 : 2.1834375858306885
Nearest to aedifico: pertineo, invitus, sacerdotium, praesidium, praecludo,
Nearest to adversarius·adversaria: fu, dius·divus, biennium, adsum, considero,
Nearest to quidem: defensio, potis, nullus, memini, mercenarius,
failed to find key for 3
failed to find key for 4
Nearest to coagmento·coagmentum: littera, navus·no¹·navis, concedo,
Nearest to circumvenio: aqua, deligo², adjuvo, seni, faveo,
Loss at step 6000 : 2.0464587211608887
Loss at step 8000 : 1.3909521102905273
Loss at step 10000 : 3.307637929916382
Nearest to aedifico: invitus, infestus, pertineo, claudo¹, praestolor,
Nearest to adversarius·adversaria: fu, dius·divus, biennium, considero, sedeo,
Nearest to quidem: defensio, mercenarius, potis, nullus, memini,
failed to find key for 2
failed to find key for 3
Nearest to coagmento·coagmentum: navus·no¹·navis, littera, concedo,
Nearest to circumvenio: seni, aqua, deligo², adjuvo, faveo,
Loss at step 12000 : 1.9680907726287842
Loss at step 14000 : 1.7793277502059937
Nearest to aedifico: invitus, infestus, pertineo, praestolor, apparatus²,
Nearest to adversarius·adversaria: fu, dius·divus, biennium, considero, sedeo,
Nearest to quidem: mercenarius, defensio, potis, memini, dens,
failed to find key for 2
failed to find key for 3
failed to find key for 4
Nearest to coagmento·coagmentum: navus·no¹·navis, littera,
Nearest to circumvenio: seni, deligo², adjuvo, aqua, faveo,
Loss at step 16000 : 1.7202776670455933
Loss at step 18000 : 2.041233539581299
Loss at step 20000 : 3.3179919719696045
Nearest to aedifico: invitus, vimineus, infestus, praestolor, claudo¹,
Nearest to adversarius·adversaria: fu, sedeo, biennium, dius·divus, considero,
Nearest to quidem: mercenarius, defensio, memini, potis, dens,
failed to find key for 2
failed to find key for 3
failed to find key for 4
Nearest to coagmento·coagmentum: navus·no¹·navis, littera,
Nearest to circumvenio: seni, adjuvo, deligo², aqua, rostrum,
Loss at step 22000 : 1.8857903480529785
Loss at step 24000 : 1.4803756475448608
Nearest to aedifico: invitus, praestolor, vimineus, infestus, apparatus²,
Nearest to adversarius·adversaria: fu, sedeo, biennium, dius·divus, considero,
Nearest to quidem: mercenarius, defensio, memini, dens, nullus,
failed to find key for 2
failed to find key for 3
Nearest to coagmento·coagmentum: navus·no¹·navis, littera, reduco,
Nearest to circumvenio: seni, deligo², adjuvo, faveo, rostrum,
similarities [[ 1.9295411e-03  1.8730892e-01  2.0729756e-01 ...  1.3278409e-02
  -6.0417712e-02 -2.0446607e-01]
 [ 4.0547360e-02  7.2905677e-05  3.9064221e-02 ...  3.7155230e-02
  -5.0242592e-02 -9.1756515e-02]
 [ 1.6467479e-01  2.4846146e-01  1.6734241e-01 ...  1.3284846e-01
   1.5371240e-02 -1.4059354e-01]
 [ 8.2497887e-02  8.5548811e-02  4.2694062e-02 ...  1.1676947e-02
  -3.1849176e-02 -1.1821497e-01]
 [ 5.7438657e-02  2.7344361e-01  2.4401173e-01 ... -7.1074270e-02
  -6.3520081e-02 -3.3145533e-03]]

gensim says of circumvenio:

0.821 	refugio 	

[vector graph]
0.809 	procurro
0.799 	expedio
0.794 	antecedo
0.793 	sinister
0.787 	sagittarius
0.774 	sagittarii
0.773 	cornus¹
0.772 	subsequor
0.771 	cornu
0.771 	appropinquo
0.757 	sinistrum
0.753 	impono
0.748 	medius
0.747 	cratis



adjust batch size and learning rate

['responsus²·respondeo·responsum', 'creditor', 'pecunia', 'verbum', 'mobilitas·mobilito']
2018-02-17 23:32:21.979190: I tensorflow/core/platform/cpu_feature_guard.cc:137] Your CPU supports instructions that this TensorFlow binary was not compiled to use: SSE4.2 AVX
Loss at step 2000 : 26.524118423461914
Loss at step 4000 : 13.660235404968262
Nearest to responsus²·respondeo·responsum: duoviri·duumvira, praepono, sentina, incendo, intervallum·intervallo,
Nearest to creditor: siquando, peritus·peritissimus·pereo, propinquus·propinqua, inclino, custos,
Nearest to pecunia: praesidium, provincia, impedio, teneo, dimitto,
Nearest to verbum: artificium, exercio, celeriter, urbs, procurro,
Nearest to mobilitas·mobilito: protectum·protego, heres, vulgo¹·vulgo²·vulgus, totidem, tenue·tenuis,
Loss at step 6000 : 8.003875732421875
Loss at step 8000 : 5.492268085479736
Loss at step 10000 : 3.49160099029541
Nearest to responsus²·respondeo·responsum: praepono, duoviri·duumvira, sentina, incendo, intervallum·intervallo,
Nearest to creditor: siquando, altitudo, peritus·peritissimus·pereo, propinquus·propinqua, inclino,
Nearest to pecunia: praesidium, impedio, existimatio, provincia, teneo,
Nearest to verbum: artificium, exercio, celeriter, urbs, procurro,
Nearest to mobilitas·mobilito: protectum·protego, heres, vulgo¹·vulgo²·vulgus, totidem, tenue·tenuis,
Loss at step 12000 : 4.995999336242676
Loss at step 14000 : 3.8147058486938477
Nearest to responsus²·respondeo·responsum: praepono, sentina, duoviri·duumvira, diluo, incendo,
Nearest to creditor: siquando, altitudo, propius, inclino, navigium,
Nearest to pecunia: existimatio, impedio, praesidium, filius, provincia,
Nearest to verbum: artificium, exercio, celeriter, hospitium, quattuor,
Nearest to mobilitas·mobilito: protectum·protego, vulgo¹·vulgo²·vulgus, totidem, heres, tenue·tenuis,
Loss at step 16000 : 2.5549161434173584
Loss at step 18000 : 2.640185832977295
Loss at step 20000 : 2.1628966331481934
Nearest to responsus²·respondeo·responsum: praepono, sentina, duoviri·duumvira, diluo, incendo,
Nearest to creditor: siquando, altitudo, propius, inclino, navigium,
Nearest to pecunia: existimatio, impedio, praesidium, erigo, filius,
Nearest to verbum: artificium, exercio, quattuor, hospitium, celeriter,
Nearest to mobilitas·mobilito: protectum·protego, vulgo¹·vulgo²·vulgus, totidem, tenue·tenuis, heres,
Loss at step 22000 : 2.5759263038635254
Loss at step 24000 : 2.1635682582855225
Nearest to responsus²·respondeo·responsum: praepono, sentina, duoviri·duumvira, diluo, intervallum·intervallo,
Nearest to creditor: siquando, altitudo, propius, navigium, inclino,
Nearest to pecunia: existimatio, impedio, erigo, praesidium, filius,
Nearest to verbum: artificium, quattuor, hospitium, exercio, celeriter,
Nearest to mobilitas·mobilito: protectum·protego, vulgo¹·vulgo²·vulgus, tenue·tenuis, totidem, heres,
similarities [[ 0.05868693  0.10331594  0.0624117  ...  0.1866371   0.0187183
   0.0290859 ]
 [ 0.06022784  0.1057726   0.01363345 ... -0.02199721 -0.00560955
  -0.03184037]
 [ 0.01173329  0.10875327  0.25501138 ...  0.01903673  0.07664359
  -0.03135491]
 [ 0.22421081  0.15741768  0.19507284 ... -0.0823223   0.10735729
  -0.02112347]
 [ 0.06104147 -0.03684769  0.06346136 ... -0.06775664  0.1211601
  -0.10587066]]


['voveo', 'digredior', 'acer²', 'versor', 'exaedifico']
Loss at step 2000 : 45.394344329833984
Loss at step 4000 : 23.24372100830078
Nearest to voveo: merces¹, excursus², dispersero¹, quini, amico,
Nearest to digredior: andrius, triduum, coeptum, innascor, necessitudo,
Nearest to acer²: indo, pauci, gloria, pulsus², barbarus,
Nearest to versor: turris, facio, praeficio, no¹, eques,
Nearest to exaedifico: timidus, neco, elices, intervallo, noto,
Loss at step 6000 : 12.286938667297363
Loss at step 8000 : 6.055044651031494
Loss at step 10000 : 4.871432304382324
Nearest to voveo: merces¹, excursus², quini, dispersero¹, amico,
Nearest to digredior: absum, fortis, necessitudo, triduum, andrius,
Nearest to acer²: pauci, indo, parvus, barbarus, permoveo,
Nearest to versor: turris, praeficio, facio, no¹, sus,
Nearest to exaedifico: timidus, neco, elices, intervallo, noto,
Loss at step 12000 : 2.7527472972869873
Loss at step 14000 : 6.896480083465576
Nearest to voveo: merces¹, excursus², quini, dispersero¹, profero,
Nearest to digredior: absum, fortis, triduum, angustum, necessitudo,
Nearest to acer²: indo, pauci, barbarus, pulsus², parvus,
Nearest to versor: praeficio, turris, facio, no¹, corpus,
Nearest to exaedifico: timidus, locum, neco, levis¹, noto,
Loss at step 16000 : 3.1658027172088623
Loss at step 18000 : 2.5402045249938965
Loss at step 20000 : 2.8434066772460938
Nearest to voveo: merces¹, excursus², quini, profero, amico,
Nearest to digredior: fortis, absum, angustum, triduum, necessitudo,
Nearest to acer²: indo, pauci, pulsus², barbarus, regia,
Nearest to versor: praeficio, turris, facio, no¹, corpus,
Nearest to exaedifico: locum, timidus, levis¹, neco, noto,
Loss at step 22000 : 1.186185359954834
Loss at step 24000 : 1.6347655057907104
Nearest to voveo: merces¹, excursus², quini, profero, dispersero¹,
Nearest to digredior: triduum, angustum, fortis, absum, necessitudo,
Nearest to acer²: indo, pauci, pulsus², regia, barbarus,
Nearest to versor: praeficio, turris, facio, iniquitas, no¹,
Nearest to exaedifico: timidus, locum, levis¹, neco, noto,
similarities [[ 0.06946201  0.0188651   0.13538174 ...  0.02524121  0.10198931
  -0.06715611]
 [ 0.07158905  0.17657521  0.10853659 ...  0.00163822  0.06703465
   0.19781666]
 [-0.087439    0.16681887  0.06178586 ...  0.16035926 -0.02021601
   0.05312629]
 [ 0.12657799  0.07908393  0.2619318  ...  0.11901414 -0.05133739
   0.17418306]
 [ 0.10359956  0.00798041  0.11965031 ...  0.09680425 -0.0171023
   0.02591592]]
[2018-02-17 23:38:17,219] ERROR in app: Exception on /executesearch/1518928617927 [GET]
Traceback (most recent call last):
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/flask/app.py", line 1982, in wsgi_app
    response = self.full_dispatch_request()
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/flask/app.py", line 1615, in full_dispatch_request
    return self.finalize_request(rv)
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/flask/app.py", line 1630, in finalize_request
    response = self.make_response(rv)
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/flask/app.py", line 1725, in make_response
    raise ValueError('View function did not return a response')
ValueError: View function did not return a response


Verrine orations

['reservo', 'stultus', 'animadversio', 'barbarus', 'orator']
2018-02-18 07:58:10.575131: I tensorflow/core/platform/cpu_feature_guard.cc:137] Your CPU supports instructions that this TensorFlow binary was not compiled to use: SSE4.2 AVX
Loss at step 2000 : 51.33185958862305
Loss at step 4000 : 29.942792892456055
Nearest to reservo: conicio, corruptela, nummulus, neglegentia, duo,
Nearest to stultus: hibernum, dacius, addictus, oleum, aedificatio,
Nearest to animadversio: turibulum, humanus, aro, pertinax, planus²,
Nearest to barbarus: aversor², liberalis¹, rapina¹, columna, puto,
Nearest to orator: intestatus², glaeba, captivus, centiens, reticeo,
Loss at step 6000 : 22.848176956176758
Loss at step 8000 : 3.9753808975219727
Loss at step 10000 : 4.402499198913574
Nearest to reservo: conicio, duo, cella, pecunia, mirandus,
Nearest to stultus: hibernum, mirus, addictus, dacius, oleum,
Nearest to animadversio: turibulum, humanus, aro, pertinax, planus²,
Nearest to barbarus: aversor², puto, liberalis¹, columna, rapina¹,
Nearest to orator: intestatus², glaeba, captivus, centiens, reticeo,
Loss at step 12000 : 9.873517990112305
Loss at step 14000 : 10.272629737854004
Nearest to reservo: conicio, duo, cella, pecunia, civis,
Nearest to stultus: hibernum, mirus, debeo, restituo, publicus,
Nearest to animadversio: turibulum, aro, humanus, pertinax, planus²,
Nearest to barbarus: liberalis¹, aversor², puto, columna, rapina¹,
Nearest to orator: glaeba, intestatus², captivus, reticeo, centiens,
Loss at step 16000 : 2.162527561187744
Loss at step 18000 : 2.5864920616149902
Loss at step 20000 : 4.323953628540039
Nearest to reservo: duo, conicio, cella, pecunia, mirandus,
Nearest to stultus: hibernum, mirus, restituo, debeo, praesens,
Nearest to animadversio: aro, turibulum, humanus, planus², pertinax,
Nearest to barbarus: liberalis¹, columna, puto, morior, aversor²,
Nearest to orator: glaeba, intestatus², captivus, reticeo, centiens,
Loss at step 22000 : 5.008556842803955
Loss at step 24000 : 2.7152037620544434
Nearest to reservo: conicio, duo, cella, mirandus, pecunia,
Nearest to stultus: hibernum, mirus, restituo, praesens, debeo,
Nearest to animadversio: aro, turibulum, humanus, planus², pars,
Nearest to barbarus: liberalis¹, columna, puto, morior, aversor²,
Nearest to orator: glaeba, intestatus², captivus, reticeo, centiens,
similarities [[ 0.02465165  0.0539796   0.12021755 ...  0.13269116  0.06007751
  -0.01891185]
 [ 0.1109712   0.10961493  0.2815597  ...  0.09188539  0.11949956
  -0.1075343 ]
 [ 0.05473766  0.01427753  0.04326814 ... -0.06925254  0.04596263
  -0.058966  ]
 [ 0.01056252  0.09540829  0.07056317 ...  0.01720598  0.1845353
  -0.02027962]
 [-0.03540321  0.04929211 -0.05362207 ...  0.11060964  0.02615426
   0.06637716]]
[2018-02-18 08:01:12,323] ERROR in app: Exception on /executesearch/1518958681950 [GET]
Traceback (most recent call last):
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/flask/app.py", line 1982, in wsgi_app
    response = self.full_dispatch_request()
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/flask/app.py", line 1615, in full_dispatch_request
    return self.finalize_request(rv)
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/flask/app.py", line 1630, in finalize_request
    response = self.make_response(rv)
  File "/Users/erik/hipparchia_venv/lib/python3.6/site-packages/flask/app.py", line 1725, in make_response
    raise ValueError('View function did not return a response')
ValueError: View function did not return a response


CBOW in Cicero's ad atticum

['spolio', 'desertum', 'verro', 'praetorius', 'gravitas']
2018-02-18 08:13:54.283609: I tensorflow/core/platform/cpu_feature_guard.cc:137] Your CPU supports instructions that this TensorFlow binary was not compiled to use: SSE4.2 AVX
Loss at step 2000 : 50.167720794677734
Loss at step 4000 : 35.51740646362305
Nearest to spolio: animo, μεθαρμόζω, lacerta, hostio¹, dormio,
Nearest to desertum: scitus², corpus, avis, resido, asspico,
Nearest to verro: questus², recognosco, prosum, optime, fastus¹,
Nearest to praetorius: capio, sortitus, struma¹, quaero, discrepo,
Nearest to gravitas: πάτρα, obtego, τεχνολογία, aris², accido²,
Loss at step 6000 : 28.08907699584961
Loss at step 8000 : 12.777727127075195
Loss at step 10000 : 12.256503105163574
Nearest to spolio: animo, μεθαρμόζω, acte², hostio¹, lacerta,
Nearest to desertum: scitus², corpus, avis, resido, asspico,
Nearest to verro: questus², recognosco, prosum, igitur, asscribo,
Nearest to praetorius: capio, quaero, sortitus, struma¹, impedio,
Nearest to gravitas: πάτρα, obtego, accido², rescribo, locum,
Loss at step 12000 : 19.29497718811035
Loss at step 14000 : 11.959770202636719
Nearest to spolio: animo, μεθαρμόζω, acte², conturbo, hostio¹,
Nearest to desertum: scitus², corpus, avis, resido, acervus,
Nearest to verro: questus², prosum, igitur, conficio, asscribo,
Nearest to praetorius: capio, quaero, sortitus, struma¹, impedio,
Nearest to gravitas: πάτρα, accido², rescribo, locum, nosco,
Loss at step 16000 : 4.654924392700195
Loss at step 18000 : 5.507625579833984
Loss at step 20000 : 6.700153350830078
Nearest to spolio: animo, μεθαρμόζω, acte², conturbo, hostio¹,
Nearest to desertum: scitus², corpus, avis, resido, praesens,
Nearest to verro: prosum, questus², conficio, optime, accido²,
Nearest to praetorius: capio, quaero, impedio, amicus², delibero,
Nearest to gravitas: accido², rescribo, locum, πάτρα, nosco,
Loss at step 22000 : 3.191617965698242
Loss at step 24000 : 5.831408500671387
Nearest to spolio: animo, μεθαρμόζω, acte², conturbo, duco,
Nearest to desertum: scitus², corpus, avis, praesens, resido,
Nearest to verro: prosum, questus², optime, conficio, accido²,
Nearest to praetorius: capio, quaero, impedio, amicus², delibero,
Nearest to gravitas: accido², rescribo, locum, lectus, rectum,
similarities [[-0.01589521  0.17148384  0.12973797 ...  0.02516987 -0.07128377
  -0.02328461]
 [ 0.01277893  0.03365164  0.05617415 ...  0.03673007  0.19661224
  -0.06634295]
 [ 0.00991528  0.24858929  0.17016412 ...  0.06293859  0.01890729
  -0.16503449]
 [ 0.00711736  0.21280469  0.14851825 ...  0.07084265 -0.03677169
   0.07868067]
 [-0.09484798  0.1269372   0.03407417 ... -0.00843405  0.07157806
   0.01010384]]

vs gensim on gravitas:

0.729 	praecipio 	
0.675 	perpetuus
0.668 	revoco
0.661 	offex
0.66 	plenum
0.659 	conservo
0.654 	perpetuum
0.648 	decretum
0.647 	plenus
0.644 	forensis
0.64 	auctoro
0.631 	existimatio
0.627 	imperator
0.625 	concurro
0.624 	honor


CBOW + joined on Cicero, Ad Atticum

['cano', 'nauta', 'abjungo', 'peccatum·pecco', 'pertimeo·pertimesco']
2018-02-18 08:21:40.194598: I tensorflow/core/platform/cpu_feature_guard.cc:137] Your CPU supports instructions that this TensorFlow binary was not compiled to use: SSE4.2 AVX
Loss at step 2000 : 32.10240173339844
Loss at step 4000 : 13.151476860046387
Nearest to cano: placeo·placo, contubernalis, aliter, ϲεμνόϲ, eloquentia,
Nearest to nauta: locus·locum·loco, copis¹·copia¹, aliquis·aliqui, minuo, illustro,
Nearest to abjungo: secunda·secundus¹·secundo², paro¹·paro²·paratus², vicis·vicus, volito, custodia,
Nearest to peccatum·pecco: exsolvo, verro·versus³·versum·verto, avello, funditus, monstrum·monstro,
Nearest to pertimeo·pertimesco: βουλεύω, caelus·caelum¹·caelum², labo, calidus, singillatim,
Loss at step 6000 : 18.458942413330078
Loss at step 8000 : 4.209968566894531
Loss at step 10000 : 7.159870147705078
Nearest to cano: placeo·placo, contubernalis, aliter, ϲεμνόϲ, eloquentia,
Nearest to nauta: locus·locum·loco, copis¹·copia¹, aliquis·aliqui, illustro, labefacto,
Nearest to abjungo: secunda·secundus¹·secundo², paro¹·paro²·paratus², vicis·vicus, volito, reconcilio,
Nearest to peccatum·pecco: exsolvo, verro·versus³·versum·verto, avello, monstrum·monstro, frustro·frustra,
Nearest to pertimeo·pertimesco: βουλεύω, caelus·caelum¹·caelum², labo, singillatim, iambus,
Loss at step 12000 : 8.852496147155762
Loss at step 14000 : 5.321883678436279
Nearest to cano: placeo·placo, contubernalis, aliter, ϲεμνόϲ, eloquentia,
Nearest to nauta: locus·locum·loco, copis¹·copia¹, aliquis·aliqui, illustro, labefacto,
Nearest to abjungo: secunda·secundus¹·secundo², paro¹·paro²·paratus², reconcilio, custodia, pacificatio,
Nearest to peccatum·pecco: exsolvo, verro·versus³·versum·verto, avello, monstrum·monstro, frustro·frustra,
Nearest to pertimeo·pertimesco: βουλεύω, caelus·caelum¹·caelum², iambus, singillatim, ὑπόϲταϲιϲ,
Loss at step 16000 : 7.495054721832275
Loss at step 18000 : 5.299540996551514
Loss at step 20000 : 4.432943344116211
Nearest to cano: placeo·placo, contubernalis, aliter, ϲεμνόϲ, eloquentia,
Nearest to nauta: locus·locum·loco, copis¹·copia¹, aliquis·aliqui, illustro, labefacto,
Nearest to abjungo: secunda·secundus¹·secundo², paro¹·paro²·paratus², reconcilio, vicis·vicus, volito,
Nearest to peccatum·pecco: exsolvo, verro·versus³·versum·verto, avello, monstrum·monstro, frustro·frustra,
Nearest to pertimeo·pertimesco: βουλεύω, caelus·caelum¹·caelum², ὑπόϲταϲιϲ, hortulus, iambus,
Loss at step 22000 : 4.634878635406494
Loss at step 24000 : 4.9213972091674805
Nearest to cano: placeo·placo, aliter, contubernalis, ϲεμνόϲ, eloquentia,
Nearest to nauta: locus·locum·loco, copis¹·copia¹, aliquis·aliqui, labefacto, illustro,
Nearest to abjungo: secunda·secundus¹·secundo², paro¹·paro²·paratus², reconcilio, pacificatio, acerbum·acerbus,
Nearest to peccatum·pecco: exsolvo, verro·versus³·versum·verto, avello, monstrum·monstro, frustro·frustra,
Nearest to pertimeo·pertimesco: βουλεύω, caelus·caelum¹·caelum², ὑπόϲταϲιϲ, iambus, hortulus,
similarities [[-0.07444538  0.00016824  0.05655763 ... -0.00711618 -0.03579539
   0.01444323]
 [ 0.02131999  0.01714435 -0.03222964 ...  0.00023356  0.07354401
  -0.11851147]
 [-0.04277072  0.06155002 -0.06350119 ...  0.07324563  0.11557309
  -0.01381822]
 [ 0.01624409  0.04151002 -0.03002328 ...  0.0027299   0.03504315
  -0.06000794]
 [ 0.1432774  -0.05004353 -0.04265362 ... -0.01479933  0.12889808
  -0.01326656]]
  
vs pecco in gensim

0.907 	peccatum 	
0.693 	dedecus
0.654 	vitium
0.653 	affligo
0.651 	desino
0.631 	consolor
0.617 	consolo
0.617 	socius
0.608 	vitio
0.602 	impono
0.596 	invidia
0.594 	suspicio²
0.594 	luctus
0.592 	domestici
0.59 	lugeo

"""