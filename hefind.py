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
import scipy.ndimage.morphology
import sys


HELIUM_LINES = [3888.65, 4471.5, 5015.678, 5875.6404, 6678.1517, 7065.2153]
WINDOW_WIDTH = 7
TOLERANCE = 0.1


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
    return numpy.array(alist)


def plot_spectrum(freqs, fluxes, min_lambda=3700, max_lambda=8000):
    """Plot the flux as a function of frequency."""
    plt.plot(freqs, fluxes)
    plt.xlim((min_lambda, max_lambda))
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


def find_line(line, wavs, fluxes):
    """Determine whether there is an absorption or emission line at wavelength
    ``line`` for the spectra given by ``wavs`` and ``flux``."""
    for i, wav in enumerate(wavs):
        if wav > line:
            break
    # Find the NB_FOR_AVG wavelengths around the line center and calculate the
    # average. Do the same for the continuum to the left and to the right.
    low = i - NB_FOR_AVG//2
    hi = low + NB_FOR_AVG
    in_line = (numpy.mean(wavs[low:hi]), numpy.mean(fluxes[low:hi]))
    low = low - NB_CONTINUUM
    hi = low + NB_FOR_AVG
    blue = (numpy.mean(wavs[low:hi]), numpy.mean(fluxes[low:hi]))
    low = i + NB_FOR_AVG//2 + NB_CONTINUUM
    hi = low + NB_FOR_AVG
    red = (numpy.mean(wavs[low:hi]), numpy.mean(fluxes[low:hi]))

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


def find_minima(wavs, fluxes):
    """Find the minima in the spectra by using the zero crossings of the first
    derivative to identify the critical points. The flux should be smoothed
    before calling this function.

    """
    diff = np.diff(fluxes)
    zero_crossings = np.where(np.diff(np.sign(diff)))[0]


def baseline(fluxes):
    nbpts = 0.2*len(fluxes)
    y = -fluxes
    structure = numpy.ones(nbpts)
    z = scipy.ndimage.morphology.white_tophat(y, None, structure)
    return -z


def smooth_spectra(fluxes, window_width=7, passes=3):
    """Produce a smoothed version of the spectra using a sliding window
    approach."""
    flux_len = len(fluxes)
    smoothed = numpy.array(fluxes)
    resmoothed = numpy.array(fluxes)
    for j in range(passes):
        for i in range(flux_len):
            low = i - window_width // 2
            if low < 0: low = 0
            hi = low + window_width
            if hi > flux_len: hi = flux_len
            smoothed[i] = numpy.mean(resmoothed[low:hi])
        resmoothed = numpy.array(smoothed)
    return smoothed


if __name__ == "__main__":
    for fname in sys.argv[1:]:
        f = open(fname)
        nb_wavs = int(f.readline().split()[0])
        wavs = read_list(f, nb_wavs)
        fluxes = read_list(f, nb_wavs)
        smoothed = smooth_spectra(fluxes)
        basel = baseline(smoothed)
        #plot_spectrum(wavs, fluxes)
        #plot_spectrum(wavs, basel)
        #plt.show()

        min_flux = numpy.min(basel)
        threshold = 0.1*min_flux
        pos = 0
        lines = []
        while pos < len(basel):
            min_pos = pos
            while pos < len(basel) and basel[pos] < threshold:
                pos += 1
            if pos > min_pos:
                lines.append(wavs[(pos+min_pos)//2])
            pos += 1

        found = []
        for line in lines:
            for heline in HELIUM_LINES:
                if abs(line - heline) < 5.:
                    found.append(line)
        if len(found) >= 2:
            print(fname)

        if found:
            plot_spectrum(wavs, fluxes)
            ylims = plt.ylim()
            for line in found:
                plt.axvline(x=line, color='r', alpha=0.2, linewidth=2)
            plt.show()

