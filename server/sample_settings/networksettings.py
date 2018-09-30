### [2] network values ###
##  [only change these if you know why you are doing it: you have a firewall problem, etc.] ##
#
# LISTENINGADDRESS sets the interface to listen on; '0.0.0.0' is
# 	'all', i.e., anyone anywhere can reach this server at this address
#
# MYEXTERNALIPADDRESS needs to be set if you are going to view polls
# 	remotely: this is basically a firewall/routing issue
#
# FLASKSERVEDFROMPORT is the port flask will serve from
#
# FLASKSEENATPORT might diverge from this if you are feeding flask
# 	through uWSGI + nginx
#
# CONNECTIONTYPE determines whether you generate a series of one-off connections to the
#   database or if you use a persistent pool of connections instead. 'simple' gives you
#   the former. Anything else gives you the latter which is faster. But with a pool you
#   will have more memory allocated all of the time and you run the risk of exhausting
#   the pool if you have too many concurrent searches (but simple connections are supposed
#   to be made as a fallback when a pooled one is not available).
#
# POLLCONNECTIONTYPE will either use a shared memory ProgressPoll() or one that saves
#   information in a redis database. The latter option is set by setting the value to 'redis'.
#   If Hipparchia is served via WSGI you cannot save the polls in shared memory.
#
# REDISPORT says where to look for redis; 0 means use a (faster) UnixDomainSocketConnection.
#   redis does not enable this by default. Instead redis defaults to TCP connections at 6379.
#   redis.conf should be edited accordingly.
#
# REDISCOCKET defines where to look for the socket file; this needs to match the value in redis.conf.
#
# REDISDBID sets the numerical value of the database we will use; 0 is a typical default; if your machine
#   has other things going on with redis, then it is possible to generate conflicts is you leave this as '0'
#
# SEARCHLISTCONNECTIONTYPE if set to 'redis' you will not use Manager() to manage the searchlists but redis
#   instead. At the moment this is all about tracking down a memory management oddity. Do not use this
#   unless searches are hanging and you are desperate to find a fix... This code is significantly slower.
#   Waiting for redis to do a SPOP is not nearly as fast as accessing memory directly. The longer the searchlist
#   the greater the penalty: a search of 236,835 texts is quite costly.
#

# hipparchia itself as a server
FLASKSERVEDFROMPORT = 5000
FLASKSEENATPORT = 5000
PROGRESSPOLLDEFAULTPORT = 5010
LISTENINGADDRESS = '127.0.0.1'
MYEXTERNALIPADDRESS = '127.0.0.1'


# postgresql connection instance; see also 'securitysettings.py'
DBHOST = '127.0.0.1'
DBPORT = 5432
CONNECTIONTYPE = 'pool'

# you might be using redis; but note that redis is NOT pre-installed in standard or minimal installations
REDISPORT = 6379
REDISCOCKET = '/tmp/redis.sock'
REDISDBID = 0
POLLCONNECTIONTYPE = 'notredis'
SEARCHLISTCONNECTIONTYPE = 'notredis'
