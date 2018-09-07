# CSSSTYLESHEET presupposes './server/css' as part of its path; i.e. you
# 	will want to put custom CSS in the same directory as the
# 	default installed css ('hipparchiastyles.css')
#
# HOSTEDFONTFAMILY sets which of the font families that Hipparchia downloads upon
#   installation will be served to clients. Any of them should ensure full
#   coverage for both Greek and Latin without any need to have a special font
#   installed at the system level by people who visit.
#
# DEFAULTLOCALFONT sets the global font. A generic unicode font with good coverage
#   is what you want to pick. You are also responsible for getting the name
#   right. And, most importantly, it should be installed at the system-level for
#   anyone who visits.
#
# DEFAULTLOCALGREEKFONT is meaningful only if DISTINCTGREEKANDLATINFONTS is 'yes'.
#   In that case Greek characters will display in this font
#
# DEFAULTLOCALNONGREEKFONT is meaningful only if DISTINCTGREEKANDLATINFONTS is 'yes'.
#   In that case all non-Greek characters will display in this font.
#
# ENBALEFONTPICKER allows you to select fonts from the web interface; but see notes on
#   FONTPICKERLIST before enabling this. Anything other than 'yes' disables this option.
#
# FONTPICKERLIST is a list of fonts to choose from. These are *local to the client*.
#   The item set here alters DEFAULTLOCALFONT in the CSS. So there is no point in enabling
#   this in an environment where you expect to have remote users: if they choose 'GFSOrpheusSans'
#   what are the chances that it is already installed on their system?
#

CSSSTYLESHEET = 'hipparchiastyles.css'
DISTINCTGREEKANDLATINFONTS = 'no'
HOSTEDFONTFAMILY = 'Roboto'  # DejaVu, IBMPlex, Noto, and Roboto should be pre-installed by Hipparchia
DEFAULTLOCALFONT = 'yourfonthere_otherwise_fallbacktohipparchiahostedfonts'
DEFAULTLOCALGREEKFONT = 'yourfonthere_otherwise_fallbacktohipparchiahostedfonts'
DEFAULTLOCALNONGREEKFONT = 'yourfonthere_otherwise_fallbacktohipparchiahostedfonts'
ENBALEFONTPICKER = 'yes'
FONTPICKERLIST = ['Noto', 'DejaVu', 'IBMPlex', 'Roboto']