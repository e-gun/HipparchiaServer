//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-20
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)


function setoptions(sessionvar, value){
	$.getJSON( {url: '/setsessionvariable/' + sessionvar + '/' + value,
	    async: false,
	    success: function (resultdata) {
		 // do nothing special: the return exists but is not relevant
	    }
	    });
}

function refreshselections() {
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
}

function loadoptions() {
    $.getJSON('/getsessionvariables', function (data) {
        // console.log(data);
        const simpletoggles = {
            'authorssummary': $('#authorssummary'),
            'bracketangled': $('#bracketangled'),
            'bracketcurly': $('#bracketcurly'),
            'bracketround': $('#bracketround'),
            'bracketsquare': $('#bracketsquare'),
            'christiancorpus': $('#christiancorpus'),
            'collapseattic': $('#collapseattic'),
            'cosdistbylineorword': $('#cosdistbylineorword'),
            'cosdistbysentence': $('#cosdistbysentence'),
            'debughtml': $('#debughtml'),
            'debugdb': $('#debugdb'),
            'debuglex': $('#debuglex'),
            'debugparse': $('#debugparse'),
            'greekcorpus': $('#greekcorpus'),
            'incerta': $('#includeincerta'),
            'indexskipsknownwords': $('#indexskipsknownwords'),
            'inscriptioncorpus': $('#inscriptioncorpus'),
            'latincorpus': $('#latincorpus'),
            'morphdialects': $('#morphdialects'),
            'morphduals': $('#morphduals'),
            'morphemptyrows': $('#morphemptyrows'),
            'morphimper': $('#morphimper'),
            'morphinfin': $('#morphinfin'),
            'morphfinite': $('#morphfinite'),
            'morphpcpls': $('#morphpcpls'),
            'morphtables': $('#morphtables'),
            'nearestneighborsquery': $('#nearestneighborsquery'),
            'papyruscorpus': $('#papyruscorpus'),
            'principleparts': $('#principleparts'),
            'quotesummary': $('#quotesummary'),
            'searchinsidemarkup': $('#searchinsidemarkup'),
            'semanticvectorquery': $('#semanticvectorquery'),
            'sensesummary': $('#sensesummary'),
            'sentencesimilarity': $('#sentencesimilarity'),
            'showwordcounts': $('#showwordcounts'),
            'simpletextoutput': $('#simpletextoutput'),
            'spuria': $('#includespuria'),
            'suppresscolors': $('#suppresscolors'),
            'tensorflowgraph': $('#tensorflowgraph'),
            'topicmodel': $('#topicmodel'),
            'varia': $('#includevaria'),
            'zaplunates': $('#zaplunates'),
            'zapvees': $('#zapvees'),
        };

        Object.keys(simpletoggles).forEach(function(key) {
            if (data[key] === 'yes') {
                simpletoggles[key].prop('checked', true);
            } else {
                simpletoggles[key].prop('checked', false);
            }
        });

        const sidebaricontoggles = {
            'greekcorpus': {'t': $('#grkisactive'), 'f': $('#grkisnotactive')},
            'latincorpus': {'t': $('#latisactive'), 'f': $('#latisnotactive')},
            'inscriptioncorpus': {'t': $('#insisactive'), 'f': $('#insnotisactive')},
            'papyruscorpus': {'t': $('#ddpisactive'), 'f': $('#ddpnotisactive')},
            'christiancorpus': {'t': $('#chrisactive'), 'f': $('#chrnotisactive')},
            'spuria': {'t': $('#spuriaistrue'), 'f': $('#spuriaisfalse')},
            'varia': {'t': $('#variaistrue'), 'f': $('#variaisfalse')},
            'incerta': {'t': $('#undatedistrue'), 'f': $('#undatedisfalse')}
        };

        Object.keys(sidebaricontoggles).forEach(function(key) {
            if (data[key] === 'yes') {
                sidebaricontoggles[key]['t'].show();
                sidebaricontoggles[key]['f'].hide();
            } else {
                sidebaricontoggles[key]['t'].hide();
                sidebaricontoggles[key]['f'].show();
            }
        });

        const xoredtoggles = {
            'onehit': {'y': $('#onehit_y'), 'n': $('#onehit_n'), 'f': $('#onehitisfalse'), 't': $('#onehitistrue')},
            'headwordindexing': {'y': $('#headwordindexing_y'), 'n': $('#headwordindexing_n'), 'f': $('#headwordindexinginactive'), 't': $('#headwordindexingactive')},
            'indexbyfrequency': {'y': $('#frequencyindexing_y'), 'n': $('#frequencyindexing_n'), 'f': $('#frequencyindexinginactive'), 't': $('#frequencyindexingactive')}
        };

        Object.keys(xoredtoggles).forEach(function(key) {
            if (data[key] === 'yes') {
                xoredtoggles[key]['y'].prop('checked', true);
                xoredtoggles[key]['n'].prop('checked', false);
                xoredtoggles[key]['t'].show();
                xoredtoggles[key]['f'].hide();
            } else {
                xoredtoggles[key]['n'].prop('checked', true);
                xoredtoggles[key]['y'].prop('checked', false);
                xoredtoggles[key]['f'].show();
                xoredtoggles[key]['t'].hide();
            }
        });

        let setspinnervalues = {
            'earliestdate': $('#earliestdate'),
            'latestdate': $('#latestdate'),
            'linesofcontext': $('#linesofcontextspinner'),
            'maxresults': $('#hitlimitspinner'),
            'browsercontext': $('#browserspinner')
        };

        Object.keys(setspinnervalues).forEach(function(key) {
            setspinnervalues[key].spinner('value', data[key]);
        });

        $('#sortresults').val(data.sortorder);
        $('#sortresults').selectmenu('refresh');

        $('#fontchoice').val(data.fontchoice);
        $('#fontchoice').selectmenu('refresh');

        if(data['principleparts'] === 'yes') { $('#mophologytablesoptions').show(); } else { $('#mophologytablesoptions').hide(); }

        if (data.cosdistbysentence === 'yes' || data.cosdistbylineorword === 'yes' || data.semanticvectorquery === 'yes' ||
            data.nearestneighborsquery === 'yes' || data.tensorflowgraph === 'yes' || data.sentencesimilarity === 'yes' ||
            data.topicmodel === 'yes') {
            showextendedsearch();
            }
        });
}


