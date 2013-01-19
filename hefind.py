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


import argparse
import matplotlib.pyplot as plt
import numpy
import os
import scipy
import scipy.ndimage.morphology
import sys


# The 3888.65 He I line is very close to lots of strong lines for other
# elements and may lead to many false positives.
HELIUM_I_LINES = [3888.65, 4471.5, 5015.678, 5875.6404, 6678.1517, 7065.2153]
HELIUM_II_LINES = [4685.7]
HELIUM_LINES = HELIUM_I_LINES + HELIUM_II_LINES


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
    plt.ylabel(r'$Flux$', size=16)
    #plt.axes().minorticks_on()


def make_spectrum_figure(f):
    """Create a figure showing spectrum contained in file f."""
    nb_freqs = int(f.readline().split()[0])
    freqs = read_list(f, nb_freqs)
    fluxes = read_list(f, nb_freqs)
    plot_spectrum(freqs, fluxes)
    plt.show()


def find_centers(line_complex):
    """Given a line complex in the (smoothed, corrected) spectrum, determine
    all line centers using a zero crossings approach."""
    # There is a line where the flux is at a minimum, i.e., the second
    # derivative is positive.
    diff2 = numpy.diff(numpy.sign(numpy.diff(line_complex)))
    zero_crossings = numpy.where(diff2 > 0.)[0]
    return zero_crossings + 1


def find_lines(fluxes, smoothed, corrected, threshold=1., fraction_pts=0.2,
        wavs=None, plot=False):
    """Find all the spectral lines (i.e., valleys) in the spectrum ``fluxes``
    given a corrected version of the spectrum ``corrected``.

    Return a list of pairs (line center index, signal to noise ratio for the
    line).
    """
    line_indices = []
    window_width = int(len(fluxes) * fraction_pts / 2) * 2 + 1
    half_width = window_width // 2
    # Reflect the endpoints of the spectrum.
    x = numpy.concatenate((fluxes[half_width:0:-1], fluxes,
        fluxes[-2:-half_width - 2:-1]))
    xs = numpy.concatenate((smoothed[half_width:0:-1], smoothed,
                           smoothed[-2:-half_width - 2:-1]))
    # Residual decribes the noise.
    residual = numpy.abs(x - xs)
    # The noise is the average residual over a window of width
    # ``window_width``.  noise has same length as fluxes
    noise = numpy.convolve(residual, numpy.ones(window_width) / window_width,
                           'valid')

    # If the plot flag is on, show the line complex and the lines that are
    # found.
    if plot:
        if wavs is None:
            wavs = range(len(fluxes))
        plt.plot(wavs, corrected, wavs, -noise)

    # A line complex is found if the flux value is smaller than ``threshold``
    # times the average noise.
    pos = 0
    max_pos = len(corrected)
    while pos < max_pos:
        min_pos = pos # Lowest index for line
        while (pos < max_pos and corrected[pos] < -threshold * noise[pos]):
            pos += 1
        # Check if a line complex has been found
        if pos > min_pos:
            if plot:
                plt.axvspan(wavs[min_pos], wavs[pos - 1], color='g', alpha=0.1)
            # Find the line center for each line in the complex.
            centers = min_pos + find_centers(corrected[min_pos:pos])

            # Calculate signal to noise ratio for the line.
            for center in centers:
                sn = residual[center + half_width] / noise[center]
                line_indices.append((center, sn))
        pos += 1

    if plot:
        for line, sn in line_indices:
            plt.axvline(x=wavs[line], color='r', alpha=0.3, linewidth=2)
        plt.show()

    return line_indices


def baseline(fluxes, fraction_pts=0.2):
    """Correct the baseline of the spectrum whose ordinate values are in
    ``fluxes``. Baseline correction uses the white top hat algorithm."""
    nb_pts = fraction_pts * len(fluxes)
    # Top hat fits the lowest values. Since most spectrum have
    # absorption lines and that the continuum plays the role of baseline, the
    # flux must first be reflected along the abscissa.
    y = -fluxes
    structure = numpy.ones(nb_pts)
    z = scipy.ndimage.morphology.white_tophat(y, structure=structure,
                                              mode='reflect')

    # Reflect the baseline corrected flux and return it.
    return -z


def smooth_spectrum(fluxes, window_width=7, passes=3):
    """Produce a smoothed version of the spectra using a sliding window
    approach."""
    smoothed = numpy.array(fluxes)
    weights = numpy.ones(window_width) / window_width
    half_width = window_width // 2
    for i in range(passes):
        smoothed = numpy.concatenate((smoothed[half_width:0:-1], smoothed,
                smoothed[-2:-half_width - 2: -1]))
        smoothed = numpy.convolve(smoothed, weights, 'valid')
    return smoothed


def find_helium(fname, plot=False, plot_all=False, verbose=False,
        threshold=1.0):
    """Open the spectrum file ``fname`` and determine whether there are traces
    of helium."""
    f = open(fname)
    nb_wavs = int(f.readline().split()[0])
    wavs = read_list(f, nb_wavs)
    fluxes = read_list(f, nb_wavs)
    f.close()

    # Smooth the spectrum and correct its baseline, i.e., transform the
    # continuum into a straight line.
    smoothed = smooth_spectrum(fluxes)
    corrected = baseline(smoothed)
    #plot_spectrum(wavs, fluxes)
    #plt.plot(wavs, smoothed)
    #plot_spectrum(wavs, corrected)
    #plt.show()

    line_indices_sn = find_lines(fluxes, smoothed, corrected, wavs=wavs,
            plot=plot_all, threshold=threshold)

    found = []
    for line_index, sn in line_indices_sn:
        for heline in HELIUM_LINES:
            # Tolerate a 5 angstrom difference.
            if abs(wavs[line_index] - heline) < 5.:
                found.append((wavs[line_index], sn))
    if len(found) >= 2:
        print(fname)
        if verbose:
            for line, sn in found:
                print('   line {:.1f} angstrom; S/N {:.2f}'.format(line, sn))
        if plot:
            plot_spectrum(wavs, fluxes)
            for line, sn in found:
                plt.axvline(x=line, color='r', alpha=0.2, linewidth=2)
            plt.show()


def run(argv=sys.argv[1:]):
    """Parse the command line arguments and run the appropriate command."""
    clparser = argparse.ArgumentParser(description='Determine whether there' +
            ' are traces of helium in a given spectrum.')
    clparser.add_argument('-v', '--version', action='version',
            version='%(prog)s ' + __version__)
    clparser.add_argument('-a', '--plot-all', action='store_true',
            help='draw plot showing all the lines found in spectrum')
    clparser.add_argument('-p', '--plot', action='store_true',
            help='draw plot showing helium lines in spectrum')
    clparser.add_argument('filenames', nargs='+',
            help='spectrum files to process')
    clparser.add_argument('--verbose', action='store_true',
            help='verbose output (prints lines and signal to noise ratio)')
    clparser.add_argument('-t', '--threshold', nargs='?', type=float,
            const=1.0, default=1.0,
            help='a signal raises that many times above the background noise')
    args = clparser.parse_args(argv)

    for fname in args.filenames:
        find_helium(fname, plot=args.plot, plot_all=args.plot_all,
                verbose=args.verbose, threshold=args.threshold)


if __name__ == "__main__":
    run()

