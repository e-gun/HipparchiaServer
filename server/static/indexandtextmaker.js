//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-21
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)


//
// COMPLETE INDEX TO
//

// https://stackoverflow.com/questions/105034/create-guid-uuid-in-javascript#2117523
function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    )
}

// https://stackoverflow.com/questions/1349404/generate-random-string-characters-in-javascript
// dec2hex :: Integer -> String
function dec2hex (dec) {
  return ('0' + dec.toString(16)).substr(-2);
}

// generateId :: Integer -> String
function generateId (len) {
  let arr = new Uint8Array((len || 40) / 2);
  window.crypto.getRandomValues(arr);
  return Array.from(arr, dec2hex).join('');
}


$('#makeanindex').click( function() {
        let headertext = 'Index to ';
        let name = $('#authorsautocomplete').val();
        let authorid = name.slice(-7, -1);
        let locus = locusdataloader();
        let endpoint = endpointdataloader();
        let wrk = $('#worksautocomplete').val().slice(-4, -1);
        let searchid = generateId(8);
        let rawlocus = $('#rawlocationinput').val();
        let rawendpoint = $('#rawendpointinput').val();
        if ($('#endpointnotice').is(':hidden')) {
            rawendpoint = '';
            endpoint = '';
        }
        $('#searchsummary').html('');
        $('#displayresults').html('');

        if (authorid !== '') {
            if ($('#autofillinput').is(':checked')) {
                // you are using the autofill boxes
                if (endpoint === '') {
                    checkactivityviawebsocket(searchid);
                    let url = '';
                    if (wrk === '') {
                        url = '/indexto/' + searchid + '/' + authorid;
                    } else if (locus === '') {
                        url = '/indexto/' + searchid + '/' + authorid + '/' + wrk;
                    } else {
                        url = '/indexto/' + searchid + '/' + authorid + '/' + wrk + '/' + locus;
                    }
                    $.getJSON(url, function (indexdata) {
                        loadindexintodisplayresults(indexdata, headertext);
                    });
                } else {
                    checkactivityviawebsocket(searchid);
                    let url = '/indexto/' + searchid + '/' + authorid + '/' + wrk + '/' + locus + '/' + endpoint;
                    $.getJSON(url, function (indexdata) {
                        loadindexintodisplayresults(indexdata, headertext);
                    });
                }
            } else {
                // you are using the raw entry subsystem
                checkactivityviawebsocket(searchid);
                let url = '';
                if (wrk === '') {
                    url = '/indexto/' + searchid + '/' + authorid;
                } else if (rawlocus === '' && rawendpoint === '') {
                    url = '/indexto/' + searchid + '/' + authorid + '/' + wrk;
                } else if (rawendpoint === '') {
                    url = '/indextorawlocus/' + searchid + '/' + authorid + '/' + wrk + '/' + rawlocus;
                } else {
                    url = '/indextorawlocus/' + searchid + '/' + authorid + '/' + wrk + '/' + rawlocus + '/' + rawendpoint;
                }
                $.getJSON(url, function (indexdata) {
                    loadindexintodisplayresults(indexdata, headertext);
                });
            }
        }
});


function loadindexintodisplayresults(indexdata) {
        let linesreturned = '';
        linesreturned += 'Index to ' + indexdata['authorname'];
        if (indexdata['title'] !== '') { linesreturned += ',&nbsp;<span class="foundwork">'+indexdata['title']+'</span>'; }
        if (indexdata['worksegment'] === '') {
            linesreturned += '<br />';
            } else {
            linesreturned += '&nbsp;'+indexdata['worksegment']+'<br />';
            }
        if (indexdata['title'] !== '') { linesreturned += 'citation format:&nbsp;'+indexdata['structure']+'<br />'; }
        linesreturned += indexdata['wordsfound']+' words found<br />';

        let dLen = indexdata['keytoworks'].length;
        if (dLen > 0) {
            linesreturned += '<br />Key to works:<br />';
            for (let i = 0; i < dLen; i++) {
                linesreturned += indexdata['keytoworks'][i]+'<br />';
            }
        }

        linesreturned += '<span class="small">(' + indexdata['elapsed']+ 's)</span><br />';

        $('#searchsummary').html(linesreturned);
        $('#displayresults').html(indexdata['indexhtml']);

        let bcsh = document.getElementById("indexclickscriptholder");
        if (bcsh.hasChildNodes()) { bcsh.removeChild(bcsh.firstChild); }

        $('#indexclickscriptholder').html(indexdata['newjs']);
}


//
// VOCABLISTS
//


