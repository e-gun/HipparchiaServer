# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-20
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import json
import random
import re

from io import BytesIO
from multiprocessing import current_process

from server.formatting.jsformatting import generatevectorjs
from server.hipparchiaobjects.searchobjects import SearchOutputObject

from server.hipparchiaobjects.vectorobjects import VectorValues

# https://matplotlib.org/faq/howto_faq.html#matplotlib-in-a-web-application-server
# do this before importing pylab or pyplot: otherwise you will see:
#   RuntimeError: main thread is not in main loop
#   Tcl_AsyncDelete: async handler deleted by the wrong thread

# you also want a noninteractive backend; allegedly 'agg' is one, but that behavior changed with
# matplotlib-2.2.3 --> 3.0.0
# now it launches IPython even though you don't want it...
#
# How to use Matplotlib in a web application server
# In general, the simplest solution when using Matplotlib in a web server is to completely avoid using pyplot
# (pyplot maintains references to the opened figures to make show work, but this will cause memory leaks unless
# the figures are properly closed). Since Matplotlib 3.1, one can directly create figures using the Figure constructor
# and save them to in-memory buffers. The following example uses Flask, but other frameworks work similarly: ...
#
# BUT, a plt contains many, many objects of which a Figure() is only one. It would take a lot of rewriting?
#
from server.semanticvectors.vectorhelpers import reducetotwodimensions

try:
	import matplotlib
	matplotlib.use('Agg')
	import matplotlib.pyplot as plt
	# from matplotlib.figure import Figure
	import networkx as nx
	import numpy as np
	from sklearn.manifold import TSNE
	from sklearn.decomposition import PCA
	from sklearn.cluster import KMeans
	from umap import UMAP
	# see below on a versioning problem with matplotlib. It *seems* to be fixed but the commented-out code should linger
	# for a little while

	# from pkg_resources import get_distribution as checkversion
	# from packaging.version import parse as versionparse
	# from server.formatting.miscformatting import consolewarning
	#
	# ml = checkversion("matplotlib").version
	# validmll = '3.1.3'
	# invalidmpl = '3.2.0'
	#
	# if versionparse(ml) > versionparse(validmll):
	# 	consolewarning('\tvector graphing is BROKEN if you use the 3.2.x branch of matplotlib\t', color='red',
	# 	               isbold=True, baremessage=True)
	# 	consolewarning('\tyou have version {v} installed\t'.format(v=ml), color='red', isbold=True, baremessage=True)
	# 	consolewarning('\tconsider forcing the last known good version:\t', color='red', isbold=True, baremessage=True)
	# 	consolewarning('\t"~/hipparchia_venv/bin/pip install matplotlib=={v}"\t'.format(v=validmll), color='red',
	# 	               isbold=True, baremessage=True)
except ModuleNotFoundError as e:
	if current_process().name == 'MainProcess':
		print('required math module(s) not available:')
		print('\t{e}'.format(e=e))
	matplotlib = None
	plt = None
	nx = None
	np = None
	TSNE = None
	PCA = None
	UMAP = None
	Kmeans = None

import psycopg2

from server import hipparchia
from server.dbsupport.tablefunctions import assignuniquename
from server.dbsupport.vectordbfunctions import createstoredimagestable
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.startup import authordict, workdict


def graphbliteraldistancematches(searchterm, mostsimilartuples, searchobject):
	"""

	mostsimilartuples [('γράφω', 0.6708203932499369), ('εἰκών', 0.447213595499958), ('τρέχω', 0.447213595499958), ...]

	:param searchterm:
	:param mostsimilartuples:
	:param vectorspace:
	:param searchlist:
	:return:
	"""

	vv = searchobject.vectorvalues
	mostsimilartuples = [t for t in mostsimilartuples if t[1] > vv.localcutoffdistance]
	mostsimilartuples = mostsimilartuples[:vv.neighborscap]

	terms = [searchterm] + [t[0] for t in mostsimilartuples]

	# interrelationships = {t: caclulatecosinevalues(t, vectorspace, terms) for t in terms}

	relevantconnections = dict()

	title = givetitletograph('Words most concretely connected with', searchterm, searchobject)
	imagename = graphmatches(title, searchterm, searchobject, mostsimilartuples, terms, relevantconnections, vtype='rudimentary')

	return imagename


