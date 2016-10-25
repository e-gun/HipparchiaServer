//
// AUTHORS
//

function reloadselections(selectiondata){
    // the data comes back from the server as a dict with three keys: timeexclusions, selections, exclusions

    if (selectiondata.numberofselections > -1) {
            $('#selectionstable').show();
            $('#droptodelete').droppable( {
                drop: deleteondrop
                });
            $('#droptodelete').show();
            $( function() {
                for (i = 0; i <= selectiondata.numberofselections; i++) {
                    var newdrag = '#searchselection_0'+i.toString();
                    $(newdrag).draggable();
                    }
                });
        } else {
            $('#selectionstable').hide();
        }

    $('#timerestrictions').html(selectiondata.timeexclusions);
    $('#selectioninfocell').html(selectiondata.selections);
    $('#exclusioninfocell').html(selectiondata.exclusions);
    }


function deleteondrop(event, ui) {
    var todelete = ui.draggable;
    var cla = todelete.attr('class').split(' ');
    var listposition = todelete.attr('listval');
    $.getJSON('/clearselections?cat='+cla[0]+'&id='+listposition, function (selectiondata) { reloadselections(selectiondata); });
    document.getElementById('searchlistcontents').innerHTML = '';
    $('#searchlistcontents').hide();
    // alert( 'delete '+todelete.attr('id')+' cl:'+cla[0]+' lv:'+todelete.attr('listval'))
}


function reloadAuthorlist(){
    $.getJSON('/makeselection', function (selectiondata) {
        reloadselections(selectiondata);
        $('#worksautocomplete').hide();
        $('#level05').hide();
        $('#level04').hide();
        $('#level03').hide();
        $('#level02').hide();
        $('#level01').hide();
        $('#level00').hide();
        $('#browseto').hide();
        $('#concordance').hide();
        $('#textofthis').hide();
        $('#fewerchoices').hide();
        $('#genresautocomplete').hide();
        $('#genreinfo').hide();
        $('#genrelistcontents').hide();
        $('#workgenresautocomplete').hide();
        $('#pickgenre').hide();
        $('#excludegenre').hide();
        $('#setoptions').hide();
        $('#lexica').hide();
        $('#authinfo').hide();
        $('#authorholdings').hide();
        $('#searchlistcontents').hide();
    }
    );
}


function resetworksautocomplete() {
        $('#level05').hide(); $('#level05').val('');
        $('#level04').hide(); $('#level04').val('');
        $('#level03').hide(); $('#level03').val('');
        $('#level02').hide(); $('#level02').val('');
        $('#level01').hide(); $('#level01').val('');
        $('#level00').hide(); $('#level00').val('');
}


function checklocus() {
    var locusval = '';
    for (i = 5; i > -1; i--) {
        if ($('#level0'+i.toString()).val() != '') {
            var foundval = $('#level0'+i.toStrint()).val();
            if (locusval != '') {
                locusval += '|'+foundval;
            } else {
                locusval = foundval;
            }
        }
    }
    console.log(locusval)
    return locusval;
}


$('#authorsautocomplete').autocomplete({
    change: reloadAuthorlist(),
    source: "/getauthorhint",
    select: function (event, ui) {
        $('#concordance').show();
        $('#textofthis').show();
        $('#browseto').show();
        $('#worksautocomplete').hide();
        $('#worksautocomplete').val('');
        resetworksautocomplete();
        loadWorklist($('#authorsautocomplete').val().slice(-7, -1));
        $('#worksautocomplete').show();
        $('#authinfo').show();
        $('#worksautocomplete').prop('placeholder', '(Pick a work)');
        }
    });


$('#pickauthor').click( function() {
        var authorid = $('#authorsautocomplete').val().slice(-7, -1);
        var name = $('#authorsautocomplete').val();
        var locus = locusdataloader();
        $('#authorsautocomplete').val('');
        var wrk = $('#worksautocomplete').val().slice(-4, -1);
        $('#worksautocomplete').val('');
        resetworksautocomplete();
        if (authorid != '') {
            $('#clearpick').show();
            if (wrk == '') {
              $.getJSON('/makeselection?auth=' + authorid, function (selectiondata) {
                   reloadselections(selectiondata);
                   loadWorklist(authorid);
                  $('#worksautocomplete').prop('placeholder', '(Pick a work)');
                  });
             } else if (locus == '') {
                $.getJSON('/makeselection?auth=' + authorid + '&work=' + wrk, function (selectiondata) {
                    reloadselections(selectiondata);
                });
             } else {
                $.getJSON('/makeselection?auth=' + authorid + '&work=' + wrk + '&locus=' + locus, function (selectiondata) {
                    reloadselections(selectiondata);
                });
             }
        }
        $('#searchlistcontents').hide();
});


