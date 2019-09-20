# -*- coding: utf-8 -*-
### the default instance for various 'session' items ###
##  [set any/all of these to suit your own typical use scenarios] ##
# these items can all be set to different temporary values via the
# 	web interface below you have the values that represent what you
# 	get if you clear the session and reset your web session

# note that internally 'yes'/'no' are converted to True/False, but one should still use 'yes'/'no'
# and definitely *do not* use 'True'/'False' since they are not the same as True/False...

# valid options for the next are: shortname, authgenre, location, provenance, universalid, converted_date
DEFAULTSORTORDER = 'shortname'

DEFAULTEARLIESTDATE = '-850'
DEFAULTLATESTDATE = '1500'

DEFAULTLINESOFCONTEXT = 4
DEFAULTBROWSERLINES = 10
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

DEFAULTSUMMARIZELEXICALSENSES = 'no'
DEFAULTSUMMARIZELEXICALAUTHORS = 'yes'
DEFAULTSUMMARIZELEXICALQUOTES = 'yes'

DEFAULTHIGHLIGHTSQUAREBRACKETS = 'yes'
DEFAULTHIGHLIGHTROUNDBRACKETS = 'no'
DEFAULTHIGHLIGHTANGLEDBRACKETS = 'yes'
DEFAULTHIGHLIGHTCURLYBRACKETS = 'yes'
