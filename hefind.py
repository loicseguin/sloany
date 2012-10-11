#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
======
hefind
======

Given an observed spectra files, determine whether there are signs of helium or
not.

Copyright (c) 2012, Loïc Séguin-C. <loicseguin@gmail.com>

"""


__author__ = "Loïc Séguin-C. <loicseguin@gmail.com>"
__license__ = "BSD"
__version__ = '0.1dev'


import matplotlib.pyplot as plt
import numpy
import os
import scipy
import sys


HELIUM_LINES = [3888.65, 4471.5, 5015.678, 5875.6404, 6678.1517, 7065.2153]
NB_FOR_AVG = 5
NB_CONTINUUM = 20
TOL = 2.


def read_list(f, nb_freqs):
    """Read nb_freqs real values from f and return the corresponding list."""
    alist = []
    while len(alist) < nb_freqs:
        line = f.readline()
        splitted = line.split()
        well_splitted = True
        for entry in splitted:
            well_splitted = well_splitted and entry.count('.') <= 1
        if well_splitted:
            entries = splitted
        else:
            if line.count('-') > 0:
                # Probably coming from an SDSS spectrum.
                entries = [line[i:i+12] for i in range(0, len(line) - 1, 12)]
            else:
                entries = [line[i:i+8] for i in range(0, len(line) - 1, 8)]
        for entry in entries:
            try:
                alist.append(float(entry))
            except ValueError:
                # If conversion to float fails, put 0 instead.
                alist.append(0)
    return alist


def plot_spectrum(freqs, fluxes, min_lambda=3200, max_lambda=7000):
    """Plot the flux as a function of frequency."""
    plt.plot(freqs, fluxes)
    plt.xlim((min_lambda, max_lambda))
    #plt.ylim((0.000045, 0.000058))
    plt.xlabel(r'$\lambda\, (\AA)$', size=16)
    plt.ylabel(r'$H_\nu$', size=16)
    #plt.axes().minorticks_on()


def make_spectrum_figure(f):
    """Create a figure showing spectrum contained in file f."""
    nb_freqs = int(f.readline().split()[0])
    freqs = read_list(f, nb_freqs)
    fluxes = read_list(f, nb_freqs)
    plot_spectrum(freqs, fluxes)
    plt.show()


def noise(wavs, fluxes):
    """Calculate the amplitude of the noise for the spectrum given by wavs and
    fluxes."""
    pass


def find_line(line, wavs, fluxes):
    """Determine whether there is an absorption or emission line at wavelength
    ``line`` for the spectra given by ``wavs`` and ``flux``."""
    for i, wav in enumerate(wavs):
        if wav > line:
            break
    # Find the NB_FOR_AVG wavelengths around the line center and calculate the
    # average. Do the same for the continuum to the left and to the right.
    low = i - NB_FOR_AVG//2
    hi = low + NB_FOR_AVG + 1
    in_line = (sum(wavs[low:hi])/NB_FOR_AVG, sum(fluxes[low:hi])/NB_FOR_AVG)
    low = low - NB_CONTINUUM
    hi = low + NB_FOR_AVG + 1
    blue = (sum(wavs[low:hi])/NB_FOR_AVG, sum(fluxes[low:hi])/NB_FOR_AVG)
    low = i + NB_FOR_AVG//2 + NB_CONTINUUM
    hi = low + NB_FOR_AVG + 1
    red = (sum(wavs[low:hi])/NB_FOR_AVG, sum(fluxes[low:hi])/NB_FOR_AVG)

    # If the flux in the line is above or below the linear interpolation
    # between the blue and the red points, then a line has been found.
    flux_continuum = ((in_line[0] - blue[0])*(blue[1] - red[1]) / (blue[0] -
                      red[0]) + blue[1])
    diff = flux_continuum - in_line[1]
    if diff > 0 and diff > TOL:
        return 'ABSORPTION'
    elif diff < 0 and abs(diff) > TOL:
        return 'EMISSION'
    return None


if __name__ == "__main__":
    for fname in sys.argv[1:]:
        f = open(fname)
        nb_wavs = int(f.readline().split()[0])
        wavs = read_list(f, nb_wavs)
        fluxes = read_list(f, nb_wavs)
        found = []
        for line in HELIUM_LINES:
            line_type = find_line(line, wavs, fluxes)
            if line_type:
                print('Found He {} line at {} angstrom'.format(line_type, line))
                found.append(line)
        if found:
            plot_spectrum(wavs, fluxes)
            plt.plot(found, [5 for wav in found], '|r', markersize=100)
            plt.show()

