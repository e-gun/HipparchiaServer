## CONFIGURATION NOTES
## [1] and [3] and [5] are relevant to the initial configuration of HipparchiaServer
## [7] is probably the only place you will visit after that: day-to-day default interface settings

### [1] Flask variables ###
##  [set once and forget: SECRET_KEY] ##
# DEBUG=True is considered to be a serious security hazard in a networked environment
# if you are working on Hipparchia's code, you might be interested in this; otherwise there
# are only bad reasons to set this to 'True'
DEBUG=False
SECRET_KEY = 'yourkeyhereitshouldbelongandlooklikecryptographicgobbledygook'

### [2] network values ###
##  [only change these if you know why you are doing it: presumably you have a firewall problem] ##
##  LISTENINGADDRESS sets the interface to listen on; '0.0.0.0' is 'all'
##  MYEXTERNALIPADDRESS needs to be set if you are going to view polls remotely
##  FLASKSERVEDFROMPORT is the port flask will serve from
##  FLASKSEENATPORT might diverge from this if you are feeding flask through uWSGI + nginx
FLASKSERVEDFROMPORT = 5000
FLASKSEENATPORT = 5000
PROGRESSPOLLDEFAULTPORT = 5010
PROGRESSPOLLMAXPORT = 5001
PROGRESSPOLLMINPORT = 5016
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
# DBDEBUGMODE and HTMLDEBUGMODE will show DB locations of hits and/or the raw HTML markup inside the DB
# there are no security implications here; these can only be set at launch; any changes require restarting HipparchiaServer
# 'yes' is only useful if you think there is some sort of glitch in the data and/or its representation that you want to check
# CALCULATEWORDWEIGHTS will recalibrate the weighting constants: only useful after a new DB build with new corpora definitions.
#   this can take a couple of minutes to calculate, so leaving it at 'yes' is not such a great idea.
#   and the new numbers are not in fact entered into the code, just calculated; so you have to edit dbHeadwordObject() yourself
#   after you are given the numbers to send to it
DBDEBUGMODE = 'no'
HTMLDEBUGMODE = 'no'
CALCULATEWORDWEIGHTS = 'no'


### [5] Hipparchia performance variable ###
##  [set once and forget: WORKERS] ##
# pick a number based on your cpu cores: on an 8 core machine diminishing returns kick in between 3 and 4 as the bottleneck shifts elsewhere
# on a one-core virtual machine extra workers don't do much good and tend to just get in the way of one another: '1' seems to be best
# a high number on a fast machine risks lockout from the db as too many requests come too fast: will need to recalibrate the default commit count if you go over 5
# your mileage will indeed vary, but N > cores*(.5) is probably not going to do much good. Buy a faster drive first.
WORKERS = 3


### [6] settings that you can only configure here ###
##  [only change this if you know why you are doing it] ##
# HipparchiaServer has to be restarted for them to go into effect
# CSSSTYLESHEET presupposes './server' as part of its path; i.e. you will want to put custom CSS in the
#   same directory as the default installed css
# TLGASSUMESBETACODE means that if you only have the TLG active typing 'ball' is like typing 'βαλλ' and 'ba/ll' is 'βάλλ'
# MINIMUMBROWSERWIDTH is either a number of whitespace characters or 'off'
# HOBBLEREGEX is 'yes' if you have foolishly exposed Hipparchia to a network but are not so foolish as to allow "!|'", etc.
#   only [].^$ will be allowed and all digits will be dropped
# EXCLUDEMINORGENRECOUNTS will mitigate spikes in the genre counts when a word appears in a sparsely populated genre
#   by ignoring all 'small' genres whose word values will give them more than a 500:1 hit weight; everything smaller than lyric...
#   this is more or less *essential* if you are dealing with Latin words since the editoral inserions in minor Greek genres
#   will give you 3 words tagged 'mech' whose weight will be 390506.33x as great as any individual word in a historian.
# COLLAPSEDGENRECOUNTS will bundle things like 'apocal' and 'theol' under 'allrelig' when counting
# NUMBEROFGENRESTOTRACK affects how many relative genre weight counts you will see
# AVOIDCIRCLEDLETTERS if you have trouble displaying Ⓖ, etc.
# INDEXBYHEADWORDS will tell the indexer to aggregate words under their dictionary headword;
#   *many* homonymn issues, unparsed words, etc.
#   you probably don't want to enable this unless you are ready to wrestle with the results

CSSSTYLESHEET = '/static/hipparchia_styles.css'
TLGASSUMESBETACODE = 'yes'
SHOWLINENUMBERSEVERY = 10
SUPPRESSLONGREQUESTMESSAGE = 'no'
HOBBLEREGEX = 'no'
MINIMUMBROWSERWIDTH=100
ENOUGHALREADYWITHTHECOPYRIGHTNOTICE='no'
# lexical output settings
SHOWLEXICALSUMMARYINFO = 'yes'
SHOWGLOBALWORDCOUNTS = 'yes'
EXCLUDEMINORGENRECOUNTS='yes'
COLLAPSEDGENRECOUNTS='yes'
NUMBEROFGENRESTOTRACK = 8
AVOIDCIRCLEDLETTERS='no'
INDEXBYHEADWORDS = False


### [7] the default settings for various 'session' items ###
##  [set any/all of these to suit your own typical use scenarios] ##
# these items can all be set to different values via the web interface
# below you have the values that represent what you get if you clear the session and start anew

# valid options for the next are: shortname, authgenre, location, provenance, universalid, converted_date
DEFAULTSORTORDER = 'shortname'
DEFAULTEARLIESTDATE = '-850'
DEFAULTLATESTDATE = '1500'

DEFAULTLINESOFCONTEXT = 4
DEFAULTBROWSERLINES = 20
DEFAULTMAXRESULTS = 200

DEFAULTVARIA='yes'
DEFAULTINCERTA='yes'
DEFAULTSPURIA='yes'
DEFAULTONEHIT='no'

DEFAULTGREEKCORPUSVALUE = 'yes'
DEFAULTLATINCORPUSVALUE = 'yes'
DEFAULTINSCRIPTIONCORPUSVALUE = 'no'
DEFAULTPAPYRUSCORPUSVALUE = 'no'
DEFAULTCHRISTIANCORPUSVALUE = 'no'
