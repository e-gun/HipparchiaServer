# INSISTUPONSTANDARDANGLEBRACKETS: 'no' means you will see ⟨ and ⟩;
#   'yes' means you will see < and >
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
#
# CAPONDICTIONARYFINDS: refuse to find more than N items; useful to stop searches for 'δ'
#   from hijacking the machine

INSISTUPONSTANDARDANGLEBRACKETS = 'no'
FORCELUNATESIGMANOMATTERWHAT = 'no'
RESTOREMEDIALANDFINALSIGMA = 'no'

# lexical output instance
SHOWGLOBALWORDCOUNTS = 'yes'
EXCLUDEMINORGENRECOUNTS = 'yes'
COLLAPSEDGENRECOUNTS = 'yes'
NUMBEROFGENRESTOTRACK = 8
AVOIDCIRCLEDLETTERS = 'no'
FALLBACKTODOUBLESTRIKES = 'yes'
REVERSELEXICONRESULTSBYFREQUENCY = 'yes'
CAPONDICTIONARYFINDS = 50

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

CLICKABLEINDEXEDPASSAGECAP = 1500   # -1, 0, or N
CLICKABLEINDEXEDWORDSCAP = 64000    # -1, 0, or N
SEARCHLISTPREVIEWCAP = 250
SHOWLINENUMBERSEVERY = 10
MINIMUMBROWSERWIDTH = 100
SUPPRESSLONGREQUESTMESSAGE = 'no'
ENOUGHALREADYWITHTHECOPYRIGHTNOTICE = 'no'
