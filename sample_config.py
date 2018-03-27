## CONFIGURATION NOTES
## [0] is probably the only place you will visit after your initial configuration: day-to-day default interface settings
## [1] and [3] and [5] are relevant to the initial configuration of HipparchiaServer
## if DBUSER, DBNAME, and DBPASS re not properly configured in [3], HipparchiaServer will not launch

### [0] the default settings for various 'session' items ###
##  [set any/all of these to suit your own typical use scenarios] ##
# these items can all be set to different temporary values via the
# 	web interface below you have the values that represent what you
# 	get if you clear the session and reset your web session

# valid options for the next are: shortname, authgenre, location, provenance, universalid, converted_date
DEFAULTSORTORDER = 'shortname'
DEFAULTEARLIESTDATE = '-850'
DEFAULTLATESTDATE = '1500'

DEFAULTLINESOFCONTEXT = 4
DEFAULTBROWSERLINES = 14
DEFAULTMAXRESULTS = 200

DEFAULTGREEKCORPUSVALUE = 'yes'
DEFAULTLATINCORPUSVALUE = 'yes'
DEFAULTINSCRIPTIONCORPUSVALUE = 'no'
DEFAULTPAPYRUSCORPUSVALUE = 'no'
DEFAULTCHRISTIANCORPUSVALUE = 'no'

DEFAULTVARIA = 'yes'
DEFAULTINCERTA = 'yes'
DEFAULTSPURIA = 'yes'
DEFAULTONEHIT = 'no'
DEFAULTINDEXBYHEADWORDS = 'no'
DEFAULTINDEXBYFREQUENCY = 'no'

DEFAULTSHOWLEXICALSENSES = 'yes'
DEFAULTSHOWLEXICALAUTHORS = 'yes'
DEFAULTSHOWLEXICALQUOTES = 'yes'

DEFAULTHIGHLIGHTSQUAREBRACKETS = 'yes'
DEFAULTHIGHLIGHTROUNDBRACKETS = 'no'
DEFAULTHIGHLIGHTANGLEDBRACKETS = 'yes'
DEFAULTHIGHLIGHTCURLYBRACKETS = 'yes'

### [1] Flask variables ###
##  [set once and forget: SECRET_KEY] ##
SECRET_KEY = 'yourkeyhereitshouldbelongandlooklikecryptographicgobbledygook'

### [2] network values ###
##  [only change these if you know why you are doing it: presumably you have a firewall problem] ##
#
# LISTENINGADDRESS sets the interface to listen on; '0.0.0.0' is
# 	'all'
#
# MYEXTERNALIPADDRESS needs to be set if you are going to view polls
# 	remotely
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

FLASKSERVEDFROMPORT = 5000
FLASKSEENATPORT = 5000
PROGRESSPOLLDEFAULTPORT = 5010
LISTENINGADDRESS = '127.0.0.1'
MYEXTERNALIPADDRESS = '127.0.0.1'
CONNECTIONTYPE = 'pool'

### [3] DB variables ###
##  [set once and forget: DBPASS] ##
# a read-only db user is highly recommended; write access means inviting a world of hurt,
# even if the code does everything it can to prevent the DBUSER from altering the DB

DBUSER = 'hippa_rd'
DBHOST = '127.0.0.1'
DBPORT = 5432
DBNAME = 'hipparchiaDB'
DBPASS = 'yourpassheretrytomakeitstrongplease'


### [4] Hipparchia debug variables ###
##  [only change this if you know why you are doing it] ##
#
# SUPPRESSWARNINGS will turn of various messages like:
#   MorphPossibilityObject.getbaseform() is confused ἐνέρριψε, ἐν, ἐν-ῥίπτω ['ἐνέρριψε', 'ἐν', 'ἐν-ῥίπτω']
#   These are not of much interest unless you are debugging the source code
#
# DBDEBUGMODE and HTMLDEBUGMODE will show DB locations of hits and/or
# 	the raw HTML markup inside the DB there are no security
# 	implications here; these can only be set at launch; any changes
# 	require restarting HipparchiaServer 'yes' is only useful if you
# 	think there is some sort of glitch in the data and/or its
# 	representation that you want to check
#
# CALCULATEWORDWEIGHTS will recalibrate the weighting constants: only
# 	useful after a new DB build with new corpora definitions.
# 	this can take a couple of minutes to calculate, so leaving it
# 	at 'yes' is not such a great idea. And the new numbers are
# 	not in fact entered into the code, just calculated; so you have
# 	to edit dbHeadwordObject() yourself  after you are given the
# 	numbers to send to it; if COLLAPSEDGENRECOUNTS is 'yes', you will
#   not see all of the possibilities
#
# ENABLELOGGING = 'yes' will turn on logging and send the logs to
#   HIPPARCHIALOGFILE
#
# HIPPARCHIALOGFILE is the log file; pick your path wisely: it is
#   relative to 'run.py' and so to 'HipparchiaServer'
#

