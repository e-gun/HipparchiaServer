//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-20
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)

//
// vector spinners
//

function loadvectorspinners() {
    $.getJSON('/getvectorranges', function (vsdata) {
        let bcsh = document.getElementById("vectorspinnerscriptholder");
        if (bcsh.hasChildNodes()) {
            bcsh.removeChild(bcsh.firstChild);
        }
        $('#vectorspinnerscriptholder').html(vsdata);
    });
}

//
// vector checkboxes in main page body
//

const thesearchforms = ['#wordsearchform', '#lemmatasearchform', '#proximatesearchform', '#proximatelemmatasearchform'];
const wsf = $('#wordsearchform');
const lsf = $('#lemmatasearchform');
const plsf = $('#proximatelemmatasearchform');
const psf = $('#proximatesearchform');
const trmonelem = $('#termoneisalemma');
const trmtwolem = $('#termtwoisalemma');
const vschon = $('#vectorizing-ison');
const vschoff  = $('#vectorizing-isoff');
const lschon = $('#lemmatizing-ison');
const lschoff= $('#lemmatizing-isoff');

function clearsearchboxvalues() {
    for (let i = 0; i < thesearchforms.length; i++) {
        let box = $(thesearchforms[i]);
        box.val('');
    }
}

function restoreplaceholders() {
    wsf.attr('placeholder', '(looking for...)');
    psf.attr('placeholder', '(near... and within...)');
    lsf.attr('placeholder', '(all forms of...)');
    plsf.attr('placeholder', '(near all forms of... and within...)');
    clearsearchboxvalues();
}

function hideallboxes() {
    for (let i = 0; i < thesearchforms.length; i++) {
        let box = $(thesearchforms[i]);
        box.hide();
    }
}

function findotheroptions(thisoption) {
    const xoredoptions = ['#cosdistbysentence', '#cosdistbylineorword', '#semanticvectorquery', '#nearestneighborsquery', '#tensorflowgraph',
        '#sentencesimilarity', '#topicmodel', '#analogiescheckbox'];
    return xorfinder(thisoption, xoredoptions);
}

function xorbaggingoptions(thisoption) {
    const xoredoptions = ['#flatbagbutton', '#alternatebagbutton', '#winnertakesallbutton', '#unlemmatizedbutton'];
    return xorfinder(thisoption, xoredoptions);
}

function xorfinder(thisoption, xoredoptions){
    let xor = Array();
    for (let i = 0; i < xoredoptions.length; i++) {
        let opt = $(xoredoptions[i]);
        if (opt.attr('id') !== thisoption) {
            xor.push(xoredoptions[i]);
        }
    }
    xor = xor.join(',');
    return xor;
}

function activatethisbox(toactivate, placeholder) {
    toactivate.show();
    toactivate.val('');
    toactivate.attr('placeholder', placeholder);
}

function displayvectorsandlemmata() {
    vschon.show();
    vschoff.hide();
    lschon.show();
    lschoff.hide();
}

function hidevectorsandlemmata() {
    vschon.hide();
    vschoff.show();
    lschon.hide();
    lschoff.show();
}

function hidevectornotification() {
    vschon.hide();
    vschoff.show();
}

function showvectornotification() {
    vschon.show();
    vschoff.hide();
}

function hidelemmatanotification() {
    lschon.hide();
    lschoff.show();
}

function showlemmatanotification() {
    lschon.show();
    lschoff.hide();
}

function restorecheckboxestodefault() {
    console.log('restorecheckboxestodefault');
    trmonelem.prop('checked', false);
    trmtwolem.prop('checked', false);
    hidelemmatanotification();
    restoreplaceholders();
    hidevectornotification();
    wsf.show();
    psf.show();
    lsf.hide();
    plsf.hide();
}

// match sessionfunctions.py
// 	baggingmethods = [
// 		'alternates',
// 		'flat',
// 		'winnertakesall' ]

$('#alternatebagbutton').change(function() {
    let myname = 'alternates';
    if(this.checked) {
        let others = xorbaggingoptions(this.id);
        $(others).prop('checked', false);
        setoptions('baggingmethod', myname);
    } else {
        setoptions('baggingmethod', 'resettodefault');
        }
    });

$('#flatbagbutton').change(function() {
    let myname = 'flat';
    if(this.checked) {
        let others = xorbaggingoptions(this.id);
        $(others).prop('checked', false);
        setoptions('baggingmethod', myname);
    } else {
        setoptions('baggingmethod', 'resettodefault');
        }
    });

$('#unlemmatizedbutton').change(function() {
    let myname = 'unlemmatized';
    if(this.checked) {
        let others = xorbaggingoptions(this.id);
        $(others).prop('checked', false);
        setoptions('baggingmethod', myname);
    } else {
        setoptions('baggingmethod', 'resettodefault');
        }
    });

$('#winnertakesallbutton').change(function() {
    let myname = 'winnertakesall';
    if(this.checked) {
        let others = xorbaggingoptions(this.id);
        $(others).prop('checked', false);
        setoptions('baggingmethod', myname);
    } else {
        setoptions('baggingmethod', 'resettodefault');
        }
    });