//
// vector spinners
//

function loadvectorspinners() {
    $.getJSON('/getvectorranges', function (vsdata) {
        let bcsh = document.getElementById("vectorspinnerscriptholder");
        if (bcsh.hasChildNodes()) {
            bcsh.removeChild(bcsh.firstChild);
        }
        $('#vectorspinnerscriptholder').html(vsdata);
    });
}


// UPPER LEFT OPTIONS PANEL CLICKS

function openoptionsslider() {
    let windowWidth = $(window).width();
    let w = Math.min(windowWidth*.30, 250);
    document.getElementById("setoptionsnavigator").style.width = w+"px";
    document.getElementById("vectoroptionsetter").style.width = "0";
    document.getElementById("mainbody").style.marginLeft = w+"px";
    $('#alt_upperleftbuttons').show();
    $('#vector_upperleftbuttons').hide();
    $('#upperleftbuttons').hide();
}

function closeoptionsslider() {
    document.getElementById("setoptionsnavigator").style.width = "0";
    document.getElementById("vectoroptionsetter").style.width = "0";
    document.getElementById("mainbody").style.marginLeft = "0";
    $('#alt_upperleftbuttons').hide();
    $('#vector_upperleftbuttons').hide();
    $('#upperleftbuttons').show();
}

function openvectoroptionsslider() {
    let windowWidth = $(window).width();
    let w = Math.min(windowWidth*.30, 250);
    document.getElementById("setoptionsnavigator").style.width = "0";
    document.getElementById("vectoroptionsetter").style.width = w+"px";
    document.getElementById("mainbody").style.marginLeft = w+"px";
    $('#alt_upperleftbuttons').hide();
    $('#vector_upperleftbuttons').show();
    $('#upperleftbuttons').hide();
}

$('#openoptionsbutton').click(function(){
    loadoptions();
    openoptionsslider();
});

$('#vectoralt_openoptionsbutton').click(function(){
    loadoptions();
    openoptionsslider();
});

$('#closeoptionsbutton').click(function(){
    closeoptionsslider();
});

$('#close_vector_options_button').click(function(){
    closeoptionsslider();
});

$('#vector_options_button').click(function(){
    loadoptions();
    loadvectorspinners();
    openvectoroptionsslider();
});

$('#alt_vector_options_button').click(function(){
    loadoptions();
    loadvectorspinners();
    openvectoroptionsslider();
});

// BROWSER CLICKS

