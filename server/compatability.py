# -*- coding: utf-8 -*-
"""
    HipparchiaServer: an interface to a database of Greek and Latin texts
    Copyright: E Gunderson 2016-22
    License: GNU GENERAL PUBLIC LICENSE 3
        (see LICENSE in the top level directory of the distribution)
"""

import re
import subprocess

from distutils.version import LooseVersion

from versionconstants import GOHELPERMIN, RUSTHELPERMIN, BUILDERMIN, SQLTEMPLATE
from server.formatting.miscformatting import consolewarning, debugmessage
from server.hipparchiaobjects.connectionobject import ConnectionObject
from server.searching.miscsearchfunctions import getexternalhelperpath
from server import hipparchia


def checkcompatability():
    """

    make sure the helper binary works with this version of the server

    slated for removal...

    note the distutils is deprecated and going away in 3.12

    """
    if hipparchia.config['EXTERNALGRABBER']:
        extbin = hipparchia.config['EXTERNALBINARYNAME']
        p = getexternalhelperpath(extbin)

        if 'Rust' in extbin:
            vmin = RUSTHELPERMIN
            pre = '--'
        else:
            vmin = GOHELPERMIN
            pre = '-'

        commandandarguments = [p, '{p}v'.format(p=pre)]
        version = subprocess.run(commandandarguments, capture_output=True)
        version = version.stdout

        # b'Hipparchia Golang Helper CLI Debugging Interface (v.1.3.2)\n'

        vfinder = re.compile(r'\(v\.((\d+)\.(\d+)\.(\d+))\)')
        # extra brackets let you find the components, but you only need v[1]: "1.3.2"
        # note how "1.3.2b", etc. are doomed to fail...

        v = re.search(vfinder, str(version))

        try:
            minversion = LooseVersion(vmin)
        except ValueError:
            minversion = None
            consolewarning('checkcompatability() failed to parse minimum version string "{v}"'.format(v=vmin))

        try:
            binversion = LooseVersion(v[1])
        except ValueError:
            binversion = None
            consolewarning('checkcompatability() failed to parse version info string "{v}"'.format(v=version))
        except TypeError:
            # TypeError: 'NoneType' object is not subscriptable
            binversion = None

        if not binversion or not minversion:
            return

        if binversion >= minversion:
            debugmessage('checkcompatability() says that {b} {x} >= {y}'.format(b=extbin, x=v[1], y=vmin))
            pass
        else:
            w = '{b} is out of date. You have {x}. You need {y}. Some/Many functions are likely to fail.'
            consolewarning(w.format(b=extbin, x=v[1], y=vmin), color='red')
            w = 'You should either upgrade {b} or disable the helper in "settings/helpersettings.py"'
            consolewarning(w.format(b=extbin))
            consolewarning('I am now forcibly disabling the grabber...')
            hipparchia.config['EXTERNALGRABBER'] = False

    return


def dbversionchecking(activedbs: list) -> str:
    """

    send a warning if the corpora were built from a different template than the one active on the server

    :param activedbs:
    :param expectedsqltemplateversion:
    :return:
    """

    dbconnection = ConnectionObject()
    cursor = dbconnection.cursor()

    activedbs += ['lx', 'lm']
    labeldecoder = {
        'lt': 'The corpus of Latin authors',
        'gr': 'The corpus of Greek authors',
        'in': 'The corpus of classical inscriptions',
        'dp': 'The corpus of papyri',
        'ch': 'The corpus of Christian era inscriptions',
        'lx': 'The lexical database',
        'lm': 'The parsing database'
    }

    q = 'SELECT corpusname, templateversion, corpusbuilddate FROM builderversion'

    warn = """
        WARNING: VERSION MISMATCH"""
    info = """
        {d} has a builder template version of >>{v}<<
        (and was compiled {t})
        This version of HipparchiaServer expects the template version to be >>{e}<<.
        You should either rebuild your data or revert to a compatible version of HipparchiaServer
        FAILED SEARCHES / UNEXPECTED OUTPUT POSSIBLE
        """
    build = """
        Before rebuilding please fetch {v} (or later) of HipparchiaBuilder.
    """
    try:
        cursor.execute(q)
        results = cursor.fetchall()
    except:
        # UndefinedTable, presumably: 'relation "builderversion" does not exist'
        # the only way to see this is to run the Server without a build inside the DB?
        dbconnection.connectioncleanup()
        return str()

    corpora = {r[0]: (r[1], r[2]) for r in results}

    for db in activedbs:
        if db in corpora:
            if int(corpora[db][0]) != SQLTEMPLATE:
                consolewarning(warn, baremessage=True, color='red')
                consolewarning(info.format(d=labeldecoder[db], v=corpora[db][0], t=corpora[db][1],
                                           e=SQLTEMPLATE), baremessage=True, color='yellow')
                consolewarning(build.format(v=BUILDERMIN), baremessage=True)

    buildinfo = ['\t{corpus}: {date} [{prolix}]'.format(corpus=c, date=corpora[c][1], prolix=labeldecoder[c])
                for c in sorted(corpora.keys())]
    buildinfo = '\n'.join(buildinfo)

    dbconnection.connectioncleanup()

    return buildinfo