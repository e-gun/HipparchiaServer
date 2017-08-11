//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-17
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)


function browseuponclick(url){
	$.getJSON(
	    { url: '/browse/'+url,
	    success: function (passagereturned) {
            $('#browseforward').unbind('click');
            $('#browseback').unbind('click');

            var fb = parsepassagereturned(passagereturned);
            // left and right arrow keys

            $('#browseforward').bind('click', function(){ browseuponclick(fb[0]); });
            $('#browseback').bind('click', function(){ browseuponclick(fb[1]); });
            }
        }
        );
    }

function parsepassagereturned(passagereturned) {
		$('#browserdialogtext').text('');
        // the first item is info
        // {'forwardsandback': ['/browseto/lt1254w001_AT_2|2|3|6', '/browseto/lt1254w001_AT_6|9|2|6']}
        var fwdurl = passagereturned['browseforwards'];
        var bkdurl = passagereturned['browseback'];

        resetworksautocomplete();
        $('#authorsautocomplete').val(passagereturned['authorboxcontents']);
        $('#authorsautocomplete').prop('placeholder', '');
        $('#worksautocomplete').val(passagereturned['workboxcontents']);
        $('#worksautocomplete').prop('placeholder', '');
        loadWorklist(passagereturned['authornumber']);
        loadLevellist(passagereturned['workid'],'-1');

        $('#browserdialogtext').html(passagereturned['browserhtml']);

        var ids = new Array('#worksautocomplete', '#makeanindex', '#textofthis', '#browseto', '#authinfo', '#browserdialog');
        bulkshow(ids);

        $('observed').click( function(e) {
            e.preventDefault();
            var windowWidth = $(window).width();
            var windowHeight = $(window).height();
            $( '#lexicadialogtext' ).dialog({
                    closeOnEscape: true,
                    autoOpen: false,
                    minWidth: windowWidth*.33,
                    maxHeight: windowHeight*.9,
                    // position: { my: "left top", at: "left top", of: window },
                    title: this.id,
                    draggable: true,
                    icons: { primary: 'ui-icon-close' },
                    click: function() { $( this ).dialog( 'close' ); }
                    });
            $( '#lexicadialogtext' ).dialog( 'open' );
            $( '#lexicadialogtext' ).html('[searching...]');
            $.getJSON('/parse/'+this.id, function (definitionreturned) {
                $( '#lexicon').val(definitionreturned[0]['trylookingunder']);
                var dLen = definitionreturned.length;
                var linesreturned = []
                for (i = 0; i < dLen; i++) {
                    linesreturned.push(definitionreturned[i]['value']);
                    }
                $( '#lexicadialogtext' ).html(linesreturned);
            });
            return false;
        });
	return [fwdurl, bkdurl]
}
