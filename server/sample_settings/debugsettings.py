# -*- coding: utf-8 -*-
# note that internally 'yes'/'no' are converted to True/False; and so one can use 'yes'/'no'
# but definitely *do not* use 'True'/'False' since they are not the same as True/False...

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
# 	require restarting HipparchiaServer True is only useful if you
# 	think there is some sort of glitch in the data and/or its
# 	representation that you want to check
#
# LEXDEBUGMODE will show the dictionary ID number after the entry name
#
# PARSERBUGMODE will show the xref value after the match
#
# ENABLELOGGING = True will turn on logging and send the logs to
#   HIPPARCHIALOGFILE
#
# HIPPARCHIALOGFILE is the log file; pick your path wisely: it is
#   relative to 'run.py' and so to 'HipparchiaServer'
#
# RETAINREDISPOLLS will prevent redis-based progress polls from being deleted after use
#
# RETAINFIGURES will prevent graphs from being deleted after display
#
# BLOCKRESETPATHS if not False, then you cannot access (the hidden) URLs 'resetvectors/' or 'resetvectorimages/'
#
# ALLOWUSERTOSETDEBUGMODES will enable toggles for next five options on the web interface
#   (DBDEBUGMODE, LEXDEBUGMODE, PARSERDEBUGMODE, HTMLDEBUGMODE, and SEARCHMARKEDUPLINE)
#
# SEARCHMARKEDUPLINE will enable searching for things like "hmu_date_or_numeric_equivalent_of_date". It will also ruin
#   many, many other kinds of search
#
# ONTHEFLYLEXICALFIXES is False if HipparchiaBuilder did not try to fix the bad Perseus data for Euripides, etc.
#

SUPPRESSWARNINGS = True
ENABLELOGGING = False
HIPPARCHIALOGFILE = '../HipparchiaData/hipparchia_access.log'
RETAINREDISPOLLS = False
RETAINFIGURES = False
BLOCKRESETPATHS = True

ALLOWUSERTOSETDEBUGMODES = False
DBDEBUGMODE = False
LEXDEBUGMODE = False
PARSERDEBUGMODE = False
HTMLDEBUGMODE = False
SEARCHMARKEDUPLINE = False

ONTHEFLYLEXICALFIXES = False