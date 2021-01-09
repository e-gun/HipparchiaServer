# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-21
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import networkx as nx
from bokeh.io import output_file, show
from bokeh.models import Circle, MultiLine, LabelSet, Label, ColumnDataSource
from bokeh.models.graphs import EdgesAndLinkedNodes, NodesAndLinkedEdges, from_networkx
from bokeh.plotting import figure
from bokeh.palettes import Spectral4

# except ImportError:
# 	print('bokeh is not available')
# 	file_html = None
# 	figure = None
# 	from_networkx = None

# from server.semanticvectors.vectorgraphing import storevectorgraph


def bokehgraphmatches(graphtitle, searchterm, mostsimilartuples, terms, relevantconnections, vtype):
	"""

	this does not work yet: storing and retrieving the graph requires more work

	mostsimilartuples come in a list and look like:
		[('ὁμολογέω', 0.8400295972824097), ('θέα', 0.8328431844711304), ('θεά', 0.8282027244567871), ...]

	relevantconnections is a dict each of whose keyed entries unpacks into a mostsimilartuples-like list


	from_networkx is quite limited

	would need to

	:param searchterm:
	:param mostsimilartuples:
	:param vectorspace:
	:param searchlist:
	:return:
	"""

	# print('mostsimilartuples:', mostsimilartuples)
	# print('terms:', terms)
	# print('relevantconnections', relevantconnections)

	# the nx part

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

	scalednodes = [1200*t[1]*10 for t in mostsimilartuples]

	# nodes
	nx.draw_networkx_nodes(graph, pos, node_size=scalednodes, alpha=0.75, node_color=range(len(terms)), cmap='Pastel1')
	nx.draw_networkx_labels(graph, pos, font_size=20, font_family='sans-serif', font_color='Black')

	# edges
	nx.draw_networkx_edges(graph, pos, width=3, alpha=0.85, edge_color='dimgrey')
	nx.draw_networkx_edge_labels(graph, pos, edgelabels, font_size=12, alpha=0.8, label_pos=0.5, font_family='sans-serif')

	# the bokeh part
	plot = figure(title="Networkx Integration Demonstration", x_range=(-1.1, 1.1), y_range=(-1.1, 1.1), tools="", toolbar_location=None)
	bokehgraph = from_networkx(graph, nx.spring_layout, scale=1, center=(0, 0))

	bokehgraph.node_renderer.glyph = Circle(size=15, fill_color=Spectral4[0])
	bokehgraph.node_renderer.selection_glyph = Circle(size=15, fill_color=Spectral4[2])
	bokehgraph.node_renderer.hover_glyph = Circle(size=15, fill_color=Spectral4[1])
	bokehgraph.node_renderer.glyph.properties_with_values()

	bokehgraph.edge_renderer.glyph = MultiLine(line_color="#CCCCCC", line_alpha=0.8, line_width=5)
	bokehgraph.edge_renderer.selection_glyph = MultiLine(line_color=Spectral4[2], line_width=5)
	bokehgraph.edge_renderer.hover_glyph = MultiLine(line_color=Spectral4[1], line_width=5)

	bokehgraph.selection_policy = NodesAndLinkedEdges()
	bokehgraph.inspection_policy = EdgesAndLinkedNodes()

	# broken atm

	# source = ColumnDataSource(data=dict(terms=terms))
	# labels = LabelSet(x_offset=0, y_offset=0, source=source, render_mode='canvas')
	# plot.add_layout(labels)

	plot.renderers.append(bokehgraph)

	# graphobject = file_html(bokehgraph)

	output_file("interactive_graphs.html")
	show(plot)
	imagename = None
	# imagename = storevectorgraph(graphobject)

	return imagename
