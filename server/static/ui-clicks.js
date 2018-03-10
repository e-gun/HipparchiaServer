//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-18
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)


function setoptions(sessionvar, value){
	$.getJSON( {url: '/setsessionvariable?' + sessionvar + '=' + value,
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
        var simpletoggles = {
            'spuria': $('#includespuria'),
            'varia': $('#includevaria'),
            'incerta': $('#includeincerta'),
            'sensesummary': $('#sensesummary'),
            'bracketsquare': $('#bracketsquare'),
            'bracketround': $('#bracketround'),
            'bracketangled': $('#bracketangled'),
            'bracketcurly': $('#bracketcurly'),
            'authorssummary': $('#authorssummary'),
            'quotesummary': $('#quotesummary'),
            'greekcorpus': $('#greekcorpus'),
            'latincorpus': $('#latincorpus'),
            'inscriptioncorpus': $('#inscriptioncorpus'),
            'papyruscorpus': $('#papyruscorpus'),
            'christiancorpus': $('#christiancorpus'),
            'cosdistbysentence': $('#cosdistbysentence'),
            'cosdistbylineorword': $('#cosdistbylineorword'),
            'semanticvectorquery': $('#semanticvectorquery'),
            'nearestneighborsquery': $('#nearestneighborsquery'),
            'tensorflowgraph': $('#tensorflowgraph'),
            'sentencesimilarity': $('#sentencesimilarity')
        };

        Object.keys(simpletoggles).forEach(function(key) {
            if (data[key] === 'yes') {
                simpletoggles[key].prop('checked', true);
            } else {
                simpletoggles[key].prop('checked', false);
            }
        });

        var sidebaricontoggles = {
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

        var xoredtoggles = {
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

        var setspinnervalues = {
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
   
        if (data.cosdistbysentence === 'yes') {
            $('#complexsearching').show();
            $('#proximatesearchform').val('');
            }
        if (data.cosdistbylineorword === 'yes') {
            $('#complexsearching').show();
            $('#proximatesearchform').val('');
            }
        });
}


function browsetopassage() {
    var auth = $('#authorsautocomplete').val().slice(-7, -1);
    var wrk = $('#worksautocomplete').val().slice(-4, -1);
    var l5 = $('#level05').val();
    var l4 = $('#level04').val();
    var l3 = $('#level03').val();
    var l2 = $('#level02').val();
    var l1 = $('#level01').val();
    var l0 = $('#level00').val();
    var lvls = [ l5,l4,l3,l2,l1,l0];
    var loc = '';
    for (var i = 5; i > -1; i-- ) {
        if (lvls[i] !== '') {
            loc += lvls[i]+'|';
        } else {
            if (i === 5) {
                loc += '-1|';
                }
            }
        }

    if (wrk.length !== 3) { wrk = '999'}
    loc = auth+'w'+wrk+'_AT_'+loc.slice(0, (loc.length)-1);
    browseuponclick(loc);
}


$('#openoptions').click(function(){
    loadoptions();
    $('#setoptions').toggle();
});


$('#addtolist').click(function(){ addtosearchlist(); });

$('#browseto').click(function(){ browsetopassage(); });

$('#fewerchoices').click(function(){
    $('#morechoices').show();
    var ids = Array('#fewerchoices', '#genresautocomplete', '#workgenresautocomplete', '#locationsautocomplete',
        '#provenanceautocomplete', '#pickgenre', '#excludegenre', '#genreinfo', '#genrelistcontents', '#edts',
        '#ldts', '#spur');
    bulkhider(ids);
    });


$('#morechoices').click(function(){
    $('#morechoices').hide();
    var ids = Array('#fewerchoices', '#genresautocomplete', '#workgenresautocomplete', '#locationsautocomplete',
        '#provenanceautocomplete', '#pickgenre', '#excludegenre', '#genreinfo', '#edts', '#ldts', '#spur');
    bulkshow(ids);
    loadoptions();
    });


$('#moretools').click(function(){ $('#lexica').toggle(); });

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
    var dictterm = $('#lexicon').val();
    var restoreme = dictterm;
    // trailing space will be lost unless you do this: ' gladiator ' --> ' gladiator' and so you can't spearch for only that word...
    if (dictterm.slice(-1) === ' ') { dictterm = dictterm.slice(0,-1) + '%20'; }
    var parseterm = $('#parser').val();
    var reverseterm = $('#reverselexicon').val();
    var windowWidth = $(window).width();
    var windowHeight = $(window).height();
    var searchterm = '';
    var url = '';
    var dialogtitle = '';
    var mydictfield = '';
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
        var originalterm = reverseterm;
        // disgustingly, if you send 'STRING ' to window.location it strips the whitespace and turns it into 'STRING'
        if (reverseterm.slice(-1) === ' ') { reverseterm = reverseterm.slice(0,-1) + '%20'; }
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
            var ldt = $('#lexicadialogtext');
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
           var dLen = definitionreturned.length;
           var linesreturned = [];
            for (var i = 0; i < dLen; i++) {
                linesreturned.push(definitionreturned[i]['value']);
                }
            ldt.html(linesreturned);
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

//
// vector checkboxes
//

const thesearchforms = ['#wordsearchform', '#lemmatasearchform', '#proximatesearchform', '#proximatelemmatasearchform']

function restoreplaceholders() {
    var wsf = $('#wordsearchform');
    var lsf = $('#lemmatasearchform');
    var psf = $('#proximatesearchform');
    var plsf = $('#proximatelemmatasearchform');
    wsf.attr('placeholder', '(looking for...)');
    psf.attr('placeholder', '(near... and within...)');
    lsf.attr('placeholder', '(all forms of...)');
    plsf.attr('placeholder', '(near all forms of... and within...)');
}

function clearsearchboxvalues() {
    for (var i = 0; i < thesearchforms.length; i++) {
        var b = $(thesearchforms[i]);
        b.val('');
    }
}

function hideallboxes() {
    for (var i = 0; i < thesearchforms.length; i++) {
        var b = $(thesearchforms[i]);
        b.hide();
    }
}

function findotheroptions(thisoption) {
    const xoredoptions = ['#cosdistbysentence', '#cosdistbylineorword', '#semanticvectorquery', '#nearestneighborsquery', '#tensorflowgraph', '#sentencesimilarity'];
    var xor = [];
    for (var i = 0; i < xoredoptions.length; i++) {
        var o = $(xoredoptions[i]);
        if (o.attr('id') !== thisoption) {
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


$('#cosdistbysentence').change(function() {
    restoreplaceholders();
    if(this.checked) {
        clearsearchboxvalues();
        var others = findotheroptions(this.id);
        $(others).prop('checked', false);
        var wsf = $('#wordsearchform');
        var lsf = $('#lemmatasearchform');
        var plsf = $('#proximatelemmatasearchform');
        var psf = $('#proximatesearchform');
        activatethisbox(lsf, '(pick a lemma)');
        activatethisbox(plsf, '(unused for this type of query)');
        wsf.hide();
        psf.hide();
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        }
    });

$('#cosdistbylineorword').change(function() {
    restoreplaceholders();
    if(this.checked) {
        clearsearchboxvalues();
        var others = findotheroptions(this.id);
        $(others).prop('checked', false);
        var wsf = $('#wordsearchform');
        var lsf = $('#lemmatasearchform');
        var plsf = $('#proximatelemmatasearchform');
        var psf = $('#proximatesearchform');
        activatethisbox(lsf, '(pick a lemma)');
        activatethisbox(plsf, '(unused for this type of query)');
        wsf.hide();
        psf.hide();
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        }
    });

$('#semanticvectorquery').change(function() {
    restoreplaceholders();
    if(this.checked) {
        clearsearchboxvalues();
        var others = findotheroptions(this.id);
        $(others).prop('checked', false);
        var wsf = $('#wordsearchform');
        wsf.show();
        wsf.attr('placeholder', '(enter a word or phrase)');
        $('#lemmatasearchform').hide();
        $('#proximatelemmatasearchform').attr('placeholder', '(unused for this type of query)');
        $('#proximatesearchform').attr('placeholder', '(unused for this type of query)');
        $('#termoneisalemma').prop('checked', false);
        $('#termtwoisalemma').prop('checked', false);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        }
    });

$('#nearestneighborsquery').change(function() {
    restoreplaceholders();
    if(this.checked) {
        clearsearchboxvalues();
        var others = findotheroptions(this.id);
        $(others).prop('checked', false);
        $('#complexsearching').show();
        var wsf = $('#wordsearchform');
        var lsf = $('#lemmatasearchform');
        var plsf = $('#proximatelemmatasearchform');
        var psf = $('#proximatesearchform');
        activatethisbox(lsf, '(pick a lemma)');
        activatethisbox(plsf, '(unused for this type of query)');
        wsf.hide();
        psf.hide();
        $('#termoneisalemma').prop('checked', true);
        $('#termtwoisalemma').prop('checked', true);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        }
    });

$('#tensorflowgraph').change(function() {
    restoreplaceholders();
    if(this.checked) {
        clearsearchboxvalues();
        var others = findotheroptions(this.id);
        $(others).prop('checked', false);
        $('#complexsearching').show();
        var wsf = $('#wordsearchform');
        var lsf = $('#lemmatasearchform');
        var psf = $('#proximatesearchform');
        var plsf = $('#proximatelemmatasearchform');
        activatethisbox(lsf, '(unused for tensorflowgraph)');
        activatethisbox(plsf, '(unused for this type of query)');
        wsf.hide();
        psf.hide();
        $('#termoneisalemma').prop('checked', true);
        $('#termtwoisalemma').prop('checked', true);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        }
    });

$('#sentencesimilarity').change(function() {
    restoreplaceholders();
    if(this.checked) {
        clearsearchboxvalues();
        var others = findotheroptions(this.id);
        $(others).prop('checked', false);
        $('#complexsearching').show();
        var wsf = $('#wordsearchform');
        var lsf = $('#lemmatasearchform');
        var psf = $('#proximatesearchform');
        var plsf = $('#proximatelemmatasearchform');
        activatethisbox(lsf, '(unused for sentencesimilarity)');
        activatethisbox(plsf, '(unused for this type of query)');
        wsf.hide();
        psf.hide();
        $('#termoneisalemma').prop('checked', true);
        $('#termtwoisalemma').prop('checked', true);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        }
    });


$('#termoneisalemma').change(function() {
    var wsf = $('#wordsearchform');
    var lsf = $('#lemmatasearchform');
    if(this.checked) {
        wsf.hide();
        wsf.val('');
        lsf.show();
        } else {
        lsf.hide();
        lsf.val('');
        wsf.show();
        }
    });

$('#termtwoisalemma').change(function() {
    var psf = $('#proximatesearchform');
    var plsf = $('#proximatelemmatasearchform');
    if(this.checked) {
        psf.hide();
        psf.val('');
        plsf.show();
        } else {
        plsf.hide();
        plsf.val('');
        psf.show();
        }
    });

//
// spinners
//

$('#linesofcontextspinner').spinner({
    max: 20,
    min: 0,
    value: 2,
    step: 2,
    stop: function( event, ui ) {
        var result = $('#linesofcontextspinner').spinner('value');
        setoptions('linesofcontext', String(result));
        },
    spin: function( event, ui ) {
        var result = $('#linesofcontextspinner').spinner('value');
        setoptions('linesofcontext', String(result));
        }
        });


$('#browserspinner').spinner({
    max: 50,
    min: 5,
    value: 1,
    stop: function( event, ui ) {
        var result = $('#browserspinner').spinner('value');
        setoptions('browsercontext', String(result));
        },
    spin: function( event, ui ) {
        var result = $('#browserspinner').spinner('value');
        setoptions('browsercontext', String(result));
        }
        });


$( "#hitlimitspinner" ).spinner({
    min: 1,
    value: 1000,
    step: 50,
    stop: function( event, ui ) {
        var result = $('#hitlimitspinner').spinner('value');
        setoptions('maxresults', String(result));
        },
    spin: function( event, ui ) {
        var result = $('#hitlimitspinner').spinner('value');
        setoptions('maxresults', String(result));
        }
        });


$( "#latestdate" ).spinner({
    min: -850,
    max: 1500,
    value: 1500,
    step: 50,
    stop: function( event, ui ) {
        var result = $('#latestdate').spinner('value');
        setoptions('latestdate', String(result));
        refreshselections();
        },
    spin: function( event, ui ) {
        var result = $('#latestdate').spinner('value');
        setoptions('latestdate', String(result));
        refreshselections();
        }
        });


$( "#earliestdate" ).spinner({
    min: -850,
    max: 1500,
    value: -850,
    step: 50,
    stop: function( event, ui ) {
        var result = $('#earliestdate').spinner('value');
        setoptions('earliestdate', String(result));
        refreshselections();
        },
    spin: function( event, ui ) {
        var result = $('#earliestdate').spinner('value');
        setoptions('earliestdate', String(result));
        refreshselections();
        }
        });

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

$('#sortresults').selectmenu();
$(function() {
        $('#sortresults').selectmenu({
            change: function() {
                var result = $('#sortresults').val();
                setoptions('sortorder', String(result));
            }
        });
});


//
// info
//

$('#authinfo').click(function(){
        $('#authorholdings').toggle();
        var authorid = $('#authorsautocomplete').val().slice(-7, -1);
        $.getJSON('/getauthorinfo/' + authorid, function (selectiondata) {
                $('#authorholdings').html(selectiondata);
                 });
    });


$('#searchinfo').click(function(){
        var slc = $('#searchlistcontents');
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
