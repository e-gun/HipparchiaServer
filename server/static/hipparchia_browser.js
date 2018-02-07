//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-18
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)


function browseuponclick(url){
	$.getJSON(
	    { url: '/browse/' + url,
	    success: function (passagereturned) {
	        var bf = $('#browseforward');
	        var bb = $('#browseback');
            bf.unbind('click');
            bb.unbind('click');

            var fb = parsepassagereturned(passagereturned);
            // left and right arrow keys

            bf.bind('click', function(){ browseuponclick(fb[0]); });
            bb.bind('click', function(){ browseuponclick(fb[1]); });
            }
        }
        );
    }

function parsepassagereturned(passagereturned) {
        var bdt = $('#browserdialogtext');
        var ldt = $('#lexicadialogtext');
        var aac = $('#authorsautocomplete');
        var wac = $('#worksautocomplete');
		bdt.text('');
        // the first item is info
        // {'forwardsandback': ['/browseto/lt1254w001_AT_2|2|3|6', '/browseto/lt1254w001_AT_6|9|2|6']}
        var fwdurl = passagereturned['browseforwards'];
        var bkdurl = passagereturned['browseback'];

        resetworksautocomplete();
        aac.val(passagereturned['authorboxcontents']);
        aac.prop('placeholder', '');
        wac.val(passagereturned['workboxcontents']);
        wac.prop('placeholder', '');
        loadWorklist(passagereturned['authornumber']);
        loadLevellist(passagereturned['workid'],'-1');

        bdt.html(passagereturned['browserhtml']);

        var ids = Array('#worksautocomplete', '#makeanindex', '#textofthis', '#browseto', '#authinfo', '#browserdialog');
        bulkshow(ids);

        $('observed').click( function(e) {
            e.preventDefault();
            var windowWidth = $(window).width();
            var windowHeight = $(window).height();
            ldt.dialog({
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
            ldt.dialog( 'open' );
            ldt.html('[searching...]');
            $.getJSON('/parse/' + this.id, function (definitionreturned) {
                $('#lexicon').val(definitionreturned[0]['trylookingunder']);
                var dLen = definitionreturned.length;
                var linesreturned = Array();
                for (var i = 0; i < dLen; i++) {
                    linesreturned.push(definitionreturned[i]['value']);
                    }
                ldt.html(linesreturned);
            });
            return false;
        });
	return [fwdurl, bkdurl]
}
