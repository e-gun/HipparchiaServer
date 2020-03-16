//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-20
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)
//

//
// BULK OPERATIONS ON ARRAYS OF ELEMENTS
//

function hidemany(arrayofelements) {
    for (let i = 0; i < arrayofelements.length; i++) {
        $(arrayofelements[i]).hide();
        }
}

function showmany(arrayofelements) {
    for (let i = 0; i < arrayofelements.length; i++) {
        $(arrayofelements[i]).show();
        }
}

function clearmany(arrayofelements) {
    for (let i = 0; i < arrayofelements.length; i++) {
        $(arrayofelements[i]).val('');
        }
}

// python to generate these...
// idfind = re.compile(r'id="(.*?)"')
// y = re.findall(idfind, x)
// y.sort()

const activeoptionshtmlids = Array('#activeoptions', '#chrisactive', '#chrnotisactive', '#ddpisactive', '#ddpnotisactive',
    '#frequencyindexingactive', '#frequencyindexinginactive', '#grkisactive', '#grkisnotactive', '#headwordindexingactive',
    '#headwordindexiningactive', '#insisactive', '#insnotisactive', '#latisactive', '#latisnotactive', '#lemmatizing-isoff',
    '#lemmatizing-ison', '#onehitisfalse', '#onehitistrue', '#spuriaisfalse', '#spuriaistrue', '#undatedisfalse', '#undatedistrue',
    '#usingautoinput', '#usingrawinput', '#variaisfalse', '#variaistrue', '#vectorizing-isoff', '#vectorizing-ison');

const basehtmlids = Array('#versioning');

const browserdialoghtmlidl = Array('#browseback', '#browseforward', '#browserclose', '#browserdialog', '#browserdialogtext',
    '#browsernavigationbuttons');

const hipparchiahelphtmlids = Array('#BasicSyntax', '#Browsing', '#Dictionaries', '#Extending', '#IncludedMaterials',
    '#Interface', '#LemmaSearching', '#MakingSearchLists', '#Oddities', '#Openness', '#RegexSearching', '#SpeedSearching',
    '#VectorSearching', '#helptabs');

const lexicahtmlids = Array('#lexica', '#lexicalsearch', '#lexicon', '#parser', '#reverselexicon');

const miscuielementshtmlids = Array('#bottommessage', '#clear_button', '#clickforhelp', '#cookiemessage', '#helpbutton',
    '#moretools', '#openoptionsbutton', '#upperleftbuttons', '#vector_options_button');

const outputboxhtmlids = Array('#authoroutputcontent', '#exclusioninfocell', '#jscriptwigetcell', '#outputbox',
    '#searchinfo', '#searchlistcontents', '#selectioninfocell', '#selectionstable', '#timerestrictions');

const saveslotshtmlids = Array('#load01', '#load02', '#load03', '#load04', '#load05', '#loadslots', '#save01', '#save02',
    '#save03', '#save04', '#save05', '#savedprofiles', '#saveslots', '#toggleloadslots', '#togglesaveslots');

const searchfieldhtmlids = Array('#addauthortosearchlist', '#authinfobutton', '#authorendpoint', '#authorholdings',
    '#authorsautocomplete', '#browseto', '#earliestdate', '#edts', '#endpointbutton-isclosed', '#endpointbutton-isopen',
    '#endpointnotice', '#excludeauthor', '#excludeauthorfromsearchlist', '#excludegenre', '#fewerchoicesbutton', '#fromnotice', '#genreinfobutton',
    '#genrelistcontents', '#genresautocomplete', '#includeincerta', '#includespuria', '#includevaria', '#latestdate',
    '#ldts', '#level00', '#level00endpoint', '#level01', '#level01endpoint', '#level02', '#level02endpoint', '#level03',
    '#level03endpoint', '#level04', '#level04endpoint', '#level05', '#level05endpoint', '#locationsautocomplete',
    '#makeanindex', '#morechoicesbutton','#provenanceautocomplete', '#rawendpointinput', '#rawlocationinput', '#searchfield',
    '#selectionendpoint', '#spuriacheckboxes', '#workendpoint', '#workgenresautocomplete', '#worksautocomplete');

const searchhtlmids = Array('#browserclickscriptholder', '#displayresults', '#imagearea', '#indexclickscriptholder',
    '#lexicadialog', '#lexicadialogtext', '#mainbody', '#pollingdata', '#searchsummary', '#vectorspinnerscriptholder',
    '#vectorspinnerscriptholder');

