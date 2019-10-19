# -*- coding: utf-8 -*-
# note that internally 'yes'/'no' are converted to True/False, but one should still use 'yes'/'no'
# and definitely *do not* use 'True'/'False' since they are not the same as True/False...

##  [set once and forget: SECRET_KEY] ##
SECRET_KEY = 'yourkeyhereitshouldbelongandlooklikecryptographicgobbledygook'

### DB variables ###
##  [set once and forget: DBPASS] ##
# a read-only db user is highly recommended; write access means inviting a world of hurt,
# even if the code does everything it can to prevent the DBUSER from altering the DB

# DBWRITEUSER & DBWRITEPASS should match the values in config.ini for HipparchiaBuilder
#   unless you want a third user. These variables allow the vector infrastructure to store
#   calculated vector spaces and then to fetch them so that the very time-consuming task
#   of mapping out the space does not have to be repeated more than necessary.

DBUSER = 'hippa_rd'
DBNAME = 'hipparchiaDB'
DBPASS = 'yourpassheretrytomakeitstrongplease'

DBWRITEUSER = 'consider_re-using_HipparchiaBuilder_user'
DBWRITEPASS = 'consider_re-using_HipparchiaBuilder_pass'


# HOBBLEREGEX is 'yes' if you have foolishly exposed Hipparchia to a
# 	network but are not so foolish as to allow "!|'", etc. only
# 	[].^$ will be allowed and all digits will be dropped

# FOOLISHLYALLOWREGEX is a collection of character you *will* accept: '!*+', e.g.

HOBBLEREGEX = 'no'
FOOLISHLYALLOWREGEX = ''

