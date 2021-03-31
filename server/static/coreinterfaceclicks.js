//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-21
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)

function refreshselections() {
    $.getJSON('/selection/fetch', function (selectiondata) { reloadselections(selectiondata); });
}

function loadoptions() {
    $.getJSON('/get/json/sessionvariables', function (data) {
        // console.log(data);
        const simpletoggles = {
            'authorssummary': $('#authorssummary'),
            'authorflagging': $('#authorflagging'),
            'bracketangled': $('#bracketangled'),
            'bracketcurly': $('#bracketcurly'),
            'bracketround': $('#bracketround'),
            'bracketsquare': $('#bracketsquare'),
            'christiancorpus': $('#christiancorpus'),
            'collapseattic': $('#collapseattic'),
            'cosdistbylineorword': $('#cosdistbylineorword'),
            'cosdistbysentence': $('#cosdistbysentence'),
            'debughtml': $('#debughtml'),
            'debugdb': $('#debugdb'),
            'debuglex': $('#debuglex'),
            'debugparse': $('#debugparse'),
            'greekcorpus': $('#greekcorpus'),
            'incerta': $('#includeincerta'),
            'indexskipsknownwords': $('#indexskipsknownwords'),
            'inscriptioncorpus': $('#inscriptioncorpus'),
            'latincorpus': $('#latincorpus'),
            'morphdialects': $('#morphdialects'),
            'morphduals': $('#morphduals'),
            'morphemptyrows': $('#morphemptyrows'),
            'morphimper': $('#morphimper'),
            'morphinfin': $('#morphinfin'),
            'morphfinite': $('#morphfinite'),
            'morphpcpls': $('#morphpcpls'),
            'morphtables': $('#morphtables'),
            'nearestneighborsquery': $('#nearestneighborsquery'),
            'papyruscorpus': $('#papyruscorpus'),
            'phrasesummary': $('#phrasesummary'),
            'principleparts': $('#principleparts'),
            'quotesummary': $('#quotesummary'),
            'searchinsidemarkup': $('#searchinsidemarkup'),
            'semanticvectorquery': $('#semanticvectorquery'),
            'sensesummary': $('#sensesummary'),
            'sentencesimilarity': $('#sentencesimilarity'),
            'showwordcounts': $('#showwordcounts'),
            'simpletextoutput': $('#simpletextoutput'),
            'spuria': $('#includespuria'),
            'suppresscolors': $('#suppresscolors'),
            'tensorflowgraph': $('#tensorflowgraph'),
            'topicmodel': $('#topicmodel'),
            'varia': $('#includevaria'),
            'zaplunates': $('#zaplunates'),
            'zapvees': $('#zapvees'),
        };

        Object.keys(simpletoggles).forEach(function(key) {
            if (data[key] === 'yes') {
                simpletoggles[key].prop('checked', true);
            } else {
                simpletoggles[key].prop('checked', false);
            }
        });

        const sidebaricontoggles = {
            'greekcorpus': {'t': $('#grkisactive'), 'f': $('#grkisnotactive')},
            'latincorpus': {'t': $('#latisactive'), 'f': $('#latisnotactive')},
            'inscriptioncorpus': {'t': $('#insisactive'), 'f': $('#insnotisactive')},
            'papyruscorpus': {'t': $('#ddpisactive'), 'f': $('#ddpnotisactive')},
            'christiancorpus': {'t': $('#chrisactive'), 'f': $('#chrnotisactive')},
            'spuria': {'t': $('#spuriaistrue'), 'f': $('#spuriaisfalse')},
            'varia': {'t': $('#variaistrue'), 'f': $('#variaisfalse')},
            'incerta': {'t': $('#undatedistrue'), 'f': $('#undatedisfalse')}
        };

        Object.keys(sidebaricontoggles).forEach(function(key) {
            if (data[key] === 'yes') {
                sidebaricontoggles[key]['t'].show();
                sidebaricontoggles[key]['f'].hide();
            } else {
                sidebaricontoggles[key]['t'].hide();
                sidebaricontoggles[key]['f'].show();
            }
        });

        const xoredtoggles = {
            'onehit': {'y': $('#onehit_y'), 'n': $('#onehit_n'), 'f': $('#onehitisfalse'), 't': $('#onehitistrue')},
            'headwordindexing': {'y': $('#headwordindexing_y'), 'n': $('#headwordindexing_n'), 'f': $('#headwordindexinginactive'), 't': $('#headwordindexingactive')},
            'indexbyfrequency': {'y': $('#frequencyindexing_y'), 'n': $('#frequencyindexing_n'), 'f': $('#frequencyindexinginactive'), 't': $('#frequencyindexingactive')},
            'rawinputstyle': {'y': $('#manualinput'), 'n': $('#autofillinput'), 'f': $('#usingautoinput'), 't': $('#usingrawinput')},
        };

        Object.keys(xoredtoggles).forEach(function(key) {
            if (data[key] === 'yes') {
                xoredtoggles[key]['y'].prop('checked', true);
                xoredtoggles[key]['n'].prop('checked', false);
                xoredtoggles[key]['t'].show();
                xoredtoggles[key]['f'].hide();
            } else {
                xoredtoggles[key]['n'].prop('checked', true);
                xoredtoggles[key]['y'].prop('checked', false);
                xoredtoggles[key]['f'].show();
                xoredtoggles[key]['t'].hide();
            }
        });

        const baggingmethods =  {
            // be careful about 'winnertakeall' vs 'winnerstakeall', etc.
            //
            'alternates': $('#alternatebagbutton'),
            'flat': $('#flatbagbutton'),
            'winnertakesall': $('#winnertakesallbutton'),
            'unlemmatized': $('#unlemmatizedbutton'),
        };

        const baggingbuttons =  {
            'alternates': $('#alternates-ison'),
            'flat': $('#flatlemma-ison'),
            'winnertakesall': $('#winnertakesall-ison'),
            'unlemmatized': $('#unlemmatized-ison'),
        };

        Object.keys(baggingmethods).forEach(function(returnedkey) {
            if (data.baggingmethod !== returnedkey) {
                baggingmethods[returnedkey].prop('checked', false);
                baggingbuttons[returnedkey].hide();
            } else {
                baggingmethods[returnedkey].prop('checked', true);
                baggingbuttons[returnedkey].show();
            }
        });

        const trimmingoptions =  {
            'none': $('#trimming-none'),
            'declined': $('#trimming-declined'),
            'conjugated': $('#trimming-conjugated'),
        };

        Object.keys(trimmingoptions).forEach(function(returnedkey) {
            if (data.trimvectoryby !== returnedkey) {
                trimmingoptions[returnedkey].prop('checked', false);
            } else {
                trimmingoptions[returnedkey].prop('checked', true);
            }
        });

        let setspinnervalues = {
            'earliestdate': $('#earliestdate'),
            'latestdate': $('#latestdate'),
            'linesofcontext': $('#linesofcontextspinner'),
            'maxresults': $('#hitlimitspinner'),
            'browsercontext': $('#browserspinner')
        };

        Object.keys(setspinnervalues).forEach(function(key) {
            setspinnervalues[key].spinner('value', data[key]);
        });

        $('#sortresults').val(data.sortorder);
        $('#sortresults').selectmenu('refresh');

        $('#fontchoice').val(data.fontchoice);
        $('#fontchoice').selectmenu('refresh');

        if(data['principleparts'] === 'yes') { $('#mophologytablesoptions').show(); } else { $('#mophologytablesoptions').hide(); }

        if (data.nearestneighborsquery === 'yes' || data.analogyfinder === 'yes') {
            $('#trimmingcheckboxes').show();
        } else {
            $('#trimmingcheckboxes').hide();
        }

        if (data.cosdistbysentence === 'yes' || data.cosdistbylineorword === 'yes' || data.semanticvectorquery === 'yes' ||
            data.nearestneighborsquery === 'yes' || data.tensorflowgraph === 'yes' || data.sentencesimilarity === 'yes' ||
            data.topicmodel === 'yes' || data.analogyfinder === 'yes') {
            showextendedsearch();
            }
        });
}