$('#makevocablist').click( function() {
        let headertext = 'Vocabulary for ';
        let name = $('#authorsautocomplete').val();
        let authorid = name.slice(-7, -1);
        let locus = locusdataloader();
        let endpoint = endpointdataloader();
        let wrk = $('#worksautocomplete').val().slice(-4, -1);
        let searchid = generateId(8);
        let rawlocus = $('#rawlocationinput').val();
        let rawendpoint = $('#rawendpointinput').val();
        if ($('#endpointnotice').is(':hidden')) {
            rawendpoint = '';
            endpoint = '';
        }
        $('#searchsummary').html('');
        $('#displayresults').html('');

        if (authorid !== '') {
            if ($('#autofillinput').is(':checked')) {
                // you are using the autofill boxes
                if (endpoint === '') {
                    checkactivityviawebsocket(searchid);
                    let url = '';
                    if (wrk === '') {
                        url = '/vocabularyfor/' + searchid + '/' + authorid;
                    } else if (locus === '') {
                        url = '/vocabularyfor/' + searchid + '/' + authorid + '/' + wrk;
                    } else {
                        url = '/vocabularyfor/' + searchid + '/' + authorid + '/' + wrk + '/' + locus;
                    }
                    $.getJSON(url, function (vocabdata) {
                        loadtextintodisplayresults(vocabdata, headertext);
                    });
                } else {
                    checkactivityviawebsocket(searchid);
                    let url = '/vocabularyfor/' + searchid + '/' + authorid + '/' + wrk + '/' + locus + '/' + endpoint;
                    $.getJSON(url, function (vocabdata) {
                        loadtextintodisplayresults(vocabdata, headertext);
                    });
                }
            } else {
                // you are using the raw entry subsystem
                checkactivityviawebsocket(searchid);
                let url = '';
                if (wrk === '') {
                    url = '/vocabularyfor/' + searchid + '/' + authorid;
                } else if (rawlocus === '' && rawendpoint === '') {
                    url = '/vocabularyfor/' + searchid + '/' + authorid + '/' + wrk;
                } else if (rawendpoint === '') {
                    url = '/vocabularyforrawlocus/' + searchid + '/' + authorid + '/' + wrk + '/' + rawlocus;
                } else {
                    url = '/vocabularyforrawlocus/' + searchid + '/' + authorid + '/' + wrk + '/' + rawlocus + '/' + rawendpoint;
                }
                $.getJSON(url, function (vocabdata) {
                    loadtextintodisplayresults(vocabdata, headertext);
                });
            }
        }
});


//
// TEXTMAKER
//

$('#textofthis').click( function() {
        let headertext = 'Text of ';
        let name = $('#authorsautocomplete').val();
        let authorid = name.slice(-7, -1);
        let locus = locusdataloader();
        let endpoint = endpointdataloader();
        let wrk = $('#worksautocomplete').val().slice(-4, -1);
        let rawlocus = $('#rawlocationinput').val();
        let rawendpoint = $('#rawendpointinput').val();
        if ($('#endpointnotice').is(':hidden')) {
            rawendpoint = '';
            endpoint = '';
        }
        if (authorid !== '') {
            if ($('#autofillinput').is(':checked')) {
                // you are using the autofill boxes
                if (endpoint === '') {
                    let url = '';
                    if (wrk === '') {
                        url = '/textof/' + authorid;
                    } else if (locus === '') {
                        url = '/textof/' + authorid + '/' + wrk;
                    } else {
                        url = '/textof/' + authorid + '/' + wrk + '/' + locus;
                    }
                    $.getJSON(url, function (returnedtext) {
                        loadtextintodisplayresults(returnedtext, headertext);
                    });
                } else {
                    let url = '/textof/' + authorid + '/' + wrk + '/' + locus + '/' + endpoint;
                    $.getJSON(url, function (returnedtext) {
                        loadtextintodisplayresults(returnedtext, headertext);
                    });
                }
            } else {
                // you are using the raw entry subsystem
                let url = '';
                if (wrk === '') {
                    url = '/textof/' + authorid;
                } else if (rawlocus === '' && rawendpoint === '') {
                    url = '/textof/' + authorid + '/' + wrk;
                } else if (rawendpoint === '') {
                    url = '/textofrawlocus/' + authorid + '/' + wrk + '/' + rawlocus;
                } else {
                    url = '/textofrawlocus/' + authorid + '/' + wrk + '/' + rawlocus + '/' + rawendpoint;
                }
                $.getJSON(url, function (returnedtext) {
                loadtextintodisplayresults(returnedtext, headertext);
                });
            }
        }
    });


function loadtextintodisplayresults(returnedtext, headertext) {
    let linesreturned = '';
    linesreturned += headertext + returnedtext['authorname'];
    linesreturned += ',&nbsp;<span class="foundwork">' + returnedtext['title'] + '</span>';
    if (returnedtext['worksegment'] === '') {
        linesreturned += '<br /><br />';
        } else {
        linesreturned += '&nbsp;' + returnedtext['worksegment'] + '<br /><br />';
        }
    linesreturned += 'citation format:&nbsp;' + returnedtext['structure'] + '<br />';

    $('#searchsummary').html(linesreturned);

    $('#displayresults').html(returnedtext['texthtml']);

    $('#indexclickscriptholder').html(returnedtext['newjs']);

    }