//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-19
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)

//
// AUTHORS
//

// these next two are repeats from documentready.js, but Safari would load this before documentready and so lack access to the functions
function hidemany(arrayofelements) {
    for (let i = 0; i < arrayofelements.length; i++) {
        $(arrayofelements[i]).hide();
        }
}

function clearmany(arrayofelements) {
    for (let i = 0; i < arrayofelements.length; i++) {
        $(arrayofelements[i]).val('');
        }
}

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
    let holder = document.getElementById("selectionscriptholder");
    if (holder.hasChildNodes()) { holder.removeChild(holder.firstChild); }
    $('#selectionscriptholder').html(selectiondata['newjs']);
    }


function reloadAuthorlist(){
    $.getJSON('/getselections', function (selectiondata) {
        reloadselections(selectiondata);
        let ids = Array('#worksautocomplete', '#level05', '#level04', '#level03', '#level02', '#level01', '#level00',
            '#browseto', '#makeanindex', '#textofthis', '#fewerchoices', '#genresautocomplete', '#genreinfo',
            '#genrelistcontents', '#workgenresautocomplete', '#locationsautocomplete', '#provenanceautocomplete',
            '#pickgenre', '#excludegenre', '#setoptions', '#lexica', '#authinfo', '#authorholdings', '#searchlistcontents',
            '#loadslots', '#saveslots');
        hidemany(ids);
    });
}

function resetworksautocomplete(){
    let ids = Array('#level05', '#level04', '#level03', '#level02', '#level01', '#level00');
    hidemany(ids);
    clearmany(ids);
}


function checklocus() {
    let locusval = '';
    for (let i = 5; i > -1; i--) {
        if ($('#level0'+i.toString()).val() !== '') {
            let foundval = $('#level0'+i.toStrint()).val();
            if (locusval !== '') {
                locusval += '|'+foundval;
            } else {
                locusval = foundval;
            }
        }
    }
    console.log(locusval);
    return locusval;
}


$('#authorsautocomplete').autocomplete({
    change: reloadAuthorlist(),
    source: "/getauthorhint",
    select: function (event, ui) {
        let selector = $('#worksautocomplete');
        selector.val('');
        resetworksautocomplete();
        // stupid timing issue if you select with mouse instead of keyboard: nothing happens
        // see: http://stackoverflow.com/questions/9809013/jqueryui-autocomplete-select-does-not-work-on-mouse-click-but-works-on-key-eve
        let origEvent = event;
        let auid = '';
        while (origEvent.originalEvent !== undefined){ origEvent = origEvent.originalEvent; }
        if (origEvent.type === 'click'){
            document.getElementById('authorsautocomplete').value = ui.item.value;
            auid = $('#authorsautocomplete').val().slice(-7, -1);
        } else {
            auid = $('#authorsautocomplete').val().slice(-7, -1);
        }
        loadWorklist(auid);
        selector.prop('placeholder', '(Pick a work)');
        let ids = Array('#worksautocomplete', '#makeanindex', '#textofthis', '#browseto', '#authinfo');
        bulkshow(ids);
        }
    });


