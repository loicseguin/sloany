#!/usr/bin/env python3

"""
======
sloany
======

A command line utility to query the SDSS database and retreive spectra files.

This utility is inspired by sqlcl.py by Tamas Budavari <budavari@jhu.edu>.

Usage
=====
::

    sloany [OPTIONS] FILES

Options
-------
    -q query  : specify SQL query on the command line
    -v	      : print version
    -h	      : print help message

"""


__author__ = "Loïc Séguin-C. <loicseguin@gmail.com>"
__license__ = "BSD"
__version__ = '0.1'


import argparse
import os
import pyfits
import sys
import urllib.request
import urllib.parse


skyserver_url='http://skyserver.sdss3.org/public/en/tools/search/x_sql.asp'
boss_url = 'http://data.sdss3.org/sas/dr9/boss/spectro/redux/v5_4_45/spectra/lite'
sdss_url = 'http://data.sdss3.org/sas/dr9/sdss/spectro/redux/lite'


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
    params = urllib.parse.urlencode({'cmd': query, 'format': 'csv'})
    raw_results = urllib.request.urlopen(skyserver_url + '?%s' % params)
    raw_results = raw_results.read().decode('utf-8')
    raw_results = raw_results.strip().split('\n')

    results = []
    # First line of results is a coma separated list of column names.
    keys = raw_results[0].split(',')

    ## Other lines are csv for objects that match the query.
    for line in raw_results[1:]:
        results.append(dict(zip(keys, line.split(','))))
    return results


def fetch_spectra(spec_files):
    """Fetch the spectra for all objects in spec_files. Ask user confirmation
    first.
    
    ``spec_files`` is a list of triples (filename, plate, survey).
    
    """
    existing = []
    for specfile in spec_files:
        if os.path.exists(specfile[0]):
            existing.append(specfile)

    # Ask user if he wants to fetch the spectra.
    if existing:
        print('Some spectra seem to be already present in the current ' +
              'directory.\nDo you want to fetch all spectra [A], ' +
              'only the missing spectra [Y], or nothing [N].')
        for specfile in spec_files:
            if specfile in existing:
                print(specfile[0] + '\tExisting')
            else:
                print(specfile[0])
        answer = input('A/Y/N [Y]:  ')
        answer = answer or 'Y'
        if answer.upper() in ('Y', 'YES'):
            for specfile in existing:
                spec_files.remove(specfile)
        if answer.upper() in ('A', 'ALL'):
            answer = 'Y'
    else:
        print('Do you want to fetch the following spectra?')
        for specfile in spec_files:
            print(specfile[0])
        answer = input('Y/N [Y]:  ')
        answer = answer or 'Y'

    if answer.upper() not in ('Y', 'YES'):
        return
    for specfile in spec_files:
        if specfile[2].upper() == 'BOSS':
            url = boss_url + '/%s/' % specfile[1] + specfile[0]
        elif specfile[2].upper() == 'SDSS':
            url = sdss_url + '/%s/' % specfile[1] + specfile[0]
        print('Fetching %s...' % specfile[0])
        try:
            urllib.request.urlretrieve(url, specfile[0])
        except (ValueError, IOError):
            print('WARNING: Could not retrieve %s.' % specfile[0],
                    file=sys.stderr)


def reduce_spectra(files):
    """Produce a clean text file containing the spectra for each file in
    files."""
    print('Do you want to reduce the following spectra?')
    for fname in files:
        if fname:
            print(fname)
    answer = input('Y/N [Y]:  ')
    answer = answer or 'Y'
    if answer.upper() not in ('Y', 'YES'):
        return
    for fname in files:
        if not fname:
            continue
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
        spec_files = []
        for obj in results:
            specfile = ('spec-%04d-%05d-%04d.fits' %
                    (int(obj['plate']), int(obj['mjd']), int(obj['fiberid'])))
            spec_files.append((specfile, obj['plate'], obj.get('survey')))
        fetch_spectra(spec_files)
        reduce_spectra([fname for fname, plate, survey in spec_files])


if __name__=='__main__':
    run()