function browsetopassage() {
    let auth = $('#authorsautocomplete').val().slice(-7, -1);
    let wrk = $('#worksautocomplete').val().slice(-4, -1);
    let l5 = $('#level05').val();
    let l4 = $('#level04').val();
    let l3 = $('#level03').val();
    let l2 = $('#level02').val();
    let l1 = $('#level01').val();
    let l0 = $('#level00').val();
    let lvls = [ l5, l4, l3, l2, l1, l0];
    let loc = Array();
    for (let i = 5; i > -1; i-- ) {
        if (lvls[i] !== '') {
            loc.push(lvls[i]);
        } else {
            if (i === 5) {
                loc.push('_0');
                }
            }
        }

    loc.reverse();
    let locstring = loc.join('|');

    if (wrk.length !== 3) { wrk = '_firstwork'}
    loc = 'locus/' + auth + '/' + wrk + '/' +locstring.slice(0, locstring.length);
    browseuponclick(loc);
}

$('#browseto').click(function(){
    $('#endpointbutton-isopen').hide();
    $('#endpointbutton-isclosed').hide();
    browsetopassage();
});

$('#addtolist').click(function(){ addtosearchlist(); });

$('#fewerchoices').click(function(){
    $('#morechoices').show();
    const ids = Array('#fewerchoices', '#genresautocomplete', '#workgenresautocomplete', '#locationsautocomplete',
        '#provenanceautocomplete', '#pickgenre', '#excludegenre', '#genreinfo', '#genrelistcontents', '#edts',
        '#ldts', '#spur');
    hidemany(ids);
    });

$('#morechoices').click(function(){
    $('#morechoices').hide();
    const ids = Array('#fewerchoices', '#genresautocomplete', '#workgenresautocomplete', '#locationsautocomplete',
        '#provenanceautocomplete', '#pickgenre', '#excludegenre', '#genreinfo', '#edts', '#ldts', '#spur');
    bulkshow(ids);
    loadoptions();
    });

function showextendedsearch() {
        const ids = Array('#cosinedistancesentencecheckbox', '#cosinedistancelineorwordcheckbox', '#semanticvectorquerycheckbox',
            '#semanticvectornnquerycheckbox', '#tensorflowgraphcheckbox', '#sentencesimilaritycheckbox', '#complexsearching', '#topicmodelcheckbox');
        bulkshow(ids);
}

$('#moretools').click(function(){ $('#lexica').toggle(); });
$('#alt_moretools').click(function(){ $('#lexica').toggle(); });
$('#vectoralt_moretools').click(function(){ $('#lexica').toggle(); });

// not working as expected
// supposed to clear out the other boxes and restore the placeholder; only clears the boxes

//$('#parser').on('focus', function() {
//    var $rl = $('#reverselexicon');
//    var $lx = $('#lexicon');
//    $rl.val(''); $rl.removeAttr("value"); $rl.attr('placeholder', '(English to Greek or Latin)');
//    $lx.val(''); $lx.removeAttr("value"); $lx.attr('placeholder', '(Dictionary Search)');
//    });
//
//$('#reverselexicon').on('focus', function() {
//    var $pp = $('#parser');
//    var $lx = $('#lexicon');
//    $pp.val(''); $pp.removeAttr("value"); $pp.attr('placeholder', '(Morphology Search)');
//    $lx.val(''); $lx.removeAttr("value"); $lx.attr('placeholder', '(Dictionary Search)');
//    });
//
//$('#lexicon').on('focus', function() {
//    var $rl = $('#reverselexicon');
//    var $lx = $('#lexicon');
//    $rl.val(''); $rl.removeAttr("value"); $rl.attr('placeholder', '(English to Greek or Latin)');
//    $lx.val(''); $lx.removeAttr("value"); $lx.attr('placeholder', '(Dictionary Search)');
//    });


