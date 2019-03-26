# note that internally 'yes'/'no' are converted to True/False, but one should still use 'yes'/'no'
# and definitely *do not* use 'True'/'False' since they are not the same as True/False...

# CSSSTYLESHEET presupposes './server/css' as part of its path; i.e. you
# 	will want to put custom CSS in the same directory as the
# 	default installed css ('hipparchiastyles.css')
#
# SUPPRESSCOLORS if set to 'yes' will set all colors to black in the CSS.
#
# HOSTEDFONTFAMILY sets which of the font families that Hipparchia downloads upon
#   installation will be served to clients. Any of them should ensure full
#   coverage for both Greek and Latin without any need to have a special font
#   installed at the system level by people who visit. HipparchiaThirdPartySoftware contains more
#   hostable fonts inside the 'extra_fonts' directory. Install the TTF files into
#   ~/hipparchia_venv/HipparchiaServer/server/static/ttf
#
# USEFONTFILESFORSTYLES will use something like Roboto-BoldItalic.ttf instead of
#   using CSS commands like font-style: italic; + font-weight: bold;
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
# FONTPICKERLIST is a list of fonts to choose from. These can EITHER be served OR local to the client.
#   The item set here alters DEFAULTLOCALFONT in the CSS. To avoid problems the list should contain
#   only HOSTEDFONTS or you know you have installed. Also, remote users can get in trouble here:
#   if they choose 'GFSOrpheusSans' what are the chances that it is already installed on their system?
#

CSSSTYLESHEET = 'hipparchiastyles.css'
DISTINCTGREEKANDLATINFONTS = 'no'
SUPPRESSCOLORS = 'no'
HOSTEDFONTFAMILY = 'Noto'  # Noto should be pre-installed by Hipparchia; see above about adding more
USEFONTFILESFORSTYLES = 'yes'  # Only valid if you are using a HOSTEDFONTFAMILY
DEFAULTLOCALFONT = 'yourfonthere_otherwise_fallbacktohipparchiahostedfonts'  # Arial is often present and it is very good
DEFAULTLOCALGREEKFONT = 'yourfonthere_otherwise_fallbacktohipparchiahostedfonts'
DEFAULTLOCALNONGREEKFONT = 'yourfonthere_otherwise_fallbacktohipparchiahostedfonts'
ENBALEFONTPICKER = 'no'
FONTPICKERLIST = ['Noto', 'CMUSans', 'CMUSerif', 'DejaVuSans', 'DejaVuSerif', 'EBGaramond',
                  'Fira', 'IBMPlex', 'Roboto', 'Ubuntu']  # see above about editing this list
