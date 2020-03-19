# -*- coding: utf-8 -*-
# note that internally 'yes'/'no' are converted to True/False; and so one can use 'yes'/'no'
# but definitely *do not* use 'True'/'False' since they are not the same as True/False...

# [7] SEMANTIC VECTORS: experimental and in-progress
#   many extra packages need to be configured and installed
#   the results are not well explained; they cannot necessarily be trusted.
#   Changing any value below even by a small amount can produce large shifts
#   in your results. That should make you at least a little anxious.
#   [see also mostcommonheadwords() in vectorhelpers.py: a number of deletions
#   occur there]
#
#   All of this is useful for exploring ideas, but it should NOT be confused
#   with "knowledge". The more one reads up on semantic vectors, the more
#   one comes to appreciate that human tastes, judgement, and decisions
#   are all key factors in determining what makes for a sensible set of
#   values to use. Some choices will inevitably yield very flawed results.
#   For example, a dimensionality of 1000 is known to be worse than 300 in most
#   cases... Similarly, these tools are supposed to able a dumb machine to make
#   a good guess about something it does not understand. They are not supposed
#   to make smart people so foolish as to assume that the dumb machine knows best.
#   Please consider researching the topic before making any arguments based
#   on the results that this code will generate.
#
# FORBIDUSERDEFINEDVECTORSPACES: if True you are effectively saying only the autobot-generated sets are valid for
#   searching; this option will block anything that is not already vectorized from returning a result
#
# LITERALCOSINEDISTANCEENABLED allows you to seek the concrete neighbors of words.
#   In all of the instances of X, what other terms also show up nearby? This
#   is not necessarily the most interesting search.
#
# CONCEPTMAPPINGENABLED allows you to generate graphs of the relationships between
#   a lemmatized term and all of the other terms that "neighbor" it in the vector
#   space.
#
# VECTORANALOGIESENABLED = find A:B :: C:D; that is, 'vir':'bonus' :: 'mulier' : ???
#
# TOPICMODELINGENABLED allows you to build graphs of topic clusters via Latent Dirichlet Allocation.
#
# CONCEPTSEARCHINGENABLED allows you to search for sentences related to a lemmatized
#   term or terms. What sentences are about "men"? Which sentences are related to the
#   relationship that subsists between "good" and "man"?
#
# MAXVECTORSPACE: what is the largest set of words you are willing
#   to vectorize in order to find the association network of a given
#   lemmatized term? This sort of query get exponentially harder to
#   execute and so you if you allow a full corpora search you will
#   bring your system to it knees for a long, long time. 7548165 is
#   all of Latin. 13518316 is all Greek literature up to 300 BCE.
# 	75233492 is all Greek literature. It takes >12GB of RAM to autovectorize
#   all of greek, so be careful about this if you turn on AUTOVECTORIZE
#   with MAXVECTORSPACE > 75233492.
#   If you search for the literal cosine distances of a common word you can easily
#   chew up >24GB of RAM. Your system will hang unless/until Hipparchia
#   receives more memory optimizations. Gensim NN vectorization of all
#   of Latin will take 554.08s on a 6-threaded 3.6GHz machine.
#
# VECTORDISTANCECUTOFF: how close Word A needs to be to Word B for the associative matrix
#   calculations to decide that there is a relationship worth pursuing: a value between 1 and 0
#   100 --> identical;
#   0 --> completely unrelated
#
# VECTORTRAININGITERATIONS sets the number of training passes; this is a tricky one
#   over-training Livy with 15 passes will destroy the results for "auctoritas"
#
# VECTORDOWNSAMPLE is the threshold for configuring which higher-frequency words are randomly
#   downsampled, useful range is (0, 1e-5).
#
# VECTORMINIMALPRESENCE is the number of times you must be found before you are ranked as a
#   significant word
#
# VECTORDIMENSIONS is the number of features you want to keep track of. More is better, until
#   it isn't. The classic numbers are 100, 200, and 300.
#
# VECTORDISTANCECUTOFFS set the value at which something is no longer going to be considered
#   "related" to what you are looking for.
#
# NEARESTNEIGHBORSCAP says when to stop looking for neighbors
#
# SENTENCESPERDOCUMENT determines how many sentences will be used to build a 'document'. 1 is usual, but
#   larger values are also acceptable if you want to experiment.
#
# AUTOVECTORIZE will fill the vector db in the background; this will chew up plenty of resources:
#   both drive space and CPU time; do not set this to True unless you are ready for the commitment
#
# DEFAULTBAGGINGMETHOD defines what makes for a bag of words and so determines the core structure of the vectorized
#   landscape...
#
# Windows 10 is not ready for semantic vectors
#	TypeError: can't pickle psycopg2.extensions.connection objects

SEMANTICVECTORSENABLED = False
FORBIDUSERDEFINEDVECTORSPACES = False
LITERALCOSINEDISTANCEENABLED = False
CONCEPTMAPPINGENABLED = False
TOPICMODELINGENABLED = False
VECTORANALOGIESENABLED = False    # user interface is incomplete; results are not so hot; do not enable as thing stand
CONCEPTSEARCHINGENABLED = False   # of dubious value as currently implemented
MAXVECTORSPACE = 7548165
MAXSENTENCECOMPARISONSPACE = 50000
VECTORDIMENSIONS = 300
VECTORWINDOW = 10
VECTORTRAININGITERATIONS = 12
VECTORMINIMALPRESENCE = 10
VECTORDOWNSAMPLE = 5
VECTORDISTANCECUTOFFLOCAL = 33
VECTORDISTANCECUTOFFNEARESTNEIGHBOR = 15
VECTORDISTANCECUTOFFLEMMAPAIR = 50
NEARESTNEIGHBORSCAP = 15
SENTENCESPERDOCUMENT = 1

# settings for ldatopicgraphing()
LDAMAXFEATURES = 2000
LDACOMPONENTS = 10      # topics
LDAMAXFREQ = 49         # fewer than n% of sentences should have this word (i.e., purge common words)
LDAMINFREQ = 5          # word must be found >n times
LDAITERATIONS = 12
LDAMUSTBELONGERTHAN = 3

AUTOVECTORIZE = False

# baggingmethods = {'flat': buildflatbagsofwords,
#                   'alternates': buildbagsofwordswithalternates,
#                   'winnertakeall': buildwinnertakeallbagsofwords,
#                   'unlemmatized': buidunlemmatizedbagsofwords}

DEFAULTBAGGINGMETHOD = 'flat'


"""
vectorranges = {
	'ldacomponents': range(1, 51),
	'ldaiterations': range(1, 26),
	'ldamaxfeatures': range(1, 5001),
	'ldamaxfreq': range(1, 101),
	'ldaminfreq': range(1, 21),
	'ldamustbelongerthan': range(1, 5),
	'vcutlem': range(0, 101),
	'vcutloc': range(0, 101),
	'vcutneighb': range(0, 101),
	'vdim': range(50, 500),
	'vdsamp': range(1, 21),
	'viterat': range(1, 21),
	'vminpres': range(1, 21),
	'vnncap': range(1, 26),
	'vsentperdoc': range(1, 6),
	'vwindow': range(2, 20)
}
"""