// UPPER LEFT OPTIONS PANEL CLICKS

function openoptionsslider() {
    let windowWidth = $(window).width();
    let w = Math.min(windowWidth*.30, 250);
    document.getElementById("setoptionsnavigator").style.width = w+"px";
    document.getElementById("vectoroptionsetter").style.width = "0";
    document.getElementById("mainbody").style.marginLeft = w+"px";
    $('#alt_upperleftbuttons').show();
    $('#vector_upperleftbuttons').hide();
    $('#upperleftbuttons').hide();
}

function closeoptionsslider() {
    document.getElementById("setoptionsnavigator").style.width = "0";
    document.getElementById("vectoroptionsetter").style.width = "0";
    document.getElementById("mainbody").style.marginLeft = "0";
    $('#alt_upperleftbuttons').hide();
    $('#vector_upperleftbuttons').hide();
    $('#upperleftbuttons').show();
}

function openvectoroptionsslider() {
    let windowWidth = $(window).width();
    let w = Math.min(windowWidth*.30, 250);
    document.getElementById("setoptionsnavigator").style.width = "0";
    document.getElementById("vectoroptionsetter").style.width = w+"px";
    document.getElementById("mainbody").style.marginLeft = w+"px";
    $('#alt_upperleftbuttons').hide();
    $('#vector_upperleftbuttons').show();
    $('#upperleftbuttons').hide();
}

