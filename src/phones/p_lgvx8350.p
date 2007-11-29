### BITPIM
###
### Copyright (C) 2007 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to LG VX8350"""

from p_lgvx8550 import *
# same as the VX-8550 except as noted below

NUMPHONEBOOKENTRIES=1000
NUMPHONENUMBERENTRIES=5000

# sizes of pbfileentry and pnfileentry
PHONEBOOKENTRYSIZE=256
PHONENUMBERENTRYSIZE=64

NUM_EMAILS=2
NUMPHONENUMBERS=5

pb_file_name    = 'pim/pbentry.dat'
pn_file_name    = 'pim/pbnumber.dat'
speed_file_name = 'pim/pbspeed.dat'
ice_file_name   = 'pim/pbice.dat'

%}
