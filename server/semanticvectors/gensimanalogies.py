from server.semanticvectors.gensimnearestneighbors import buildnnvectorspace
from server.semanticvectors.vectorroutehelperfunctions import emptyvectoroutput


def generateanalogies(sentencetuples, workssearched, searchobject, vectorspace):
	"""

	very much in progress

	need a formatting function like nearestneighborgenerateoutput()

	until then this is console only

		most_similar(positive=None, negative=None, topn=10, restrict_vocab=None, indexer=None)
			[analogies; most_similar(positive=['woman', 'king'], negative=['man']) --> queen]

		most_similar_cosmul(positive=None, negative=None, topn=10)
		[analogy finder; most_similar_cosmul(positive=['baghdad', 'england'], negative=['london']) --> iraq]

	:param sentencetuples:
	:param searchobject:
	:param vectorspace:
	:return:
	"""

	so = searchobject
	if not so.lemmaone or not so.lemmatwo or not so.lemmathree:
		return emptyvectoroutput(so, '[did not have three valid lemmata]')
	if not vectorspace:
		vectorspace = buildnnvectorspace(sentencetuples, so)
		if vectorspace == 'failed to build model':
			reasons = [vectorspace]
			return emptyvectoroutput(so, reasons)

	a = so.lemmaone.dictionaryentry
	b = so.lemmatwo.dictionaryentry
	c = so.lemmathree.dictionaryentry
	positive = [a, b]
	negative = [c]

	# similarities are less interesting than cosimilarities
	# similarities = vectorspace.wv.most_similar(positive=positive, negative=negative, topn=4)

	cosimilarities = vectorspace.wv.most_similar_cosmul(positive=positive, negative=negative, topn=5)

	# print('generateanalogies() similarities are')
	# for s in similarities:
	# 	print('\t',s)

	print('generateanalogies() cosimilarities\n')
	print('{a} : {b} :: {c} : _______'.format(a=a, b=b, c=c))
	for s in cosimilarities:
		print('\t{v: .3f}: {t}'.format(t=s[0], v=s[1]))

	output = None

	return emptyvectoroutput(so, '[test code is sending the real output to the console]')