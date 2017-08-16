# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""


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

	js = jstemplate % (tagname)

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
