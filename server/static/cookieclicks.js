//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-21
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)

//
// cookies + options
//

$('#togglesaveslots').click( function(){ $('#saveslots').toggle()});

$('#toggleloadslots').click( function(){ $('#loadslots').toggle()});

function javascriptsessionintocookie(cookienumberstr){
    $.getJSON('/getsessionvariables', function (data) {
    		Cookies.set('session'+cookienumberstr, data, { sameSite: 'strict' });
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
