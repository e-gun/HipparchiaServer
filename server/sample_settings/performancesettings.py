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
#   the bottleneck.
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
#   makes for slow faster; 40 tries of 10 variants is faster
#

AUTOCONFIGWORKERS = 'yes'
WORKERS = 3
MPCOMMITCOUNT = 250
LEMMACHUNKSIZE = 10