const setoptionshtmlids = Array('#alt_clear_button', '#alt_moretools', '#alt_upperleftbuttons',
    '#alt_vector_options_button', '#authorssummary', '#autofillinput', '#bracketangled', '#bracketcurly', '#bracketround',
    '#bracketsquare', '#browserspinner', '#christiancorpus', '#closeoptionsbutton', '#collapseattic', '#debugdb', '#debughtml',
    '#debuglex', '#debugparse', '#fontchoice', '#frequencyindexing_n', '#frequencyindexing_y', '#greekcorpus',
    '#headwordindexing_n', '#headwordindexing_y', '#hitlimitspinner', '#indexskipsknownwords', '#inscriptioncorpus',
    '#latincorpus', '#linesofcontextspinner', '#manualinput', '#mophologytablesoptions', '#morphdialects', '#morphduals',
    '#morphemptyrows', '#morphfinite', '#morphimper', '#morphinfin', '#morphpcpls', '#onehit_n', '#onehit_y', '#papyruscorpus',
    '#principleparts', '#quotesummary', '#searchinsidemarkup', '#sensesummary', '#setoptionsnavigator', '#showwordcounts',
    '#simpletextoutput', '#sortresults', '#suppresscolors', '#zaplunates', '#zapvees');

const vectorformattingdotpyids = Array(['#analogiescheckbox', '#analogyfinder', '#cosdistbylineorword',
    '#cosdistbysentence', '#cosinedistancelineorwordcheckbox', '#cosinedistancesentencecheckbox', '#nearestneighborsquery',
    '#semanticvectornnquerycheckbox', '#semanticvectorquery', '#semanticvectorquerycheckbox', '#sentencesimilarity',
    '#sentencesimilaritycheckbox', '#tensorflowgraph', '#tensorflowgraphcheckbox', '#topicmodel', '#topicmodelcheckbox']);

// searchfield.html structure

const toplevelofsearchfieldhtml = Array('#searchfield', '#authorholdings', '#selectionendpoint');

// passage selection UI

const levelsids = Array('#level05', '#level04', '#level03', '#level02', '#level01', '#level00');

const inputids = levelsids.concat(Array('#rawlocationinput'));

const endpointlevelssids = Array('#level05endpoint', '#level04endpoint', '#level03endpoint', '#level02endpoint',
    '#level01endpoint', '#level00endpoint');

const endpointids = endpointlevelssids.concat(Array('#rawendpointinput', '#authorendpoint', '#authorendpoint'));

const endpointnotices = Array('#endpointnotice', '#fromnotice');

const endpointbuttons = Array('#endpointbutton-isopen', '#endpointbutton-isclosed');

const rawinputuielements = Array('#rawlocationinput', '#rawendpointinput', '#fromnotice', '#endpointnotice',
        '#endpointbutton-isopen', '#endpointbutton-isclosed', '#rawlocationinput', '#rawendpointinput');

const endpointnoticesandbuttons = endpointnotices.concat(endpointbuttons);

// category selection ui

const categoryautofills = Array('#genresautocomplete', '#workgenresautocomplete', '#locationsautocomplete', '#provenanceautocomplete');

const nonessentialautofills = categoryautofills.concat(Array('#worksautocomplete'));

// info buttons

const infobuttons = Array('#authinfobutton', '#genreinfobutton');

// action buttons

const coreactionbuttons = Array('#addauthortosearchlist', '#excludeauthorfromsearchlist');
const extendedactionbuttons = Array('#browseto', '#makeanindex', '#textofthis', '#fewerchoices', '#pickgenre', '#excludegenre');
const actionbuttons = Array().concat(coreactionbuttons, extendedactionbuttons);

// datespinners and includespuria checkboxes

const datespinners = Array('#edts', '#ldts');
const miscrestrictions = Array().concat(datespinners, ['#spuriacheckboxes']);

// infoboxes

const infoboxes = Array('#genrelistcontents', '#outputbox');

// loadandsave UI

const loadandsaveslots = Array('#loadslots', '#saveslots');

// searchforms

const extrasearchforms = Array('#lemmatasearchform', '#proximatesearchform', '#proximatelemmatasearchform');
const extrasearchuielements = Array('#nearornot', '#termonecheckbox', '#termtwocheckbox', '#complexsearching');

//

const tohideonfirstload = Array().concat(['#browserdialog', '#helptabs', '#fewerchoicesbutton', '#vectorzone'], vectorformattingdotpyids, endpointnoticesandbuttons,
    endpointids, inputids, actionbuttons, infobuttons, miscrestrictions, infoboxes, extrasearchforms, extrasearchuielements);