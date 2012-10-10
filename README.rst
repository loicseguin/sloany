======
Sloany
======

Command line script to access Sloan Digital Sky Survey data.

This script can perform SQL queries on the data. It then offers to obtain the
spectra FITS file for the results.


Usage
=====

Execute with::

    $ ./sloany.py -q "SELECT top 10 s.survey,s.plate,s.mjd,s.fiberid
    FROM bestdr9..SpecObj AS s
    WHERE s.zWarning = 0
    AND ((s.ancillary_target1 & CAST(13194139533312 AS BIGINT)) > 0)
    AND s.class = 'star'"

The output should look like::

    survey,plate,mjd,fiberid
    boss,4075,55352,802
    boss,4724,55742,734
    boss,4724,55742,760
    boss,4077,55361,709
    boss,4077,55361,755
    boss,4446,55589,190
    boss,4711,55737,258
    boss,4711,55737,262
    boss,4096,55501,836
    boss,4860,55691,700

Then, ``sloany`` offers to fetch the spectra for each of these files::

    Do you want to fetch 10 spectra from the database? [Y/n]: 

When the user says yes, files spec-PLATE-MJD-FIBER.fits are fetched from
http://data.sdss3.org/sas/dr9/sdss/spectro/redux/lite or
http://data.sdss3.org/sas/dr9/boss/spectro/redux/v5_4_45/spectra/lite/PLATE.

