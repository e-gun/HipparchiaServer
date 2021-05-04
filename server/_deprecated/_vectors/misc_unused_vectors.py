import json
import locale
import random
import re
from io import BytesIO

from sklearn.cluster import KMeans

from server import hipparchia
from server._deprecated._vectors.preparetextforvectorization import vectorprepdispatcher
from server._deprecated._vectors.rudimentaryvectormath import buildrudimentaryvectorspace, caclulatecosinevalues
from server._deprecated._vectors.wordbaggers import buildflatbagsofwords
from server.dbsupport.vectordbfunctions import fetchverctorenvirons

from server.formatting.jsformatting import generatevectorjs
from server.formatting.vectorformatting import formatnnmatches
from server.hipparchiaobjects.searchobjects import SearchOutputObject
from server.listsandsession.genericlistfunctions import findsetofallwords
from server.listsandsession.searchlistmanagement import compilesearchlist, flagexclusions, calculatewholeauthorsearches
from server.listsandsession.whereclauses import configurewhereclausedata
from server._deprecated._vectors.scikitlearntopics import ldavis as ldavis, CountVectorizer, ldatopicgraphing
from server.semanticvectors.vectorgraphing import plt as plt, storevectorgraph, np as np, PCA, UMAP, \
    generategraphitdata, graphbliteraldistancematches
from server.semanticvectors.vectorhelpers import reducetotwodimensions, convertmophdicttodict, emptyvectoroutput
from server.startup import lemmatadict, listmapper, workdict, authordict
from server.textsandindices.textandindiceshelperfunctions import getrequiredmorphobjects


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


def findabsolutevectorsbysentence(searchobject):
	"""

	use the searchlist to grab a collection of sentences

	then take a lemmatized search term and build association semanticvectors around that term in those passages

	generators are tempting, but dealing with generators+MP is a trick:

		TypeError: can't pickle generator objects

	:param searchitem:
	:param vtype:
	:return:
	"""

	so = searchobject
	activepoll = so.poll

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
	activecorpora = [c for c in allcorpora if so.session[c]]

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
		reasons = ['the vector scope max exceeded: {a} > {b} '.format(a=locale.format_string('%d', wordstotal, grouping=True), b=locale.format_string('%d', maxwords, grouping=True))]
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
		sentencetuples = vectorprepdispatcher(so)
		sentences = [s[1] for s in sentencetuples]
		output = generateabsolutevectorsoutput(sentences, workssearched, so, 'sentences')
	else:
		return emptyvectoroutput(so)

	return output


def findabsolutevectorsfromhits(searchobject, hitdict, workssearched):
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
	activepoll = so.poll

	so.proximate = str()
	so.proximatelemma = str()

	activepoll.statusis('Compiling proximite wordlists')
	environs = fetchverctorenvirons(hitdict, so)

	output = generateabsolutevectorsoutput(environs, workssearched, so, 'passages')

	return output


