//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-18
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)

//
// AUTHORS
//

function reloadselections(selectiondata){
    // the data comes back from the server as a dict with three keys: timeexclusions, selections, exclusions

    if (selectiondata.numberofselections > -1) {
            $('#selectionstable').show();
        } else {
            $('#selectionstable').hide();
        }
    $('#timerestrictions').html(selectiondata.timeexclusions);
    $('#selectioninfocell').html(selectiondata.selections);
    $('#exclusioninfocell').html(selectiondata.exclusions);
    var holder = document.getElementById("selectionscriptholder");
    if (holder.hasChildNodes()) { holder.removeChild(holder.firstChild); }
    $('#selectionscriptholder').html(selectiondata['newjs']);
    }


function reloadAuthorlist(){
    $.getJSON('/getselections', function (selectiondata) {
        reloadselections(selectiondata);
        var ids = new Array('#worksautocomplete', '#level05', '#level04', '#level03', '#level02', '#level01', '#level00',
            '#browseto', '#makeanindex', '#textofthis', '#fewerchoices', '#genresautocomplete', '#genreinfo',
            '#genrelistcontents', '#workgenresautocomplete', '#locationsautocomplete', '#provenanceautocomplete',
            '#pickgenre', '#excludegenre', '#setoptions', '#lexica', '#authinfo', '#authorholdings', '#searchlistcontents',
            '#loadslots', '#saveslots');
        bulkhider(ids);
    });
}

function resetworksautocomplete(){
    var ids = new Array('#level05', '#level04', '#level03', '#level02', '#level01', '#level00');
    bulkhider(ids);
    bulkclear(ids);
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
        $('#worksautocomplete').val('');
        resetworksautocomplete();
        // stupid timing issue if you select with mouse instead of keyboard: nothing happens
        // see: http://stackoverflow.com/questions/9809013/jqueryui-autocomplete-select-does-not-work-on-mouse-click-but-works-on-key-eve
        var origEvent = event;
        while (origEvent.originalEvent !== undefined){ origEvent = origEvent.originalEvent; }
        if (origEvent.type == 'click'){
            document.getElementById('authorsautocomplete').value = ui.item.value;
            var auid = $('#authorsautocomplete').val().slice(-7, -1);
        } else {
            var auid = $('#authorsautocomplete').val().slice(-7, -1);
        }
        loadWorklist(auid);
        $('#worksautocomplete').prop('placeholder', '(Pick a work)');
        var ids = new Array('#worksautocomplete', '#makeanindex', '#textofthis', '#browseto', '#authinfo');
        bulkshow(ids);
        }
    });


$('#pickauthor').click( function() {
        var authorid = $('#authorsautocomplete').val().slice(-7, -1);
        var name = $('#authorsautocomplete').val();
        var locus = locusdataloader();
        // $('#authorsautocomplete').val('');
        var wrk = $('#worksautocomplete').val().slice(-4, -1);
        // $('#worksautocomplete').val('');
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
        // $('#authorsautocomplete').val('');
        var wrk = $('#worksautocomplete').val().slice(-4, -1);
        // $('#worksautocomplete').val('');
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
    $.getJSON('/getworksof/'+authornumber, function (selectiondata) {
        var dLen = selectiondata.length;
        var worksfound = [];
        for (i = 0; i < dLen; i++) { worksfound.push(selectiondata[i]); }
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
    // and bad things happen if you send level00 info

    // python will return info about the next level down such as:
    //  [{'totallevels',3},{'level': 0}, {'label': 'verse'}, {'low': 1}, {'high': 100]
    $.getJSON('/getstructure/'+workid+'_AT_'+pariallocus, function (selectiondata) {
        var top = selectiondata['totallevels']-1;
        var atlevel = selectiondata['level'];
        var label = selectiondata['label'];
        var low = selectiondata['low'];
        var high = selectiondata['high'];

        var possibilities = selectiondata['range'];

        var generateme = '#level0'+String(atlevel);
        if ( low != '-9999') { $(generateme).prop('placeholder', '('+label+' '+String(low)+' to '+String(high)+')'); }
        else { $(generateme).prop('placeholder', '(awaiting a valid selection...)'); }
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

$('#locationsautocomplete').autocomplete({
    source: '/getaulocationhint'
    });

$('#provenanceautocomplete').autocomplete({
    source: '/getwkprovenancehint'
    });

$('#pickgenre').click( function() {
        var genre = $('#genresautocomplete').val();
        var wkgenre = $('#workgenresautocomplete').val();
        var loc = $('#locationsautocomplete').val();
        var prov = $('#provenanceautocomplete').val();

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
        if (loc != '') {
            $.getJSON('/makeselection?auloc=' + loc, function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        if (prov != '') {
            $.getJSON('/makeselection?wkprov=' + prov, function (selectiondata) {
                reloadselections(selectiondata);
             });
        }

        $('#searchlistcontents').hide();
    });



$('#excludegenre').click( function() {
        var genre = $('#genresautocomplete').val();
        var wkgenre = $('#workgenresautocomplete').val();
        var loc = $('#locationsautocomplete').val();
        var prov = $('#provenanceautocomplete').val();

        if (genre != '') {
            $.getJSON('/makeselection?genre=' + genre +'&exclude=t', function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        if (wkgenre != '') {
            $.getJSON('/makeselection?wkgenre=' + wkgenre +'&exclude=t', function (selectiondata) {
                reloadselections(selectiondata);
             });
        }

        if (loc != '') {
            $.getJSON('/makeselection?auloc=' + loc +'&exclude=t', function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        if (prov != '') {
            $.getJSON('/makeselection?wkprov=' + prov +'&exclude=t', function (selectiondata) {
                reloadselections(selectiondata);
             });
        }

        $('#searchlistcontents').hide();
    });


//
// LEMMATA
//

$('#lemmatasearchform').autocomplete({
    source: '/getlemmahint'
    });


$('#proximatelemmatasearchform').autocomplete({
    source: '/getlemmahint'
    });
