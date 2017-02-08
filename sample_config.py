### [1] Flask variables ###
##  [set once and forget: SECRET_KEY] ##
# DEBUG=True is considered to be a serious security hazard in a networked environment
# if you are working on Hipparchia's code, you might be interested in this; otherwise there
# are only bad reasons to set this to 'True'
DEBUG=False
SECRET_KEY = 'yourkeyhereitshouldbelongandlooklikecryptographicgobbledygook'


### [2] DB variables ###
##  [set once and forget: DBPASS] ##
# a read-only db user is highly recommended; write access means inviting a world of hurt,
# even if the code does everything it can to hobble the ability of DBUSER to alter the DB
DBUSER = 'hippa_rd'
DBHOST = '127.0.0.1'
DBPORT = 5432
DBNAME = 'hipparchiaDB'
DBPASS = 'yourpassheretrytomakeitstrongplease'

LDICT = 'latin_dictionary'
GDICT = 'greek_dictionary'


### [3] Hipparchia performance variable ###
##  [set once and forget: WORKERS] ##
# pick a number based on your cpu cores: on an 8 core machine diminishing returns kick in between 3 and 4 as the bottleneck shifts elsewhere
# on a one-core virtual machine extra workers don't do much good and tend to just get in the way of one another: '1' seems to be best
# a high number on a fast machine risks lockout from the db as too many requests come too fast: will need to recalibrate the default commit count if you go over 5
# your mileage will indeed vary, but N > cores*(.5) is probably not going to do much good. But a faster drive first.
WORKERS = 3


### [4] Hipparchia debug variables ###
##  [only change this if you know why you are doing it] ##
# show DB locations of hits and/or the raw HTML markup inside the DB
# there are no security implications here; these can only be set at launch; any changes require restarting HipparchiaServer
# 'yes' is only useful if you think there is some sort of glitch in the data and/or its representation that you want to check
DBDEBUGMODE = 'no'
HTMLDEBUGMODE = 'no'


### [5] settings that you can only configure here ###
##  [only change this if you know why you are doing it] ##
# HipparchiaServer has to be restarted for them to go into effect
# the css presupposes './server' as part of its path; i.e. you will want to put custom CSS in the
# same directory as the default installed css
TLGASSUMESBETACODE = 'yes'
SHOWLINENUMBERSEVERY = 10
CSSSTYLESHEET = '/static/hipparchia_styles.css'


### [6] the default settings for various 'session' items ###
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
DEFAULTACCENTSMATTER='no'
DEFAULTONEHIT='no'

DEFAULTGREEKCORPUSVALUE = 'yes'
DEFAULTLATINCORPUSVALUE = 'no'
DEFAULTINSCRIPTIONCORPUSVALUE = 'no'
DEFAULTPAPYRUSCORPUSVALUE = 'no'
DEFAULTCHRISTIANCORPUSVALUE = 'no'
