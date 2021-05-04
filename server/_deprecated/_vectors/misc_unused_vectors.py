import json
import random
import re
from io import BytesIO

from sklearn.cluster import KMeans

from server.formatting.jsformatting import generatevectorjs
from server.hipparchiaobjects.searchobjects import SearchOutputObject
from server.semanticvectors.vectorgraphing import plt as plt, storevectorgraph, np as np, PCA, UMAP, generategraphitdata
from server.semanticvectors.vectorhelpers import reducetotwodimensions


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

	activepoll.statusis('Reducing data to {size} features using PCA'.format(size=pcasize))
	pca = PCA(n_components=pcasize)
	pcavecs = pca.fit_transform(samplevectors)

	activepoll.statusis('Reducing data to {size} features using UMAP'.format(size=umapsize))
	umap = UMAP(n_neighbors=15, min_dist=0.1, metric='euclidean', n_components=umapsize)
	umapvecs = umap.fit_transform(pcavecs)

	# activepoll.statusis('Reducing data to {size} features using T-SNE (slow)')
	# tsne = TSNE(n_components=tsnesize)
	# tsnevecs = tsne.fit_transform(pcavecs)

	activepoll.statusis('Using KMeans to generate {size} groups so the final graph is prettier...'.format(size=numberofclusters))
	clusters = KMeans(n_clusters=numberofclusters).fit_predict(umapvecs)

	graphdata = generategraphitdata(gensimmodel, vectors, indices, clusters)

	return graphdata


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

	# jsfiles = ['popper.min.js', 'bootstrap.min.js', 'three.min.js', 'OrbitControls.js', 'Lut.js', 'graphit.js']
	jsfiles = ['graphit.js']
	jqi = ['jQuery.getScript("/static/3d/{f}");'.format(f=f) for f in jsfiles]
	jqi = '\n'.join(jqi)

	css = str()
	# cssfiles = ['3d_bootstrap.min.css', '3d_graphit.css']
	# css = [csstemplate.format(c=c) for c in cssfiles]
	# css = '\n'.join(css)

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