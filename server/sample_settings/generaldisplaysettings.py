# -*- coding: utf-8 -*-
# note that internally 'yes'/'no' are converted to True/False; and so one can use 'yes'/'no'
# but definitely *do not* use 'True'/'False' since they are not the same as True/False...

# INSISTUPONSTANDARDANGLEBRACKETS: False means you will see ⟨ and ⟩;
#   True means you will see < and >
#
# FORCELUNATESIGMANOMATTERWHAT: True means you will override σ and ς
#  	in the data and instead print ϲ; this is only
# 	meaningful if the HipparchiaBuilder (lamentably) had the 'lunates = n' option set to begin with
#
# FORCEUFORV: True means that DB 'pavor' will display as 'pauor'
#
# RESTOREMEDIALANDFINALSIGMA: True means you will, alas, override ϲ
#  	and try to print σ or ς as needed; this is only meaningful if the
#  	HipparchiaBuilder had the 'lunates = y' option set to begin with.
#   NB: if both FORCELUNATESIGMANOMATTERWHAT and RESTOREMEDIALANDFINALSIGMA
#  	are set to True lunates win (and you
#   waste CPU cycles).
#
# SIMPLETEXTOUTPUT will build texts and browser passages without an HTML table. This is much more friendly if
#   you are going to cut and paste texts. It is less easy on the eye.
#
# CAPONDICTIONARYFINDS: refuse to find more than N items; useful to stop searches for 'δ'
#   from hijacking the machine
#
# FINDPRINCIPLEPARTS: show the principle parts of verbs at the head of their dictionary entries
#

INSISTUPONSTANDARDANGLEBRACKETS = False
FORCELUNATESIGMANOMATTERWHAT = False
FORCEUFORV = False
RESTOREMEDIALANDFINALSIGMA = False
SIMPLETEXTOUTPUT = False
SORTWORKSBYNUMBER = True  # otherwise sort them by name

# lexical output instance
DEABBREVIATEAUTHORS = True
SHOWGLOBALWORDCOUNTS = True
EXCLUDEMINORGENRECOUNTS = True
COLLAPSEDGENRECOUNTS = True
NUMBEROFGENRESTOTRACK = 8
AVOIDCIRCLEDLETTERS = False
FALLBACKTODOUBLESTRIKES = True
CAPONDICTIONARYFINDS = 50
FINDPRINCIPLEPARTS = True

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
# SUPPRESSLONGREQUESTMESSAGE = True if you do not want to be
# 	reminded that there is a way to abort your long requests
#
# ENOUGHALREADYWITHTHECOPYRIGHTNOTICE = True if you have lost your
# 	passion for legalese
#

CLICKABLEINDEXEDPASSAGECAP = 1500   # -1, 0, or N
CLICKABLEINDEXEDWORDSCAP = 64000    # -1, 0, or N
SEARCHLISTPREVIEWCAP = 250
SHOWLINENUMBERSEVERY = 10
MINIMUMBROWSERWIDTH = 100
SUPPRESSLONGREQUESTMESSAGE = False
ENOUGHALREADYWITHTHECOPYRIGHTNOTICE = False


# DELETEUNACCENTEDGREEKFROMINDEX prevents fragmentary words in inscriptions, etc from being indexed
#
# DROPLATININAGREEKINDEX will drop Latin words from an index if they are far outnumbered by Greek
#   words. In which case the latin words are almost all editorial comments: 'deest', etc.
#

DELETEUNACCENTEDGREEKFROMINDEX = True
DROPLATININAGREEKINDEX = True

# the next control buttons you might want to drop from the #searchfield
# note that dropping some of these will break core functions
# note also that the relevant paths will remain active so this is not a security measure, just a UI issue
# the full known set is:
# ['addauthortosearchlist', 'excludeauthorfromsearchlist', 'morechoicesbutton', 'fewerchoicesbutton', 'browseto', 'textofthis', 'makeanindex', 'makevocablist', 'authinfobutton']

# BUTTONSTOSKIP = None
BUTTONSTOSKIP = ['makevocablist']


# here you can toggle items in the extended searchfield
# note that dropping some of these will break core functions and there are some nonsense combos you might pick
# note also that the relevant paths will remain active so this is not a security measure, just a UI issue
# the full known set is:
# ['genresautocomplete', 'workgenresautocomplete', 'locationsautocomplete', 'provenanceautocomplete', 'pickgenrebutton', 'excludegenrebutton', 'genreinfobutton']

HOLDINGSTOSKIP = None
# HOLDINGSTOSKIP = ['locationsautocomplete', 'provenanceautocomplete']


# here you can toggle the lexical search boxes
# note that the relevant paths will remain active so this is not a security measure, just a UI issue
# the full known set is:
# ['lexicon', 'parser', 'reverselexicon']
LEXICABOXESTOSKIP = ['parser']


INCLUDEDATESEARCHINGHTML = True