SUPPRESSWARNINGS = 'yes'
DBDEBUGMODE = 'no'
HTMLDEBUGMODE = 'no'
CALCULATEWORDWEIGHTS = 'no'
ENABLELOGGING = 'no'
HIPPARCHIALOGFILE = '../HipparchiaData/hipparchia_access.log'

### [5] Hipparchia performance variables ###
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


### [6] settings that you can only configure here ###
##  [only change these items if you know why you are doing it] ##
# HipparchiaServer has to be restarted for them to go into effect
#
# CSSSTYLESHEET presupposes './server' as part of its path; i.e. you
# 	will want to put custom CSS in the same directory as the
# 	default installed css
#
# TLGASSUMESBETACODE means that if you only have the TLG active
# 	typing 'ball' is like typing 'βαλλ' and 'ba/ll' is 'βάλλ'
#
# UNIVERSALASSUMESBETACODE means that all latin input is converted to
# 	unicode. You will be unable to search for 'arma' because it
# 	will be parsed as 'αρμα' and so hit words like 'φαρμάκων' and
# 	'μαρμαίρωϲιν'
#
# CLICKABLEINDEXEDPASSAGECAP: you can click to browse the passage
# 	associated with an index item. Why would you even turn
# 	something so awesome off? Because the clicks will stop working
# 	with big indices: 'RangeError: Maximum call stack size
# 	exceeded'.  This is a javascript/browser limitation: too many
# 	objects get piled onto the page. Different browsers have
# 	different caps.  If you hit the cap, then you will have a fat,
# 	useless wad of tags that are super slow to load and take   up
# 	lots of memory but do nothing else. The same problem can arise
# 	for the lookup clicks in a monster index  even if you turn the
# 	browser clicking off. -1: always try to make every item of
# 	every index clickable; 0: never try to make any item clickable;
# 	N: do not try if you are indexing more than N lines (1500 is a
# 	decent number to pick)
#
# CLICKABLEINDEXEDWORDSCAP: see CLICKABLEINDEXEDPASSAGECAP for the
# 	issues. -1: always try to make every word of every index;
# 	clickable 0: never try to make any word clickable; N: do not try
# 	if you are indexing more than N word (64000 is a decent number
# 	to pick)
#
# SEARCHLISTPREVIEWCAP: do not show more than N items; useful since
#   some lists might contain >100k items and choke the browser
#
# SHOWLINENUMBERSEVERY does just what you think it does
#
# MINIMUMBROWSERWIDTH is either a number of whitespace characters or
# 	'off'
#
# SUPPRESSLONGREQUESTMESSAGE = 'yes' if you do not want to be
# 	reminded that there is a way to abort your long requests
#
# ENOUGHALREADYWITHTHECOPYRIGHTNOTICE = 'yes' if you have lost your
# 	passion for legalese
#
# HOBBLEREGEX is 'yes' if you have foolishly exposed Hipparchia to a
# 	network but are not so foolish as to allow "!|'", etc. only
# 	[].^$ will be allowed and all digits will be dropped
#
# INSISTUPONSTANDARDANGLEBRACKETS: 'no' means you will see ⟨ and ⟩;
#   'yes' means you will see < and >
#
# FORCELUNATESIGMANOMATTERWHAT: 'yes' means you will override σ and ς
#  	in the data and instead print ϲ; this is only
# 	meaningful if the HipparchiaBuilder (lamentably) had the 'lunates = n' option set to begin with
#
# RESTOREMEDIALANDFINALSIGMA: 'yes' means you will, alas, override ϲ
#  	and try to print σ or ς as needed; this is only meaningful if the
#  	HipparchiaBuilder had the 'lunates = y' option set to begin with.
#   NB: if both FORCELUNATESIGMANOMATTERWHAT and RESTOREMEDIALANDFINALSIGMA
#  	are set to 'yes' lunates win (and you
#   waste CPU cycles).
#
# EXCLUDEMINORGENRECOUNTS will mitigate spikes in the genre counts
# 	when a word appears in a sparsely populated genre by ignoring
# 	all 'small' genres whose word values will give them more than a
# 	500:1 hit weight; everything smaller than lyric... this is more
# 	or less *essential* if you are dealing with Latin words since
# 	the editorial insertions in minor Greek genres will give you 3
# 	words tagged 'mech' whose weight will be 390506.33x as great as
# 	any individual word in a historian.
#
# COLLAPSEDGENRECOUNTS will bundle things like 'apocal' and 'theol'
# 	under 'allrelig' when counting
#
# NUMBEROFGENRESTOTRACK affects how many relative genre weight counts
# 	you will see
#
# AVOIDCIRCLEDLETTERS if you have trouble displaying Ⓖ, etc.
#
# FALLBACKTODOUBLESTRIKES will give you 𝔾, etc. if you turned Ⓖ off.
#
# REVERSELEXICONRESULTSBYFREQUENCY will either give you the lookup
# 	results in alphabetical order ('no') or in descending order by
# 	frequency of occurrence ('yes')
#