$('#lexicalsearch').click(function(){
    // note that modifications to this script should be kept in sync with dictionaryentryjs() in jsformatting.py
    let dictterm = $('#lexicon').val();
    let restoreme = dictterm;
    // trailing space will be lost unless you do this: ' gladiator ' --> ' gladiator' and so you can't spearch for only that word...
    if (dictterm.slice(-1) === ' ') { dictterm = dictterm.slice(0, -1) + '%20'; }
    let parseterm = $('#parser').val();
    let reverseterm = $('#reverselexicon').val();
    let windowWidth = $(window).width();
    let windowHeight = $(window).height();
    let searchterm = '';
    let url = '';
    let dialogtitle = '';
    let mydictfield = '';
    if ( dictterm.length > 0) {
        searchterm = dictterm;
        url = '/dictsearch/';
        dialogtitle = restoreme;
        mydictfield = '#lexicon';
    } else if ( parseterm.length > 0 ) {
        searchterm = parseterm;
        url = '/parse/';
        dialogtitle = searchterm;
        mydictfield = '#parser';
        restoreme = searchterm;
    } else if ( reverseterm.length > 0 ) {
        let originalterm = reverseterm;
        // disgustingly, if you send 'STRING ' to window.location it strips the whitespace and turns it into 'STRING'
        if (reverseterm.slice(-1) === ' ') { reverseterm = reverseterm.slice(0, -1) + '%20'; }
        searchterm = reverseterm;
        url = '/reverselookup/';
        dialogtitle = originalterm;
        mydictfield = '#reverselexicon';
        restoreme = searchterm;
    } else {
        searchterm = 'nihil';
        url = '/dictsearch/';
        dialogtitle = searchterm;
    }

    $(mydictfield).val('[Working on it...]');
    $.getJSON(url + searchterm, function (definitionreturned) {
        let ldt = $('#lexicadialogtext');
        let jshld = $('#lexicaljsscriptholder');
        ldt.dialog({
            closeOnEscape: true,
            autoOpen: false,
            maxHeight: windowHeight*.9,
            maxWidth: windowHeight*.9,
            minWidth: windowHeight*.33,
            position: { my: "left top", at: "left top", of: window },
            title: dialogtitle,
            draggable: true,
            icons: { primary: 'ui-icon-close' },
            click: function() { $( this ).dialog( 'close' ); }
            });
            ldt.dialog( 'open' );
            ldt.html(definitionreturned['newhtml']);
            jshld.html(definitionreturned['newjs']);
            $(mydictfield).val(restoreme);
        });
    });


//
// the radio options
//

$('#headwordindexing_y').click( function(){
    setoptions('headwordindexing', 'yes'); $('#headwordindexingactive').show(); $('#headwordindexinginactive').hide();
});

$('#headwordindexing_n').click( function(){
    setoptions('headwordindexing', 'no'); $('#headwordindexinginactive').show(); $('#headwordindexingactive').hide();
});

$('#frequencyindexing_y').click( function(){
    setoptions('indexbyfrequency', 'yes'); $('#frequencyindexingactive').show(); $('#frequencyindexinginactive').hide();
});

$('#frequencyindexing_n').click( function(){
    setoptions('indexbyfrequency', 'no'); $('#frequencyindexinginactive').show(); $('#frequencyindexingactive').hide();
});


$('#onehit_y').click( function(){
    setoptions('onehit', 'yes'); $('#onehitistrue').show(); $('#onehitisfalse').hide();
});

$('#onehit_n').click( function(){
    setoptions('onehit', 'no'); $('#onehitisfalse').show(); $('#onehitistrue').hide();
});

