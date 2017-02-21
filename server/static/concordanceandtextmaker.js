//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-17
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)


//
// CONCORDANCE
//

$('#concordance').click( function() {
        var authorid = $('#authorsautocomplete').val().slice(-7, -1);
        var name = $('#authorsautocomplete').val();
        var locus = locusdataloader();
        var wrk = $('#worksautocomplete').val().slice(-4, -1);
        $('#searchsummary').html('');
        $('#displayresults').html('');

        if (authorid != '') {
            $('#clearpick').show();
            var searchid = Date.now();

            if (wrk == '') { var url = '/concordance?auth=' + authorid+'&id='+searchid; }
            else if (locus == '') { var url = '/concordance?auth=' + authorid + '&work=' + wrk +'&id='+searchid; }
            else { var url = '/concordance?auth=' + authorid + '&work=' + wrk + '&locus=' + locus +'&id='+searchid; }

            $.getJSON( url, function (concordancedata) { loadconcordanceintodisplayresults(concordancedata); });
            checkactivityviawebsocket(searchid);
//          old polling mechanism: slated for removal
//          var i = setInterval(function(){
//                $.getJSON('/progress'+'?id='+searchid, function(progress) { displayprogress(progress); if (progress['active'] == false) { clearInterval(i); document.getElementById('pollingdata').innerHTML = ''; } });
//                }, 400);
        }
});


function loadconcordanceintodisplayresults(concordancedata) {
        var linesreturned = '';
        linesreturned += 'Concordance to ' + concordancedata['authorname']
        if (concordancedata['title'] != '') { linesreturned += ',&nbsp;<span class="foundwork">'+concordancedata['title']+'</span>'; }
        if (concordancedata['worksegment'] == '') {
            linesreturned += '<br />';
            } else {
            linesreturned += '&nbsp;'+concordancedata['worksegment']+'<br />';
            }
        if (concordancedata['title'] != '') { linesreturned += 'citation format:&nbsp;'+concordancedata['structure']+'<br />'; }
        linesreturned += concordancedata['wordsfound']+' words found<br />';

        var dLen = concordancedata['keytoworks'].length;
        if (dLen > 0) {
            linesreturned += '<br />Key to works:<br />'
            for (i = 0; i < dLen; i++) {
                linesreturned += concordancedata['keytoworks'][i]+'<br />';
            }
        }

        linesreturned += '<span class="small">('+concordancedata['elapsed']+'s)</span><br />';

        $('#searchsummary').html(linesreturned);

        var linesreturned = '';
        var dLen = concordancedata['lines'].length;
        for (i = 0; i < dLen; i++) {
            linesreturned += concordancedata['lines'][i];
            }
        $('#displayresults').html(linesreturned);
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
            if (wrk == '') { var url = '/text?auth=' + authorid + '&work=999'; }
            else if (locus == '') { var url = '/text?auth=' + authorid + '&work=' + wrk; }
            else { var url = '/text?auth=' + authorid + '&work=' + wrk + '&locus=' + locus; }

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

        var linesreturned = '';
        var dLen = returnedtext['lines'].length;
        for (i = 0; i < dLen; i++) {
            linesreturned += returnedtext['lines'][i];
            }
        $('#displayresults').html(linesreturned);
    }

