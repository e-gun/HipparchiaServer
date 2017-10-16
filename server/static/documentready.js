//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-17
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
    $('#helptabs').tabs();
    $('#helpbutton').click( function() {
        if (document.getElementById('Interface').innerHTML == '<!-- placeholder -->') {
            $.getJSON('/loadhelpdata', function (data) {
                var l = data.helpcategories.length;
                for (i = 0; i < l; i++) {
                    var divname = data.helpcategories[i];
                    if (data[divname].length > 0) {
                        document.getElementById(divname).innerHTML = data[divname];
                        }
                    }
                });
            }
        $('#helptabs').toggle();
        $('#executesearch').toggle();
        $('#extendsearch').toggle();
    });

    $('#extendsearch').click( function() {
        $.getJSON('/getsessionvariables', function (data) {
                $( "#proximityspinner" ).spinner('value', data.proximity);
                if (data.searchscope == 'L') {
                    $('#searchlines').prop('checked', true); $('#searchwords').prop('checked', false);
                } else {
                    $('#searchlines').prop('checked', false); $('#searchwords').prop('checked', true);
                }
                if (data.nearornot == 'T') {
                    $('#wordisnear').prop('checked', true); $('#wordisnotnear').prop('checked', false);
                } else {
                    $('#wordisnear').prop('checked', false); $('#wordisnotnear').prop('checked', true);
                }
                });
        $('#complexsearching').toggle();
        });

    $('#executesearch').click( function(){
        var seeking = $('#wordsearchform').val();
        var proximate = $('#proximatesearchform').val();
        var lemmasearch = $('#lemmatasearchform').val();
        // disgustingly, if you send 'STRING ' to window.location it strips the whitespace and turns it into 'STRING'
        if (seeking.slice(-1) == ' ') { seeking = seeking.slice(0,-1) + '%20'; }
        if (proximate.slice(-1) == ' ') { proximate = proximate.slice(0,-1) + '%20'; }
        $('#searchsummary').html('');
        $('#displayresults').html('');

        // the script additions can pile up: so first kill off any scripts we have already added
        var bcsh = document.getElementById("browserclickscriptholder");
        if (bcsh.hasChildNodes()) { bcsh.removeChild(bcsh.firstChild); }

        var searchid = Date.now();
        var url = '/executesearch/'+searchid+'?s='+seeking+'&p='+proximate+'&l='+lemmasearch;

        $.getJSON(url, function (returnedresults) { loadsearchresultsintodisplayresults(returnedresults); });

        checkactivityviawebsocket(searchid);

        });

    function setoptions(sessionvar,value){
	    $.getJSON('/setsessionvariable?'+sessionvar+'='+value, function (resultdata) {
		 // do nothing special: the return exists but is not relevant
		 // [{"searchsyntax": "R"}]
	    });
        }

    function loadsearchresultsintodisplayresults(output) {
        //  THE DATA YOU RECEIVE
        //
        //		output['title'] = thesearch
        //		output['found'] = findshtml
		//      output['js'] = findsjs
        //		output['resultcount'] = resultcount
        //		output['scope'] = str(len(indexedworklist))
        //		output['searchtime'] = str(searchtime)
        //		output['proximate'] = proximate
        //		output['thesearch'] = thesearch
        //		output['htmlsearch'] = htmlsearch
        //		output['hitmax'] = hitmax
        //      output['onehit'] = session['onehit']
        //		output['icandodates'] = yes/no
        //		output['sortby'] = session['sortorder']
        //		output['dmin'] = dmin
        //		output['dmax'] = dmax

        document.title = output['title'];

        //
        // THE SUMMARY INFORMATION
        //

        var summaryhtml = '';

        summaryhtml += 'Sought '+output['htmlsearch']+'<br />\n';
        if ( output['scope'] != '1') { summaryhtml += 'Searched '+output['scope']+' texts '; } else { summaryhtml += 'Searched 1 text '; }
        summaryhtml += 'and found '+output['resultcount']+' passages';
        summaryhtml += ' ('+output['searchtime']+'s)';
        if (output['icandodates'] == 'yes' ) { if (output['dmin'] != '850 B.C.E.' || output['dmax'] != '1500 C.E.') { summaryhtml += '<br />Searched between '+output['dmin']+' and '+output['dmax']; } }
        if (output['onehit'] == 'yes') { summaryhtml += '<br />Only allowing one match per item searched (either a whole author or a specified work)'; }
        summaryhtml += '<br />Sorted by '+output['sortby'];
        if (output['hitmax'] == 'true') { summaryhtml += '<br />[Search suspended: result cap reached.]';}

        $('#searchsummary').html(summaryhtml);

        //
        // THE FINDS: each find should come as a lump of HTML formated by htmlifysearchfinds()
        //

        $('#displayresults').html(output['found']);

        //
        // JS UPDATE
        // [http://stackoverflow.com/questions/9413737/how-to-append-script-script-in-javascript#9413803]
        //

        var browserclickscript = document.createElement("script");
        browserclickscript.innerHTML = output['js'];
        document.getElementById('browserclickscriptholder').appendChild(browserclickscript);
    }

    $('#searchlines').click( function(){ setoptions('searchscope', 'L'); });
    $('#searchwords').click( function(){ setoptions('searchscope', 'W'); });

    $('#wordisnear').click( function(){ setoptions('nearornot', 'T'); });
    $('#wordisnotnear').click( function(){ setoptions('nearornot', 'F'); });

    $( "#proximityspinner" ).spinner({
        min: 1,
        value: 1,
        step: 1,
        stop: function( event, ui ) {
            var result = $('#proximityspinner').spinner('value');
            setoptions('proximity', String(result));
            },
        spin: function( event, ui ) {
            var result = $('#proximityspinner').spinner('value');
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


    var tohideonfirstload = new Array('#clearpick', '#helptabs', '#edts', '#ldts', '#spur',
        '#browserdialog', '#complexsearching', '#lemmatasearchform', '#proximatelemmatasearchform');
    bulkhider(tohideonfirstload);

    //
    // BULK OPERATIONS ON ARRAYS OF ELEMENTS
    //

    function bulkhider(arrayofelements) {
        for (i = 0; i < arrayofelements.length; i++) {
            $(arrayofelements[i]).hide();
            }
    }

    function bulkshow(arrayofelements) {
        for (i = 0; i < arrayofelements.length; i++) {
            $(arrayofelements[i]).show();
            }
    }

    function bulkclear(arrayofelements) {
        for (i = 0; i < arrayofelements.length; i++) {
            $(arrayofelements[i]).val('');
            }
    }

    //
    // PROGRESS INDICATOR
    //

    function checkactivityviawebsocket(searchid) {
        $.getJSON('/confirm/'+searchid, function(portnumber) {
            // s = new WebSocket('ws://localhost:'+portnumber+'/');
            // NOTE: according to the above, you will not be able to get progress reports if you are not at localhost
            // that might be something you want to ensure
            // the following is required for remote progress reports
            var ip = location.hostname;
            s = new WebSocket('ws://'+ip+':'+portnumber+'/');
            var amready = setInterval(function(){
                if (s.readyState === 1) { s.send(JSON.stringify(searchid)); clearInterval(amready); }
                }, 10);
            s.onmessage = function(e){
                var progress = JSON.parse(e.data);
                displayprogress(progress);
                if  (progress['active'] == 'inactive') { $('#pollingdata').html(''); s.close(); s = null; }
                }
        });
    }

    function displayprogress(progress){
        var r = progress['remaining'];
        var t = progress['total'];
        var h = progress['hits'];
        var pct = Math.round((t-r) / t * 100);
        var done = t - r;
        var m = progress['message']
        var e = progress['elapsed']
        var x = progress['extrainfo']

        var thehtml = ''
        if (t != -1) {
            thehtml += m + ': <span class="progress">' + pct+'%</span> completed ('+e+'s)';
        } else {
            thehtml += m;
            }

       if ( h > 0) { thehtml += '<br />(<span class="progress">'+h+'</span> found)'; }

       thehtml += '<br />'+x

       $('#pollingdata').html(thehtml);
    }