CSSSTYLESHEET = '/static/hipparchia_styles.css'
TLGASSUMESBETACODE = 'yes'
UNIVERSALASSUMESBETACODE = 'no'
CLICKABLEINDEXEDPASSAGECAP = 1500   # -1, 0, or N
CLICKABLEINDEXEDWORDSCAP = 64000    # -1, 0, or N
SEARCHLISTPREVIEWCAP = 250
SHOWLINENUMBERSEVERY = 10
MINIMUMBROWSERWIDTH = 100
SUPPRESSLONGREQUESTMESSAGE = 'no'
ENOUGHALREADYWITHTHECOPYRIGHTNOTICE = 'no'
HOBBLEREGEX = 'no'
INSISTUPONSTANDARDANGLEBRACKETS = 'no'
FORCELUNATESIGMANOMATTERWHAT = 'no'
RESTOREMEDIALANDFINALSIGMA = 'no'
DISTINCTGREEKANDLATINFONTS = 'no'

# lexical output settings
SHOWGLOBALWORDCOUNTS = 'yes'
EXCLUDEMINORGENRECOUNTS = 'yes'
COLLAPSEDGENRECOUNTS = 'yes'
NUMBEROFGENRESTOTRACK = 8
AVOIDCIRCLEDLETTERS = 'no'
FALLBACKTODOUBLESTRIKES = 'yes'
REVERSELEXICONRESULTSBYFREQUENCY = 'yes'


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
# CONCEPTSEARCHINGENABLED allows you to search for sentences related to a lemmatized
#   term or terms. What sentences are about "men"? Which sentences are related to the
#   relationship that subsists between "good" and "man"?
#
# TENSORFLOWVECTORSENABLED will let you dig into the deeply broken tensorflow code.
#   Results only go to the console or filesystem. It is very slow to execute. The
#   neighbors it identifies make very little sense. See the notes ad loc. Only enable
#   if you are debugging/coding.
#
# MAXVECTORSPACE: what is the largest set of words you are willing
#   to vectorize in order to find the association network of a given
#   lemmatized term? This sort of query get exponentially harder to
#   execute and so you if you allow a full corpora search you will
#   bring your system to it knees for a long, long time. 7548165 is
#   all of Latin. 13518316 is all Greek literature up to 300 BCE.
#   If you search for a common word you can easily
#   chew up >24GB of RAM. Your system will hang unless/until Hipparchia
#   receives more memory optimizations. Gensim NN vectorization of all
#   of Latin will take 554.08s on a 6-threaded 3.6GHz machine.
#
# VECTORDISTANCECUTOFF: how close Word A needs to be to Word B for the associative matrix
#   calculations to decide that there is a relationship worth pursuing: a value between 1 and 0
#   1 --> identical;
#   0 --> completely unrelated
#
# DBWRITEUSER & DBWRITEPASS should match the values in config.ini for HipparchiaBuilder
#   unless you want a third user. These varaibles allow the vector infrastructure to stor
#   calculated vector spaces and then to fetch them so that the very time-consuming task
#   of mapping out the space does not have to be repeated more than necessary.
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
# AUTOVECTORIZE will fill the vector db in the background; this will chew up plenty of resources:
#   both drive space and CPU time; do not set this to 'yes' unless you are ready for the commitment
#

SEMANTICVECTORSENABLED = 'no'
LITERALCOSINEDISTANCEENABLED = 'no'
CONCEPTSEARCHINGENABLED = 'no'
CONCEPTMAPPINGENABLED = 'no'
TENSORFLOWVECTORSENABLED = 'no'
SENTENCESIMILARITYENABLED = 'no'
MAXVECTORSPACE = 7548165
MAXSENTENCECOMPARISONSPACE = 50000
DBWRITEUSER = 'consider_re-using_HipparchiaBuilder_user'
DBWRITEPASS = 'consider_re-using_HipparchiaBuilder_pass'
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
