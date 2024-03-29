# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-22
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from os import name as osname


def insertbrowserclickjs(tagname: str) -> str:
	"""
	the clickable urls don't work without inserting new js into the page to catch the clicks
	need to match the what we used to get via the flask template

	:return:
	"""

	jstemplate = """
	
	// Chromium can send poll data after the search is done... 
	$('#pollingdata').hide();
	
	$('%s').click( function() {
		$.getJSON('/browse/'+this.id, function (passagereturned) {
			$('#browseforward').unbind('click');
			$('#browseback').unbind('click');
			var fb = parsepassagereturned(passagereturned)
			// left and right arrow keys
			$('#browserdialogtext').keydown(function(e) {
				switch(e.which) {
					case 37: browseuponclick(fb[1]); break;
					case 39: browseuponclick(fb[0]); break;
				}
			});
			$('#browseforward').bind('click', function(){ browseuponclick(fb[0]); });
			$('#browseback').bind('click', function(){ browseuponclick(fb[1]); });
		});
	});
	"""

	js = jstemplate % tagname

	return js


def insertlexicalbrowserjs() -> str:
	"""

	supplement the html with some js that can see the new objects

	:param htmlentry:
	:return:
	"""
	tagname = 'bibl'
	jstemplate = insertbrowserclickjs(tagname)
	js = """
	<script>
		{jst}
	</script>
	"""

	newjs = js.format(jst=jstemplate)

	return newjs


def generatevectorjs() -> str:
	"""

	this JS is mainly a copy of material from documentready.js

	the click target is going to be:
		@hipparchia.route('/vectors/<vectortype>/<searchid>/<headform>')
		def vectorsearch(vectortype, searchid, headform):

	:param path:
	:return:
	"""

	jstemplate = """
	
		function whichVectorChoice () {
			let xor = [];
			for (let i = 0; i < vectorboxes.length; i++) {
				let opt = $(vectorboxes[i]);
				if (opt.prop('checked')) { xor.push(vectorboxes[i].slice(1)); }
				}
			return xor[0];
		}

		$('lemmaheadword').click( function(e) { 
			var searchid = generateId(8);
			flaskpath = '/vectors/';
			let vchoice = whichVectorChoice();
			url = '/vectors/' + vchoice + '/' + searchid + '/' + this.id;
			$('#imagearea').empty();
			$('#searchsummary').html(''); 
			$('#displayresults').html('');
			$('#wordsearchform').hide();
			$('#lemmatasearchform').show();
			$('#lemmatasearchform').val(this.id);
			$('#lexicon').val(' '+this.id+' ');
			var w = window.innerWidth * .9;
			var h = window.innerHeight * .9;
			$.getJSON(url, function (output) { 
				document.title = output['title'];
				
				$('#searchsummary').html(output['searchsummary']);
				
				$('#displayresults').html(output['found']);
				
				//
				// THE GRAPH: if there is one... Note that if it is embedded in the output table, then
				// that table has to be created and  $('#imagearea') with it before you do any of the following
				//
				
				var imagetarget = $('#imagearea');
				if (typeof output['image'] !== 'undefined' && output['image'] !== '') {
					var w = window.innerWidth * .9;
					var h = window.innerHeight * .9;
					jQuery('<img/>').prependTo(imagetarget).attr({
						src: '/get/response/vectorfigure/' + output['image'],
						alt: '[vector graph]',
						id: 'insertedfigure',
						height: h
					});
				}
								
					var browserclickscript = document.createElement("script");
					browserclickscript.innerHTML = output['js'];
					document.getElementById('browserclickscriptholder').appendChild(browserclickscript);
				});		

			$.getJSON('/search/confirm/'+searchid, function(portnumber) {
			var ip = location.hostname;
			var s = new WebSocket('ws://'+ip+':'+portnumber+'/');
			var amready = setInterval(function(){ if (s.readyState === 1) { s.send(JSON.stringify(searchid)); clearInterval(amready); } }, 10);
			s.onmessage = function(e){
				var progress = JSON.parse(e.data);
				displayprogress(progress);
				if  (progress['active'] === 'inactive') { $('#pollingdata').html(''); s.close(); s = null; }
				}
			});
		});
	"""

	return jstemplate


def supplementalvocablistjs() -> str:
	"""

	vocab list version

	note that 'vocablocation' is not currently used/useful

	:return:
	"""

	return observedformjs('vocabobserved', 'vocablocation')


def supplementalindexjs() -> str:
	"""

	indexmaker version

	:return:
	"""

	return observedformjs('indexobserved', 'indexedlocation')


