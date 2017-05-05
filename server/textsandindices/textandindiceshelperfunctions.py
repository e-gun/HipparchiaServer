# -*- coding: utf-8 -*-
"""
	HipparchiaServer: an interface to a database of Greek and Latin texts
	Copyright: E Gunderson 2016-17
	License: GNU GENERAL PUBLIC LICENSE 3
		(see LICENSE in the top level directory of the distribution)
"""

import re
from collections import deque
from string import punctuation

from server.dbsupport.citationfunctions import finddblinefromincompletelocus
from server.dbsupport.dbfunctions import grabonelinefromwork, dblineintolineobject, makeanemptyauthor, makeanemptywork
from server.searching.searchfunctions import whereclauses


def tcparserequest(request, authordict, workdict):
	"""
	return the author, work, and locus requested
	also some other handy veriable derived from these items
	:param requestobject:
	:return:
	"""
	
	try:
		uid = re.sub('[\W_]+', '', request.args.get('auth', ''))
	except:
		uid = ''
		
	try:
		workid = re.sub('[\W_]+', '', request.args.get('work', ''))
	except:
		workid = ''

	try:
		locus = re.sub('[!@#$%^&*()=]+', '', request.args.get('locus', ''))
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
	
	w = whereclauses(selection, '=', {authorobject.universalid: authorobject})
	d = [workobject.universalid]
	qw = ''
	for i in range(0, len(w)):
		qw += 'AND (' + w[i][0] + ') '
		d.append(w[i][1])

	query = 'SELECT index FROM ' + authorobject.universalid + ' WHERE wkuniversalid=%s ' + qw + ' ORDER BY index DESC LIMIT 1'
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

	previousheadword = ''

	outputlines = deque()
	if useheadwords:
		outputlines.append('[nb: <span class="word"><span class="homonym">homonyms</span></span> are listed under every known '
		                   'headword and their <span class="word"><span class="homonym">display differs</span></span> from '
		                   'that of <span class="word">unambiguous entries</span>]<br />')
		outputlines.append('<table><tr><th>headword</th><th>word</th><th>count</th><th>passages</th></tr>\n')
	else:
		outputlines.append('<table><tr><th>word</th><th>count</th><th>passages</th></tr>\n')
	for i in indexingoutput:
		outputlines.append('<tr>')
		headword = i[0]
		observedword = i[1]
		if useheadwords and headword != previousheadword:
			outputlines.append('<td class="headword"><indexobserved id="{hw}">{hw}</indexobserved></td>'.format(hw=headword))
			previousheadword = headword
		elif useheadwords and headword == previousheadword:
			outputlines.append('<td class="headword">&nbsp;</td>')
		if i[4] == 'isahomonymn':
			outputlines.append('<td class="word"><span class="homonym"><indexobserved id="{wd}">{wd}</indexobserved></span></td>'.format(wd=observedword))
		else:
			outputlines.append('<td class="word"><indexobserved id="{wd}">{wd}</indexobserved></td>'.format(wd=observedword))
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


def cleanindexwords(word):
	"""
	remove gunk that should not be present in a cleaned line

	:param word:
	:return:
	"""

	extrapunct = '\′‵’‘·̆́“”„—†⌈⌋⌊⟫⟪❵❴⟧⟦(«»›‹⸐„⸏⸎⸑–⏑–⏒⏓⏔⏕⏖⌐∙×⁚⁝‖⸓'
	punct = re.compile('[{s}]'.format(s=re.escape(punctuation + extrapunct)))
	# hard to know whether or not to do the editorial insertions stuff: ⟫⟪⌈⌋⌊
	# word = re.sub(r'\[.*?\]','', word) # '[o]missa' should be 'missa'
	word = re.sub(r'[0-9]', '', word)
	word = re.sub(punct, '', word)
	# best do punct before this next one...
	try:
		if re.search(r'[a-zA-z]', word[0]) is None:
			word = re.sub(r'[a-zA-z]', '', word)
	except:
		# must have been ''
		pass

	invals = u'jv'
	outvals = u'iu'
	word = word.translate(str.maketrans(invals, outvals))

	return word


def observedformjs():
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
	            $( '#parserdialog' ).dialog({
	                    autoOpen: false,
	                    minWidth: windowWidth*.33,
	                    maxHeight: windowHeight*.9,
	                    // position: { my: "left top", at: "left top", of: window },
	                    title: this.id,
	                    draggable: true,
	                    icons: { primary: 'ui-icon-close' },
	                    click: function() { $( this ).dialog( 'close' ); }
	                    });
	            $( '#parserdialog' ).dialog( 'open' );
	            $( '#parserdialog' ).html('[searching...]');
	            $.getJSON('/parse/'+this.id, function (definitionreturned) {
	                $( '#lexicon').val(definitionreturned[0]['trylookingunder']);
	                var dLen = definitionreturned.length;
	                var linesreturned = []
	                for (i = 0; i < dLen; i++) {
	                    linesreturned.push(definitionreturned[i]['value']);
	                    }
	                $( '#parserdialog' ).html(linesreturned);
	            });
            return false;
        });
        </script>
	"""

	return js