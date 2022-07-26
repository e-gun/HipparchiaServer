# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from server import hipparchia
from server.formatting.miscformatting import htmlcommentdecorator
from server.semanticvectors.vectorhelpers import vectordefaults, vectorlabels, vectorranges


@htmlcommentdecorator
def vectorhtmlforfrontpage() -> str:
	"""

	read the config and generate the html

	:return:
	"""

	cdc = """
		<span id="cosinedistancesentencecheckbox">
			<span class="small">Word environs:</span>
			<span class="small">by sentence</span><input type="checkbox" id="cosdistbysentence" value="yes" title="Cosine distances: words in the same sentence">
		</span>
		<span id="cosinedistancelineorwordcheckbox">
			<span class="small">within N lines/words</span><input type="checkbox" id="cosdistbylineorword" value="yes" title="Cosine distances within N lines or words">
		</span>
		"""

	cs = """
		<span id="semanticvectorquerycheckbox">
			<span class="small">Concept search</span><input type="checkbox" id="semanticvectorquery" value="yes" title="Make a latent semantic analysis query">
		</span>
		"""

	cm = """
		<span id="semanticvectornnquerycheckbox">
			<span class="small">Concept map</span><input type="checkbox" id="nearestneighborsquery" value="yes" title="Make a nearest neighbor query">
		</span>
		"""

	tf = """
		<span id="tensorflowgraphcheckbox">
			<span class="small">tensor flow graph:</span>
			<input type="checkbox" id="tensorflowgraph" value="yes" title="Make an associative graph of all the selected words">
		</span>
		"""

	ss = """
		<span id="sentencesimilaritycheckbox">
			<span class="small">sentence similarities</span>
			<input type="checkbox" id="sentencesimilarity" value="yes" title="Find sentence similarities in and between works">
		</span>
	"""

	lda = """
		<span id="topicmodelcheckbox">
			<span class="small">Topic map</span>
			<input type="checkbox" id="topicmodel" value="yes" title="Find topics within a search zone">
		</span>
	"""

	anal = """
		<span id="analogiescheckbox">
			<span class="small">Analogy Finder</span>
			<input type="checkbox" id="analogyfinder" value="yes" title="Find analogies in a vector space (A:B::C:D)">
		</span>
	"""

	testing = """
		<span id="vectortestcheckbox">
			<span class="small">Vectortestfunction</span>
			<input type="checkbox" id="vectortestfunction" value="yes" title="Do whatever one does...">
		</span>
	"""


	if not hipparchia.config['SEMANTICVECTORSENABLED']:
		return str()

	textmapper = {#'LITERALCOSINEDISTANCEENABLED': cdc,
	              # 'CONCEPTSEARCHINGENABLED': cs,
	              'CONCEPTMAPPINGENABLED': cm,
	              # 'TENSORFLOWVECTORSENABLED': tf,
	              # 'SENTENCESIMILARITYENABLED': ss,
	              'VECTORANALOGIESENABLED': anal,
	              'TOPICMODELINGENABLED': lda,
	              'TESTINGVECTORBUTTONENABLED': testing,
	              }

	vectorhtml = list()
	for conf in textmapper:
		if hipparchia.config[conf]:
			vectorhtml.append(textmapper[conf])

	vectorhtml = '\n'.join(vectorhtml)

	return vectorhtml


