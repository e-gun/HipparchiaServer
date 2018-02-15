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

	for t in mostsimilartuples:
		graph.add_edge(searchterm, t[0], weight=round(t[1], 3))
		# graph[searchterm][t[0]]['weight'] = t[1]

	for r in relevantconnections:
		for c in relevantconnections[r]:
			graph.add_edge(r, c[0], weight=round(c[1], 3))
			# graph[r][c[0]]['weight'] = c[1]

	edgelabels = dict([((u, v,), d['weight']) for u, v, d in graph.edges(data=True)])

	pos = nx.fruchterman_reingold_layout(graph)
	nx.draw(graph, with_labels=True)
	nx.draw_networkx_edge_labels(graph, pos, font_size=9, edge_labels=edgelabels)

	plt.savefig("matchesgraph.png")

	del graph

	return



