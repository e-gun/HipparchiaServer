__all__ = ['browseroute', 'frontpage', 'getterroutes', 'hintroutes', 'inforoutes', 'lexicalroutes', 'searchroute',
           'selectionroutes', 'textandindexroutes', 'websocketroutes']

"""
what can be found where: [routes/ $ grep "^@" *.py]

    browseroute.py:@hipparchia.route('/browse/<locus>')
    frontpage.py:@hipparchia.route('/')
    frontpage.py:@hipparchia.route('/favicon.ico')
    frontpage.py:@hipparchia.route('/apple-touch-icon-precomposed.png')
    getterroutes.py:@hipparchia.route('/getsessionvariables')
    getterroutes.py:@hipparchia.route('/getcookie/<cookienum>')
    getterroutes.py:@hipparchia.route('/getworksof/<authoruid>')
    getterroutes.py:@hipparchia.route('/getstructure/<locus>')
    getterroutes.py:@hipparchia.route('/getauthorinfo/<authorid>')
    getterroutes.py:@hipparchia.route('/getsearchlistcontents')
    getterroutes.py:@hipparchia.route('/getgenrelistcontents')
    hintroutes.py:@hipparchia.route('/getauthorhint', methods=['GET'])
    hintroutes.py:@hipparchia.route('/getgenrehint', methods=['GET'])
    hintroutes.py:@hipparchia.route('/getworkgenrehint', methods=['GET'])
    hintroutes.py:@hipparchia.route('/getaulocationhint', methods=['GET'])
    hintroutes.py:@hipparchia.route('/getwkprovenancehint', methods=['GET'])
    inforoutes.py:@hipparchia.route('/authors')
    lexicalroutes.py:@hipparchia.route('/parse/<observedword>')
    lexicalroutes.py:@hipparchia.route('/dictsearch/<searchterm>')
    lexicalroutes.py:@hipparchia.route('/reverselookup/<searchterm>')
    searchroute.py:@hipparchia.route('/executesearch/<timestamp>', methods=['GET'])
    selectionroutes.py:@hipparchia.route('/makeselection', methods=['GET'])
    selectionroutes.py:@hipparchia.route('/setsessionvariable', methods=['GET'])
    selectionroutes.py:@hipparchia.route('/clearselections', methods=['GET'])
    selectionroutes.py:@hipparchia.route('/getselections')
    selectionroutes.py:@hipparchia.route('/clear')
    textandindexroutes.py:@hipparchia.route('/indexto', methods=['GET'])
    textandindexroutes.py:@hipparchia.route('/textof', methods=['GET'])
    websocketroutes.py:@hipparchia.route('/startwspolling/<theport>', methods=['GET'])
    websocketroutes.py:@hipparchia.route('/confirm/<ts>')

"""