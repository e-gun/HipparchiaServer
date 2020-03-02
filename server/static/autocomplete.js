//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-20
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)

//
// AUTHORS
//

// these next two are repeats from documentready.js, but Safari would load this before documentready and so lacked access to the functions
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
    let ids = Array('#worksautocomplete', '#level05', '#level04', '#level03', '#level02', '#level01', '#level00',
        '#browseto', '#makeanindex', '#textofthis', '#fewerchoices', '#genresautocomplete', '#genreinfo',
        '#genrelistcontents', '#workgenresautocomplete', '#locationsautocomplete', '#provenanceautocomplete',
        '#pickgenre', '#excludegenre', '#setoptions', '#lexica', '#authinfo', '#authorholdings', '#searchlistcontents',
        '#loadslots', '#saveslots', '#endpointbutton-isopen', '#endpointbutton-isclosed', '#fromnotice', '#endpointnotice');
    hidemany(ids);
    $.getJSON('/getselections', function (selectiondata) {
        reloadselections(selectiondata);
    });
}

function resetworksautocomplete(){
    let ids = Array('#level05', '#level04', '#level03', '#level02', '#level01', '#level00',
        '#level05endpoint', '#level04endpoint', '#level03endpoint', '#level02endpoint', '#level01endpoint',
        '#level00endpoint', '#endpointnotice', '#fromnotice', '#authorendpoint', '#workendpoint');
    hidemany(ids);
    clearmany(ids);
}


$('#authorsautocomplete').autocomplete({
    change: reloadAuthorlist(),
    source: "/getauthorhint",
    select: function (event, ui) {
        let thisselector = $('#authorsautocomplete');
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
            auid = thisselector.val().slice(-7, -1);
        } else {
            auid = thisselector.val().slice(-7, -1);
        }
        loadWorklist(auid);
        selector.prop('placeholder', '(Pick a work)');
        let ids = Array('#worksautocomplete', '#makeanindex', '#textofthis', '#browseto', '#authinfo');
        bulkshow(ids);
        $('#authorendpoint').val(thisselector.val());
        }
    });


