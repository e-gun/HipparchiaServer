# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-21
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import re
from typing import List

from server import hipparchia
from server.formatting.miscformatting import debugmessage
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.hipparchiaobjects.searchobjects import SearchObject
from server.hipparchiaobjects.worklineobject import dbWorkLine
from server.searching.sqlsearching import generatepreliminaryhitlist
from server.searching.searchhelperfunctions import lookoutsideoftheline


def precomposedsqlphrasesearch(so: SearchObject) -> List[dbWorkLine]:
    """

    you are searching for a relatively rare word: we will keep things simple-ish

    note that the second half of this is not MP: but searches already only take 6s; so clean code probably wins here

    FIXME:

    can't find the phrases in here...:

        κατεϲκεύαϲεν τὸ ἐνϲόριον FAILS
        ϲεν τὸ ἐνϲόριον το SUCCEEDS

    ch0005w001/2749

    1 Ῥουφεῖνα Ἰουδαία ἀρχι-
    2 ϲυνάγωγοϲ κατεϲκεύα-
    3 ϲεν τὸ ἐνϲόριον τοῖϲ ἀπε-     ( match: ἀπελευθέροιϲ )
    4 λευθέροιϲ καὶ θρέμ(μ)αϲιν
    5 μηδενὸϲ ἄλ(λ)ου ἐξουϲίαν ἔ-

    actually, this is a BUILDER problem AND a SERVER problem:

    BUILDER:

    2749 does not have κατεϲκεύαϲεν in it

    hipparchiaDB=# select index, accented_line, hyphenated_words  from ch0005 where index between 2746 and 2752;
     index |           accented_line           | hyphenated_words
    -------+-----------------------------------+------------------
      2748 | ῥουφεῖνα ἰουδαία ἀρχιϲυνάγωγοϲ    | ἀρχιϲυνάγωγοϲ
      2749 | κατεϲκεύα-                        |
      2750 | ϲεν τὸ ἐνϲόριον τοῖϲ ἀπελευθέροιϲ | ἀπελευθέροιϲ
      2751 | καὶ θρέμμαϲιν                     |
      2752 | μηδενὸϲ ἄλλου ἐξουϲίαν ἔχοντοϲ    | ἔχοντοϲ
    (5 rows)

    SERVER: ἀπελευθέροιϲ καὶ θρέμμαϲιν is missed by precomposedsqlphrasesearch()
    but it is found by precomposedsqlsubqueryphrasesearch()

    maybe it is time to nuke precomposedsqlphrasesearch() after all...

    NB: the dynamic workonphrasesearch() CAN find 'ἀπελευθέροιϲ καὶ θρέμμαϲιν'

    """
    debugmessage('executing a precomposedsqlphrasesearch()')

    so.termone = so.leastcommon
    searchphrase = so.phrase
    phraselen = len(searchphrase.split(' '))

    initialhitlines = generatepreliminaryhitlist(so)

    m = 'Now searching among the {h} initial hits for the full phrase "{p}"'
    so.poll.statusis(m.format(h=so.poll.gethits(), p=so.originalseeking))
    so.poll.sethits(0)

    fullmatches = list()

    dbconnection = ConnectionObject()
    dbcursor = dbconnection.cursor()
    commitcount = 0
    while initialhitlines and len(fullmatches) <= so.cap:
        commitcount += 1
        if commitcount == hipparchia.config['MPCOMMITCOUNT']:
            dbconnection.commit()
            commitcount = 0

        hit = initialhitlines.pop()

        wordset = lookoutsideoftheline(hit.index, phraselen - 1, hit.authorid, so, dbcursor)

        if not so.accented:
            wordset = re.sub(r'[.?!;:,·’]', str(), wordset)
        else:
            # the difference is in the apostrophe: δ vs δ’
            wordset = re.sub(r'[.?!;:,·]', str(), wordset)

        if so.near and re.search(searchphrase, wordset):
            fullmatches.append(hit)
            so.poll.addhits(1)
        elif not so.near and re.search(searchphrase, wordset) is None:
            fullmatches.append(hit)
            so.poll.addhits(1)

    dbconnection.connectioncleanup()

    return fullmatches