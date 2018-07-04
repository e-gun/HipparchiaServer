# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from io import BytesIO

# https://matplotlib.org/faq/howto_faq.html#matplotlib-in-a-web-application-server
# do this before importing pylab or pyplot: otherwise you will see:
#   RuntimeError: main thread is not in main loop
#   Tcl_AsyncDelete: async handler deleted by the wrong thread
try:
	import matplotlib
	matplotlib.use('Agg')
	import matplotlib.pyplot as plt
	import networkx as nx
except ModuleNotFoundError:
	matplotlib = None
	plt = None
	nx = None

import psycopg2
from server import hipparchia
from server.dbsupport.tablefunctions import uniquetablename
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

	mostsimilartuples = [t for t in mostsimilartuples if t[1] > hipparchia.config['VECTORDISTANCECUTOFFLOCAL']]
	mostsimilartuples = mostsimilartuples[:hipparchia.config['NEARESTNEIGHBORSCAP']]

	terms = [searchterm] + [t[0] for t in mostsimilartuples]

	# interrelationships = {t: caclulatecosinevalues(t, vectorspace, terms) for t in terms}

	relevantconnections = dict()

	title = givetitletograph('Words most concretely connected with', searchterm, searchobject)
	imagename = graphmatches(title, searchterm, mostsimilartuples, terms, relevantconnections, vtype='rudimentary')

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

	imagename = graphmatches(title, searchterm, mostsimilartuples, terms, relevantconnections, vtype='nn')

	return imagename


def graphmatches(graphtitle, searchterm, mostsimilartuples, terms, relevantconnections, vtype):
	# fnc = bokehgraphmatches
	fnc = matplotgraphmatches
	return fnc(graphtitle, searchterm, mostsimilartuples, terms, relevantconnections, vtype)


def matplotgraphmatches(graphtitle, searchterm, mostsimilartuples, terms, relevantconnections, vtype):
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

	# nodes
	nx.draw_networkx_nodes(graph, pos, node_size=scalednodes, alpha=0.75, node_color=range(len(terms)), cmap='Pastel1')
	nx.draw_networkx_labels(graph, pos, font_size=20, font_family='sans-serif', font_color='Black')

	# edges
	nx.draw_networkx_edges(graph, pos, width=3, alpha=0.85, edge_color='dimgrey')
	nx.draw_networkx_edge_labels(graph, pos, edgelabels, font_size=12, alpha=0.8, label_pos=0.5, font_family='sans-serif')

	# the fine print
	plt.text(0, -1.1, generatethefineprint(vtype), ha='center', va='bottom')
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

	randomid = uniquetablename()

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

	if hipparchia.config['RETAINFIGURES'] == 'yes':
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

	title = '{t} »{w}«\nin {s}'.format(t=topic, w=searchterm, s=source)

	return title


def generatethefineprint(vtype):
	"""

	label graphs with setting values

	:return:
	"""

	cutofffinder = {
		'rudimentary': 'VECTORDISTANCECUTOFFLOCAL',
		'nn': 'VECTORDISTANCECUTOFFNEARESTNEIGHBOR',
		'unused': 'VECTORDISTANCECUTOFFLEMMAPAIR'
	}

	try:
		c = hipparchia.config[cutofffinder[vtype]]
	except KeyError:
		c = '[unknown]'
	d = hipparchia.config['VECTORDIMENSIONS']
	w = hipparchia.config['VECTORWINDOW']
	i = hipparchia.config['VECTORTRAININGITERATIONS']
	p = hipparchia.config['VECTORMINIMALPRESENCE']
	s = hipparchia.config['VECTORDOWNSAMPLE']
	n = hipparchia.config['SENTENCESPERDOCUMENT']

	fineprint = 'dimensions: {d} · sentences per document: {n} · window: {w} · minimum presence: {p} · training runs: {i} · downsample: {s} · cutoff: {c}'
	fineprint = fineprint.format(d=d, n=n, w=w, p=p, i=i, s=s, c=c)

	return fineprint