$('#pickauthor').click( function() {
        let name = $('#authorsautocomplete').val();
        let authorid = name.slice(-7, -1);
        let locus = locusdataloader();
        let endpoint = endpointdataloader();
        let wrk = $('#worksautocomplete').val().slice(-4, -1);
        resetworksautocomplete();
        if (authorid !== '') {
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
             } else if (locus === endpoint){
                $.getJSON('/makeselection?auth=' + authorid + '&work=' + wrk + '&locus=' + locus, function (selectiondata) {
                    reloadselections(selectiondata);
                });
             } else {
                $.getJSON('/makeselection?auth=' + authorid + '&work=' + wrk + '&locus=' + locus + '&endpoint=' + endpoint, function (selectiondata) {
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
        let endpoint = endpointdataloader();
        let wrk = $('#worksautocomplete').val().slice(-4, -1);
        resetworksautocomplete();
        if (authorid !== '') {
            if (wrk === '') {
              $.getJSON('/makeselection?auth=' + authorid+'&exclude=t', function (selectiondata) {
                   reloadselections(selectiondata);
                   loadWorklist(authorid);
                  $('#worksautocomplete').prop('placeholder', '(Pick a work)');
                  });
             } else if (locus === '') {
                $.getJSON('/makeselection?auth=' + authorid + '&work=' + wrk + '&exclude=t', function (selectiondata) {
                    reloadselections(selectiondata);
                });
             } else if (locus === endpoint){
                $.getJSON('/makeselection?auth=' + authorid + '&work=' + wrk + '&locus=' + locus + '&exclude=t', function (selectiondata) {
                    reloadselections(selectiondata);
                });
             } else {
                $.getJSON('/makeselection?auth=' + authorid + '&work=' + wrk + '&locus=' + locus + '&endpoint=' + endpoint + '&exclude=t', function (selectiondata) {
                    reloadselections(selectiondata);
                });
                $('#fromnotice').hide();
                $('#endpointnotice').hide();
                $('#endpointbutton-isclosed').hide();
                $('#endpointbutton-isopen').hide();
            }
        }
        $('#searchlistcontents').hide();
});

//
// WORKS
//

function loadWorklist(authornumber){
    $('#fromnotice').hide();
    $('#endpointnotice').hide();
    $('#endpointbutton-isclosed').hide();
    $('#endpointbutton-isopen').hide();
    $.getJSON('/getworksof/'+authornumber, function (selectiondata) {
        let dLen = selectiondata.length;
        let worksfound = Array();
        selector = $('#worksautocomplete');
        for (let i = 0; i < dLen; i++) { worksfound.push(selectiondata[i]); }
        selector.autocomplete( "enable" );
        selector.autocomplete({ source: worksfound });
    });
}


$('#worksautocomplete').autocomplete({
    focus: function (event, ui) {
        resetworksautocomplete();
        let auth = $("#authorsautocomplete").val().slice(-7, -1);
        let wrk = ui.item.value.slice(-4, -1);
        loadLevellist(auth, wrk,'firstline');
        },
     select: function (event, ui) {
        let thisselector = $('#worksautocomplete');
        $('#workendpoint').val(thisselector.val());
        toggleendpointarrows();
     }
});

function toggleendpointarrows() {
    let isclosed = $('#endpointbutton-isclosed');
    let isopen = $('#endpointbutton-isopen');
    if ( isclosed.is(':hidden') && isopen.is(':hidden')) {
        isclosed.show();
    }
}


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

function endpointdataloader() {
    let l5 = $('#level05endpoint').val();
    let l4 = $('#level04endpoint').val();
    let l3 = $('#level03endpoint').val();
    let l2 = $('#level02endpoint').val();
    let l1 = $('#level01endpoint').val();
    let l0 = $('#level00endpoint').val();
    let lvls = [ l5, l4, l3, l2, l1, l0];
    let locusdata = '';
    for (let i = 0; i < 6; i++ ) {
        if (lvls[i] !== '') { locusdata += lvls[i]+'|' } }
    locusdata = locusdata.slice(0, (locusdata.length)-1);

    return locusdata;
}


function loadLevellist(author, work, pariallocus){
    // python is hoping to be sent something like:
    //
    //  /getstructure/lt1254w001
    //  /getstructure/lt0474w043/3|12
    //
    // bad things happen if you send level00 info
    //
    // python will return info about the next level down such as:
    //  ws =  {'totallevels': 5, 'level': 2, 'label': 'par', 'low': '1', 'high': '10', 'range': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']}

    let getpath = '';
    if ( pariallocus !== 'firstline' ) {
        getpath = author + '/' + work + '/' + pariallocus;
    } else {
        getpath = author + '/' + work;
    }

    let openbutton = $('#endpointbutton-isclosed');
    let closebutton = $('#endpointbutton-isopen');
    let workboxval = $('#worksautocomplete').val();

    $.getJSON('/getstructure/' + getpath, function (selectiondata) {
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
                if (atlevel > 0) {
                    let loc = locusdataloader();
                    loadLevellist(author, work, loc);
                    }
                },
            source: possibilities,
            select: function (event, ui) {
                let loc = locusdataloader();
                loadLevellist(author, work, String(loc));
                if ( atlevel && workboxval && openbutton.is(':hidden') === true && closebutton.is(':hidden') === true) {
                    openbutton.show();
                }
                if (!workboxval) { openbutton.hide(); closebutton.hide(); }
            }});

        let endpointlevel = atlevel+1;
        let endpointbox = '#level0'+String(endpointlevel)+'endpoint';
        let startpointbox = '#level0'+endpointlevel;
        $(endpointbox).val($(startpointbox).val());

        let generateendpoint = '#level0'+String(atlevel)+'endpoint';
        if ( low !== '-9999') { $(generateendpoint).prop('placeholder', '('+label+' '+String(low)+' to '+String(high)+')'); }
        else { $(generateendpoint).prop('placeholder', '(awaiting a valid selection...)'); }
        $(generateendpoint).autocomplete ({
            focus: function (event, ui) {
                if (atlevel > 0) {
                    let loc = endpointdataloader();
                    endpointloadLevellist(author, work, loc);
                    }
                // if we do partialloc browsing then this can be off
                // if (atlevel <= 1) { $('#browseto').show(); }
                },
            source: possibilities,
            select: function (event, ui) {
                // if we do partialloc browsing then this can be off
                // if (atlevel <= 1) { $('#browseto').show(); }
                let loc = endpointdataloader();
                endpointloadLevellist(author, work, String(loc));
            }});
    });
}


function endpointloadLevellist(author, work, pariallocus){
    // python is hoping to be sent something like:
    //
    //  /getstructure/lt1254w001
    //  /getstructure/lt0474w043/3|12
    //
    // bad things happen if you send level00 info
    //
    // python will return info about the next level down such as:
    //  ws =  {'totallevels': 5, 'level': 2, 'label': 'par', 'low': '1', 'high': '10', 'range': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']}

    let getpath = '';
    if ( pariallocus !== 'firstline' ) {
        getpath = author + '/' + work + '/' + pariallocus;
    } else {
        getpath = author + '/' + work;
    }

    $.getJSON('/getstructure/' + getpath, function (selectiondata) {
        let top = selectiondata['totallevels']-1;
        let atlevel = selectiondata['level'];
        let label = selectiondata['label'];
        let low = selectiondata['low'];
        let high = selectiondata['high'];
        let possibilities = selectiondata['range'];

        let generateme = '#level0'+String(atlevel)+'endpoint';

        if ( low !== '-9999') { $(generateme).prop('placeholder', '('+label+' '+String(low)+' to '+String(high)+')'); }
        else { $(generateme).prop('placeholder', '(awaiting a valid selection...)'); }

        $(generateme).show();
        $(generateme).autocomplete ({
            focus: function (event, ui) {
                if (atlevel > 0) {
                    let loc = endpointdataloader();
                    endpointdataloader(author, work, loc);
                    }
                },
            source: possibilities,
            select: function (event, ui) {
                let loc = endpointdataloader();
                endpointdataloader(author, work, String(loc));
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