$('#includespuria').change(function() {
    if(this.checked) { setoptions('spuria', 'yes'); } else { setoptions('spuria', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#includevaria').change(function() {
    if(this.checked) { setoptions('varia', 'yes'); } else { setoptions('varia', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#includeincerta').change(function() {
    if(this.checked) { setoptions('incerta', 'yes'); } else { setoptions('incerta', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#greekcorpus').change(function() {
    if(this.checked) { setoptions('greekcorpus', 'yes'); } else { setoptions('greekcorpus', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#latincorpus').change(function() {
    if(this.checked) { setoptions('latincorpus', 'yes'); } else { setoptions('latincorpus', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#inscriptioncorpus').change(function() {
    if(this.checked) { setoptions('inscriptioncorpus', 'yes'); } else { setoptions('inscriptioncorpus', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#papyruscorpus').change(function() {
    if(this.checked) { setoptions('papyruscorpus', 'yes'); } else { setoptions('papyruscorpus', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#christiancorpus').change(function() {
    if(this.checked) { setoptions('christiancorpus', 'yes'); } else { setoptions('christiancorpus', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#sensesummary').change(function() {
    if(this.checked) { setoptions('sensesummary', 'yes'); } else { setoptions('sensesummary', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#authorssummary').change(function() {
    if(this.checked) { setoptions('authorssummary', 'yes'); } else { setoptions('authorssummary', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#quotesummary').change(function() {
    if(this.checked) { setoptions('quotesummary', 'yes'); } else { setoptions('quotesummary', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#bracketsquare').change(function() {
    if(this.checked) { setoptions('bracketsquare', 'yes'); } else { setoptions('bracketsquare', 'no');}
    refreshselections();
    loadoptions();
    });

$('#bracketround').change(function() {
    if(this.checked) { setoptions('bracketround', 'yes'); } else { setoptions('bracketround', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#bracketangled').change(function() {
    if(this.checked) { setoptions('bracketangled', 'yes'); } else { setoptions('bracketangled', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#bracketcurly').change(function() {
    if(this.checked) { setoptions('bracketcurly', 'yes'); } else { setoptions('bracketcurly', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#debughtml').change(function() {
    if(this.checked) { setoptions('debughtml', 'yes'); } else { setoptions('debughtml', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#debugdb').change(function() {
    if(this.checked) { setoptions('debugdb', 'yes'); } else { setoptions('debugdb', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#debuglex').change(function() {
    if(this.checked) { setoptions('debuglex', 'yes'); } else { setoptions('debuglex', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#debugparse').change(function() {
    if(this.checked) { setoptions('debugparse', 'yes'); } else { setoptions('debugparse', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#indexskipsknownwords').change(function() {
    if(this.checked) { setoptions('indexskipsknownwords', 'yes'); } else { setoptions('indexskipsknownwords', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#searchinsidemarkup').change(function() {
    if(this.checked) { setoptions('searchinsidemarkup', 'yes'); } else { setoptions('searchinsidemarkup', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#zaplunates').change(function() {
    if(this.checked) { setoptions('zaplunates', 'yes'); } else { setoptions('zaplunates', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#zapvees').change(function() {
    if(this.checked) { setoptions('zapvees', 'yes'); } else { setoptions('zapvees', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#suppresscolors').change(function() {
    if(this.checked) { setoptions('suppresscolors', 'yes'); } else { setoptions('suppresscolors', 'no'); }
    refreshselections();
    loadoptions();
    window.location.href = '/';
    });

$('#simpletextoutput').change(function() {
    if(this.checked) { setoptions('simpletextoutput', 'yes'); } else { setoptions('simpletextoutput', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#principleparts').change(function() {
    if(this.checked) { setoptions('principleparts', 'yes'); } else { setoptions('principleparts', 'no'); }
    if(this.checked) { $('#mophologytablesoptions').show(); } else { $('#mophologytablesoptions').hide(); }
    refreshselections();
    loadoptions();
    });

$('#showwordcounts').change(function() {
    if(this.checked) { setoptions('showwordcounts', 'yes'); } else { setoptions('showwordcounts', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphdialects').change(function() {
    if(this.checked) { setoptions('morphdialects', 'yes'); } else { setoptions('morphdialects', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphduals').change(function() {
    if(this.checked) { setoptions('morphduals', 'yes'); } else { setoptions('morphduals', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphemptyrows').change(function() {
    if(this.checked) { setoptions('morphemptyrows', 'yes'); } else { setoptions('morphemptyrows', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphimper').change(function() {
    if(this.checked) { setoptions('morphimper', 'yes'); } else { setoptions('morphimper', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphinfin').change(function() {
    if(this.checked) { setoptions('morphinfin', 'yes'); } else { setoptions('morphinfin', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphfinite').change(function() {
    if(this.checked) { setoptions('morphfinite', 'yes'); } else { setoptions('morphfinite', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphpcpls').change(function() {
    if(this.checked) { setoptions('morphpcpls', 'yes'); } else { setoptions('morphpcpls', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphtables').change(function() {
    if(this.checked) { setoptions('morphtables', 'yes'); } else { setoptions('morphtables', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#collapseattic').change(function() {
    if(this.checked) { setoptions('collapseattic', 'yes'); } else { setoptions('collapseattic', 'no'); }
    refreshselections();
    loadoptions();
    });

//
// vector checkboxes in main page body
//

const thesearchforms = ['#wordsearchform', '#lemmatasearchform', '#proximatesearchform', '#proximatelemmatasearchform'];
const wsf = $('#wordsearchform');
const lsf = $('#lemmatasearchform');
const plsf = $('#proximatelemmatasearchform');
const psf = $('#proximatesearchform');
const trmonelem = $('#termoneisalemma');
const trmtwolem = $('#termtwoisalemma');
const vschon = $('#vectorizing-ison');
const vschoff  = $('#vectorizing-isoff');
const lschon = $('#lemmatizing-ison');
const lschoff= $('#lemmatizing-isoff');

function clearsearchboxvalues() {
    for (let i = 0; i < thesearchforms.length; i++) {
        let box = $(thesearchforms[i]);
        box.val('');
    }
}

function restoreplaceholders() {
    wsf.attr('placeholder', '(looking for...)');
    psf.attr('placeholder', '(near... and within...)');
    lsf.attr('placeholder', '(all forms of...)');
    plsf.attr('placeholder', '(near all forms of... and within...)');
    clearsearchboxvalues();
}

function hideallboxes() {
    for (let i = 0; i < thesearchforms.length; i++) {
        let box = $(thesearchforms[i]);
        box.hide();
    }
}

function findotheroptions(thisoption) {
    const xoredoptions = ['#cosdistbysentence', '#cosdistbylineorword', '#semanticvectorquery', '#nearestneighborsquery', '#tensorflowgraph', '#sentencesimilarity', '#topicmodel'];
    let xor = [];
    for (let i = 0; i < xoredoptions.length; i++) {
        let opt = $(xoredoptions[i]);
        if (opt.attr('id') !== thisoption) {
            xor.push(xoredoptions[i]);
        }
    }
    xor = xor.join(',');
    return xor;
}

function activatethisbox(toactivate, placeholder) {
    toactivate.show();
    toactivate.val('');
    toactivate.attr('placeholder', placeholder);
}

function displayvectorsandlemmata() {
    vschon.show();
    vschoff.hide();
    lschon.show();
    lschoff.hide();
}

function hidevectorsandlemmata() {
    vschon.hide();
    vschoff.show();
    lschon.hide();
    lschoff.show();
}

function hidevectornotification() {
    vschon.hide();
    vschoff.show();
}

function showvectornotification() {
    vschon.show();
    vschoff.hide();
}

function hidelemmatanotification() {
    lschon.hide();
    lschoff.show();
}

function showlemmatanotification() {
    lschon.show();
    lschoff.hide();
}

function restorecheckboxestodefault() {
    console.log('restorecheckboxestodefault');
    trmonelem.prop('checked', false);
    trmtwolem.prop('checked', false);
    hidelemmatanotification();
    restoreplaceholders();
    hidevectornotification();
    wsf.show();
    psf.show();
    lsf.hide();
    plsf.hide();
}

$('#cosdistbysentence').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        activatethisbox(lsf, '(pick a headword)');
        activatethisbox(plsf, '(unused for this type of query)');
        trmtwolem.prop('checked', false);
        wsf.hide();
        psf.hide();
        displayvectorsandlemmata();
        trmonelem.prop('checked', true);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#cosdistbylineorword').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        activatethisbox(lsf, '(pick a headword)');
        activatethisbox(plsf, '(unused for this type of query)');
        trmtwolem.prop('checked', false);
        wsf.hide();
        psf.hide();
        displayvectorsandlemmata();
        trmonelem.prop('checked', true);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#semanticvectorquery').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        wsf.show();
        wsf.attr('placeholder', '(enter a word or phrase)');
        $('#lemmatasearchform').hide();
        $('#proximatelemmatasearchform').attr('placeholder', '(unused for this type of query)');
        $('#proximatesearchform').attr('placeholder', '(unused for this type of query)');
        trmonelem.prop('checked', false);
        trmtwolem.prop('checked', false);
        hidelemmatanotification();
        showvectornotification();
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#nearestneighborsquery').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        $('#complexsearching').show();
        activatethisbox(lsf, '(pick a headword)');
        activatethisbox(plsf, '(unused for this type of query)');
        wsf.hide();
        psf.hide();
        displayvectorsandlemmata();
        trmonelem.prop('checked', true);
        trmtwolem.prop('checked', false);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#tensorflowgraph').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        $('#complexsearching').show();
        activatethisbox(lsf, '(unused for tensorflowgraph)');
        activatethisbox(plsf, '(unused for this type of query)');
        wsf.hide();
        psf.hide();
        hidelemmatanotification();
        showvectornotification();
        trmonelem.prop('checked', false);
        trmtwolem.prop('checked', false);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#sentencesimilarity').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        $('#complexsearching').show();
        activatethisbox(lsf, '(unused for sentencesimilarity)');
        activatethisbox(plsf, '(unused for this type of query)');
        trmonelem.prop('checked', false);
        trmtwolem.prop('checked', false);
        wsf.hide();
        psf.hide();
        hidelemmatanotification();
        showvectornotification();
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#topicmodel').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        $('#complexsearching').show();
        activatethisbox(lsf, '(unused for topic models)');
        activatethisbox(plsf, '(unused for this type of query)');
        trmonelem.prop('checked', false);
        trmtwolem.prop('checked', false);
        wsf.hide();
        psf.hide();
        vschon.show();
        vschoff.hide();
        hidelemmatanotification();
        showvectornotification();
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

trmonelem.change(function() {
    if(this.checked) {
        wsf.hide();
        wsf.val('');
        lsf.show();
        showlemmatanotification();
        } else {
        lsf.hide();
        lsf.val('');
        wsf.show();
        if(!trmtwolem.is(':checked')) {
            hidelemmatanotification();
            }
        }
    });

trmtwolem.change(function() {
    if(this.checked) {
        psf.hide();
        psf.val('');
        plsf.show();
        showlemmatanotification();
        } else {
        plsf.hide();
        plsf.val('');
        psf.show();
        if(!trmonelem.is(':checked')) {
            hidelemmatanotification();
            }
        }
    });

//
// non-vector spinners
//

$('#linesofcontextspinner').spinner({
    max: 20,
    min: 0,
    value: 2,
    step: 2,
    stop: function( event, ui ) {
        let result = $('#linesofcontextspinner').spinner('value');
        setoptions('linesofcontext', String(result));
        },
    spin: function( event, ui ) {
        let result = $('#linesofcontextspinner').spinner('value');
        setoptions('linesofcontext', String(result));
        }
        });

$('#browserspinner').spinner({
    max: 50,
    min: 5,
    value: 1,
    stop: function( event, ui ) {
        let result = $('#browserspinner').spinner('value');
        setoptions('browsercontext', String(result));
        },
    spin: function( event, ui ) {
        let result = $('#browserspinner').spinner('value');
        setoptions('browsercontext', String(result));
        }
        });

$( '#hitlimitspinner' ).spinner({
    min: 1,
    value: 1000,
    step: 50,
    stop: function( event, ui ) {
        let result = $('#hitlimitspinner').spinner('value');
        setoptions('maxresults', String(result));
        },
    spin: function( event, ui ) {
        let result = $('#hitlimitspinner').spinner('value');
        setoptions('maxresults', String(result));
        }
        });

$( '#latestdate' ).spinner({
    min: -850,
    max: 1500,
    value: 1500,
    step: 50,
    stop: function( event, ui ) {
        let result = $('#latestdate').spinner('value');
        setoptions('latestdate', String(result));
        refreshselections();
        },
    spin: function( event, ui ) {
        let result = $('#latestdate').spinner('value');
        setoptions('latestdate', String(result));
        refreshselections();
        }
        });


$( '#earliestdate' ).spinner({
    min: -850,
    max: 1500,
    value: -850,
    step: 50,
    stop: function( event, ui ) {
        let result = $('#earliestdate').spinner('value');
        setoptions('earliestdate', String(result));
        refreshselections();
        },
    spin: function( event, ui ) {
        let result = $('#earliestdate').spinner('value');
        setoptions('earliestdate', String(result));
        refreshselections();
        }
        });


// 'width' property not working when you define the spinners
const spinners = ["#earliestdate", "#latestdate", "#hitlimitspinner", "#linesofcontextspinner", "#browserspinner"];
for (let i = 0; i < spinners.length; i++) {
    const mywidth = 90;
    $(spinners[i]).width(mywidth);
}


//
// cookies + options
//

$('#togglesaveslots').click( function(){ $('#saveslots').toggle()});

$('#toggleloadslots').click( function(){ $('#loadslots').toggle()});

function javascriptsessionintocookie(cookienumberstr){
    $.getJSON('/getsessionvariables', function (data) {
		    Cookies.set('session'+cookienumberstr, data, { expires: 1000 });
		});
}

// had trouble getting cookieread + setviaurl in js: everything 'worked' according to the logs, but the session would nevertheless reset
// switched over to a hybrid js and python solution
// an async timing issue

$('#save01').click( function(){ javascriptsessionintocookie('01'); $('#setoptions').hide(); $('#saveslots').hide(); });
$('#save02').click( function(){ javascriptsessionintocookie('02'); $('#setoptions').hide(); $('#saveslots').hide(); });
$('#save03').click( function(){ javascriptsessionintocookie('03'); $('#setoptions').hide(); $('#saveslots').hide(); });
$('#save04').click( function(){ javascriptsessionintocookie('04'); $('#setoptions').hide(); $('#saveslots').hide(); });
$('#save05').click( function(){ javascriptsessionintocookie('05'); $('#setoptions').hide(); $('#saveslots').hide(); });

// timing issues: you will get the cookie properly, but the selections will not show up right unless you use the misleadingly named .always()
//  'the .always() method replaces the deprecated .complete() method.'
$('#load01').click( function(){ $.getJSON('/getcookie/01').always( function() { $.getJSON('/getselections', function(selectiondata) { reloadselections(selectiondata); }); location.reload(); }); });
$('#load02').click( function(){ $.getJSON('/getcookie/02').always( function() { $.getJSON('/getselections', function(selectiondata) { reloadselections(selectiondata); }); location.reload(); }); });
$('#load03').click( function(){ $.getJSON('/getcookie/03').always( function() { $.getJSON('/getselections', function(selectiondata) { reloadselections(selectiondata); }); location.reload(); }); });
$('#load04').click( function(){ $.getJSON('/getcookie/04').always( function() { $.getJSON('/getselections', function(selectiondata) { reloadselections(selectiondata); }); location.reload(); }); });
$('#load05').click( function(){ $.getJSON('/getcookie/05').always( function() { $.getJSON('/getselections', function(selectiondata) { reloadselections(selectiondata); }); location.reload(); }); });

///
/// selectmenu
///

$('#sortresults').selectmenu({ width: 120});

$(function() {
        $('#sortresults').selectmenu({
            change: function() {
                let result = $('#sortresults').val();
                setoptions('sortorder', String(result));
            }
        });
});


$('#fontchoice').selectmenu({ width: 120});
$(function() {
        $('#fontchoice').selectmenu({
            change: function() {
                let result = $('#fontchoice').val();
                setoptions('fontchoice', String(result));
                window.location.reload();
            }
        });
});

//
// info
//

$('#authinfo').click(function(){
        $('#authorholdings').toggle();
        let authorid = $('#authorsautocomplete').val().slice(-7, -1);
        $.getJSON('/getauthorinfo/' + authorid, function (selectiondata) {
                $('#authorholdings').html(selectiondata);
                 });
    });


$('#searchinfo').click(function(){
        let slc = $('#searchlistcontents');
        if ( slc.is(':visible') === true ) {
            slc.hide();
            slc.html('<p class="center"><span class="small>(this might take a second...)</span></p>');
        } else {
            slc.html('');
            slc.show();
            $.getJSON('/getsearchlistcontents', function (selectiondata) {
                slc.html(selectiondata);
                });
            }
    });


$('#genreinfo').click(function(){
        $('#genrelistcontents').toggle();
        $.getJSON('/getgenrelistcontents', function (selectiondata) {
                document.getElementById('genrelistcontents').innerHTML = selectiondata;
                });
    });

//
// ENDPOINT UI CLICKS
//

$('#endpointbutton-isclosed').click(function(){
    // go from invisible to visible
    let aep = $('#authorendpoint');
    let aac = $('#authorsautocomplete');
    // aep.show();
    aep.val(aac.val());
    // $('#workendpoint').show();
    $('#fromnotice').show();
    $('#endpointnotice').show();
    $('#endpointbutton-isopen').show();
    $('#endpointbutton-isclosed').hide();
    let levellist = ['00', '01', '02', '03', '04', '05'];
    let author = aac.val().slice(-7, -1);
    let work = $('#worksautocomplete').val().slice(-4, -1);
    let getpath = author + '/' + work;
    $.getJSON('/getstructure/' + getpath, function (selectiondata) {
        let lvls = selectiondata['totallevels'];
        for (var i = 0; i < lvls; i++) {
            $('#level'+levellist[i]+'endpoint').show();
            }
        });
    });

$('#endpointbutton-isopen').click(function(){
    // go from visible to invisible
    // $('#authorendpoint').hide();
    // $('#workendpoint').hide();
    $('#fromnotice').hide();
    $('#endpointnotice').hide();
    $('#endpointbutton-isclosed').show();
    $('#endpointbutton-isopen').hide();
    let lvls = ['05', '04', '03', '02', '01', '00'];
    for (var i = 0; i < lvls.length; i++) { $('#level'+lvls[i]+'endpoint').hide(); }
    });
