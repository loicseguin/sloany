#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
======
sloany
======

A command line utility to query the SDSS database and retrieve spectra files.

This utility is inspired by sqlcl.py by Tamas Budavari <budavari@jhu.edu>.

Usage
=====
::

    sloany [OPTIONS] FILES

FILES is a list of filenames containing SQL queries.

Options
-------
    -q --query  : specify SQL query on the command line
    -f --fetch  : fetch the (lite) spectra for the objects
    -r --reduce : read the FITS file and produce a spectrum file readable by
                  fitchi2
    -v	        : print version
    -h	        : print help message

Example
=======

The following example retrieves survey name, plate number, MJD date,
fiber number, right ascension and declination for all objects with the
ANCILLARY_TARGET1 flag set to WHITEDWARF_NEW (objects for these spectra have
been observed by the BOSS spectrometer).::

    sloany -q "select top 10 s.survey,s.plate,s.mjd,s.fiberid,s.ra,s.dec from \
        bestdr9..SpecObj as s where s.zWarning = 0 and \
        ((s.ancillary_target1 & WHITEDWARF_NEW) > 0) and s.class = STAR"

The results of this query are::

    mjd      plate    fiberid  survey   ra        dec
    ======== ======== ======== ======== ========= ==========
    55742    4724     734      boss     241.30465 26.982166
    55361    4077     709      boss     319.35173 4.7338973
    55361    4077     755      boss     319.5121  4.4102067
    55589    4446     190      boss     126.03102 31.702923
    55737    4711     262      boss     211.08108 38.303709
    55501    4096     836      boss     329.32275 6.06972922
    55691    4860     700      boss     217.07998 7.0316488
    55691    4860     830      boss     217.61187 7.5803584
    55680    4175     460      boss     254.04522 19.700587
    55277    3873     672      boss     217.85955 31.020043

See http://www.sdss3.org/dr9/spectro/targets.php for a list of target flags.