@htmlcommentdecorator
def vectorhtmlforoptionsbar() -> str:
	"""

	if we are doing vectors, then allow values to be set

	need html (and js...) support for this

	:return:
	"""

	if not hipparchia.config['SEMANTICVECTORSENABLED']:
		emptyframe = """
		<div id="vectoroptionsetter"></div>
		"""
		return emptyframe

	framedcontents = """
	<div id="vectoroptionsetter" class="sidenavigation">
		<div id="vector_upperleftbuttons">
			<span id="vectoralt_openoptionsbutton" class="ui-icon ui-icon-gear" title="Configuration options"></span>
			<span id="close_vector_options_button" class="ui-icon ui-icon-arrowthick-1-sw" title="Vector options"></span>
			<span id="vectoralt_moretools" title="Lexical tools" class="ui-icon ui-icon-wrench"></span>
			<span id="vectoralt_clear_button" class="ui-icon ui-icon-close" title="Reset session/Clear search"></span>
		</div>
		{contents}
	</div>
	"""

	fieldtemplate = """
	<fieldset id="{k}field">
		<legend>{lg}</legend>
		<input id="{k}" type="text" value="{d}" width="20px;">
	</fieldset>
	"""

	legendtemplate = '{lb} ({min} - {max})'

	htmlsupplement = list()
	for k in vectordefaults.keys():
		r = list(vectorranges[k])
		m = r[0]
		x = r[-1]
		lg = legendtemplate.format(lb=vectorlabels[k], min=m, max=x)
		htmlsupplement.append(fieldtemplate.format(k=k, lg=lg, d=vectordefaults[k]))

	htmlsupplement = '\n'.join(htmlsupplement)
	htmlsupplement = '<p class="optionlabel">Semantic Vector Settings</p>\n' + htmlsupplement

	baggingtemplate = """
	<span id="{sid}" style="">
			<span class="small">{slb}</span>
			<input type="checkbox" id="{bid}" value="yes" title="{bti}">
	</span>
	"""

	baggingoptions = {
		'flat': {'sid': 'flatbagspan', 'slb': 'Flat bags', 'bid': 'flatbagbutton', 'bti': 'Build flat bags of words'},
		'alternates': {'sid': 'alternatebagspan', 'slb': 'Composite alternates', 'bid': 'alternatebagbutton', 'bti': 'Build composite alternates bags of words'},
		'winnertakesall': {'sid': 'winnerbagspan', 'slb': 'Winner takes all', 'bid': 'winnertakesallbutton', 'bti': 'Bags contain only the most popular homonym'},
		'unlemmatized': {'sid': 'unlemmatizedspan', 'slb': 'No lemmatizing', 'bid': 'unlemmatizedbutton', 'bti': 'Bags contain exactly what the sentence says'},
	}

	baggingsupplement = list()
	for b in baggingoptions:
		sid = baggingoptions[b]['sid']
		slb = baggingoptions[b]['slb']
		bid = baggingoptions[b]['bid']
		bti = baggingoptions[b]['bti']
		baggingsupplement.append(baggingtemplate.format(sid=sid, slb=slb, bid=bid, bti=bti))

	baggingsupplement = '&middot;&nbsp;\n'.join(baggingsupplement)

	baggingsupplement = '<p class="optionlabel">How to fill the bags of words</p>\n' + baggingsupplement

	# prepend
	htmlsupplement = baggingsupplement + htmlsupplement

	htmlsupplement = framedcontents.format(contents=htmlsupplement)

	return htmlsupplement


@htmlcommentdecorator
def getsearchfieldbuttonshtml() -> str:
	"""

	which buttons to show in #searchfield

	full set is:

		<button id="addauthortosearchlist" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="Include this author/work"><span class="ui-icon ui-icon-plus"></span><span class="ui-button-icon-space"> </span>&nbsp;</button>
		<button id="excludeauthorfromsearchlist" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="Exclude this author/work"><span class="ui-icon ui-icon-minus"></span><span class="ui-button-icon-space"> </span>&nbsp;</button>
		<button id="morechoicesbutton" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="More search choices"><span class="ui-icon ui-icon-arrowreturnthick-1-s"></span><span class="ui-button-icon-space"> </span>&nbsp;</button>
		<button id="fewerchoicesbutton" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="Fewer search choices"><span class="ui-icon ui-icon-arrowreturnthick-1-n"></span><span class="ui-button-icon-space"> </span>&nbsp;</button>
		<button id="browseto" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="Browse this location"><span class="ui-icon ui-icon-note"></span><span class="ui-button-icon-space"> </span>&nbsp;</button>
		<button id="textofthis" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="Generate a simple text of this selection"><span class="ui-icon ui-icon-bookmark"></span><span class="ui-button-icon-space"> </span>&nbsp;</button>
		<button id="makeanindex" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="Build an index to this selection"><span class="ui-icon ui-icon-calculator"></span><span class="ui-button-icon-space"> </span>&nbsp;</button>
		<button id="makevocablist" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="Build a vocabulary list for this selection"><span class="ui-icon ui-icon-lightbulb"></span><span class="ui-button-icon-space"> </span>&nbsp;</button>
		<button id="authinfobutton" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="Show/Hide local info about the works of this author"><span class="ui-icon ui-icon-person"></span><span class="ui-button-icon-space"> </span>&nbsp;</button>

	:return:
	"""

	buttontemplate = '\t\t<button id="{i}" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="{t}"><span class="ui-icon ui-icon-{g}"></span><span class="ui-button-icon-space"></span>&nbsp;</button>'

	knownbuttons = {'addauthortosearchlist': ('Include this author/work', 'plus'),
	                'excludeauthorfromsearchlist': ('Exclude this author/work', 'minus'),
	                'morechoicesbutton': ('More search choices', 'arrowreturnthick-1-s'),
	                'fewerchoicesbutton': ('Fewer search choices', 'arrowreturnthick-1-n'),
	                'browseto': ('Browse this location', 'note'),
	                'textofthis': ('Generate a simple text of this selection', 'bookmark'),
	                'makeanindex': ('Build an index to this selection', 'calculator'),
	                'makevocablist': ('Build a vocabulary list for this selection', 'lightbulb'),
	                'authinfobutton': ('Show/Hide local info about the works of this author', 'person')}

	skipping = hipparchia.config['BUTTONSTOSKIP']
	if not isinstance(skipping, list):
		skipping = list()

	mybuttons = [b for b in knownbuttons if b not in skipping]

	mybuttons = [buttontemplate.format(i=b, t=knownbuttons[b][0], g=knownbuttons[b][1]) for b in mybuttons]

	buttonhtml = '\n'.join(mybuttons)

	return buttonhtml