$('#excludeauthor').click( function() {
        var authorid = $('#authorsautocomplete').val().slice(-7, -1);
        var name = $('#authorsautocomplete').val();
        var locus = locusdataloader();
        $('#authorsautocomplete').val('');
        var wrk = $('#worksautocomplete').val().slice(-4, -1);
        $('#worksautocomplete').val('');
        resetworksautocomplete();
        if (authorid != '') {
            $('#clearpick').show();
            if (wrk == '') {
              $.getJSON('/makeselection?auth=' + authorid+'&exclude=t', function (selectiondata) {
                   reloadselections(selectiondata);
                   loadWorklist(authorid);
                  $('#worksautocomplete').prop('placeholder', '(Pick a work)');
                  });
             } else if (locus == '') {
                $.getJSON('/makeselection?auth=' + authorid + '&work=' + wrk+'&exclude=t', function (selectiondata) {
                    reloadselections(selectiondata);
                });
             } else {
                $.getJSON('/makeselection?auth=' + authorid + '&work=' + wrk + '&locus=' + locus+'&exclude=t', function (selectiondata) {
                    reloadselections(selectiondata);
                });
             }
        }
        $('#searchlistcontents').hide();
});

//
// WORKS
//

function loadWorklist(authornumber){
    $.getJSON('/getworkhint?auth='+authornumber, function (selectiondata) {
        var dLen = selectiondata.length;
        var worksfound = [];
        for (i = 0; i < dLen; i++) {
            worksfound.push(selectiondata[i]);
            }
        $('#worksautocomplete').autocomplete( "enable" );
        $('#worksautocomplete').autocomplete({
            source: worksfound
            });
        // $('#worksautocomplete').val(worksfound[0]);
    });
}


$('#worksautocomplete').autocomplete({
    focus: function (event, ui) {
        resetworksautocomplete();
        var auth = $("#authorsautocomplete").val().slice(-7, -1);
        var wrk = ui.item.value.slice(-4, -1);
        loadLevellist(auth+'w'+wrk,'-1');
        }
});


//
// LEVELS
//

function locusdataloader() {
    var l5 = $('#level05').val();
    var l4 = $('#level04').val();
    var l3 = $('#level03').val();
    var l2 = $('#level02').val();
    var l1 = $('#level01').val();
    var l0 = $('#level00').val();
    var lvls = [ l5,l4,l3,l2,l1,l0];
    var locusdata = '';
    for (i = 0; i < 6; i++ ) {
        if (lvls[i] != '') { locusdata += lvls[i]+'|' } }
    locusdata = locusdata.slice(0,(locusdata.length)-1);

    return locusdata;
    }


function loadLevellist(workid,pariallocus){
    // python is hoping to see something like ImmutableMultiDict([('locus', 'gr0026w001_AT_3')])
    //  or gr0565w001_AT_-1 (-1 = no knowledge of the work yet)
    //  or gr0565w001_AT_2|3
    // note that this is to be read as lowest known level first
    // and bad thing happen if you send level00 info
    // python will return info about the next level down such as:
    //  [{'totallevels',3},{'level': 0}, {'label': 'verse'}, {'low': 1}, {'high': 100]
    $.getJSON('/getstructure?locus='+workid+'_AT_'+pariallocus, function (selectiondata) {
        var top = selectiondata[0]['totallevels']-1;
        var atlevel = selectiondata[1]['level'];
        var label = selectiondata[2]['label'];
        var low = selectiondata[3]['low'];
        var high = selectiondata[4]['high'];

        var possibilities = selectiondata[5]['rng'];

        var generateme = '#level0'+String(atlevel);
        $(generateme).prop('placeholder', '('+label+' '+String(low)+' to '+String(high)+')');
        $(generateme).show();
        $(generateme).autocomplete ({
            focus: function (event, ui) {
                var auth = workid.slice(0,6);
                var wrk = workid.slice(7,10);
                if (atlevel > 0) {
                    var loc = locusdataloader();
                    loadLevellist(auth+'w'+wrk,loc);
                    }
                // if we do partialloc browsing then this can be off
                // if (atlevel <= 1) { $('#browseto').show(); }
                },
            source: possibilities,
            select: function (event, ui) {
                // if we do partialloc browsing then this can be off
                // if (atlevel <= 1) { $('#browseto').show(); }
                var auth = workid.slice(0,6);
                var wrk = workid.slice(7,10);
                var loc = locusdataloader();

                loadLevellist(auth+'w'+wrk,String(loc));

            }});
    });
}


