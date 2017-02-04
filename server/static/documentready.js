//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-17
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)

$(document).ready( function () {

    $(document).keydown(function(e) {
        // forward and back arrow; but the click does not exist until you open a passage browser
        switch(e.which) {
            case 37:  $('#browseback').click(); break;
            case 39: $('#browseforward').click(); break;
            }
        });

    $('#clear_button').click(
        function() {
            window.location.href = '/clear';
        	}
    	);
    $('#clearpick').hide();
    $('#moreinfotabs').hide();
    $('#moreinfotabs').tabs();
    $('#edts').hide();
    $('#ldts').hide();
    $('#spur').hide();

    $('#helpbutton').click( function() { $('#moreinfotabs').toggle(); $('#executesearch').toggle(); $('#extendsearch').toggle(); });

    $('#browserdialog').hide();
    $('#complexsearching').hide();
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
        var proximate = $("#proximatesearchform").val();
        // disgustingly, if you send 'STRING ' to window.location it strips the whitespace and turns it into 'STRING'
        if (seeking.slice(-1) == ' ') { seeking = seeking.slice(0,-1) + '%20'; }
        if (proximate.slice(-1) == ' ') { proximate = proximate.slice(0,-1) + '%20'; }
        $('#searchsummary').html('');
        $('#displayresults').html('');

        // the script additions can pile up: so first kill off any scripts we have already added
        var bcsh = document.getElementById("browserclickscriptholder");
        if (bcsh.hasChildNodes()) { bcsh.removeChild(bcsh.firstChild); }

        var searchid = Date.now();

        if (proximate == '') { var url = '/executesearch?seeking='+seeking+'&id='+searchid; }
        else { var url = '/executesearch?seeking='+seeking+'&proximate='+proximate+'&id='+searchid; }

        $.getJSON(url, function (returnedresults) { loadsearchresultsintodisplayresults(returnedresults); });
        // ws additions start
        // $.getJSON('/progress?id='+searchid);
        // var s = new WebSocket("ws://localhost:9876/");
        // s.onmessage = function(e){ alert("got: " + e.data); }
        // ws additions end
         var i = setInterval(function(){
            $.getJSON('/progress?id='+searchid, function(progress) {
                displayprogress(progress);
                if (progress['active'] == false ) { clearInterval(i); document.getElementById('pollingdata').innerHTML = ''; }
                });
            }, 400);
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
        //		output['found'] = finds
		//      output['js'] = findsjs
        //		output['resultcount'] = resultcount
        //		output['scope'] = str(len(indexedworklist))
        //		output['searchtime'] = str(searchtime)
        //		output['lookedfor'] = seeking
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

        document.getElementById('searchsummary').innerHTML = summaryhtml;

        //
        // THE FINDS: each find should come as a lump of HTML formated by htmlifysearchfinds()
        //

        var dLen = output['found'].length;
        var passagesreturned = '';
        for (i = 0; i < dLen; i++) { passagesreturned += output['found'][i]; }

        document.getElementById('displayresults').innerHTML = passagesreturned;

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
    		$("#browserdialog").hide();
    		$('#browseback').unbind('click');
    		$('#browseforward').unbind('click');
    		}
		);
	});

