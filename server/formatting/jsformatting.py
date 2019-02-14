# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-19
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re


def insertbrowserclickjs(tagname: str) -> str:
	"""
	the clickable urls don't work without inserting new js into the page to catch the clicks
	need to match the what we used to get via the flask template

	:return:
	"""

	jstemplate = """
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


def generatevectorjs(path: str) -> str:
	"""

	this JS is mainly a copy of material from documentready.js

	:param path:
	:return:
	"""

	jstemplate = """
		$('lemmaheadword').click( function(e) { 
			var searchid = generateId(8);
			var url = '/REGEXREPLACE/'+searchid+'?lem='+this.id;
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
						src: '/getstoredfigure/' + output['image'],
						alt: '[vector graph]',
						id: 'insertedfigure',
						height: h
					});
				}
								
					var browserclickscript = document.createElement("script");
					browserclickscript.innerHTML = output['js'];
					document.getElementById('browserclickscriptholder').appendChild(browserclickscript);
				});		

			$.getJSON('/confirm/'+searchid, function(portnumber) {
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

	js = re.sub('REGEXREPLACE', path, jstemplate)

	return js


def supplementalindexjs() -> str:
	"""

	insert a js block to handle observed forms

	:return:
	"""

	js = """
		<script>
			$('indexobserved').click( function(e) {
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
				$.getJSON('/parse/'+this.id, function (definitionreturned) {
					$( '#lexicadialogtext' ).html(definitionreturned['newhtml']);
					$( '#lexicaljsscriptholder' ).html(definitionreturned['newjs']);
				});
			return false;
		});

			$('indexedlocation').click( function(e) {
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

	return js


def dictionaryentryjs() -> str:
	"""

	return js to insert

	ensure exact matches, otherwise ἔρδω will pull up ὑπερδώριοϲ too

	and so:
		'/dictsearch/^'+this.id+'$'

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
		
		$.getJSON('/dictsearch/^'+this.id+'$', function (definitionreturned) {
			ldt.html(definitionreturned['newhtml']);
			jshld.html(definitionreturned['newjs']);		
			});
			
		return false;
		
		});
		
	$('formsummary').click( function(e) {
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
		
		$.getJSON('/morphologychart/'+this.lang+'/'+this.id+'/'+this.lexid, function (definitionreturned) {
			ldt.html(definitionreturned['newhtml']);
			jshld.html(definitionreturned['newjs']);		
			});
			
		return false;
		
		});
			
	</script>
	"""

	return template
