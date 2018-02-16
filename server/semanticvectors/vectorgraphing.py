# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import matplotlib.pyplot as plt
import networkx as nx


def graphmatches(searchterm, mostsimilartuples, vectorspace):
	"""

	tuples come in a list and look like:
		[('ὁμολογέω', 0.8400295972824097), ('θέα', 0.8328431844711304), ('θεά', 0.8282027244567871), ...]

	:param searchterm:
	:param mostsimilartuples:
	:param vectorspace:
	:return:
	"""

	plt.figure(figsize=(18, 18))

	terms = [searchterm] + [t[0] for t in mostsimilartuples]

	graph = nx.Graph()

	interrelationships = {t: vectorspace.most_similar(t) for t in terms}

	relevantconnections = dict()
	for i in interrelationships:
		relevantconnections[i] = [sim for sim in interrelationships[i] if sim[0] in terms]
	del interrelationships

	# print('relevantconnections')
	# for r in relevantconnections:
	# 	print(r, relevantconnections[r])

	for t in terms:
		graph.add_node(t)

	for r in relevantconnections:
		graph.add_node(r)

	edgelist = list()
	for t in mostsimilartuples:
		edgelist.append((searchterm, t[0], round(t[1]*10, 3)))

	for r in relevantconnections:
		for c in relevantconnections[r]:
			edgelist.append((r, c[0], round(c[1]*10, 3)))

	graph.add_weighted_edges_from(edgelist)
	edgelabels = {(u, v): d['weight'] for u, v, d in graph.edges(data=True)}

	pos = nx.fruchterman_reingold_layout(graph)

	# nodes
	# https://matplotlib.org/examples/color/colormaps_reference.html
	nx.draw_networkx_nodes(graph, pos, node_size=6000, node_color=range(len(terms)), cmap='Pastel1')
	nx.draw_networkx_labels(graph, pos, font_size=20, font_family='sans-serif', font_color='Black')

	# edges
	nx.draw_networkx_edges(graph, pos, width=4, alpha=0.5, edge_color='black')
	nx.draw_networkx_edge_labels(graph, pos, edgelabels, font_size=12, label_pos=0.3)

	plt.axis('off')
	plt.savefig('matchesgraph.png')
	plt.clf()

	return



