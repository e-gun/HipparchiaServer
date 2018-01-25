//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-17
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)


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
    for (i = 5; i > -1; i-- ) {
        if (lvls[i] != '') {
            loc += lvls[i]+'|';
        } else {
            if (i == 5) {
                loc += '-1|';
                }
            }
        }

    if (wrk.length != 3) { wrk == '999'}
    loc = auth+'w'+wrk+'_AT_'+loc.slice(0,(loc.length)-1);
    browseuponclick(loc);
}


function loadoptions() {
    $.getJSON('/getsessionvariables', function (data) {
        $('#earliestdate').spinner( 'value', data.earliestdate);
        $('#latestdate').spinner('value', data.latestdate);
        $('#linesofcontextspinner').spinner('value', data.linesofcontext);
        $('#hitlimitspinner').spinner('value', data.maxresults);
        $('#browserspinner').spinner('value', data.browsercontext);
        $('#sortresults').val(data.sortorder);
        $('#sortresults').selectmenu('refresh');
        if (data.onehit == 'no') {
            $('#onehit_y').prop('checked', false);
            $('#onehit_n').prop('checked', true);
            $('#onehitisfalse').show();
            $('#onehitistrue').hide();
            } else {
            $('#onehit_y').prop('checked', true);
            $('#onehit_n').prop('checked', false);
            $('#onehitistrue').show();
            $('#onehitisfalse').hide();
            }
        if (data.headwordindexing == 'no') {
            $('#headwordindexing_y').prop('checked', false);
            $('#headwordindexing_n').prop('checked', true);
            $('#headwordindexinginactive').show();
            $('#headwordindexingactive').hide();
            } else {
            $('#headwordindexing_y').prop('checked', true);
            $('#headwordindexing_n').prop('checked', false);
            $('#headwordindexingactive').show();
            $('#headwordindexinginactive').hide();
            }
        if (data.indexbyfrequency == 'no') {
            $('#frequencyindexing_y').prop('checked', false);
            $('#frequencyindexing_n').prop('checked', true);
            $('#frequencyindexinginactive').show();
            $('#frequencyindexingactive').hide();
            } else {
            $('#frequencyindexing_y').prop('checked', true);
            $('#frequencyindexing_n').prop('checked', false);
            $('#frequencyindexingactive').show();
            $('#frequencyindexinginactive').hide();
            }
        if (data.spuria == 'no') {
            $('#includespuria').prop('checked', false);
            } else {
            $('#includespuria').prop('checked', true);
            }
        if (data.varia == 'no') {
            $('#includevaria').prop('checked', false);
            } else {
            $('#includevaria').prop('checked', true);
            }
        if (data.incerta == 'no') {
            $('#includeincerta').prop('checked', false);
            } else {
            $('#includeincerta').prop('checked', true);
            }
        if (data.sensesummary == 'no') {
            $('#sensesummary').prop('checked', false);
            } else {
            $('#sensesummary').prop('checked', true);
            }
        if (data.bracketsquare == 'no') {
            $('#bracketsquare').prop('checked', false);
            } else {
            $('#bracketsquare').prop('checked', true);
            }
        if (data.bracketround == 'no') {
            $('#bracketround').prop('checked', false);
            } else {
            $('#bracketround').prop('checked', true);
            }
        if (data.bracketangled == 'no') {
            $('#bracketangled').prop('checked', false);
            } else {
            $('#bracketangled').prop('checked', true);
            }
        if (data.bracketcurly == 'no') {
            $('#bracketcurly').prop('checked', false);
            } else {
            $('#bracketcurly').prop('checked', true);
            }
        if (data.authorssummary == 'no') {
            $('#authorssummary').prop('checked', false);
            } else {
            $('#authorssummary').prop('checked', true);
            }
        if (data.quotesummary == 'no') {
            $('#quotesummary').prop('checked', false);
            } else {
            $('#quotesummary').prop('checked', true);
            }
        if (data.greekcorpus == 'yes') {
            $('#greekcorpus').prop('checked', true);
            $('#grkisactive').show();
            } else {
            $('#greekcorpus').prop('checked', false);
            $('#grkisactive').hide();
            }
        if (data.latincorpus == 'yes') {
            $('#latincorpus').prop('checked', true);
            $('#latisactive').show();
            } else {
            $('#latincorpus').prop('checked', false);
            $('#latisactive').hide();
            }
        if (data.inscriptioncorpus == 'yes') {
            $('#inscriptioncorpus').prop('checked', true);
            $('#insisactive').show();
            } else {
            $('#inscriptioncorpus').prop('checked', false);
            $('#insisactive').hide();
            }
        if (data.papyruscorpus == 'yes') {
            $('#papyruscorpus').prop('checked', true);
            $('#ddpisactive').show();
            } else {
            $('#papyruscorpus').prop('checked', false);
            $('#ddpisactive').hide();
            }
        if (data.christiancorpus == 'yes') {
            $('#christiancorpus').prop('checked', true);
            $('#chrisactive').show();
            } else {
            $('#christiancorpus').prop('checked', false);
            $('#chrisactive').hide();
            }
        if (data.cosinedistancesearch == 'yes') {
            $('#cosinedistancesearch').prop('checked', true);
            } else {
            $('#cosinedistancesearch').prop('checked', false);
            }
        });
}


