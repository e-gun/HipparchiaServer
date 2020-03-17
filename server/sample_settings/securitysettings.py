# -*- coding: utf-8 -*-
# note that internally 'yes'/'no' are converted to True/False; and so one can use 'yes'/'no'
# but definitely *do not* use 'True'/'False' since they are not the same as True/False...

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

# FOOLISHLYALLOWREGEX is a collection of character you *will* accept: '!*+,', e.g.
#   HOBBLEREGEX set to 'yes'/True will override anything you put here

HOBBLEREGEX = False
FOOLISHLYALLOWREGEX = ''

# 62 chars in the following line of Accius: Quódsi, ut decuit, stáres mecum aut méus ⟨te⟩ maestarét dolor,
# 14 chars for Digest 50.17.211.pr.2
MAXIMUMQUERYLENGTH = 64
MAXIMUMLOCUSLENGTH = 24
MAXIMUMLEXICALLENGTH = 18

# apply remote access restrictions

LIMITACCESSTOLOGGEDINUSERS = False
SETADEFAULTUSER = True
DEFAULTREMOTEUSER = 'hipparchia'
DEFAULTREMOTEPASS = 'yourremoteuserpassheretrytomakeitstrongplease'
