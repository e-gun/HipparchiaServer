//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016
//	License: GPL 3 (see LICENSE in the top level directory of the distribution)

function browseuponclick(url){
	$.getJSON(
	    { url: '/browseto?locus='+url,
	    success: function (passagereturned) {
            $('#browseforward').unbind('click');
            $('#browseback').unbind('click');

            var fb = parsepassagereturned(passagereturned);
            // left and right arrow keys

            $('#browseforward').bind('click', function(){
                browseuponclick(fb[0]);
                });
            $('#browseback').bind('click', function(){
                browseuponclick(fb[1]);
                });
            }
        }
        );
    }


var openbrowserfromclick = function() {
    // now do the browsing
    $.getJSON('/browseto?locus='+this.id, function (passagereturned) {
        $('#browseforward').unbind('click');
        $('#browseback').unbind('click');
		var fb = parsepassagereturned(passagereturned)
            // left and right arrow keys
           $('#browserdialogtext').keydown(function(e) {
                switch(e.which) {
                    case 37: browseuponclick(fb[1]); break;
                    case 39: browseuponclick(fb[0]); break;
                    }
                });

        $('#browseforward').bind('click', function(){
        	browseuponclick(fb[0]);
        	});
        $('#browseback').bind('click', function(){
        	browseuponclick(fb[1]);
        	});
        });
}


function parsepassagereturned(passagereturned) {
		$('#browserdialogtext').text('');
        // the first item is info
        // {'forwardsandback': ['/browseto?locus=lt1254w001_AT_2|2|3|6', '/browseto?locus=lt1254w001_AT_6|9|2|6']}
        var fwdurl = passagereturned[0]['forwardsandback'][0]
        var bkdurl = passagereturned[0]['forwardsandback'][1]
        // the remaining lines are the lines of the passage
        var dLen = passagereturned.length;
        var linesreturned = []
        for (i = 0; i < dLen; i++) {
            linesreturned.push(passagereturned[i]['value']);
        }

        $('#browserdialogtext').html(linesreturned);
        $('#browserdialog').show();
        $('observed').click( function(e) {
            e.preventDefault();
            $.getJSON('/observed?word='+this.id, function (definitionreturned) {
                $( '#lexicon').val(definitionreturned[0]['trylookingunder']);
                var windowWidth = $(window).width();
                var windowHeight = $(window).height();
                $( '#parserdialog' ).dialog({
                    autoOpen: false,
                    minWidth: windowWidth*.33,
                    maxHeight: windowHeight*.9,
                    // position: { my: "left top", at: "left top", of: window },
                    title: definitionreturned[0]['observed'],
                    draggable: true,
                    icons: { primary: 'ui-icon-close' },
                    click: function() { $( this ).dialog( 'close' ); }
                    });
                $( '#parserdialog' ).dialog( 'open' );
                var dLen = definitionreturned.length;
                var linesreturned = []
                for (i = 0; i < dLen; i++) {
                    linesreturned.push(definitionreturned[i]['value']);
                    }
                $( '#parserdialog' ).html(linesreturned);

            });
            return false;
        });
	return [fwdurl, bkdurl]
}


