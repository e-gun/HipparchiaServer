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
from server.semanticvectors.vectordispatcher import findheadwords, vectorsentencedispatching
from server.semanticvectors.vectorhelpers import convertmophdicttodict
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
		sentences = vectorsentencedispatching(so, activepoll)
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

	sentencesaslists = [s.split(' ') for s in sentences]
	allwordsinorder = [item for sublist in sentencesaslists for item in sublist if item]

	setofallwords = set(allwordsinorder)
	morphdict = findheadwords(setofallwords)
	morphdict = convertmophdicttodict(morphdict)

	setofallheadwords = list()
	for w in setofallwords:
		# note that we are warping the shape of the sentences by doing this
		# an alternative is to '·'.join() the items
		try:
			setofallheadwords.extend([w for w in morphdict[w]])
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


def generatetfbatch(sentences, batchsize, windowsize, method='skipgram'):
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
			# tupledata was []
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

	# Declare model parameters
	batchsize = 100
	embeddingsize = 200
	vocabularysize = 10000
	generations = 100000
	generations = 25000
	print_loss_every = 2000
	print_valid_every = 5000

	numsampled = int(batchsize / 2)  # Number of negative examples to sample.
	windowsize = 2  # How many words to consider left and right.
	
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
	optimizer = tf.train.GradientDescentOptimizer(learning_rate=1.0).minimize(loss)

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
			activepoll.statusis('Loss at step {} : {}'.format(i + 1, loss_val))
			print("Loss at step {} : {}".format(i + 1, loss_val))

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

"""