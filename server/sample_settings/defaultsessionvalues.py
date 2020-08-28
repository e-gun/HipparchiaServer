# -*- coding: utf-8 -*-
### the default instance for various 'session' items ###
##  [set any/all of these to suit your own typical use scenarios] ##
# these items can all be set to different temporary values via the
# 	web interface below you have the values that represent what you
# 	get if you clear the session and reset your web session

# note that internally 'yes'/'no' are converted to True/False; and so one can use 'yes'/'no'
# but definitely *do not* use 'True'/'False' since they are not the same as True/False...

# valid options for the next are: shortname, authgenre, location, provenance, universalid, converted_date
DEFAULTSORTORDER = 'shortname'

DEFAULTEARLIESTDATE = '-850'
DEFAULTLATESTDATE = '1500'

DEFAULTLINESOFCONTEXT = 4
DEFAULTBROWSERLINES = 10
DEFAULTMAXRESULTS = 200

DEFAULTGREEKCORPUSVALUE = True
DEFAULTLATINCORPUSVALUE = True
DEFAULTINSCRIPTIONCORPUSVALUE = False
DEFAULTPAPYRUSCORPUSVALUE = False
DEFAULTCHRISTIANCORPUSVALUE = False

DEFAULTVARIA = True
DEFAULTINCERTA = True
DEFAULTSPURIA = True
DEFAULTONEHIT = False
DEFAULTINDEXBYHEADWORDS = False
DEFAULTINDEXBYFREQUENCY = False

DEFAULTSUMMARIZELEXICALSENSES = True
DEFAULTSUMMARIZELEXICALAUTHORS = True
DEFAULTSUMMARIZELEXICALQUOTES = True
DEFAULTSUMMARIZEPHRASES = False
DEFAULTAUTHORFLAGGING = True

DEFAULTHIGHLIGHTSQUAREBRACKETS = True
DEFAULTHIGHLIGHTROUNDBRACKETS = False
DEFAULTHIGHLIGHTANGLEDBRACKETS = True
DEFAULTHIGHLIGHTCURLYBRACKETS = True

DEFAULTUSERAWINPUTSTYLE = False