$('#openoptions').click( function() {
    loadoptions();
    $('#setoptions').toggle();
});


$('#addtolist').click( function() { addtosearchlist(); });

$('#browseto').click( function() { browsetopassage(); });

$('#fewerchoices').click( function() {
    $('#morechoices').show();
    var ids = new Array('#fewerchoices', '#genresautocomplete', '#workgenresautocomplete', '#locationsautocomplete',
        '#provenanceautocomplete', '#pickgenre', '#excludegenre', '#genreinfo', '#genrelistcontents', '#edts',
        '#ldts', '#spur');
    bulkhider(ids);
    });


$('#morechoices').click( function() {
    $('#morechoices').hide();
    var ids = new Array('#fewerchoices', '#genresautocomplete', '#workgenresautocomplete', '#locationsautocomplete',
        '#provenanceautocomplete', '#pickgenre', '#excludegenre', '#genreinfo', '#edts', '#ldts', '#spur');
    bulkshow(ids);
    loadoptions();
    });


$('#moretools').click( function() { $('#lexica').toggle(); });

// not working as expected
// supposed to clear out the other boxes and restore the placeholder; only clears the boxes

//$('#parser').on('focus', function () {
//    var $rl = $('#reverselexicon');
//    var $lx = $('#lexicon');
//    $rl.val(''); $rl.removeAttr("value"); $rl.attr('placeholder', '(English to Greek or Latin)');
//    $lx.val(''); $lx.removeAttr("value"); $lx.attr('placeholder', '(Dictionary Search)');
//    });
//
//$('#reverselexicon').on('focus', function () {
//    var $pp = $('#parser');
//    var $lx = $('#lexicon');
//    $pp.val(''); $pp.removeAttr("value"); $pp.attr('placeholder', '(Morphology Search)');
//    $lx.val(''); $lx.removeAttr("value"); $lx.attr('placeholder', '(Dictionary Search)');
//    });
//
//$('#lexicon').on('focus', function () {
//    var $rl = $('#reverselexicon');
//    var $lx = $('#lexicon');
//    $rl.val(''); $rl.removeAttr("value"); $rl.attr('placeholder', '(English to Greek or Latin)');
//    $lx.val(''); $lx.removeAttr("value"); $lx.attr('placeholder', '(Dictionary Search)');
//    });