@htmlcommentdecorator
def getauthorholdingfieldhtml() -> str:
	"""

	what to show in #authorholdings

	:return:
	"""

	inputtemplate = '\t\t<input type="text" name="{b}" id="{a}" placeholder="{c}">'
	buttontemplate = '\t\t<button id="{a}" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="{c}"><span class="ui-icon ui-icon-{b}"></span><span class="ui-button-icon-space"></span>&nbsp;</button>'

	holdingsmapper = {'genresautocomplete': (inputtemplate, 'geres', 'Author Categories'),
	                  'workgenresautocomplete': (inputtemplate, 'workgenres', 'Work Genres'),
	                  'locationsautocomplete': (inputtemplate, 'locations', 'Author Locations'),
	                  'provenanceautocomplete': (inputtemplate, 'provenances', 'Work Provenances'),
	                  'pickgenrebutton': (buttontemplate, 'plus', 'Include this category and/or genre'),
	                  'excludegenrebutton': (buttontemplate, 'minus', 'Exclude this category and/or genre'),
	                  'genreinfobutton': (buttontemplate, 'clipboard', 'Show/Hide list of available categories')}

	skipping = hipparchia.config['HOLDINGSTOSKIP']
	if not isinstance(skipping, list):
		skipping = list()

	myitems = [h for h in holdingsmapper if h not in skipping]

	myitems = [holdingsmapper[i][0].format(a=i, b=holdingsmapper[i][1], c=holdingsmapper[i][2]) for i in myitems]

	returnhtml = '\n'.join(myitems)

	return returnhtml


@htmlcommentdecorator
def getdaterangefieldhtml() -> str:
	"""

	date range spinner html

	:return:
	"""

	datehtml = """
		<br />
		<fieldset id="edts">
			<legend>Starting year</legend>
			<input id="earliestdate" type="text" value="-850" width="20px;">
		</fieldset>
		<fieldset id="ldts">
			<legend>Ending year</legend>
			<input id="latestdate" type="text" value="1500" width="20px;">
		</fieldset>
		<fieldset id="spuriacheckboxes">
			<legend>Include works that are...</legend>
			spurious <input type="checkbox" id="includespuria" value="no">&nbsp;&middot;&nbsp;
			of uncertain date<input type="checkbox" id="includeincerta" value="no">&nbsp;&middot;&nbsp;
			of varied date (e.g., scholia)<input type="checkbox" id="includevaria" value="no"><br />
		</fieldset>
	"""

	if not hipparchia.config['INCLUDEDATESEARCHINGHTML']:
		return str()
	else:
		return datehtml


@htmlcommentdecorator
def getlexicafieldhtml() -> str:
	"""

	word lookup html

	"""

	divtemplate = """
	<div id="lexica">
		<br />
		{boxes}
		<button id="lexicalsearch" class="ui-button ui-corner-all ui-widget ui-button-icon-only" title="Search dictionary or parser"><span class="ui-button-icon ui-icon ui-icon-search"></span><span class="ui-button-icon-space"> </span>&nbsp;</button>
	</div>
	"""

	boxtemplate = '<input type="text" name="lexicon" class="lexica" id="{a}" placeholder="{b}">'

	mappings = {
		'lexicon': '(Dictionary Search)',
		'parser': '(Morphology Search)',
		'reverselexicon': '(English to Greek or Latin)',
	}

	skipping = hipparchia.config['LEXICABOXESTOSKIP']
	if not isinstance(skipping, list):
		skipping = list()

	myitems = [m for m in mappings if m not in skipping]

	boxhtml = list()
	for m in sorted(myitems):
		boxhtml.append(boxtemplate.format(a=m, b=mappings[m]))

	boxhtml = '\n'.join(boxhtml)

	thehtml = divtemplate.format(boxes=boxhtml)

	return thehtml
