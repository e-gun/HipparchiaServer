# -*- coding: utf-8 -*-
# note that internally 'yes'/False are converted to True/False; and so one can use 'yes'/False
# but definitely *do not* use 'True'/'False' since they are not the same as True/False...

# TLGASSUMESBETACODE means that if you only have the TLG active
# 	typing 'ball' is like typing 'βαλλ' and 'ba/ll' is 'βάλλ'
#
# UNIVERSALASSUMESBETACODE means that all latin input is converted to
# 	unicode. You will be unable to search for 'arma' because it
# 	will be parsed as 'αρμα' and so hit words like 'φαρμάκων' and
# 	'μαρμαίρωϲιν'

TLGASSUMESBETACODE = True
UNIVERSALASSUMESBETACODE = False
