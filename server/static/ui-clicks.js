//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016
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
                loc += '1|';
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
        $('#resultsspinner').spinner('value', data.linesofcontext);
        $('#hitlimitspinner').spinner('value', data.maxresults);
        $('#browserspinner').spinner('value', data.browsercontext);
        $('#sortresults').val(data.sortorder);
        $('#sortresults').selectmenu('refresh');
        if (data.accentsmatter == 'N') {
            $('#accentsmatter_y').prop('checked', false);
            $('#accentsmatter_n').prop('checked', true);
            } else {
            $('#accentsmatter_y').prop('checked', true);
            $('#accentsmatter_n').prop('checked', false);
            }
        if (data.spuria == 'N') {
            $('#spuriaincluded').prop('checked', false);
            $('#spuriaexcluded').prop('checked', true);
            } else {
            $('#spuriaincluded').prop('checked', true);
            $('#spuriaexcluded').prop('checked', false);
            }
        if (data.greekcorpus == 'yes') {
            $('#greekcorpus').prop('checked', true);
            } else {
            $('#greekcorpus').prop('checked', false);
            }
        if (data.latincorpus == 'yes') {
            $('#latincorpus').prop('checked', true);
            } else {
            $('#latincorpus').prop('checked', false);
            }
        if (data.inscriptioncorpus == 'yes') {
            $('#inscriptioncorpus').prop('checked', true);
            } else {
            $('#inscriptioncorpus').prop('checked', false);
            }
        if (data.papyruscorpus == 'yes') {
            $('#papyruscorpus').prop('checked', true);
            } else {
            $('#papyruscorpus').prop('checked', false);
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
    $('#fewerchoices').hide();
    $('#genresautocomplete').hide();
    $('#workgenresautocomplete').hide();
    $('#locationsautocomplete').hide();
    $('#provenanceautocomplete').hide();
    $('#pickgenre').hide();
    $('#excludegenre').hide();
    $('#genreinfo').hide();
    $('#genrelistcontents').hide();
    $('#edts').hide();
    $('#ldts').hide();
    $('#spur').hide();
    });


$('#morechoices').click( function() {
    $('#fewerchoices').show();
    $('#morechoices').hide();
    $('#genresautocomplete').show();
    $('#workgenresautocomplete').show();
    $('#locationsautocomplete').show();
    $('#provenanceautocomplete').show();
    $('#pickgenre').show();
    $('#excludegenre').show();
    $('#genreinfo').show();
    $('#edts').show();
    $('#ldts').show();
    $('#spur').show();
    loadoptions();
    });


