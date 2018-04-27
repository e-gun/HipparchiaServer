import networkx as nx
try:
	from bokeh.embed import file_html
	from bokeh.plotting import figure
	from bokeh.models.graphs import from_networkx
except ImportError:
	print('bokeh is not available')
	file_html = None
	figure = None
	from_networkx = None

from server.semanticvectors.vectorgraphing import figure, from_networkx, file_html, storevectorgraph


def bokehgraphmatches(graphtitle, searchterm, mostsimilartuples, terms, relevantconnections, vtype):
	"""

	this does not work yet: storing and retrieving the graph requires more work

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
	bokehgraph = from_networkx(graph, nx.spring_layout, scale=2, center=(0, 0))

	plot.renderers.append(bokehgraph)

	graphobject = file_html(bokehgraph)

	imagename = storevectorgraph(graphobject)

	return imagename