$('#lexicalsearch').click( function() {
    var dictterm = $('#lexicon').val();
    var restoreme = dictterm;
    // trailing space will be lost unless you do this: ' gladiator ' --> ' gladiator' and so you can't spearch for only that word...
    if (dictterm.slice(-1) == ' ') { dictterm = dictterm.slice(0,-1) + '%20'; }
    var parseterm = $('#parser').val();
    var reverseterm = $('#reverselexicon').val();
    var windowWidth = $(window).width();
    var windowHeight = $(window).height();
    if ( dictterm.length > 0) {
        var searchterm = dictterm;
        var url = '/dictsearch/';
        var dialogtitle = restoreme;
        var mydictfield = '#lexicon';
    } else if ( parseterm.length > 0 ) {
        var searchterm = parseterm;
        var url = '/parse/';
        var dialogtitle = searchterm;
        var mydictfield = '#parser';
        restoreme = searchterm;
    } else if ( reverseterm.length > 0 ) {
        var originalterm = reverseterm
        // disgustingly, if you send 'STRING ' to window.location it strips the whitespace and turns it into 'STRING'
        if (reverseterm.slice(-1) == ' ') { reverseterm = reverseterm.slice(0,-1) + '%20'; }
        var searchterm = reverseterm;
        var url = '/reverselookup/';
        var dialogtitle = originalterm;
        var mydictfield = '#reverselexicon';
        restoreme = searchterm;
    } else {
        searchterm = 'nihil';
        url = '/dictsearch/';
        var dialogtitle = searchterm;
    }

    $(mydictfield).val('[Working on it...]');
    $.getJSON(url + searchterm, function (definitionreturned) {
           $( '#lexicadialogtext' ).dialog({
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
           $( '#lexicadialogtext' ).dialog( 'open' );
           var dLen = definitionreturned.length;
           var linesreturned = [];
            for (i = 0; i < dLen; i++) {
                linesreturned.push(definitionreturned[i]['value']);
                }
            $( '#lexicadialogtext' ).html(linesreturned);
            $(mydictfield).val(restoreme);
        });

    });


//
// the radio options
//


function setoptions(sessionvar,value){
	$.getJSON( {url: '/setsessionvariable?'+sessionvar+'='+value,
	    async: false,
	    success: function (resultdata) {
		 // do nothing special: the return exists but is not relevant
	    }
	    });
}

$('#headwordindexing_y').click( function(){ setoptions('headwordindexing', 'yes'); $('#headwordindexingactive').show(); $('#headwordindexinginactive').hide(); });
$('#headwordindexing_n').click( function(){ setoptions('headwordindexing', 'no'); $('#headwordindexinginactive').show(); $('#headwordindexingactive').hide(); });

$('#frequencyindexing_y').click( function(){ setoptions('indexbyfrequency', 'yes'); $('#frequencyindexingactive').show(); $('#frequencyindexinginactive').hide(); });
$('#frequencyindexing_n').click( function(){ setoptions('indexbyfrequency', 'no'); $('#frequencyindexinginactive').show(); $('#frequencyindexingactive').hide(); });


$('#onehit_y').click( function(){ setoptions('onehit', 'yes'); $('#onehitistrue').show(); $('#onehitisfalse').hide(); });
$('#onehit_n').click( function(){ setoptions('onehit', 'no'); $('#onehitisfalse').show(); $('#onehitistrue').hide(); });

$('#includespuria').change(function () {
    if(this.checked) {
        setoptions('spuria', 'yes');
        $('#spuriaistrue').show();
        $('#spuriaisfalse').hide();
    } else {
        setoptions('spuria', 'no');
        $('#spuriaistrue').hide();
        $('#spuriaisfalse').show();
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#includevaria').change(function () {
    if(this.checked) {
        setoptions('varia', 'yes');
        $('#variaistrue').show();
        $('#variaisfalse').hide();
    } else {
        setoptions('varia', 'no');
        $('#variaistrue').hide();
        $('#variaisfalse').show();
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#includeincerta').change(function () {
    if(this.checked) {
        setoptions('incerta', 'yes');
        $('#undatedistrue').show();
        $('#undatedisfalse').hide();
    } else {
        setoptions('incerta', 'no');
        $('#undatedistrue').hide();
        $('#undatedisfalse').show();
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#greekcorpus').change(function () {
    if(this.checked) {
        setoptions('greekcorpus', 'yes');
        $('#grkisactive').show();
    } else {
        setoptions('greekcorpus', 'no');
        $('#grkisactive').hide();
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#latincorpus').change(function () {
    if(this.checked) {
        setoptions('latincorpus', 'yes');
        $('#latisactive').show();
    } else {
        setoptions('latincorpus', 'no');
        $('#latisactive').hide();
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#inscriptioncorpus').change(function () {
    if(this.checked) {
        setoptions('inscriptioncorpus', 'yes');
        $('#insisactive').show();
    } else {
        setoptions('inscriptioncorpus', 'no');
        $('#insisactive').hide();
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#papyruscorpus').change(function () {
    if(this.checked) {
        setoptions('papyruscorpus', 'yes');
        $('#ddpisactive').show();
    } else {
        setoptions('papyruscorpus', 'no');
        $('#ddpisactive').hide();
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#christiancorpus').change(function () {
    if(this.checked) {
        setoptions('christiancorpus', 'yes');
        $('#chrisactive').show();
    } else {
        setoptions('christiancorpus', 'no');
        $('#chrisactive').hide();
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#sensesummary').change(function () {
    if(this.checked) {
        setoptions('sensesummary', 'yes'); } else { setoptions('sensesummary', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#authorssummary').change(function () {
    if(this.checked) {
        setoptions('authorssummary', 'yes'); } else { setoptions('authorssummary', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#quotesummary').change(function () {
    if(this.checked) {
        setoptions('quotesummary', 'yes'); } else { setoptions('quotesummary', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#bracketsquare').change(function () {
    if(this.checked) {
        setoptions('bracketsquare', 'yes'); } else { setoptions('bracketsquare', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#bracketround').change(function () {
    if(this.checked) {
        setoptions('bracketround', 'yes'); } else { setoptions('bracketround', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#bracketangled').change(function () {
    if(this.checked) {
        setoptions('bracketangled', 'yes'); } else { setoptions('bracketangled', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#bracketcurly').change(function () {
    if(this.checked) {
        setoptions('bracketcurly', 'yes'); } else { setoptions('bracketcurly', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#cosinedistancesearch').change(function () {
    if(this.checked) {
        setoptions('cosinedistancesearch', 'yes'); } else { setoptions('cosinedistancesearch', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#termoneisalemma').change(function () {
    if(this.checked) {
        $('#wordsearchform').hide();
        $('#wordsearchform').val('');
        $('#lemmatasearchform').show();
        $('#cosinedistancecheckbox').show()
        $('#cosinedistancesearch').attr('checked', false);
        } else {
        $('#lemmatasearchform').hide();
        $('#lemmatasearchform').val('');
        $('#wordsearchform').show();
        $('#cosinedistancecheckbox').hide()
        $('#cosinedistancesearch').attr('checked', false);
        }
    });

$('#termtwoisalemma').change(function () {
    if(this.checked) {
        $('#proximatesearchform').hide();
        $('#proximatesearchform').val('');
        $('#proximatelemmatasearchform').show();
        } else {
        $('#proximatelemmatasearchform').hide();
        $('#proximatelemmatasearchform').val('');
        $('#proximatesearchform').show();
        }
    });

//
// spinners
//

$( "#linesofcontextspinner" ).spinner({
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


$( "#browserspinner" ).spinner({
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
        $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
        },
    spin: function( event, ui ) {
        var result = $('#latestdate').spinner('value');
        setoptions('latestdate', String(result));
        $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
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
        $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
        },
    spin: function( event, ui ) {
        var result = $('#earliestdate').spinner('value');
        setoptions('earliestdate', String(result));
        $.getJSON('/getselections', function (selectiondata) { reloadselections(selectiondata); });
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

$( '#sortresults' ).selectmenu()
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

$('#authinfo').click( function() {
        $('#authorholdings').toggle();
        var authorid = $('#authorsautocomplete').val().slice(-7, -1);
        $.getJSON('/getauthorinfo/' + authorid, function (selectiondata) {
                $('#authorholdings').html(selectiondata);
                 });
    });


$('#searchinfo').click( function() {
        if (  $('#searchlistcontents').is(':visible') == true ) {
            $('#searchlistcontents').hide();
            $('#searchlistcontents').html('<p class="center"><span class="small>(this might take a second...)</span></p>');
        } else {
            $('#searchlistcontents').html('');
            $('#searchlistcontents').show();
            $.getJSON('/getsearchlistcontents', function (selectiondata) {
                $('#searchlistcontents').html(selectiondata);
                });
            }
    });


$('#genreinfo').click( function() {
        $('#genrelistcontents').toggle();
        $.getJSON('/getgenrelistcontents', function (selectiondata) {
                document.getElementById('genrelistcontents').innerHTML = selectiondata;
                             });
    });