def generateabsolutevectorsoutput(listsofwords: list, workssearched: list, searchobject, vtype: str):
	"""


	:return:
	"""
	so = searchobject
	vv = so.vectorvalues
	activepoll = so.poll

	# find all words in use
	allwords = findsetofallwords(listsofwords)
	# print('allwords', allwords)

	# find all possible forms of all the words we used
	# consider subtracting some set like: rarewordsthatpretendtobecommon = {}
	activepoll.statusis('Finding headwords')
	morphdict = getrequiredmorphobjects(allwords, furtherdeabbreviate=True)
	morphdict = convertmophdicttodict(morphdict)

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
	vectorspace = buildrudimentaryvectorspace(allheadwords, morphdict, listsofwords, subtractterm=subtractterm)

	# for k in vectorspace.keys():
	# 	print(k, vectorspace[k])

	if so.lemma:
		focus = so.lemma.dictionaryentry
	else:
		focus = so.seeking

	activepoll.statusis('Calculating cosine distances')
	cosinevalues = caclulatecosinevalues(focus, vectorspace, allheadwords.keys())
	# cosinevalues = vectorcosinedispatching(focus, vectorspace, allheadwords.keys())
	# print('generatevectoroutput cosinevalues', cosinevalues)

	# apply the threshold and drop the 'None' items
	threshold = 1.0 - vv.localcutoffdistance
	falseidentity = .02
	cosinevalues = {c: 1 - cosinevalues[c] for c in cosinevalues if cosinevalues[c] and falseidentity < cosinevalues[c] < threshold}
	mostsimilar = [(c, cosinevalues[c]) for c in cosinevalues]
	mostsimilar = sorted(mostsimilar, key=lambda t: t[1], reverse=True)

	findshtml = formatnnmatches(mostsimilar, vv)

	# next we look for the interrelationships of the words that are above the threshold
	activepoll.statusis('Calculating metacosine distances')
	imagename = graphbliteraldistancematches(focus, mostsimilar, so)

	findsjs = generatevectorjs()

	output = SearchOutputObject(so)

	output.title = 'Cosine distances to »{skg}«'.format(skg=focus)
	output.found = findshtml
	output.js = findsjs

	if not so.session['cosdistbylineorword']:
		space = 'related terms in {s} {t}'.format(s=len(listsofwords), t=vtype)
	else:
		dist = so.session['proximity']
		scale = {'words': 'word', 'lines': 'line'}
		if int(dist) > 1:
			plural = 's'
		else:
			plural = str()
		space = 'related terms within {a} {b}{s}'.format(a=dist, b=scale[so.session['searchscope']], s=plural)

	found = max(vv.neighborscap, len(cosinevalues))
	output.setresultcount(found, space)
	output.setscope(workssearched)

	if so.lemma:
		xtra = 'all forms of '
	else:
		xtra = str()

	output.thesearch = '{x}»{skg}«'.format(x=xtra, skg=focus)
	output.htmlsearch = '{x}<span class="sought">»{skg}«</span>'.format(x=xtra, skg=focus)

	output.sortby = 'distance with a cutoff of {c}'.format(c=vv.localcutoffdistance)
	output.image = imagename
	output.searchtime = so.getelapsedtime()

	activepoll.deactivate()

	jsonoutput = json.dumps(output.generateoutput())

	return jsonoutput


def sklearnselectedworks(searchobject):
	"""

	:param activepoll:
	:param searchobject:
	:return:
	"""

	if not ldavis or not CountVectorizer:
		reasons = ['requisite software not installed: sklearn and/or ldavis is unavailable']
		return emptyvectoroutput(searchobject, reasons)

	so = searchobject
	activepoll = so.poll

	activepoll.statusis('Preparing to search')

	so.usecolumn = 'marked_up_line'
	so.vectortype = 'topicmodel'

	allcorpora = ['greekcorpus', 'latincorpus', 'papyruscorpus', 'inscriptioncorpus', 'christiancorpus']
	activecorpora = [c for c in allcorpora if so.session[c]]

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
		reasons = ['the vector scope max exceeded: {a} > {b} '.format(a=locale.format_string('%d', wordstotal, grouping=True), b=locale.format_string('%d', maxwords, grouping=True))]
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

		sentencetuples = vectorprepdispatcher(so)
		if len(sentencetuples) > hipparchia.config['MAXSENTENCECOMPARISONSPACE']:
			reasons = ['scope of search exceeded allowed maximum: {a} > {b}'.format(a=len(sentencetuples), b=hipparchia.config['MAXSENTENCECOMPARISONSPACE'])]
			return emptyvectoroutput(so, reasons)
		output = ldatopicgraphing(sentencetuples, workssearched, so)

	else:
		return emptyvectoroutput(so)

	return output


def buildlemmatizesearchphrase(phrase: str) -> str:
	"""

	turn a search into a collection of headwords

	:param phrase:
	:return:
	"""

	# phrase = 'vias urbis munera'
	phrase = phrase.strip()
	words = phrase.split(' ')

	morphdict = getrequiredmorphobjects(words, furtherdeabbreviate=True)
	morphdict = convertmophdicttodict(morphdict)
	# morphdict {'munera': {'munero', 'munus'}, 'urbis': {'urbs'}, 'uias': {'via', 'vio'}}

	listoflistofheadwords = buildflatbagsofwords(morphdict, [words])
	# [['via', 'vio', 'urbs', 'munero', 'munus']]

	lemmatizesearchphrase = ' '.join(listoflistofheadwords[0])
	# lemmatizesearchphrase = 'via vio urbs munus munero'

	return lemmatizesearchphrase