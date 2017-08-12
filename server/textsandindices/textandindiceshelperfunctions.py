# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

from collections import deque

from server import hipparchia
from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.dbsupport.dbfunctions import grabonelinefromwork, dblineintolineobject, makeanemptyauthor, makeanemptywork
from server.formatting.wordformatting import depunct
from server.searching.searchfunctions import atsignwhereclauses


def tcparserequest(request, authordict, workdict):
	"""
	return the author, work, and locus requested
	also some other handy variable derived from these items
	:param requestobject:
	:return:
	"""
	
	try:
		uid = depunct(request.args.get('auth', ''))
	except:
		uid = ''
		
	try:
		workid = depunct(request.args.get('work', ''))
	except:
		workid = ''

	try:
		allowed = ',;|'
		locus = depunct(request.args.get('locus', ''), allowed)
	except:
		locus = ''
	
	workdb = uid + 'w' + workid
	
	if uid != '':
		try:
			ao = authordict[uid]
			if len(workdb) == 10:
				try:
					wo = workdict[workdb]
				except:
					wo = makeanemptywork('gr0000w000')
			else:
					wo = makeanemptywork('gr0000w000')
		except:
			ao = makeanemptyauthor('gr0000')
			wo = makeanemptywork('gr0000w000')
		
		passage = locus.split('|')
		passage.reverse()

	else:
		ao = makeanemptyauthor('gr0000')
		wo = makeanemptywork('gr0000w000')
		passage = []
	
	req = {}
	
	req['authorobject'] = ao
	req['workobject'] = wo
	req['passagelist'] = passage
	req['rawlocus'] = locus
	
	return req


def textsegmentfindstartandstop(authorobject, workobject, passageaslist, cursor):
	"""
	find the first and last lines of a work segment
	:return:
	"""
	
	p = tuple(passageaslist)
	lookforline = finddblinefromincompletelocus(workobject, p, cursor)
	# assuming that lookforline['code'] == 'success'
	# lookforline['code'] is (allegedly) only relevant to the Perseus lookup problem where a bad locus can be sent
	foundline = lookforline['line']
	line = grabonelinefromwork(authorobject.universalid, foundline, cursor)
	lo = dblineintolineobject(line)
	
	# let's say you looked for 'book 2' of something that has 'book, chapter, line'
	# that means that you want everything that has the same level2 value as the lineobject
	# build a where clause
	passageaslist.reverse()
	atloc = '|'.join(passageaslist)
	selection = workobject.universalid + '_AT_' + atloc
	
	w = atsignwhereclauses(selection, '=', {authorobject.universalid: authorobject})
	d = [workobject.universalid]
	qw = ''
	for i in range(0, len(w)):
		qw += 'AND (' + w[i][0] + ') '
		d.append(w[i][1])

	query = 'SELECT index FROM {au} WHERE wkuniversalid=%s {whr} ORDER BY index DESC LIMIT 1'.format(au=authorobject.universalid, whr=qw)
	data = tuple(d)

	cursor.execute(query, data)
	found = cursor.fetchone()
	
	startandstop = {}
	startandstop['startline'] = lo.index
	startandstop['endline'] = found[0]
	
	
	return startandstop


def wordindextohtmltable(indexingoutput, useheadwords):
	"""
	pre-pack the concordance output into an html table so that the page JS can just iterate through a set of lines when the time comes
	each result in the list is itself a list: [word, count, lociwherefound]
	
	input:
		('sum¹', 'sunt', 1, '1.1')
		('superus', 'summa', 1, '1.4')
		...
	:param indexingoutput:
	:return:
	"""

	if len(indexingoutput) < hipparchia.config['CLICKABLEINDEXEDWORDSCAP'] or hipparchia.config['CLICKABLEINDEXEDWORDSCAP'] < 0:
		thwd = '<td class="headword"><indexobserved id="{wd}">{wd}</indexobserved></td>'
		thom = '<td class="word"><span class="homonym"><indexobserved id="{wd}">{wd}</indexobserved></td>'
		twor = '<td class="word"><indexobserved id="{wd}">{wd}</indexobserved></td>'
	else:
		thwd = '<td class="headword">{wd}</td>'
		thom = '<td class="word"><span class="homonym">{wd}</td>'
		twor = '<td class="word">{wd}</td>'

	previousheadword = ''

	outputlines = deque()
	if useheadwords:
		boilerplate = """
		[nb: <span class="word"><span class="homonym">homonyms</span></span> 
		are listed under every known headword and their <span class="word">
		<span class="homonym">display differs</span></span> from that of 
		<span class="word">unambiguous entries</span>]
		<br>
		<br>	
		"""

		tablehead = """
		<table>
		<tr>
			<th class="indextable">headword</th>
			<th class="indextable">word</th>
			<th class="indextable">count</th>
			<th class="indextable">passages</th>
		</tr>
		"""
		outputlines.append(boilerplate)
		outputlines.append(tablehead)
	else:
		tablehead = """
		<table>
		<tr>
			<th class="indextable">word</th>
			<th class="indextable">count</th>
			<th class="indextable">passages</th>
		</tr>
		"""
		outputlines.append(tablehead)

	for i in indexingoutput:
		outputlines.append('<tr>')
		headword = i[0]
		observedword = i[1]
		if useheadwords and headword != previousheadword:
			outputlines.append(thwd.format(wd=headword))
			previousheadword = headword
		elif useheadwords and headword == previousheadword:
			outputlines.append('<td class="headword">&nbsp;</td>')
		if i[4] == 'isahomonymn':
			outputlines.append(thom.format(wd=observedword))
		else:
			outputlines.append(twor.format(wd=observedword))
		outputlines.append('<td class="count">{ct}</td>'.format(ct=i[2]))
		outputlines.append('<td class="passages">{psg}</td>'.format(psg=i[3]))
		outputlines.append('</tr>')
	outputlines.append('</table>')

	html = '\n'.join(list(outputlines))

	return html


def dictmerger(masterdict, targetdict):
	"""

	a more complex version also present in HipparchiaBuilder

	:param masterdict:
	:param targetdict:
	:return:
	"""

	for item in targetdict:
		if item in masterdict:
			masterdict[item] += targetdict[item]
		else:
			masterdict[item] = targetdict[item]

	return masterdict


def supplementalindexjs():
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
	                $( '#lexicon').val(definitionreturned[0]['trylookingunder']);
	                var dLen = definitionreturned.length;
	                var linesreturned = []
	                for (i = 0; i < dLen; i++) {
	                    linesreturned.push(definitionreturned[i]['value']);
	                    }
	                $( '#lexicadialogtext' ).html(linesreturned);
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


def setcontinuationvalue(thisline, previousline, previouseditorialcontinuationvalue, type):
	"""

	used to determine if a bracket span is running for multiple lines

	type should be something that findactivebrackethighlighting() can return and that bracketopenedbutnotclosed()
	can receive: 'square', 'curly', etc.

	:param thisline:
	:param previousline:
	:param previouseditorialcontinuationvalue:
	:param type:
	:return:
	"""

	if thisline.bracketopenedbutnotclosed(type):
		newcv = True
	elif not thisline.samelevelas(previousline):
		newcv = False
	elif (previousline.bracketopenedbutnotclosed(type) or previouseditorialcontinuationvalue) and not thisline.bracketclosed(type):
		newcv = True
	else:
		newcv = False

	return newcv