def graphnnmatches(searchterm, mostsimilartuples, vectorspace, searchobject):
	"""

	tuples come in a list and look like:
		[('ὁμολογέω', 0.8400295972824097), ('θέα', 0.8328431844711304), ('θεά', 0.8282027244567871), ...]

	:param searchterm:
	:param mostsimilartuples:
	:param vectorspace:
	:return:
	"""

	terms = [searchterm] + [t[0] for t in mostsimilartuples]

	interrelationships = {t: vectorspace.wv.most_similar(t) for t in terms}

	relevantconnections = dict()
	for i in interrelationships:
		# keep the network focused
		relevantconnections[i] = [sim for sim in interrelationships[i] if sim[0] in terms]
		# relevantconnections[i] = [s for s in interrelationships[i] if s[1] > hipparchia.config['VECTORDISTANCECUTOFFNEARESTNEIGHBOR']]

	title = givetitletograph('Conceptual neighborhood of', searchterm, searchobject)

	imagename = graphmatches(title, searchterm, searchobject, mostsimilartuples, terms, relevantconnections, vtype='nn')

	return imagename


def graphmatches(graphtitle, searchterm, searchobject, mostsimilartuples, terms, relevantconnections, vtype):
	# fnc = bokehgraphmatches
	fnc = matplotgraphmatches
	return fnc(graphtitle, searchterm, searchobject, mostsimilartuples, terms, relevantconnections, vtype)


def matplotgraphmatches(graphtitle, searchterm, searchobject, mostsimilartuples, terms, relevantconnections, vtype):
	"""

	mostsimilartuples come in a list and look like:
		[('ὁμολογέω', 0.8400295972824097), ('θέα', 0.8328431844711304), ('θεά', 0.8282027244567871), ...]

	relevantconnections is a dict each of whose keyed entries unpacks into a mostsimilartuples-like list

	consider shifting to bokeh? can have clickable bubbles, etc

		https://github.com/bokeh/bokeh/blob/master/examples/models/file/graphs.py

		http://bokeh.pydata.org/en/latest/docs/user_guide/graph.html#userguide-graph

	:param searchterm:
	:param mostsimilartuples:
	:param vectorspace:
	:param searchlist:
	:return:
	"""

	plt.figure(figsize=(18, 18))

	plt.title(graphtitle, fontsize=24)

	graph = nx.Graph()

	for t in terms:
		graph.add_node(t)

	for r in relevantconnections:
		graph.add_node(r)

	edgelist = list()
	for t in mostsimilartuples:
		edgelist.append((searchterm, t[0], round(t[1]*10, 2)))

	for r in relevantconnections:
		for c in relevantconnections[r]:
			edgelist.append((r, c[0], round(c[1]*10, 2)))

	graph.add_weighted_edges_from(edgelist)
	edgelabels = {(u, v): d['weight'] for u, v, d in graph.edges(data=True)}

	pos = nx.fruchterman_reingold_layout(graph)

	# colors: https://matplotlib.org/examples/color/colormaps_reference.html
	# cmap='tab20c' or 'Pastel1' is nice; lower alpha makes certain others more appealing

	scalednodes = [1200 * t[1] * 10 for t in mostsimilartuples]
	# scalednodes = [1200 * (t[1] ** 2.5) * 10 for t in mostsimilartuples]

	#
	# FYI: matplotlib 3.2.0 exception
	#
	# see https://github.com/matplotlib/matplotlib/issues/16739
	# @tacaswell had the solutIon: just pad the array...

	# see _axes.py 4386: len(s), x.size 15 16
	# but s needs to be the same size as x....: 16 & 16
	# s is what we send as scalednodes
	#     def scatter(self, x, y, s=None, c=None, marker=None, cmap=None, norm=None,
	#                 vmin=None, vmax=None, alpha=None, linewidths=None,
	#                 verts=None, edgecolors=None, *, plotnonfinite=False,
	#                 **kwargs):
	#
	#         A scatter plot of *y* vs. *x* with varying marker size and/or color.
	#
	#         Parameters
	#         ----------
	#         x, y : scalar or array-like, shape (n, )
	#             The data positions.
	#
	#         s : scalar or array-like, shape (n, ), optional
	#             The marker size in points**2.
	#             Default is ``rcParams['lines.markersize'] ** 2``.

	scalednodes.append(0)
	nx.draw_networkx_nodes(graph, pos, node_size=scalednodes, alpha=0.75, node_color=range(len(terms)), cmap='Pastel1')
	nx.draw_networkx_labels(graph, pos, font_size=20, font_family='sans-serif', font_color='Black')

	# edges
	nx.draw_networkx_edges(graph, pos, width=3, alpha=0.85, edge_color='dimgrey')
	nx.draw_networkx_edge_labels(graph, pos, edgelabels, font_size=12, alpha=0.8, label_pos=0.5, font_family='sans-serif')

	# the fine print
	plt.text(0, -1.1, generatethefineprint(vtype, searchobject.vectorvalues), ha='center', va='bottom')
	# plt.text(1, -1, 'gensim', ha='center', va='bottom')
	# plt.text(-1, -1, '@commit {v}'.format(v=readgitdata()[0:5]), ha='center', va='bottom')

	plt.axis('off')
	# plt.savefig('matchesgraph.png')
	graphobject = BytesIO()
	plt.savefig(graphobject)
	plt.clf()
	plt.close()

	# getvalue(): Return bytes containing the entire contents of the buffer
	# everybody from here on out want bytes and not '_io.BytesIO'
	graphobject = graphobject.getvalue()

	imagename = storevectorgraph(graphobject)

	return imagename


