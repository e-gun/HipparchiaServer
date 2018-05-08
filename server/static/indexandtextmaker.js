//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-18
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)


//
// COMPLETE INDEX TO
//

// https://stackoverflow.com/questions/1349404/generate-random-string-characters-in-javascript
// dec2hex :: Integer -> String
function dec2hex (dec) {
  return ('0' + dec.toString(16)).substr(-2);
}

// generateId :: Integer -> String
function generateId (len) {
  var arr = new Uint8Array((len || 40) / 2);
  window.crypto.getRandomValues(arr);
  return Array.from(arr, dec2hex).join('');
}


$('#makeanindex').click( function() {
        var name = $('#authorsautocomplete').val();
        var authorid = name.slice(-7, -1);
        var locus = locusdataloader();
        var wrk = $('#worksautocomplete').val().slice(-4, -1);
        $('#searchsummary').html('');
        $('#displayresults').html('');

        if (authorid !== '') {
            $('#clearpick').show();
            // var searchid = Date.now();
            var searchid = generateId(8);
            var url = '';
            if (wrk === '') { url = '/indexto?auth=' + authorid+'&id='+searchid; }
            else if (locus === '') { url = '/indexto?auth=' + authorid + '&work=' + wrk +'&id='+searchid; }
            else { url = '/indexto?auth=' + authorid + '&work=' + wrk + '&locus=' + locus +'&id='+searchid; }

            $.getJSON(url, function (indexdata) { loadindexintodisplayresults(indexdata); });
            checkactivityviawebsocket(searchid);
        }
});


function loadindexintodisplayresults(indexdata) {
        var linesreturned = '';
        linesreturned += 'Index to ' + indexdata['authorname'];
        if (indexdata['title'] !== '') { linesreturned += ',&nbsp;<span class="foundwork">'+indexdata['title']+'</span>'; }
        if (indexdata['worksegment'] === '') {
            linesreturned += '<br />';
            } else {
            linesreturned += '&nbsp;'+indexdata['worksegment']+'<br />';
            }
        if (indexdata['title'] !== '') { linesreturned += 'citation format:&nbsp;'+indexdata['structure']+'<br />'; }
        linesreturned += indexdata['wordsfound']+' words found<br />';

        var dLen = indexdata['keytoworks'].length;
        if (dLen > 0) {
            linesreturned += '<br />Key to works:<br />';
            for (var i = 0; i < dLen; i++) {
                linesreturned += indexdata['keytoworks'][i]+'<br />';
            }
        }

        linesreturned += '<span class="small">(' + indexdata['elapsed']+ 's)</span><br />';

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
        var name = $('#authorsautocomplete').val();
        var authorid = name.slice(-7, -1);
        var locus = locusdataloader();
        var wrk = $('#worksautocomplete').val().slice(-4, -1);
        if (authorid !== '') {
            $('#clearpick').show();
            var url = '';
            if (wrk === '') { url = '/textof?auth=' + authorid + '&work=999'; }
            else if (locus === '') { url = '/textof?auth=' + authorid + '&work=' + wrk; }
            else { url = '/textof?auth=' + authorid + '&work=' + wrk + '&locus=' + locus; }

            $.getJSON( url, function (returnedtext) { loadtextintodisplayresults(returnedtext); });
        }
    });


function loadtextintodisplayresults(returnedtext) {
        var linesreturned = '';
        linesreturned += 'Text of ' + returnedtext['authorname'];
        linesreturned += ',&nbsp;<span class="foundwork">' + returnedtext['title'] + '</span>';
        if (returnedtext['worksegment'] === '') {
            linesreturned += '<br /><br />';
            } else {
            linesreturned += '&nbsp;' + returnedtext['worksegment'] + '<br /><br />';
            }
        linesreturned += 'citation format:&nbsp;' + returnedtext['structure'] + '<br />';

        $('#searchsummary').html(linesreturned);

        $('#displayresults').html(returnedtext['texthtml']);
    }