def observedformjs(clickone, clicktwo) -> str:
	"""

	insert a js block to handle observed forms

	:return:
	"""

	js = """
		<script>
			$('CLICKONE').click( function(e) {
				e.preventDefault();
				var windowWidth = $(window).width();
				var windowHeight = $(window).height();
				$( '#lexicadialogtext' ).dialog({
					closeOnEscape: true, 
					autoOpen: false,
					minWidth: windowWidth*.33,
					maxHeight: windowHeight*.9,
					// position: { my: "left top", at: "left top", of: window },
					title: this.id,
					draggable: true,
					icons: { primary: 'ui-icon-close' },
					click: function() { $( this ).dialog( 'close' ); }
					});
				$( '#lexicadialogtext' ).dialog( 'open' );
				$( '#lexicadialogtext' ).html('[searching...]');
				$.getJSON('/lexica/findbyform/'+this.id, function (definitionreturned) {
					$( '#lexicadialogtext' ).html(definitionreturned['newhtml']);
					$( '#lexicaljsscriptholder' ).html(definitionreturned['newjs']);
				});
			return false;
		});

			$('CLICKTWO').click( function(e) {
				e.preventDefault();
				$.getJSON('/browse/'+this.id, function (passagereturned) {
				$('#browseforward').unbind('click');
				$('#browseback').unbind('click');
				var fb = parsepassagereturned(passagereturned)
					// left and right arrow keys
					$('#browserdialogtext').keydown(function(e) {
						switch(e.which) {
							case 37: browseuponclick(fb[1]); break;
							case 39: browseuponclick(fb[0]); break;
							}
					});
				$('#browseforward').bind('click', function(){ browseuponclick(fb[0]); });
				$('#browseback').bind('click', function(){ browseuponclick(fb[1]); });
				});
			});

		</script>
	"""

	js = re.sub(r'CLICKONE', clickone, js)
	js = re.sub(r'CLICKTWO', clicktwo, js)

	return js


def dictionaryentryjs() -> str:
	"""

	return js to insert

	$('formsummary'): build a morphology chart

	$('dictionaryidsearch'): click for next/previous

	$('dictionaryentry'): click for xrefs inside the entry

	ensure exact matches, otherwise ἔρδω will pull up ὑπερδώριοϲ too

	and so:
		'/lexica/lookup/^'+this.id+'$'

	:return:
	"""

	template = """
	<script>
	
	$('dictionaryentry').click( function(e) {
		e.preventDefault();
		var windowWidth = $(window).width();
		var windowHeight = $(window).height();
		let ldt = $('#lexicadialogtext');
		let jshld = $('#lexicaljsscriptholder');
		
		ldt.dialog({
			closeOnEscape: true,
			autoOpen: false,
			minWidth: windowWidth*.33,
			maxHeight: windowHeight*.9,
			// position: { my: "left top", at: "left top", of: window },
			title: this.id,
			draggable: true,
			icons: { primary: 'ui-icon-close' },
			click: function() { $(this).dialog('close'); }
			});
		
		ldt.dialog('open');
		ldt.html('[searching...]');
		
		$.getJSON('/lexica/lookup/^'+this.id+'$', function (definitionreturned) {
			ldt.html(definitionreturned['newhtml']);
			jshld.html(definitionreturned['newjs']);		
			});
		return false;
		
		});

	$('dictionaryidsearch').click( function(){
			$('#imagearea').empty();

			let ldt = $('#lexicadialogtext');
			let jshld = $('#lexicaljsscriptholder');
	
			let entryid = this.getAttribute("entryid");
			let language = this.getAttribute("language");

			let url = '/lexica/idlookup/' + language + '/' + entryid;
			
			$.getJSON(url, function (definitionreturned) { 
				ldt.html(definitionreturned['newhtml']);
				jshld.html(definitionreturned['newjs']);	
			});
		});
	
	$('formsummary').click( function(e) {
		e.preventDefault();
		var windowWidth = $(window).width();
		var windowHeight = $(window).height();
		let ldt = $('#lexicadialogtext');
		let jshld = $('#lexicaljsscriptholder');
		let headword = this.getAttribute("headword");
		let parserxref = this.getAttribute("parserxref");
		let lexid = this.getAttribute("lexicalid");
		
		ldt.dialog({
			closeOnEscape: true,
			autoOpen: false,
			minWidth: windowWidth*.33,
			maxHeight: windowHeight*.9,
			// position: { my: "left top", at: "left top", of: window },
			title: headword,
			draggable: true,
			icons: { primary: 'ui-icon-close' },
			click: function() { $(this).dialog('close'); }
			});
		
		ldt.dialog('open');
		ldt.html('[searching...]');
		
		$.getJSON('/lexica/morphologychart/'+this.lang+'/'+lexid+'/'+parserxref+'/'+headword, function (definitionreturned) {
			ldt.html(definitionreturned['newhtml']);
			jshld.html(definitionreturned['newjs']);		
			});
			
		return false;
		
		});
			
	</script>
	"""

	return template