$('#moretools').click( function() { $('#lexica').toggle(); });


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
        searchterm = dictterm;
        url = '/dictsearch?term=';
        var dialogtitle = restoreme;
        var mydictfield = '#lexicon';
    } else if ( parseterm.length > 0 ) {
        searchterm = parseterm;
        url = '/observed?word=';
        var dialogtitle = searchterm;
        var mydictfield = '#parser';
        restoreme = searchterm;
    } else if ( reverseterm.length > 0 ) {
        searchterm = reverseterm;
        url = '/reverselookup?word=';
        var dialogtitle = searchterm;
        var mydictfield = '#reverselexicon';
        restoreme = searchterm;
    } else {
        searchterm = 'nihil';
        url = '/dictsearch?term=';
        var dialogtitle = searchterm;
    }

    $(mydictfield).val('[Working on it...]');
    $.getJSON(url + searchterm, function (definitionreturned) {
           $( '#dictdialog' ).dialog({
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
           $( '#dictdialog' ).dialog( 'open' );
           var dLen = definitionreturned.length;
           var linesreturned = [];
            for (i = 0; i < dLen; i++) {
                linesreturned.push(definitionreturned[i]['value']);
                }
            $( '#dictdialog' ).html(linesreturned);
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


// artificial / misleading defaults
$('#eitherlang').prop('checked', true);
$('#accentsmatter_y').prop('checked', true);
$('#searchforwords').prop('checked', true);
$('#similarto').prop('checked', true);

$('#accentsmatter_y').click( function(){ setoptions('accentsmatter', 'Y'); });
$('#accentsmatter_n').click( function(){ setoptions('accentsmatter', 'N'); });
$('#spuriaincluded').click( function(){
    setoptions('spuria', 'Y');
    $.getJSON({ url: '/makeselection', async: false, success: function (selectiondata) { reloadselections(selectiondata); }
        });
    $('#searchlistcontents').hide();
    });

$('#spuriaexcluded').click( function(){
    setoptions('spuria', 'N');
    $.getJSON({ url: '/makeselection', async: false, success: function (selectiondata) { reloadselections(selectiondata); }
        });
    $('#searchlistcontents').hide();
    });

$('#greekcorpus').change(function () {
    if(this.checked) {
        setoptions('greekcorpus', 'yes');
    } else {
        setoptions('greekcorpus', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/makeselection', function (selectiondata) { reloadselections(selectiondata); });
    // document.getElementById('authoroutputcontent').innerHTML = '<p class="label">Searching all Greek authors</p>';
    });

$('#latincorpus').change(function () {
    if(this.checked) {
        setoptions('latincorpus', 'yes');
    } else {
        setoptions('latincorpus', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/makeselection', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#inscriptioncorpus').change(function () {
    if(this.checked) {
        setoptions('inscriptioncorpus', 'yes');
    } else {
        setoptions('inscriptioncorpus', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/makeselection', function (selectiondata) { reloadselections(selectiondata); });
    });

$('#papyruscorpus').change(function () {
    if(this.checked) {
        setoptions('papyruscorpus', 'yes');
    } else {
        setoptions('papyruscorpus', 'no');
    }
    // because some items on your list just got purged?
    $.getJSON('/makeselection', function (selectiondata) { reloadselections(selectiondata); });
    });

//
// spinners
//

$( "#contextspinner" ).spinner({
    max: 9,
    min: 1,
    value: 1,
    spin: function( event, ui ) {
        var result = $('#contextspinner').spinner('value');
        setoptions('proximity', String(result));
        }
        });


$( "#resultsspinner" ).spinner({
    max: 20,
    min: 2,
    value: 2,
    step: 2,
    stop: function( event, ui ) {
        var result = $('#resultsspinner').spinner('value');
        setoptions('linesofcontext', String(result));
        },
    spin: function( event, ui ) {
        var result = $('#resultsspinner').spinner('value');
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
        $.getJSON('/makeselection', function (selectiondata) { reloadselections(selectiondata); });
        },
    spin: function( event, ui ) {
        var result = $('#latestdate').spinner('value');
        setoptions('latestdate', String(result));
        $.getJSON('/makeselection', function (selectiondata) { reloadselections(selectiondata); });
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
        $.getJSON('/makeselection', function (selectiondata) { reloadselections(selectiondata); });
        },
    spin: function( event, ui ) {
        var result = $('#earliestdate').spinner('value');
        setoptions('earliestdate', String(result));
        $.getJSON('/makeselection', function (selectiondata) { reloadselections(selectiondata); });
        }
        });

//
// cookies + options
//

function javascriptsessionintocookie(cookienumberstr){
    $.getJSON('/getsessionvariables', function (data) {
		    Cookies.set('session'+cookienumberstr, data, { expires: 1000 });
		});
}

// had trouble getting cookieread + setviaurl in js: everything 'worked' according to the logs, but the session would nevertheless reset
// switched over to a hybrid js and python solution
// an async timing issue

$('#save01').click( function(){ javascriptsessionintocookie('01'); $('#setoptions').hide()});
$('#save02').click( function(){ javascriptsessionintocookie('02'); $('#setoptions').hide()});
$('#save03').click( function(){ javascriptsessionintocookie('03'); $('#setoptions').hide()});
$('#save04').click( function(){ javascriptsessionintocookie('04'); $('#setoptions').hide()});
$('#save05').click( function(){ javascriptsessionintocookie('05'); $('#setoptions').hide()});

// timing issues: you will get the cookie properly, but the selections will not show up right unless you use the misleadingly named .always()
//  'the .always() method replaces the deprecated .complete() method.'
$('#load01').click( function(){ $.getJSON('/getcookie?cookie=01').always( function() { $.getJSON('/makeselection', function(selectiondata) { reloadselections(selectiondata); }); }); $('#setoptions').hide(); });
$('#load02').click( function(){ $.getJSON('/getcookie?cookie=02').always( function() { $.getJSON('/makeselection', function(selectiondata) { reloadselections(selectiondata); }); }); $('#setoptions').hide(); });
$('#load03').click( function(){ $.getJSON('/getcookie?cookie=03').always( function() { $.getJSON('/makeselection', function(selectiondata) { reloadselections(selectiondata); }); }); $('#setoptions').hide(); });
$('#load04').click( function(){ $.getJSON('/getcookie?cookie=04').always( function() { $.getJSON('/makeselection', function(selectiondata) { reloadselections(selectiondata); }); }); $('#setoptions').hide(); });
$('#load05').click( function(){ $.getJSON('/getcookie?cookie=05').always( function() { $.getJSON('/makeselection', function(selectiondata) { reloadselections(selectiondata); }); }); $('#setoptions').hide(); });


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
        $.getJSON('/getauthorinfo?au=' + authorid, function (selectiondata) {
                document.getElementById('authorholdings').innerHTML = selectiondata;
                             });
    });


$('#searchinfo').click( function() {
        if (  $('#searchlistcontents').is(':visible') == true ) {
            $('#searchlistcontents').hide();
            document.getElementById('searchlistcontents').innerHTML = '<p class="center"><span class="small>(this might take a second...)</span></p>';
        } else {
            $('#searchlistcontents').show();
            $.getJSON('/getsearchlistcontents', function (selectiondata) {
                document.getElementById('searchlistcontents').innerHTML = selectiondata;
                 });
            }
    });


$('#genreinfo').click( function() {
        $('#genrelistcontents').toggle();
        $.getJSON('/getgenrelistcontents', function (selectiondata) {
                document.getElementById('genrelistcontents').innerHTML = selectiondata;
                             });
    });