def storevectorgraph(figureasbytes):
	"""

	store a graph in the image table so that you can subsequently display it in the browser

	note that images get deleted after use

	also note that we hand the data to the db and then immediatel grab it out of the db because of
	constraints imposed by the way flask works

	:param figureasbytes:
	:return:
	"""

	dbconnection = ConnectionObject(ctype='rw')
	dbconnection.setautocommit()
	cursor = dbconnection.cursor()

	# avoid psycopg2.DataError: value too long for type character varying(12)
	randomid = assignuniquename(12)

	q = """
	INSERT INTO public.storedvectorimages 
		(imagename, imagedata)
		VALUES (%s, %s)
	"""

	d = (randomid, figureasbytes)
	try:
		cursor.execute(q, d)
	except psycopg2.ProgrammingError:
		# psycopg2.ProgrammingError: relation "public.storedvectorimages" does not exist
		createstoredimagestable()
		cursor.execute(q, d)

	# print('stored {n} in vector image table'.format(n=randomid))

	dbconnection.connectioncleanup()

	return randomid


def fetchvectorgraph(imagename):
	"""

	grab a graph in the image table so that you can subsequently display it in the browser

	note that images get deleted after use

	also note that we hand the data to the db and then immediatel grab it out of the db because of
	constraints imposed by the way flask works

	:param imagename:
	:return:
	"""

	if hipparchia.config['RETAINFIGURES']:
		deletewhendone = False
	else:
		deletewhendone = True

	dbconnection = ConnectionObject(ctype='rw')
	dbconnection.setautocommit()
	cursor = dbconnection.cursor()

	q = 'SELECT imagedata FROM public.storedvectorimages WHERE imagename=%s'
	d = (imagename,)

	cursor.execute(q, d)

	imagedata = cursor.fetchone()
	# need to convert to bytes, otherwise:
	# AttributeError: 'memoryview' object has no attribute 'read'
	imagedata = bytes(imagedata[0])

	# print('fetched {n} from vector image table'.format(n=randomid))

	# now we should delete the image because we are done with it

	if deletewhendone:
		q = 'DELETE FROM public.storedvectorimages WHERE imagename=%s'
		d = (imagename,)
		cursor.execute(q, d)

	dbconnection.connectioncleanup()

	return imagedata


def givetitletograph(topic, searchterm, searchobject):
	"""

	generate a title for the graph

	:return:
	"""

	so = searchobject

	less = str()
	if so.session['trimvectoryby'] != 'none' and (so.session['nearestneighborsquery'] or so.session['analogyfinder']):
		if so.session['trimvectoryby'] == 'conjugated':
			less = ' (w/ unconjugated forms omitted)'
		if so.session['trimvectoryby'] == 'declined':
			less = ' (w/ non-declined forms omitted)'

	if len(so.searchlist) > 1:
		wholes = so.wholecorporasearched()
		if wholes:
			wholes = ' and '.join(wholes)
			source = 'all {w} authors'.format(w=wholes)
		else:
			first = so.searchlist[0]
			if first[:10] == first[:6]:
				source = '{au}'.format(au=authordict[first[:6]].shortname)
			else:
				source = '{au}, {wk}'.format(au=authordict[first[:6]].shortname, wk=workdict[first[:10]].title)
			if len(so.searchlist) == 2:
				pl = ''
			else:
				pl = 's'
			source = '{s} and {n} other location{pl}'.format(s=source, n=len(so.searchlist)-1, pl=pl)
	else:
		searched = so.searchlist[0]
		if searched[:10] == searched[:6]:
			source = '{au}'.format(au=authordict[searched[:6]].shortname)
		else:
			source = '{au}, {wk}'.format(au=authordict[searched[:6]].shortname, wk=workdict[searched[:10]].title)

	title = '{t} »{w}«\nin {s}{l}'.format(t=topic, w=searchterm, s=source, l=less)

	return title


