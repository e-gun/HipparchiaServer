//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-18
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)


//
// COMPLETE INDEX TO
//

$('#makeanindex').click( function() {
        var authorid = $('#authorsautocomplete').val().slice(-7, -1);
        var name = $('#authorsautocomplete').val();
        var locus = locusdataloader();
        var wrk = $('#worksautocomplete').val().slice(-4, -1);
        $('#searchsummary').html('');
        $('#displayresults').html('');

        if (authorid != '') {
            $('#clearpick').show();
            var searchid = Date.now();

            if (wrk == '') { var url = '/indexto?auth=' + authorid+'&id='+searchid; }
            else if (locus == '') { var url = '/indexto?auth=' + authorid + '&work=' + wrk +'&id='+searchid; }
            else { var url = '/indexto?auth=' + authorid + '&work=' + wrk + '&locus=' + locus +'&id='+searchid; }

            $.getJSON( url, function (indexdata) { loadindexintodisplayresults(indexdata); });
            checkactivityviawebsocket(searchid);
        }
});


function loadindexintodisplayresults(indexdata) {
        var linesreturned = '';
        linesreturned += 'Index to ' + indexdata['authorname']
        if (indexdata['title'] != '') { linesreturned += ',&nbsp;<span class="foundwork">'+indexdata['title']+'</span>'; }
        if (indexdata['worksegment'] == '') {
            linesreturned += '<br />';
            } else {
            linesreturned += '&nbsp;'+indexdata['worksegment']+'<br />';
            }
        if (indexdata['title'] != '') { linesreturned += 'citation format:&nbsp;'+indexdata['structure']+'<br />'; }
        linesreturned += indexdata['wordsfound']+' words found<br />';

        var dLen = indexdata['keytoworks'].length;
        if (dLen > 0) {
            linesreturned += '<br />Key to works:<br />'
            for (i = 0; i < dLen; i++) {
                linesreturned += indexdata['keytoworks'][i]+'<br />';
            }
        }

        linesreturned += '<span class="small">('+indexdata['elapsed']+'s)</span><br />';

        $('#searchsummary').html(linesreturned);
        $('#displayresults').html(indexdata['indexhtml']);

        var bcsh = document.getElementById("indexclickscriptholder");
        if (bcsh.hasChildNodes()) { bcsh.removeChild(bcsh.firstChild); }

        $('#indexclickscriptholder').html(indexdata['newjs']);
}


//
// TEXTMAKER
//

$('#textofthis').click( function() {
        var authorid = $('#authorsautocomplete').val().slice(-7, -1);
        var name = $('#authorsautocomplete').val();
        var locus = locusdataloader();
        var wrk = $('#worksautocomplete').val().slice(-4, -1);
        if (authorid != '') {
            $('#clearpick').show();
            if (wrk == '') { var url = '/textof?auth=' + authorid + '&work=999'; }
            else if (locus == '') { var url = '/textof?auth=' + authorid + '&work=' + wrk; }
            else { var url = '/textof?auth=' + authorid + '&work=' + wrk + '&locus=' + locus; }

            $.getJSON( url, function (returnedtext) { loadtextintodisplayresults(returnedtext); });
        }
});


function loadtextintodisplayresults(returnedtext) {
        var linesreturned = '';
        linesreturned += 'Text of ' + returnedtext['authorname']
        linesreturned += ',&nbsp;<span class="foundwork">'+returnedtext['title']+'</span>';
        if (returnedtext['worksegment'] == '') {
            linesreturned += '<br /><br />';
            } else {
            linesreturned += '&nbsp;'+returnedtext['worksegment']+'<br /><br />';
            }
        linesreturned += 'citation format:&nbsp;'+returnedtext['structure']+'<br />';
        $('#searchsummary').html(linesreturned);

        $('#displayresults').html(returnedtext['texthtml']);
    }

