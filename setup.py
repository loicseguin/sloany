# -*- coding: utf-8 -*-

from distutils.core import setup

setup(
    name = 'sloany',
    scripts = ['sloany.py'],
    version = '0.1dev',
    description = 'A command line utility to query the SDSS database and retrieve spectra files.',
    author = 'Loïc Séguin-C.',
    author_email = 'loicseguin@gmail.com',
    url = 'https://github.com/loicseguin/sloany',
    download_url = 'https://github.com/loicseguin/sloany/tarball/master',
    keywords = ['SDSS', 'Sloan', 'stars', 'astronomy'],
    classifiers = [
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Database :: Front-Ends',
        'Topic :: Scientific/Engineering :: Astronomy'
        ],
    long_description = open('README.rst', 'r').read()
)