$('#cosdistbysentence').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        activatethisbox(lsf, '(pick a headword)');
        activatethisbox(plsf, '(unused for this type of query)');
        trmtwolem.prop('checked', false);
        wsf.hide();
        psf.hide();
        displayvectorsandlemmata();
        trmonelem.prop('checked', true);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#cosdistbylineorword').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        activatethisbox(lsf, '(pick a headword)');
        activatethisbox(plsf, '(unused for this type of query)');
        trmtwolem.prop('checked', false);
        wsf.hide();
        psf.hide();
        displayvectorsandlemmata();
        trmonelem.prop('checked', true);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#semanticvectorquery').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        wsf.show();
        wsf.attr('placeholder', '(enter a word or phrase)');
        $('#lemmatasearchform').hide();
        $('#proximatelemmatasearchform').attr('placeholder', '(unused for this type of query)');
        $('#proximatesearchform').attr('placeholder', '(unused for this type of query)');
        trmonelem.prop('checked', false);
        trmtwolem.prop('checked', false);
        hidelemmatanotification();
        showvectornotification();
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#nearestneighborsquery').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        $('#complexsearching').show();
        activatethisbox(lsf, '(pick a headword)');
        activatethisbox(plsf, '(unused for nearest neighbors)');
        wsf.hide();
        psf.hide();
        displayvectorsandlemmata();
        trmonelem.prop('checked', true);
        trmtwolem.prop('checked', false);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#tensorflowgraph').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        $('#complexsearching').show();
        activatethisbox(lsf, '(unused for tensorflow graph)');
        activatethisbox(plsf, '(unused for tensorflow graph)');
        wsf.hide();
        psf.hide();
        hidelemmatanotification();
        showvectornotification();
        trmonelem.prop('checked', false);
        trmtwolem.prop('checked', false);
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#sentencesimilarity').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        $('#complexsearching').show();
        activatethisbox(lsf, '(unused for sentences similarity)');
        activatethisbox(plsf, '(unused for sentences similarity)');
        trmonelem.prop('checked', false);
        trmtwolem.prop('checked', false);
        wsf.hide();
        psf.hide();
        hidelemmatanotification();
        showvectornotification();
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#topicmodel').change(function() {
    restoreplaceholders();
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        $('#complexsearching').show();
        activatethisbox(lsf, '(unused for topic models)');
        activatethisbox(plsf, '(unused for topic models)');
        trmonelem.prop('checked', false);
        trmtwolem.prop('checked', false);
        hidemany([wsf, psf, vschoff]);
        vschon.show();
        hidelemmatanotification();
        showvectornotification();
        setoptions(this.id, 'yes');
    } else {
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#analogyfinder').change(function() {
    restoreplaceholders();
    let aia = $('#analogiesinputarea');
    if(this.checked) {
        let others = findotheroptions(this.id);
        $(others).prop('checked', false);
        aia.show();
        // $('#analogiesbox').show();
        activatethisbox(lsf, '(unused for analogies)');
        activatethisbox(plsf, '(unused for analogies)');
        trmonelem.prop('checked', false);
        trmtwolem.prop('checked', false);
        hidemany([wsf, psf, vschoff]);
        vschon.show();
        hidelemmatanotification();
        showvectornotification();
        setoptions(this.id, 'yes');
    } else {
        aia.hide();
        // $('#analogiesbox').hide();
        setoptions(this.id, 'no');
        restorecheckboxestodefault();
        hidevectorsandlemmata();
        }
    });

$('#executeanalogysearch').click(function() {
    let A = $('#analogiesinputA').val();
    let B = $('#analogiesinputB').val();
    let C = $('#analogiesinputC').val();
    let searchid = generateId(8);
    // @hipparchia.route('/vectoranalogies/<searchid>/<termone>/<termtwo>/<termthree>')
    let url = `/vectoranalogies/${searchid}/${A}/${B}/${C}`;
    $.getJSON(url, function (returnedresults) { loadanalogyresults(returnedresults); });
    checkactivityviawebsocket(searchid);
});

function loadanalogyresults(outputdata) {
    let targetarea = $('#analogiesresults');
    targetarea.html(outputdata['found']);
    // console.log(outputdata);
}



trmonelem.change(function() {
    if(this.checked) {
        wsf.hide();
        wsf.val('');
        lsf.show();
        showlemmatanotification();
        } else {
        lsf.hide();
        lsf.val('');
        wsf.show();
        if(!trmtwolem.is(':checked')) {
            hidelemmatanotification();
            }
        }
    });

trmtwolem.change(function() {
    if(this.checked) {
        psf.hide();
        psf.val('');
        plsf.show();
        showlemmatanotification();
        } else {
        plsf.hide();
        plsf.val('');
        psf.show();
        if(!trmonelem.is(':checked')) {
            hidelemmatanotification();
            }
        }
    });