$('#openoptionsbutton').click(function(){
    loadoptions();
    openoptionsslider();
});

$('#vectoralt_openoptionsbutton').click(function(){
    loadoptions();
    openoptionsslider();
});

$('#closeoptionsbutton').click(function(){
    closeoptionsslider();
});

$('#close_vector_options_button').click(function(){
    closeoptionsslider();
});

$('#vector_options_button').click(function(){
    loadoptions();
    loadvectorspinners();
    openvectoroptionsslider();
});

$('#alt_vector_options_button').click(function(){
    loadoptions();
    loadvectorspinners();
    openvectoroptionsslider();
});

// BROWSER CLICKS

function generateautofilllocationstring(){
    let l5 = $('#level05').val();
    let l4 = $('#level04').val();
    let l3 = $('#level03').val();
    let l2 = $('#level02').val();
    let l1 = $('#level01').val();
    let l0 = $('#level00').val();
    let lvls = [ l5, l4, l3, l2, l1, l0];
    let loc = Array();
    for (let i = 5; i > -1; i-- ) {
        if (lvls[i] !== '') {
            loc.push(lvls[i]);
        } else {
            if (i === 5) {
                loc.push('_0');
                }
            }
        }
    loc.reverse();
    return loc.join('|');
}

function browsetopassage() {
    let auth = $('#authorsautocomplete').val().slice(-7, -1);
    let wrk = $('#worksautocomplete').val().slice(-4, -1);

    if ($('#autofillinput').is(':checked')) {
        // you are using the autofill boxes
        let locstring = generateautofilllocationstring();
        if (wrk.length !== 3) { wrk = '_firstwork'}
        let loc = 'locus/' + auth + '/' + wrk + '/' +locstring.slice(0, locstring.length);
        browseuponclick(loc);
    } else {
        // you are using rawentry
        let rawlocus = $('#rawlocationinput').val();
        let loc = String();
        if (wrk.length !== 3) { wrk = '_firstwork'}
        if (rawlocus === '') {
            loc = auth + '/' + wrk;
        } else {
            loc = auth + '/' + wrk + '/' + rawlocus;
        }
        rawlocusbrowseuponclick(loc);
    }
}

$('#browseto').click(function(){
    hidemany(endpointbuttons);
    browsetopassage();
});

$('#addtolist').click(function(){ addtosearchlist(); });

$('#fewerchoicesbutton').click(function(){
    $('#morechoicesbutton').show();
    $('#fewerchoicesbutton').hide();
    let ids = Array('#fewerchoices', '#genresautocomplete', '#workgenresautocomplete', '#locationsautocomplete',
        '#provenanceautocomplete', '#pickgenre', '#excludegenre', '#genreinfo', '#genrelistcontents', '#edts',
        '#ldts', '#spuriacheckboxes');
    hidemany(ids);
    });

$('#morechoicesbutton').click(function(){
    $('#morechoicesbutton').hide();
    $('#fewerchoicesbutton').show();
    const ids = Array('#fewerchoices', '#genresautocomplete', '#workgenresautocomplete', '#locationsautocomplete',
        '#provenanceautocomplete', '#pickgenre', '#excludegenre', '#genreinfo', '#edts', '#ldts', '#spuriacheckboxes');
    // showmany(ids);
    let toshow = Array().concat(categoryautofills, extrasearchcriteria, genreselectbuttons);
    showmany(toshow);
    loadoptions();
    });

function showextendedsearch() {
        let ids = Array('#cosinedistancesentencecheckbox', '#cosinedistancelineorwordcheckbox', '#semanticvectorquerycheckbox',
            '#semanticvectornnquerycheckbox', '#tensorflowgraphcheckbox', '#sentencesimilaritycheckbox', '#complexsearching', '#topicmodelcheckbox',
            '#analogiescheckbox');
        showmany(ids);
        }

$('#moretools').click(function(){ $('#lexica').toggle(); });
$('#alt_moretools').click(function(){ $('#lexica').toggle(); });
$('#vectoralt_moretools').click(function(){ $('#lexica').toggle(); });

// not working as expected
// supposed to clear out the other boxes and restore the placeholder; only clears the boxes