//
// GENRES
//

$('#genresautocomplete').autocomplete({
    source: '/getgenrehint'
    });


$('#workgenresautocomplete').autocomplete({
    source: '/getworkgenrehint'
    });


$('#pickgenre').click( function() {
        var genre = $('#genresautocomplete').val();
        var wkgenre = $('#workgenresautocomplete').val();

        if (genre != '') {
            $.getJSON('/makeselection?genre=' + genre, function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        if (wkgenre != '') {
            $.getJSON('/makeselection?wkgenre=' + wkgenre, function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        $('#searchlistcontents').hide();
    });



$('#excludegenre').click( function() {
        var genre = $('#genresautocomplete').val();
        var wkgenre = $('#workgenresautocomplete').val();

        if (genre != '') {
            $.getJSON('/makeselection?genre=' + genre+'&exclude=t', function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        if (wkgenre != '') {
            $.getJSON('/makeselection?wkgenre=' + wkgenre+'&exclude=t', function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        $('#searchlistcontents').hide();
    });

//
// CONCORDANCE
//

$('#concordance').click( function() {
        var authorid = $('#authorsautocomplete').val().slice(-7, -1);
        var name = $('#authorsautocomplete').val();
        var locus = locusdataloader();
        var wrk = $('#worksautocomplete').val().slice(-4, -1);
        document.getElementById('searchsummary').innerHTML = '';
        document.getElementById('displayresults').innerHTML = ''

        if (authorid != '') {
            $('#clearpick').show();
            if (wrk == '') { var url = '/concordance?auth=' + authorid; }
            else if (locus == '') { var url = '/concordance?auth=' + authorid + '&work=' + wrk; }
            else { var url = '/concordance?auth=' + authorid + '&work=' + wrk + '&locus=' + locus; }

            $.getJSON( url, function (concordancedata) { loadconcordanceintodisplayresults(concordancedata); });
            var i = setInterval(function(){
                $.getJSON('/progress', function(progress) { displayprogress(progress); if (progress['active'] == false) { clearInterval(i); document.getElementById('pollingdata').innerHTML = ''; } });
                }, 400);
        }
});


function loadconcordanceintodisplayresults(concordancedata) {
        var linesreturned = '';
        linesreturned += 'Concordance to ' + concordancedata['authorname']
        if (concordancedata['title'] != '') { linesreturned += ',&nbsp;<span class="foundwork">'+concordancedata['title']+'</span>'; }
        if (concordancedata['worksegment'] == '') {
            linesreturned += '<br /><br />';
            } else {
            linesreturned += '&nbsp;'+concordancedata['worksegment']+'<br /><br />';
            }
        if (concordancedata['title'] != '') { linesreturned += 'citation format:&nbsp;'+concordancedata['structure']+'<br /><br />'; }
        linesreturned += concordancedata['wordsfound']+' words found<br />';

        var dLen = concordancedata['keytoworks'].length;
        if (dLen > 0) {
            linesreturned += '<br />Key to works:<br />'
            for (i = 0; i < dLen; i++) {
                linesreturned += concordancedata['keytoworks'][i]+'<br />';
            }
        }

        linesreturned += '<span class="small">('+concordancedata['elapsed']+'s)</span><br />';

        document.getElementById('searchsummary').innerHTML = linesreturned;

        var linesreturned = '';
        var dLen = concordancedata['lines'].length;
        for (i = 0; i < dLen; i++) {
            linesreturned += concordancedata['lines'][i];
            }
        document.getElementById('displayresults').innerHTML = linesreturned;
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
        document.getElementById('searchsummary').innerHTML = linesreturned;

        var linesreturned = '';
        var dLen = returnedtext['lines'].length;
        for (i = 0; i < dLen; i++) {
            linesreturned += returnedtext['lines'][i];
            }
        document.getElementById('displayresults').innerHTML = linesreturned;
    }


//
// PROGRESS
//

function displayprogress(progress){
    var r = progress['remaining'];
    var t = progress['total'];
    var h = progress['hits'];
    var pct = Math.round((t-r) / t * 100);
    var done = t - r;
    var m = progress['message']

    var thehtml = ''
    if (t != -1) {
        thehtml += m + ': <span class="progress">' + pct+'%</span> completed';
    } else {
        thehtml += m;
        }

   if ( h > 0) { thehtml += '<br />(<span class="progress">'+h+'</span> found)'; }

    document.getElementById('pollingdata').innerHTML = thehtml;
}
