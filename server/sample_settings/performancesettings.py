# -*- coding: utf-8 -*-
# note that internally 'yes'/'no' are converted to True/False, but one should still use 'yes'/'no'
# and definitely *do not* use 'True'/'False' since they are not the same as True/False...

### Hipparchia performance variables ###
##  [set once and forget: AUTOCONFIGWORKERS, WORKERS, MPCOMMITCOUNT] ##
#
# AUTOCONFIGWORKERS: if 'yes', then ignore WORKERS and set workers to
# 	threads*.5+1
#
# WORKERS: pick a number based on your cpu cores and I/O: on a
# 	4-core/8-thread machine diminishing returns kick in between 3
# 	and 4 as the bottleneck shifts to the I/O subsystem. Very high
# 	I/O throughput is a good idea if you are firing up lots of
# 	threads. In fact, high I/O throughput is probably the most
# 	important factor governing search speed. On a one-core virtual
# 	machine extra workers don't do much good and tend to just get
# 	in the way of one another: '1' seems to be best. A high number
# 	of workers on a fast machine risks lockout from the db as too
# 	many requests come too fast: you might need to recalibrate the
# 	default commit counts if you go over 5 (but the default
# 	MPCOMMITCOUNT is very conservative). A SATA SSD will max out at
#   c. 5 threads: more workers cannot grab more data. But a 12-thread
#   Ryzen 1600x with NVMe storage is capable of going faster and
#   faster all of the way up to 12 workers: the drive is no longer
#   the bottleneck. NB: each postgres client will use a decent sized
#   chung of memory: 170-350MB *per worker* has been observed.
#
# MPCOMMITCOUNT: **do not change this** unless you are getting
# 	deluged by messages about failed DB queries (see 'WORKERS'
# 	above) In which case you should *lower* the number because your
# 	many threads are accumulating too many uncommitted transactions.
# 	Avoid increasing this value: it will make very little
# 	difference to your performance, but it will greatly increase
# 	your chances of failed searches. NB: the failures will only
# 	show up in the logs as a number of lines starting with "could
# 	not execute SELECT * FROM..." in the browser you will get
# 	partial results that will present themselves as successfully
# 	executed searches. That is no good at all.
#
# LEMMACHUNKSIZE: how many lemmatized forms to search for at once
#   the query is a regex 'or' that can have > 400 variations; this
#   makes for slow faster; 40 tries of 10 variants is faster. Again,
#   there is no particular reason to change this other than to explore
#   the possibility of relatively unimportant speed gains. This is
#   an option of interest only to debuggers and hard-core optimizers.
#
# INTERMEDIATESEARCHCAP: the maximum number of items to accept in the
#   middle of a search. This is to keep "'et' near 'at'" from going insane
#
# SEARCHCODESTYLE: 'precomposed' is the newer code; 'dynamic' is tried, true
#   and faster. 'precomposed' will be needed some day for a non-forking version
#   of Hipparchia. Setting anything other than 'precomposed' will give you
#   'dynamic'
#
# GOLANGTHREADING: this is *experimental*; it requires SEARCHCODESTYLE = 'precomposed'
#   as well as a working redis installation (the latter is not present by
#   default). If True, your searches will multiprocess by being set through a
#   golang shared object whose goroutines will spawn multiple workers. The
#   point of this is to obviate the need for python to spawn/fork, etc.
#

AUTOCONFIGWORKERS = True
WORKERS = 3

MPCOMMITCOUNT = 250
LEMMACHUNKSIZE = 10
INTERMEDIATESEARCHCAP = 2000000
SEARCHCODESTYLE = 'dynamic'
GOLANGTHREADING = False