//$('#parser').on('focus', function() {
//    var $rl = $('#reverselexicon');
//    var $lx = $('#lexicon');
//    $rl.val(''); $rl.removeAttr("value"); $rl.attr('placeholder', '(English to Greek or Latin)');
//    $lx.val(''); $lx.removeAttr("value"); $lx.attr('placeholder', '(Dictionary Search)');
//    });
//
//$('#reverselexicon').on('focus', function() {
//    var $pp = $('#parser');
//    var $lx = $('#lexicon');
//    $pp.val(''); $pp.removeAttr("value"); $pp.attr('placeholder', '(Morphology Search)');
//    $lx.val(''); $lx.removeAttr("value"); $lx.attr('placeholder', '(Dictionary Search)');
//    });
//
//$('#lexicon').on('focus', function() {
//    var $rl = $('#reverselexicon');
//    var $lx = $('#lexicon');
//    $rl.val(''); $rl.removeAttr("value"); $rl.attr('placeholder', '(English to Greek or Latin)');
//    $lx.val(''); $lx.removeAttr("value"); $lx.attr('placeholder', '(Dictionary Search)');
//    });

$('#lexicalsearch').click(function(){
    // note that modifications to this script should be kept in sync with dictionaryentryjs() in jsformatting.py
    let dictterm = $('#lexicon').val();
    let restoreme = dictterm;
    // trailing space will be lost unless you do this: ' gladiator ' --> ' gladiator' and so you can't spearch for only that word...
    if (dictterm.slice(-1) === ' ') { dictterm = dictterm.slice(0, -1) + '%20'; }
    let parseterm = $('#parser').val();
    let reverseterm = $('#reverselexicon').val();
    let windowWidth = $(window).width();
    let windowHeight = $(window).height();
    let searchterm = '';
    let url = '';
    let dialogtitle = '';
    let mydictfield = '';

    // if you have toggled any of the boxes off, then $('#parser').val(), etc. will be 'undefined'
    if ( typeof dictterm !== 'undefined' && dictterm.length > 0) {
        searchterm = dictterm;
        url = '/dictsearch/';
        dialogtitle = restoreme;
        mydictfield = '#lexicon';
    } else if ( typeof parseterm !== 'undefined' && parseterm.length > 0 ) {
        searchterm = parseterm;
        url = '/parse/';
        dialogtitle = searchterm;
        mydictfield = '#parser';
        restoreme = searchterm;
    } else if ( typeof reverseterm !== 'undefined' && reverseterm.length > 0 ) {
        $('#searchsummary').html('');
        let pd = $('#pollingdata');
        pd.html('');
        pd.show();
        let searchid = generateId(8);
        checkactivityviawebsocket(searchid);
        let originalterm = reverseterm;
        // disgustingly, if you send 'STRING ' to window.location it strips the whitespace and turns it into 'STRING'
        if (reverseterm.slice(-1) === ' ') { reverseterm = reverseterm.slice(0, -1) + '%20'; }
        searchterm = reverseterm;
        url = '/reverselookup/' + searchid + '/';
        dialogtitle = originalterm;
        mydictfield = '#reverselexicon';
        restoreme = searchterm;
    } else {
        searchterm = 'nihil';
        url = '/dictsearch/';
        dialogtitle = searchterm;
    }

    $(mydictfield).val('[Working on it...]');
    $.getJSON(url + searchterm, function (definitionreturned) {
        let ldt = $('#lexicadialogtext');
        let jshld = $('#lexicaljsscriptholder');
        ldt.dialog({
            closeOnEscape: true,
            autoOpen: false,
            maxHeight: windowHeight*.9,
            maxWidth: windowHeight*.9,
            minWidth: windowHeight*.33,
            position: { my: "left top", at: "left top", of: window },
            title: dialogtitle,
            draggable: true,
            icons: { primary: 'ui-icon-close' },
            click: function() { $( this ).dialog( 'close' ); }
            });
            ldt.dialog( 'open' );
            ldt.html(definitionreturned['newhtml']);
            jshld.html(definitionreturned['newjs']);
            $(mydictfield).val(restoreme);
        });
    });

///
/// selectmenu
///

$('#sortresults').selectmenu({ width: 120});

$(function() {
        $('#sortresults').selectmenu({
            change: function() {
                let result = $('#sortresults').val();
                setoptions('sortorder', String(result));
            }
        });
});


$('#fontchoice').selectmenu({ width: 120});
$(function() {
        $('#fontchoice').selectmenu({
            change: function() {
                let result = $('#fontchoice').val();
                setoptions('fontchoice', String(result));
                window.location.reload();
            }
        });
});

