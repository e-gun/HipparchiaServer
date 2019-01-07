//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-19
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)


function browseuponclick(url){
	$.getJSON(
	    { url: '/browse/' + url,
	    success: function (passagereturned) {
	        let bf = $('#browseforward');
	        let bb = $('#browseback');
            bf.unbind('click');
            bb.unbind('click');

            let fb = parsepassagereturned(passagereturned);
            // left and right arrow keys

            bf.bind('click', function(){ browseuponclick(fb[0]); });
            bb.bind('click', function(){ browseuponclick(fb[1]); });
            }
        }
        );
    }

function parsepassagereturned(passagereturned) {
        const bdt = $('#browserdialogtext');
        const ldt = $('#lexicadialogtext');
        const aac = $('#authorsautocomplete');
        const wac = $('#worksautocomplete');
		bdt.text('');
        // the first item is info
        // {'forwardsandback': ['/browseto/lt1254w001_AT_2|2|3|6', '/browseto/lt1254w001_AT_6|9|2|6']}
        let fwdurl = passagereturned['browseforwards'];
        let bkdurl = passagereturned['browseback'];

        resetworksautocomplete();
        aac.val(passagereturned['authorboxcontents']);
        aac.prop('placeholder', '');
        wac.val(passagereturned['workboxcontents']);
        wac.prop('placeholder', '');
        loadWorklist(passagereturned['authornumber']);
        loadLevellist(passagereturned['workid'],'top');

        bdt.html(passagereturned['browserhtml']);

        let ids = Array('#worksautocomplete', '#makeanindex', '#textofthis', '#browseto', '#authinfo', '#browserdialog');
        bulkshow(ids);

        $('observed').click( function(e) {
            e.preventDefault();
            let windowWidth = $(window).width();
            let windowHeight = $(window).height();
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
                let dLen = definitionreturned.length;
                let linesreturned = Array();
                for (let i = 0; i < dLen; i++) {
                    linesreturned.push(definitionreturned[i]['value']);
                    }
                ldt.html(linesreturned);
            });
            return false;
        });
	return [fwdurl, bkdurl]
}