def morphologychartjs() -> str:
	"""

	return js to insert

	ensure exact matches, otherwise ἔρδω will pull up ὑπερδώριοϲ too

	and so:
		'/lexica/lookup/^'+this.id+'$'

	:return:
	"""

	if osname != 'nt':
		# singlewordsearch() will throw a recursion exception on Windows
		searchurl = """let url = '/search/singleword/' + searchid + '/' + searchterm;"""
	else:
		searchurl = """let url = '/search/standard/' + searchid + '?skg=%20' + searchterm + '%20';"""

	template = """
	<script>
		function displayresults(output) {
			document.title = output['title'];
			$('#searchsummary').html(output['searchsummary']);
			$('#displayresults').html(output['found']);
			let browserclickscript = document.createElement('script');
			browserclickscript.innerHTML = output['js'];
			document.getElementById('browserclickscriptholder').appendChild(browserclickscript);
		}

		$('verbform').click( function(){
			$('#imagearea').empty();
			$('#searchsummary').html('');
			$('#displayresults').html('');
			$('#pollingdata').show();
			
			let bcsh = document.getElementById("browserclickscriptholder");
			if (bcsh.hasChildNodes()) { bcsh.removeChild(bcsh.firstChild); }
	
			let searchterm = this.getAttribute("searchterm");
			
			let searchid = generateId(8);
			REGEXSEARCHURL
			
			$.getJSON(url, function (returnedresults) { displayresults(returnedresults); });
			
			checkactivityviawebsocket(searchid);
		});
		
	
		$('lemmatizable').click( function(){
			$('#imagearea').empty();
			$('#searchsummary').html('');
			$('#displayresults').html('');
			$('#pollingdata').show();
			
			let bcsh = document.getElementById("browserclickscriptholder");
			if (bcsh.hasChildNodes()) { bcsh.removeChild(bcsh.firstChild); }
	
			let headform = this.getAttribute("headform");
			
			let searchid = generateId(8);
			let url = '/search/lemmatized/' + searchid + '/' + headform;
			
			$.getJSON(url, function (returnedresults) { displayresults(returnedresults); });
			
			checkactivityviawebsocket(searchid);
		});
		
		$('dictionaryidsearch').click( function(){
			$('#imagearea').empty();

			let ldt = $('#lexicadialogtext');
			let jshld = $('#lexicaljsscriptholder');
	
			let entryid = this.getAttribute("entryid");
			let language = this.getAttribute("language");

			let url = '/lexica/idlookup/' + language + '/' + entryid;
			
			$.getJSON(url, function (definitionreturned) { 
				ldt.html(definitionreturned['newhtml']);
				jshld.html(definitionreturned['newjs']);	
			});
		});
		
		function checkactivityviawebsocket(searchid) {
			$.getJSON('/search/confirm/'+searchid, function(portnumber) {
				let ip = location.hostname;
				let s = new WebSocket('ws://'+ip+':'+portnumber+'/');
				let amready = setInterval(function(){
					if (s.readyState === 1) { s.send(JSON.stringify(searchid)); clearInterval(amready); }
					}, 10);
				s.onmessage = function(e){
					let progress = JSON.parse(e.data);
					displayprogress(progress);
					if  (progress['active'] === 'inactive') { $('#pollingdata').html(''); s.close(); s = null; }
					}
			});
		}
	
		function displayprogress(searchid, progress){
			// note that morphologychartjs() has its own version of this function: changes here should be made there too
			let r = progress['Remaining'];
			let t = progress['Poolofwork'];
			let h = progress['Hitcount'];
			let pct = Math.round((t-r) / t * 100);
			let m = progress['Statusmessage'];
			let l = progress['Launchtime'];
			let x = progress['Notes'];
			let id = progress['ID'];
			let a = progress['Activity'];
		
			// let thehtml = '[' + id + ' activity =' + a +'] ';
			if (id === searchid) {
				let thehtml = '';
				if (r !== undefined && t !== undefined && !isNaN(pct)) {
					let e = Math.round((new Date().getTime() / 1000) - l);
			
					if (t !== -1) {
						thehtml += m + ': <span class="progress">' + pct + '%</span> completed&nbsp;(' + e + 's)';
					} else {
						thehtml += m + '&nbsp;(' + e + 's)';
					}
			
					if (h > 0) {
						thehtml += '<br />(<span class="progress">' + h + '</span> found)';
					}
			
					thehtml += '<br />' + x;
				}
				$('#pollingdata').html(thehtml);
			}
		}

	</script>    
	"""

	template = re.sub(r'REGEXSEARCHURL', searchurl, template)

	return template
