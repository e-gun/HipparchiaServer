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
# RETAINREDISPOLLS will prevent redis-based progress polls from being deleted after use
#
# RETAINFIGURES will prevent graphs from being deleted after display
#
# BLOCKRESETPATHS if not 'no', then you cannot access 'resetvectors/' or 'resetvectorimages/'
#

SUPPRESSWARNINGS = 'yes'
DBDEBUGMODE = 'no'
HTMLDEBUGMODE = 'no'
CALCULATEWORDWEIGHTS = 'no'
ENABLELOGGING = 'no'
HIPPARCHIALOGFILE = '../HipparchiaData/hipparchia_access.log'
RETAINREDISPOLLS = 'no'
RETAINFIGURES = 'no'
BLOCKRESETPATHS = 'yes'