$('#pickauthor').click( function() {
        let name = $('#authorsautocomplete').val();
        let authorid = name.slice(-7, -1);
        let locus = locusdataloader();
        // $('#authorsautocomplete').val('');
        let wrk = $('#worksautocomplete').val().slice(-4, -1);
        // $('#worksautocomplete').val('');
        resetworksautocomplete();
        if (authorid !== '') {
            $('#clearpick').show();
            if (wrk === '') {
              $.getJSON('/makeselection?auth=' + authorid, function (selectiondata) {
                    reloadselections(selectiondata);
                    loadWorklist(authorid);
                    $('#worksautocomplete').prop('placeholder', '(Pick a work)');
                    });
             } else if (locus === '') {
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
        let name = $('#authorsautocomplete').val();
        let authorid = name.slice(-7, -1);
        let locus = locusdataloader();
        // $('#authorsautocomplete').val('');
        let wrk = $('#worksautocomplete').val().slice(-4, -1);
        // $('#worksautocomplete').val('');
        resetworksautocomplete();
        if (authorid !== '') {
            $('#clearpick').show();
            if (wrk === '') {
              $.getJSON('/makeselection?auth=' + authorid+'&exclude=t', function (selectiondata) {
                   reloadselections(selectiondata);
                   loadWorklist(authorid);
                  $('#worksautocomplete').prop('placeholder', '(Pick a work)');
                  });
             } else if (locus === '') {
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
        let dLen = selectiondata.length;
        let worksfound = Array();
        selector = $('#worksautocomplete');
        for (let i = 0; i < dLen; i++) { worksfound.push(selectiondata[i]); }
        selector.autocomplete( "enable" );
        selector.autocomplete({ source: worksfound });
        // selector.val(worksfound[0]);
    });
}


$('#worksautocomplete').autocomplete({
    focus: function (event, ui) {
        resetworksautocomplete();
        let auth = $("#authorsautocomplete").val().slice(-7, -1);
        let wrk = ui.item.value.slice(-4, -1);
        loadLevellist(auth+'w'+wrk,'firstline');
        }
});


//
// LEVELS
//

function locusdataloader() {
    let l5 = $('#level05').val();
    let l4 = $('#level04').val();
    let l3 = $('#level03').val();
    let l2 = $('#level02').val();
    let l1 = $('#level01').val();
    let l0 = $('#level00').val();
    let lvls = [ l5, l4, l3, l2, l1, l0];
    let locusdata = '';
    for (let i = 0; i < 6; i++ ) {
        if (lvls[i] !== '') { locusdata += lvls[i]+'|' } }
    locusdata = locusdata.slice(0, (locusdata.length)-1);

    return locusdata;
    }


function loadLevellist(workid, pariallocus){
    // python is hoping to be sent something like:
    //
    //  /getstructure/lt1254w001/firstline
    //  /getstructure/lt0474w043/3|12
    //
    // bad things happen if you send level00 info
    //
    // python will return info about the next level down such as:
    //  [{'totallevels',3},{'level': 0}, {'label': 'verse'}, {'low': 1}, {'high': 100]

    $.getJSON('/getstructure/'+workid+'/'+pariallocus, function (selectiondata) {
        let top = selectiondata['totallevels']-1;
        let atlevel = selectiondata['level'];
        let label = selectiondata['label'];
        let low = selectiondata['low'];
        let high = selectiondata['high'];

        let possibilities = selectiondata['range'];

        let generateme = '#level0'+String(atlevel);
        if ( low !== '-9999') { $(generateme).prop('placeholder', '('+label+' '+String(low)+' to '+String(high)+')'); }
        else { $(generateme).prop('placeholder', '(awaiting a valid selection...)'); }
        $(generateme).show();
        $(generateme).autocomplete ({
            focus: function (event, ui) {
                let auth = workid.slice(0,6);
                let wrk = workid.slice(7,10);
                if (atlevel > 0) {
                    let loc = locusdataloader();
                    loadLevellist(auth+'w'+wrk,loc);
                    }
                // if we do partialloc browsing then this can be off
                // if (atlevel <= 1) { $('#browseto').show(); }
                },
            source: possibilities,
            select: function (event, ui) {
                // if we do partialloc browsing then this can be off
                // if (atlevel <= 1) { $('#browseto').show(); }
                let auth = workid.slice(0,6);
                let wrk = workid.slice(7,10);
                let loc = locusdataloader();

                loadLevellist(auth+'w'+wrk, String(loc));

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
        let genre = $('#genresautocomplete').val();
        let wkgenre = $('#workgenresautocomplete').val();
        let loc = $('#locationsautocomplete').val();
        let prov = $('#provenanceautocomplete').val();

        if (genre !== '') {
            $.getJSON('/makeselection?genre=' + genre, function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        if (wkgenre !== '') {
            $.getJSON('/makeselection?wkgenre=' + wkgenre, function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        if (loc !== '') {
            $.getJSON('/makeselection?auloc=' + loc, function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        if (prov !== '') {
            $.getJSON('/makeselection?wkprov=' + prov, function (selectiondata) {
                reloadselections(selectiondata);
             });
        }

        $('#searchlistcontents').hide();
    });



$('#excludegenre').click( function() {
        let genre = $('#genresautocomplete').val();
        let wkgenre = $('#workgenresautocomplete').val();
        let loc = $('#locationsautocomplete').val();
        let prov = $('#provenanceautocomplete').val();

        if (genre !== '') {
            $.getJSON('/makeselection?genre=' + genre +'&exclude=t', function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        if (wkgenre !== '') {
            $.getJSON('/makeselection?wkgenre=' + wkgenre +'&exclude=t', function (selectiondata) {
                reloadselections(selectiondata);
             });
        }

        if (loc !== '') {
            $.getJSON('/makeselection?auloc=' + loc +'&exclude=t', function (selectiondata) {
                reloadselections(selectiondata);
             });
        }
        if (prov !== '') {
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
