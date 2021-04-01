__all__ = ['browseroute', 'frontpage', 'getterroutes', 'hintroutes', 'inforoutes', 'lexicalroutes', 'searchroute',
           'selectionroutes', 'textandindexroutes', 'resetroutes', 'cssroutes', 'authenticationroutes']

"""
what can be found where: [routes/ $ grep "^@hipp" *.py]

authenticationroutes.py:@hipparchia.route('/authentication/<action>', methods=['GET', 'POST'])
browseroute.py:@hipparchia.route('/browse/<method>/<author>/<work>')
browseroute.py:@hipparchia.route('/browse/<method>/<author>/<work>/<location>')
browseroute.py:@hipparchia.route('/browserawlocus/<author>/<work>')
browseroute.py:@hipparchia.route('/browserawlocus/<author>/<work>/<location>')
cssroutes.py:@hipparchia.route('/css/<cssrequest>', methods=['GET'])
frontpage.py:@hipparchia.route('/')
frontpage.py:@hipparchia.route('/favicon.ico')
frontpage.py:@hipparchia.route('/apple-touch-icon-precomposed.png')
frontpage.py:@hipparchia.route('/robots.txt')
frontpage.py:@hipparchia.errorhandler(400)
frontpage.py:@hipparchia.errorhandler(404)
frontpage.py:@hipparchia.errorhandler(500)
getterroutes.py:@hipparchia.route('/get/response/<fnc>/<param>')
getterroutes.py:@hipparchia.route('/get/json/<fnc>')
getterroutes.py:@hipparchia.route('/get/json/<fnc>/<one>')
getterroutes.py:@hipparchia.route('/get/json/<fnc>/<one>/<two>')
getterroutes.py:@hipparchia.route('/get/json/<fnc>/<one>/<two>/<three>')
hintroutes.py:@hipparchia.route('/hints/<category>/<_>')
inforoutes.py:@hipparchia.route('/databasecontents/<dictionarytodisplay>')
inforoutes.py:@hipparchia.route('/csssamples')
inforoutes.py:@hipparchia.route('/showsession')
inforoutes.py:@hipparchia.route('/testroute')
lexicalroutes.py:@hipparchia.route('/lexica/<action>/<one>')
lexicalroutes.py:@hipparchia.route('/lexica/<action>/<one>/<two>')
lexicalroutes.py:@hipparchia.route('/lexica/<action>/<one>/<two>/<three>/<four>')
resetroutes.py:@hipparchia.route('/reset/<item>')
searchroute.py:@hipparchia.route('/executesearch/<searchid>', methods=['GET'])
searchroute.py:@hipparchia.route('/singlewordsearch/<searchid>/<searchterm>')
searchroute.py:@hipparchia.route('/lemmatizesearch/<searchid>/<headform>')
selectionroutes.py:@hipparchia.route('/selection/<action>', methods=['GET'])
selectionroutes.py:@hipparchia.route('/selection/<action>/<one>', methods=['GET'])
selectionroutes.py:@hipparchia.route('/selection/<action>/<one>/<two>', methods=['GET'])
selectionroutes.py:@hipparchia.route('/setsessionvariable/<thevariable>/<thevalue>')
textandindexroutes.py:@hipparchia.route('/indexto/<searchid>/<author>')
textandindexroutes.py:@hipparchia.route('/indexto/<searchid>/<author>/<work>')
textandindexroutes.py:@hipparchia.route('/indexto/<searchid>/<author>/<work>/<passage>')
textandindexroutes.py:@hipparchia.route('/indexto/<searchid>/<author>/<work>/<passage>/<endpoint>')
textandindexroutes.py:@hipparchia.route('/vocabularyfor/<searchid>/<author>')
textandindexroutes.py:@hipparchia.route('/vocabularyfor/<searchid>/<author>/<work>')
textandindexroutes.py:@hipparchia.route('/vocabularyfor/<searchid>/<author>/<work>/<passage>')
textandindexroutes.py:@hipparchia.route('/vocabularyfor/<searchid>/<author>/<work>/<passage>/<endpoint>')
textandindexroutes.py:@hipparchia.route('/vocabularyforrawlocus/<searchid>/<author>/<work>/<location>')
textandindexroutes.py:@hipparchia.route('/vocabularyforrawlocus/<searchid>/<author>/<work>/<location>/<endpoint>')
textandindexroutes.py:@hipparchia.route('/indextorawlocus/<searchid>/<author>/<work>/<location>')
textandindexroutes.py:@hipparchia.route('/indextorawlocus/<searchid>/<author>/<work>/<location>/<endpoint>')
textandindexroutes.py:@hipparchia.route('/textof/<author>')
textandindexroutes.py:@hipparchia.route('/textof/<author>/<work>')
textandindexroutes.py:@hipparchia.route('/textof/<author>/<work>/<passage>')
textandindexroutes.py:@hipparchia.route('/textof/<author>/<work>/<passage>/<endpoint>')
textandindexroutes.py:@hipparchia.route('/textofrawlocus/<author>/<work>/<location>')
textandindexroutes.py:@hipparchia.route('/textofrawlocus/<author>/<work>/<location>/<endpoint>')
vectorroutes.py:@hipparchia.route('/vectors/<vectortype>/<searchid>/<headform>')
vectorroutes.py:@hipparchia.route('/vectoranalogies/<searchid>/<termone>/<termtwo>/<termthree>')
websocketroutes.py:@hipparchia.route('/confirm/<searchid>')

"""