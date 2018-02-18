# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import random
from io import BytesIO

import matplotlib.pyplot as plt
import networkx as nx
import psycopg2

from server import hipparchia
from server.dbsupport.dbfunctions import createstoredimagestable, setconnection
from server.startup import authordict, workdict


def graphbliteraldistancematches(searchterm, mostsimilartuples, vectorspace, searchlist):
	"""


	:param searchterm:
	:param mostsimilartuples:
	:param vectorspace:
	:param searchlist:
	:return:
	"""

	terms = [searchterm] + [t[0] for t in mostsimilartuples]

	# interrelationships = {t: caclulatecosinevalues(t, vectorspace, terms) for t in terms}

	relevantconnections = dict()

	title = givetitletograph('Words most concretely connected with', searchterm, searchlist)
	imagename = graphmatches(title, searchterm, mostsimilartuples, terms, relevantconnections)

	return imagename


def graphnnmatches(searchterm, mostsimilartuples, vectorspace, searchlist):
	"""

	tuples come in a list and look like:
		[('ὁμολογέω', 0.8400295972824097), ('θέα', 0.8328431844711304), ('θεά', 0.8282027244567871), ...]

	:param searchterm:
	:param mostsimilartuples:
	:param vectorspace:
	:return:
	"""

	terms = [searchterm] + [t[0] for t in mostsimilartuples]

	interrelationships = {t: vectorspace.most_similar(t) for t in terms}

	relevantconnections = dict()
	for i in interrelationships:
		relevantconnections[i] = [sim for sim in interrelationships[i] if sim[0] in terms]

	title = givetitletograph('Conceptual neighborhood of', searchterm, searchlist)

	imagename = graphmatches(title, searchterm, mostsimilartuples, terms, relevantconnections)

	return imagename


def graphmatches(graphtitle, searchterm, mostsimilartuples, terms, relevantconnections):
	"""

	mostsimilartuples come in a list and look like:
		[('ὁμολογέω', 0.8400295972824097), ('θέα', 0.8328431844711304), ('θεά', 0.8282027244567871), ...]

	relevantconnections is a dict each of whose keyed entreis unpacks into a mostsimilartuples-like list

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
	# cmap='tab20c' or 'Pastel1' is nice

	# nodes
	nx.draw_networkx_nodes(graph, pos, node_size=6500, node_color=range(len(terms)), cmap='Pastel1')
	nx.draw_networkx_labels(graph, pos, font_size=20, font_family='sans-serif', font_color='Black')

	# edges
	nx.draw_networkx_edges(graph, pos, width=3, alpha=0.8, edge_color='dimgrey')
	nx.draw_networkx_edge_labels(graph, pos, edgelabels, font_size=12, alpha=0.8, label_pos=0.5, font_family='sans-serif')

	# the fine print
	plt.text(0, -1.1, generatethefineprint(), ha='center', va='bottom')
	# plt.text(1, -1, 'gensim', ha='center', va='bottom')
	# plt.text(-1, -1, '@commit {v}'.format(v=readgitdata()[0:5]), ha='center', va='bottom')

	plt.axis('off')
	# plt.savefig('matchesgraph.png')
	graphobject = BytesIO()
	plt.savefig(graphobject)
	plt.clf()

	# getvalue(): Return bytes containing the entire contents of the buffer
	# everybody from here on out want bytes and not '_io.BytesIO'
	graphobject = graphobject.getvalue()

	imagename = storevectorgraph(graphobject)

	return imagename


def storevectorgraph(figureasbytes):
	"""


	:param figureasbytes:
	:return:
	"""

	dbconnection = setconnection('autocommit', readonlyconnection=False, u='DBWRITEUSER', p='DBWRITEPASS')
	cursor = dbconnection.cursor()

	randomid = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz') for i in range(12)])

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

	dbconnection.commit()
	cursor.close()
	del dbconnection

	return randomid


def fetchvectorgraph(imagename):
	"""

	:param imagename:
	:return:
	"""

	dbconnection = setconnection('autocommit', readonlyconnection=False, u='DBWRITEUSER', p='DBWRITEPASS')
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

	q = 'DELETE FROM public.storedvectorimages WHERE imagename=%s'
	d = (imagename,)
	cursor.execute(q, d)

	dbconnection.commit()
	cursor.close()
	del dbconnection

	return imagedata


def givetitletograph(topic, searchterm, searchlist):
	"""

	generate a title for the graph

	:return:
	"""
	if len(searchlist) > 1:
		wasitalllatin = [x for x in searchlist if x[:2] == 'lt' and len(x) == 6]
		if len(wasitalllatin) == 362:
			source = 'all Latin authors'
		else:
			source = 'multiple authors and/or works'
	else:
		searched = searchlist[0]
		if searched[:10] == searched[:6]:
			source = '{au}'.format(au=authordict[searched[:6]].shortname)
		else:
			source = '{au}, {wk}'.format(au=authordict[searched[:6]].shortname, wk=workdict[searched[:10]].title)

	title = '{t} »{w}«\nin {s}'.format(t=topic, w=searchterm, s=source)

	return title


def generatethefineprint():
	"""

	label graphs with setting values

	:return:
	"""

	d = hipparchia.config['VECTORDIMENSIONS']
	w = hipparchia.config['VECTORWINDOW']
	i = hipparchia.config['VECTORTRAININGITERATIONS']
	p = hipparchia.config['VECTORMINIMALPRESENCE']
	s = hipparchia.config['VECTORDOWNSAMPLE']

	fineprint = 'dimensions: {d} · window: {w} · minimum presence: {p} · training runs: {i} · downsample: {s}'
	fineprint = fineprint.format(d=d, w=w, p=p, i=i, s=s)

	return fineprint
