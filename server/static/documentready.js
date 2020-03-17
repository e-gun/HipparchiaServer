//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-20
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)

$(document).ready( function () {

    $(document).keydown(function(e) {
        // 27 - escape
        // 38 & 40 - up and down arrow
        // 37 & 39 - forward and back arrow; but the click does not exist until you open a passage browser
        switch(e.which) {
            case 27: $('#browserdialog').hide(); break;
            case 37: $('#browseback').click(); break;
            case 39: $('#browseforward').click(); break;
            }
        });

    $('#clear_button').click( function() { window.location.href = '/resetsession'; });
    $('#alt_clear_button').click( function() { window.location.href = '/resetsession'; });
    $('#vectoralt_clear_button').click( function() { window.location.href = '/resetsession'; });
    $('#helptabs').tabs();
    $('#helpbutton').click( function() {
        if (document.getElementById('Interface').innerHTML === '<!-- placeholder -->') {
            $.getJSON('/loadhelpdata', function (data) {
                let l = data.helpcategories.length;
                for (let i = 0; i < l; i++) {
                    let divname = data.helpcategories[i];
                    if (data[divname].length > 0) {
                        document.getElementById(divname).innerHTML = data[divname];
                        }
                    }
                });
            }
        $('#helptabs').toggle();
        $('#executesearch').toggle();
        $('#extendsearchbutton').toggle();
    });

    $('#extendsearchbutton').click( function() {
        $.getJSON('/getsessionvariables', function (data) {
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
        $('#complexsearching').toggle();
        $('#termonecheckbox').toggle();
        togglemany(vectorcheckboxspans);
        });

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

    function areWeWearchingVectors () {
        let xor = [];
        for (let i = 0; i < vectorboxes.length; i++) {
            let opt = $(vectorboxes[i]);
            if (opt.prop('checked')) { xor.push(1); }
            }
        return xor.length;
    }

    function whichVectorChoice () {
        let xor = [];
        for (let i = 0; i < vectorboxes.length; i++) {
            let opt = $(vectorboxes[i]);
            if (opt.prop('checked')) { xor.push(vectorboxes[i].slice(1)); }
            }
        return xor[0];
    }

    $('#executesearch').click( function(){
        $('#imagearea').empty();
        $('#searchsummary').html('');
        $('#displayresults').html('');

        let pd = $('#pollingdata');
        pd.html('');
        pd.show();

        // the script additions can pile up: so first kill off any scripts we have already added
        let bcsh = document.getElementById("browserclickscriptholder");
        if (bcsh.hasChildNodes()) { bcsh.removeChild(bcsh.firstChild); }

        const terms = {
            'skg': $('#wordsearchform').val(),
            'prx': $('#proximatesearchform').val(),
            'lem': $('#lemmatasearchform').val(),
            'plm': $('#proximatelemmatasearchform').val()
            };
        // disgustingly, if you send 'STRING ' to window.location it strips the whitespace and turns it into 'STRING'
        if (terms['skg'].slice(-1) === ' ') { terms['skg'] = terms['skg'].slice(0,-1) + '%20'; }
        if (terms['prx'].slice(-1) === ' ') { terms['prx'] = terms['prx'].slice(0,-1) + '%20'; }

        let qstringarray = Array();
        for (let t in terms) {
            if (terms[t] !== '') {qstringarray.push(t+'='+terms[t]); }
            }
        let qstring = qstringarray.join('&');

        let searchid = generateId(8);
        let flaskpath = '';
        let url = '';

        // let searchid = uuidv4();

        if (areWeWearchingVectors() === 0) {
            flaskpath = '/executesearch/';
            url = flaskpath + searchid + '?' + qstring;
        } else {
            let lsv = $('#lemmatasearchform').val();
            let vtype = whichVectorChoice();
            if (lsv.length === 0) { lsv = '_'; }
            flaskpath = '/vectors/';
            url = flaskpath + vtype + '/' + searchid + '/' + lsv;
        }

        $.getJSON(url, function (returnedresults) { loadsearchresultsintodisplayresults(returnedresults); });

        checkactivityviawebsocket(searchid);
        });

    function loadsearchresultsintodisplayresults(output) {
        document.title = output['title'];
        $('#searchsummary').html(output['searchsummary']);
        $('#displayresults').html(output['found']);

        //
        // THE GRAPH: if there is one... Note that if it is embedded in the output table, then
        // that table has to be created and  $('#imagearea') with it before you do any of the following
        //

        let imagetarget = $('#imagearea');
        if (typeof output['image'] !== 'undefined' && output['image'] !== '') {
            let w = window.innerWidth * .9;
            let h = window.innerHeight * .9;
            jQuery('<img/>').prependTo(imagetarget).attr({
                src: '/getstoredfigure/' + output['image'],
                alt: '[vector graph]',
                id: 'insertedfigure',
                height: h
            });
        }

        //
        // JS UPDATE
        // [http://stackoverflow.com/questions/9413737/how-to-append-script-script-in-javascript#9413803]
        //

        let browserclickscript = document.createElement('script');
        browserclickscript.innerHTML = output['js'];
        document.getElementById('browserclickscriptholder').appendChild(browserclickscript);
    }

    // setoptions() defined in coreinterfaceclicks.js
    $('#searchlines').click( function(){ setoptions('searchscope', 'lines'); });
    $('#searchwords').click( function(){ setoptions('searchscope', 'words'); });

    $('#wordisnear').click( function(){ setoptions('nearornot', 'near'); });
    $('#wordisnotnear').click( function(){ setoptions('nearornot', 'notnear'); });

    $('#proximityspinner').spinner({
        min: 1,
        value: 1,
        step: 1,
        stop: function( event, ui ) {
            let result = $('#proximityspinner').spinner('value');
            setoptions('proximity', String(result));
            },
        spin: function( event, ui ) {
            let result = $('#proximityspinner').spinner('value');
            setoptions('proximity', String(result));
            }
        });

    $('#browserclose').bind("click", function(){
    		$('#browserdialog').hide();
    		$('#browseback').unbind('click');
    		$('#browseforward').unbind('click');
    		}
		);
	});

loadoptions();

function checkCookie(){
    let c = navigator.cookieEnabled;
    if (!c){
        document.cookie = "testcookie";
        c = document.cookie.indexOf("testcookie")!=-1;
        document.cookie = "testcookie=1; expires=Thu, 01-Jan-1970 00:00:01 GMT";
    }

    if (c) {
        $('#cookiemessage').hide();
    } else {
        $('#cookiemessage').show();
    }
}

checkCookie();

//
// PROGRESS INDICATOR
//

function checkactivityviawebsocket(searchid) {
    $.getJSON('/confirm/'+searchid, function(portnumber) {
        // s = new WebSocket('ws://localhost:'+portnumber+'/');
        // NOTE: according to the above, you will not be able to get progress reports if you are not at localhost
        // that might be something you want to ensure
        // the following is required for remote progress reports
        let pd = $('#pollingdata');
        let ip = location.hostname;
        let s = new WebSocket('ws://'+ip+':'+portnumber+'/');
        let amready = setInterval(function(){
            if (s.readyState === 1) { s.send(JSON.stringify(searchid)); clearInterval(amready); }
            }, 10);
        s.onmessage = function(e){
            let progress = JSON.parse(e.data);
            displayprogress(progress);
            if  (progress['active'] === 'inactive') { pd.html(''); s.close(); s = null; }
            }
    });
}

function displayprogress(progress){
    let r = progress['remaining'];
    let t = progress['total'];
    let h = progress['hits'];
    let pct = Math.round((t-r) / t * 100);
    let m = progress['message'];
    let e = progress['elapsed'];
    let x = progress['extrainfo'];

    let thehtml = '';

    if (t !== -1) {
        thehtml += m + ': <span class="progress">' + pct + '%</span> completed&nbsp;(' + e + 's)';
    } else {
        thehtml += m + '&nbsp;(' + e + 's)';
        }

   if ( h > 0) { thehtml += '<br />(<span class="progress">' + h + '</span> found)'; }

   thehtml += '<br />' + x;

   $('#pollingdata').html(thehtml);
}

hidemany(tohideonfirstload);
togglemany(vectorcheckboxspans);