"""

from __future__ import print_function

__author__ = "Loïc Séguin-C. <loicseguin@gmail.com>"
__license__ = "BSD"
__version__ = '0.1dev'


import argparse
import os
import pyfits
import sys
try:
    import urllib.request as request
    import urllib.parse as parse
except ImportError:
    # Good old Python 2.
    import urllib as request
    import urllib as parse
    input = raw_input


skyserver_url='http://skyserver.sdss3.org/public/en/tools/search/x_sql.asp'
spectra_url = 'http://data.sdss3.org/sas/dr9/sdss/spectro/redux/%s/spectra/lite'


# Target flags for white dwarfs
# ANCILLARY_TARGET1
WHITEDWARF_NEW = 2**42
WHITEDWARF_SDSS = 2**43

# BOSS_TARGET1
STD_WD = 2**21

# LEGACY_TARGET1
STAR_WHITE_DWARF = 2**19

TARGET_FLAGS = ['WHITEDWARF_NEW', 'WHITEDWARF_SDSS', 'STD_WD',
                'STAR_WHITE_DWARF']

# Classes
GALAXY = 'GALAXY'
QSO = 'QSO'
STAR = 'STAR'
CLASSES = ['GALAXY', 'QSO', 'STAR']


def remove_comments(stmt):
    """Remove comments from SQL statement."""
    fsql = ''
    for line in stmt.split('\n'):
        fsql += line.split('--')[0] + '\n'
    return fsql


def subst_flags(stmt):
    """Replace any target flag or class name with the appropriate value."""
    for flag in TARGET_FLAGS:
        if flag in stmt:
            stmt = stmt.replace(flag, 'CAST(%d AS BIGINT)' % eval(flag))
    for classn in CLASSES:
        if classn in stmt:
            stmt = stmt.replace(classn, "'%s'" % eval(classn))
    return stmt


def exec_query(query):
    """Execute the SQL query and return a list of results.

    The results are returned as a list of dictionaries. Each result is a
    dictionary keyed by column name in the query. The values are the results of
    the query.

    """
    query = remove_comments(query)
    query = subst_flags(query)
    params = parse.urlencode({'cmd': query, 'format': 'csv'})
    raw_results = request.urlopen(skyserver_url + '?%s' % params)
    raw_results = raw_results.read().decode('utf-8')
    raw_results = raw_results.strip().split('\n')

    results = []
    # First line of results is a coma separated list of column names.
    keys = raw_results[0].split(',')

    ## Other lines are csv for objects that match the query.
    for line in raw_results[1:]:
        results.append(dict(zip(keys, line.split(','))))
    return results


def fetch_spectra(spec_triples):
    """Fetch the spectra for all objects in spec_triples. Ask user confirmation
    first.

    ``spec_triples`` is a list of triples (filename, plate, run2d).

    """
    spec_files = list(spec_triples)
    existing = []
    for specfile in spec_files:
        if os.path.exists(specfile[0]):
            existing.append(specfile)

    # Ask user if he wants to fetch the spectra.
    if existing:
        print('\nSome spectra seem to be already present in the current ' +
              'directory.\nDo you want to fetch all spectra [A], ' +
              'only the missing spectra [Y], or nothing [N].')
        if len(spec_files) <= 10:
            for specfile in spec_files:
                if specfile in existing:
                    print(specfile[0] + '\tExisting')
                else:
                    print(specfile[0])
        else:
            print("{} spectra files".format(len(spec_files)))
            print("{} existing files".format(len(existing)))
        answer = input('A/Y/N [Y]:  ')
        answer = answer or 'Y'
        if answer.upper() in ('Y', 'YES'):
            for specfile in existing:
                spec_files.remove(specfile)
        if answer.upper() in ('A', 'ALL'):
            answer = 'Y'
    else:
        print('\nDo you want to fetch the following spectra?')
        if len(spec_files) <= 10:
            for specfile in spec_files:
                print(specfile[0])
        else:
            print("{} spectra files".format(len(spec_files)))
        answer = input('Y/N [Y]:  ')
        answer = answer or 'Y'

    if answer.upper() not in ('Y', 'YES'):
        return
    for specfile in spec_files:
        if specfile[2] is None:
            print('WARNING: to fetch the spectra, query must select run2d.' +
                    ' Skipping file.', file=sys.stderr)
            continue
        url = (spectra_url % specfile[2] +
                '/{:04d}/'.format(int(specfile[1])) + specfile[0])
        print('Fetching %s...' % specfile[0])
        try:
            request.urlretrieve(url, specfile[0])
        except (ValueError, IOError):
            print('WARNING: Could not retrieve {} at {}.'.format(specfile[0],
                  url), file=sys.stderr)


def reduce_spectra(files):
    """Produce a clean text file containing the spectra for each file in
    files."""
    print('\nDo you want to reduce the following spectra?')
    if len(files) <= 10:
        for fname in files:
            if fname:
                print(fname)
    else:
        print("{} spectra files".format(len(files)))
    answer = input('Y/N [Y]:  ')
    answer = answer or 'Y'
    if answer.upper() not in ('Y', 'YES'):
        return
    for fname in files:
        if not fname:
            continue
        print('Reducing {}'.format(fname))
        f = pyfits.open(fname)
        coadd = f[1]
        fluxes = coadd.data.field('flux')
        wavs = 10**coadd.data.field('loglam')
        assert len(fluxes) == len(wavs)
        out_fname = os.path.splitext(os.path.basename(fname))[0] + '_red'
        write_flux(out_fname, wavs, fluxes)


def write_flux(fname, wavs, flux):
    """Write the flux to file named fname in a format that fitchi2 understands."""
    f = open(fname, 'w')
    f.write(str(len(wavs)))
    for i, wav in enumerate(wavs):
        if i % 10 == 0:
            f.write('\n')
        f.write('%10.2f' % wav)
    for i, fluxi in enumerate(flux):
        if i % 6 == 0:
            f.write('\n')
        f.write('%12.5e' % fluxi)
    f.write('\n')
    f.close()
    return


def print_results(results):
    """Print the results of the query."""
    if not results:
        print('Query returned no results')
        return
    keys = results[0].keys()
    for key in keys:
        print('{:<11}'.format(key), end='')
    print()
    for key in keys:
        print('{:<11}'.format(10*'='), end='')
    print()
    for result in results:
        for key in keys:
            print('{:<11}'.format(result[key]), end='')
        print()


def run(argv=sys.argv[1:]):
    """Parse the command line arguments and run the appropriate command."""
    clparser = argparse.ArgumentParser(
            description='Search SDSS and fetch spectra files.')
    clparser.add_argument('-v', '--version', action='version',
            version='%(prog)s ' + __version__)
    clparser.add_argument('-q', '--query',
            help='SQL query to execute on the skyserver')
    clparser.add_argument('filenames', help='files containing SQL commands to be'
            + ' executed on the skyserver', nargs='*')
    clparser.add_argument('-f', '--fetch', action='store_true',
            help='fetch the spectrum file for each object')
    clparser.add_argument('-r', '--reduce', action='store_true',
            help='create a file with the wavelengths and fluxes')
    args = clparser.parse_args(argv)

    # Make a list of all queries.
    queries = []
    if args.query:
        queries.append(args.query)
    for fname in args.filenames:
        try:
            queries.append(open(fname).read())
        except IOError:
            print('WARNING: Could not open %s for reading.' % fname,
                  file=sys.stderr)
            sys.exit(1)

    # Execute all queries.
    for query in queries:
        try:
            results = exec_query(query)
        except urllib.error.URLError as e:
            print('ERROR: could not connect to URL', file=sys.stderr)
            sys.exit(1)
        if not results:
            print('ERROR: query did not provide any results.', file=sys.stderr)
            sys.exit(1)
        print_results(results)
        if args.fetch or args.reduce:
            spec_files = []
            for obj in results:
                try:
                    specfile = ('spec-%04d-%05d-%04d.fits' %
                                (int(obj['plate']), int(obj['mjd']),
                                int(obj['fiberid'])))
                    spec_files.append((specfile, obj['plate'],
                                       obj.get('run2d')))
                except KeyError:
                    print(results)
                    sys.exit(1)
        if args.fetch:
            fetch_spectra(spec_files)
        if args.reduce:
            reduce_spectra([fname for fname, plate, run2d in spec_files])


if __name__=='__main__':
    run()