def generatethefineprint(vtype: str, vectorvalues: VectorValues) -> str:
	"""

	label graphs with setting values

	:return:
	"""

	vv = vectorvalues

	cutofffinder = {
		'rudimentary': vv.localcutoffdistance,
		'nn': vv.nearestneighborcutoffdistance,
		'unused': vv.lemmapaircutoffdistance
	}

	try:
		c = cutofffinder[vtype]
	except KeyError:
		c = '[unknown]'

	fineprint = 'bagging: {b} · dimensions: {d} · sentences per document: {n} · window: {w} · minimum presence: {p} · training runs: {i} · downsample: {s} · cutoff: {c}'
	fineprint = fineprint.format(b=vv.baggingmethod,
								d=vv.dimensions,
								n=vv.sentencesperdocument,
								w=vv.window,
								p=vv.minimumpresence,
								i=vv.trainingiterations,
								s=vv.downsample,
								c=c)

	return fineprint


def tsnegraphofvectors(sentencetuples, workssearched, so, vectorspace):
	"""

	lifted from https://radimrehurek.com/gensim/auto_examples/tutorials/run_word2vec.html#sphx-glr-auto-examples-tutorials-run-word2vec-py

	unused parameters so that the shape of this function's inputs can match other parallel functions

	:param sentencetuples:
	:param workssearched:
	:param so:
	:param vectorspace:
	:return:
	"""

	plotdict = reducetotwodimensions(vectorspace)
	xvalues = plotdict['xvalues']
	yvalues = plotdict['yvalues']
	labels = plotdict['labels']

	# random.seed(0)

	plt.figure(figsize=(12, 12))
	# https://jonasjacek.github.io/colors/
	plt.scatter(xvalues, yvalues, color='#c6c6c6')

	# Label randomly subsampled 25 data points
	#
	indices = list(range(len(labels)))
	selected_indices = random.sample(indices, 25)
	for i in selected_indices:
		plt.annotate(labels[i], (xvalues[i], yvalues[i]))

	graphobject = BytesIO()
	plt.savefig(graphobject)
	plt.clf()
	plt.close()

	graphobject = graphobject.getvalue()

	imagename = storevectorgraph(graphobject)

	# print('http://localhost:5000/getstoredfigure/{i}'.format(i=imagename))

	output = SearchOutputObject(so)
	output.image = imagename

	findsjs = generatevectorjs()

	htmltemplate = """
	<p id="imagearea"></p>
	"""

	output.found = str()
	output.htmlsearch = str()
	output.found = htmltemplate
	output.js = findsjs

	jsonoutput = json.dumps(output.generateoutput())

	# print('jsonoutput', jsonoutput)
	return jsonoutput


def threejsgraphofvectors(sentencetuples, workssearched, so, vectorspace):
	"""

	unused parameters so that the shape of this function's inputs can match other parallel functions

	see https://github.com/tobydoig/3dword2vec

	:param sentencetuples:
	:param workssearched:
	:param so:
	:param vectorspace:
	:return:
	"""

	output = SearchOutputObject(so)

	graphdata = reducetothreedimensions(so, vectorspace)

	output.found = str()
	output.htmlsearch = str()
	output.found = trheedimensionalhtml()
	output.js = threedimensionaljs(graphdata)

	jsonoutput = json.dumps(output.generateoutput())

	# print('jsonoutput', jsonoutput)
	return jsonoutput


def reducetothreedimensions(so, vectorspace):
	"""

	take a model and make it 3d

	then record the results:
		["ἄϲιοϲ",8.272949,7.7349167,2.156866,3],
		...

	:param so:
	:param vectorspace:
	:return:
	"""

	percentagetouse = .50
	pcasize = 50
	tsnesize = 3
	umapsize = 3
	numberofclusters = 10

	activepoll = so.poll
	activepoll.statusis('Executing a simple word search...')

	# vectors, indices = sampleVectors(gensimmodel.vectors, 1.00)
	gensimmodel = vectorspace.wv
	vectors = gensimmodel.vectors
	size = len(vectors)
	activepoll.statusis('Sampling {p}% of {size} vectors'.format(p=percentagetouse * 100, size=size))
	sample = int(size * percentagetouse)
	totalfeatures = len(vectors[0])
	samplevectors = np.ndarray((sample, totalfeatures), np.float32)
	indices = np.random.choice(len(vectors), sample)
	for i, val in enumerate(indices):
		samplevectors[i] = vectors[val]

	activepoll.statusis('Reducing data to {size} features using PCA (fast)'.format(size=pcasize))
	pca = PCA(n_components=pcasize)
	pcavecs = pca.fit_transform(samplevectors)

	activepoll.statusis('Reducing data to {size} features using UMAP (slow-ish)'.format(size=umapsize))
	umap = UMAP(n_neighbors=15, min_dist=0.1, metric='euclidean', n_components=umapsize)
	umapvecs = umap.fit_transform(pcavecs)

	# activepoll.statusis('Reducing data to {size} features using T-SNE (slow)')
	# tsne = TSNE(n_components=tsnesize)
	# tsnevecs = tsne.fit_transform(pcavecs)

	activepoll.statusis('Using KMeans to generate {size} groups so the final graph is prettier...'.format(size=numberofclusters))
	clusters = KMeans(n_clusters=numberofclusters).fit_predict(umapvecs)

	graphdata = generategraphitdata(gensimmodel, vectors, indices, clusters)

	return graphdata


