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
# LITERALCOSINEDISTANCEENABLED allows you to seek the concrete neighbors of words.
#   In all of the instances of X, what other terms also show up nearby? This
#   is not necessarily the most interesting search.
#
# CONCEPTMAPPINGENABLED allows you to generate graphs of the relationships between
#   a lemmatized term and all of the other terms that "neighbor" it in the vector
#   space.
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
#   If you search for the literal cosine distances of a common word you can easily
#   chew up >24GB of RAM. Your system will hang unless/until Hipparchia
#   receives more memory optimizations. Gensim NN vectorization of all
#   of Latin will take 554.08s on a 6-threaded 3.6GHz machine.
#
# VECTORDISTANCECUTOFF: how close Word A needs to be to Word B for the associative matrix
#   calculations to decide that there is a relationship worth pursuing: a value between 1 and 0
#   1 --> identical;
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
#   both drive space and CPU time; do not set this to 'yes' unless you are ready for the commitment
#

SEMANTICVECTORSENABLED = 'no'
LITERALCOSINEDISTANCEENABLED = 'no'
CONCEPTMAPPINGENABLED = 'no'
TOPICMODELINGENABLED = 'no'
CONCEPTSEARCHINGENABLED = 'no'  # of dubious value as currently implemented
MAXVECTORSPACE = 7548165
MAXSENTENCECOMPARISONSPACE = 50000
VECTORDIMENSIONS = 300
VECTORWINDOW = 10
VECTORTRAININGITERATIONS = 12
VECTORMINIMALPRESENCE = 10
VECTORDOWNSAMPLE = 0.05
VECTORDISTANCECUTOFFLOCAL = .33
VECTORDISTANCECUTOFFNEARESTNEIGHBOR = .33
VECTORDISTANCECUTOFFLEMMAPAIR = .5
NEARESTNEIGHBORSCAP = 15
SENTENCESPERDOCUMENT = 1
AUTOVECTORIZE = 'no'