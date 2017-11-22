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

FLASKSERVEDFROMPORT = 5000
FLASKSEENATPORT = 5000
PROGRESSPOLLDEFAULTPORT = 5010
LISTENINGADDRESS = '127.0.0.1'
MYEXTERNALIPADDRESS = '127.0.0.1'


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

AUTOCONFIGWORKERS = 'yes'
WORKERS = 3
MPCOMMITCOUNT = 750


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

# lexical output settings
SHOWGLOBALWORDCOUNTS = 'yes'
EXCLUDEMINORGENRECOUNTS = 'yes'
COLLAPSEDGENRECOUNTS = 'yes'
NUMBEROFGENRESTOTRACK = 8
AVOIDCIRCLEDLETTERS = 'no'
FALLBACKTODOUBLESTRIKES = 'yes'
REVERSELEXICONRESULTSBYFREQUENCY = 'yes'
FORCELUNATESIGMANOMATTERWHAT = 'no'
RESTOREMEDIALANDFINALSIGMA = 'no'