def generategraphitdata(model, vectors, indices, clusters):
	"""

	example:

	["ἄϲιοϲ",8.272949,7.7349167,2.156866,3],
	["νόϲοϲ",6.1557837,6.904217,5.705993,4],
	["ἐπιτίθημι",6.363636,4.9078484,4.0320854,8],
	...

	:param model:
	:param vectors:
	:param indices:
	:param clusters:
	:param fname:
	:return:
	"""
	datatemplate = """
	var W2VDATA=[
	{thelines}
	];
	"""

	linetemplate = '["{w}", {x}, {y}, {z}, {c}]'

	thelines = list()
	for i, val in enumerate(indices):
		kw = model.index2word[val]
		if len(kw) > 1:
			v = vectors[i]
			thelines.append(linetemplate.format(w=kw, x=v[0], y=v[1], z=v[2], c=clusters[i]))

	thelines = ',\n'.join(thelines)
	thegraphdata = datatemplate.format(thelines=thelines)

	return thegraphdata


def threedimensionaljs(jsgraphdata: str) -> str:
	"""

	the JS to add to the page

	see:
		https://github.com/tobydoig/3dword2vec/blob/master/html/graphit.html

	for the new css see:
		https://stackoverflow.com/questions/5680657/adding-css-file-with-jquery#5680757

	:param jsgraphdata:
	:return:
	"""

	csstemplate = """
	$('head').append('<link rel="stylesheet" href="/css/{c}" type="text/css" />');
	"""

	scripttemplate = """
		JQIREGEXSUB
		CSSREGEXSUB
		GDREGEXSUB
		function addSeed() {
			var seedElem = document.querySelector('.seedlayer input[type=text]');
			var seed = seedElem.value.trim();
			var idx = W2VDATA.findIndex((e) => { return e[0] === seed;});
			if (idx >= 0) {
				// console.log('found at ' + idx);
				addTextPoint(idx);
				var pill = document.createElement('span');
				pill.className = 'badge badge-pill badge-info';
				pill.appendChild(document.createTextNode(seed));
				
				let sl = document.querySelector('.seedlayer');
				sl.insertBefore(pill, sl.firstChild);
				seedElem.value = '';
			}
		}
	"""

	jsfiles = ['popper.min.js', 'bootstrap.min.js', 'three.min.js', 'OrbitControls.js', 'Lut.js', 'graphit.js']
	jqi = ['jQuery.getScript("/static/3d/{f}");'.format(f=f) for f in jsfiles]
	jqi = '\n'.join(jqi)

	cssfiles = ['3d_bootstrap.min.css', '3d_graphit.css']
	css = [csstemplate.format(c=c) for c in cssfiles]
	css = '\n'.join(css)

	# can't use normal formatting because js has all those brackets...
	# supplementaljs = scripttemplate.format(jqueryinserts=jqi, graphdata=jsgraphdata, cssinserts=css)
	supplementaljs = re.sub(r'JQIREGEXSUB', jqi, scripttemplate)
	supplementaljs = re.sub(r'CSSREGEXSUB', css, supplementaljs)
	supplementaljs = re.sub(r'GDREGEXSUB', jsgraphdata, supplementaljs)

	return supplementaljs


def trheedimensionalhtml() -> str:
	"""

	the HTML to add to the page

	see:
		https://github.com/tobydoig/3dword2vec/blob/master/html/graphit.html

	:return:
	"""

	htmltemplate = """
	<div class="seedouter">
		<div class="seedlayer">
			<input type="text" size="20" name="seedvalue">
			<input type="button" value="add" onclick="addSeed()">
		</div>
	</div>
	<div class="textlayer"><div class="textglass"></div><ul class="textitems"></ul></div>
	<div id="ThreeJS" style="z-index: 10; overflow: hidden;"></div>
	"""

	return htmltemplate
