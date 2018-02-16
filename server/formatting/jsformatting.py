# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-18
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re

def insertbrowserclickjs(tagname):
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


def insertlexicalbrowserjs(htmlentry):
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

	newhtml = htmlentry + js.format(jst=jstemplate)

	return newhtml


def generatevectorjs(path):
	"""

	this JS is mainly a copy of material from documentready.js

	:param headwordwordlist:
	:return:
	"""


	jstemplate = """
		$('lemmaheadword').click( function(e) { 
		var searchid = Date.now();
		var url = '/REGEXREPLACE/'+searchid+'?lem='+this.id;
		$('#imagearea').empty();
		$('#searchsummary').html(''); 
		$('#displayresults').html('');
		$('#wordsearchform').hide();
		// $.getJSON( {url: '/setsessionvariable?cosdistbylineorword=no', async: false, success: function (resultdata) { } });
		// $.getJSON( {url: '/setsessionvariable?cosdistbysentence=yes', async: false, success: function (resultdata) { } });
		$('#cosdistbysentence').prop('checked', true);
		$('#cosdistbylineorword').prop('checked', false);
		$('#complexsearching').hide();
		$('#lemmatasearchform').show();
		$('#lemmatasearchform').val(this.id);
		var w = window.innerWidth * .9;
		var h = window.innerHeight * .9;
		$.getJSON(url, function (output) { 
				document.title = output['title'];

				var summaryhtml = '';
				
				summaryhtml += 'Sought '+output['htmlsearch']+'<br />';
				if ( output['scope'] != '1') { summaryhtml += 'Searched '+output['scope']+' texts '; } else { summaryhtml += 'Searched 1 text '; }

				summaryhtml += 'and found '+output['resultcount'];
				summaryhtml += ' ('+output['searchtime']+'s)';
				
				if (output['icandodates'] == 'yes' ) { 
					if (output['dmin'] != '850 B.C.E.' || output['dmax'] != '1500 C.E.') { 
						summaryhtml += '<br />Searched between '+output['dmin']+' and '+output['dmax']; 
						} 
					}

				if (output['onehit'] == 'yes') { 
					summaryhtml += '<br />Only allowing one match per item searched (either a whole author or a specified work)'; 
					}
					
				summaryhtml += '<br />Sorted by '+output['sortby'];
				
				if (output['hitmax'] == 'true') { 
					summaryhtml += '<br />[Search suspended: result cap reached.]';
					}
									
				$('#searchsummary').html(summaryhtml);
				
				$('#displayresults').html(output['found']);
				
				var imagetarget = $('#imagearea');
				if (typeof output['image'] !== 'undefined' && output['image'] !== '') {
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
		});
	"""

	js = re.sub('REGEXREPLACE', path, jstemplate)

	return js