//
// info
//

$('#authinfobutton').click(function(){
        $('#authorholdings').toggle();
        let authorid = $('#authorsautocomplete').val().slice(-7, -1);
        $.getJSON('/get/json/authorinfo/' + authorid, function (selectiondata) {
                $('#authorholdings').html(selectiondata);
                 });
    });


$('#searchinfo').click(function(){
        let slc = $('#searchlistcontents');
        if ( slc.is(':visible') === true ) {
            slc.hide();
            slc.html('<p class="center"><span class="small>(this might take a second...)</span></p>');
        } else {
            slc.html('');
            slc.show();
            $.getJSON('/get/json/searchlistcontents', function (selectiondata) {
                slc.html(selectiondata);
                });
            }
    });


$('#genreinfo').click(function(){
        $('#genrelistcontents').toggle();
        $.getJSON('/get/json/genrelistcontents', function (selectiondata) {
                document.getElementById('genrelistcontents').innerHTML = selectiondata;
                });
    });

//
// ENDPOINT UI CLICKS
//

$('#rawlocationinput').click(function () {
    toggleendpointarrows();
});

$('#endpointbutton-isclosed').click(function(){
    // go from invisible to visible
    let aep = $('#authorendpoint');
    let aac = $('#authorsautocomplete');
    aep.val(aac.val());
    showmany(['#selectionendpoint']);
    showmany(endpointnotices);
    $('#endpointbutton-isopen').show();
    $('#endpointbutton-isclosed').hide();
     if ($('#autofillinput').is(':checked')) {
        let levellist = ['00', '01', '02', '03', '04', '05'];
        let author = aac.val().slice(-7, -1);
        let work = $('#worksautocomplete').val().slice(-4, -1);
        let getpath = author + '/' + work;
        $.getJSON('/get/json/workstructure/' + getpath, function (selectiondata) {
            let lvls = selectiondata['totallevels'];
            for (var i = 0; i < lvls; i++) {
                if ($('#level' + levellist[i]).is(':visible')) {
                    $('#level' + levellist[i] + 'endpoint').show();
                }
            }
        });
    } else {
         showmany(['#rawendpointinput']);
    }
    });

$('#endpointbutton-isopen').click(function(){
    $('#endpointbutton-isclosed').show();
    $('#endpointbutton-isopen').hide();
    hidemany(['#selectionendpoint']);
    });


//
// COMPLEX SEARCH BUTTONS (the clicks are in documentready.js; the code is here
//

function closeextendedsearcharea() {
    $('#extendsearchbutton-ispresentlyopen').hide();
    $('#extendsearchbutton-ispresentlyclosed').show();
    $('#complexsearching').hide();
    let lsf = $('#lemmatasearchform');
    let wsf = $('#wordsearchform');
    let tcb = $('#termonecheckbox');
    if ($('#termoneisalemma').is(":checked")) {
        tcb.show();
        lsf.show();
        lsf.attr('placeholder', '(all forms of...)');
        wsf.hide();
    } else {
        tcb.hide();
        lsf.hide();
        wsf.show();
    }
    $('#termtwocheckbox').hide();
    // reset vectors
    // the checkbox names can be found via
    for (let i = 0; i < vectoroptionarray.length; i++) {
        let item = $('#'+ vectoroptionarray[i] +'');
        if (item.prop('checked') ) {
            setoptions(vectoroptionarray[i], 'no');
            item.prop('checked', false);
        }
    }
    $('#vectorizing-ison').hide();
    $('#vectorizing-isoff').show();
    hidemany(vectorcheckboxspans);
}

function openextendedsearcharea() {
    $('#extendsearchbutton-ispresentlyclosed').hide();
    $('#extendsearchbutton-ispresentlyopen').show();
    $.getJSON('/get/json/sessionvariables', function (data) {
            $( "#proximityspinner" ).spinner('value', data.proximity);
            if (data.searchscope === 'lines') {
                $('#searchlines').prop('checked', true); $('#searchwords').prop('checked', false);
            } else {
                $('#searchlines').prop('checked', false); $('#searchwords').prop('checked', true);
            }
            if (data.nearornot === 'near') {
                $('#wordisnear').prop('checked', true); $('#wordisnotnear').prop('checked', false);
            } else {
                $('#wordisnear').prop('checked', false); $('#wordisnotnear').prop('checked', true);
            }
            });
    $('#complexsearching').show();
    $('#termonecheckbox').show();
    $('#termtwocheckbox').show();
    showmany(vectorcheckboxspans);
}



