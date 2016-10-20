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
        $('#concordance').show();
        $('#textofthis').show();
        $('#browseto').show();
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
                if (atlevel <= 1) { $('#browseto').show(); }
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
        console.log('g='+genre);
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
        console.log('g='+genre);
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

// the first version is selectively visible on the search page
// the second version is always visible on the concordance page
// the only difference should be the element id name

$('#concordance').click( function() {
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
                window.location = '/concordance?auth=' + authorid;
             } else if (locus == '') {
                window.location = '/concordance?auth=' + authorid + '&work=' + wrk;
             } else {
                window.location = '/concordance?auth=' + authorid + '&work=' + wrk + '&locus=' + locus;
             }
        }
});


$('#concordancemaker').click( function() {
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
                window.location = '/concordance?auth=' + authorid;
             } else if (locus == '') {
                window.location = '/concordance?auth=' + authorid + '&work=' + wrk;
             } else {
                window.location = '/concordance?auth=' + authorid + '&work=' + wrk + '&locus=' + locus;
             }
        }
});


$('#textofthis').click( function() {
        var authorid = $('#authorsautocomplete').val().slice(-7, -1);
        var name = $('#authorsautocomplete').val();
        var locus = locusdataloader();
        var wrk = $('#worksautocomplete').val().slice(-4, -1);
        if (authorid != '') {
            $('#clearpick').show();
            if (wrk == '') {
                // just an author is not enough...
             } else if (locus == '') {
                $.getJSON('/text?auth=' + authorid + '&work=' + wrk, function (selectiondata) {
                    loadtextintodisplayresults(selectiondata);
                });
             } else {
                $.getJSON('/text?auth=' + authorid + '&work=' + wrk + '&locus=' + locus, function (selectiondata) {
                    loadtextintodisplayresults(selectiondata);
                });
             }
        }
});

function loadtextintodisplayresults(selectiondata) {
        var dLen = selectiondata['lines'].length;
        var linesreturned = '';
        linesreturned += 'Text of ' + selectiondata['authorname']
        linesreturned += ',&nbsp;<span class="foundwork">'+selectiondata['title']+'</span>';
        if (selectiondata['worksegment'] == '') {
            linesreturned += '<br /><br />';
            } else {
            linesreturned += '&nbsp;'+selectiondata['worksegment']+'<br /><br />';
            }
        linesreturned += 'citation format:&nbsp;'+selectiondata['structure']+'<br />';

        document.getElementById('searchsummary').innerHTML = linesreturned;
        var linesreturned = '';
        for (i = 0; i < dLen; i++) {
            linesreturned += selectiondata['lines'][i];
            }
        document.getElementById('displayresults').innerHTML = linesreturned;
    }