### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Communicate with the LG VX6000 cell phone

The VX6000 is substantially similar to the VX4400 except that it supports more
image formats, has wallpapers in no less than 5 locations and puts things in
slightly different directories.

The code in this file mainly inherits from VX4400 code and then extends where
the 6000 has extra functionality

"""

# standard modules
import re
import time
import cStringIO
import sha

# my modules
import common
import copy
import p_lgvx6000
import com_lgvx4400
import com_brew
import com_phone
import com_lg
import prototypes

numbertypetab=( 'home', 'home2', 'office', 'office2', 'cell', 'cell2',
                    'pager', 'fax', 'fax2', 'none' )

        
class Phone(com_phone.Phone,com_brew.BrewProtocol,com_lg.LGPhonebook,com_lgvx4400.Phone):
    "Talk to the LG VX6000 cell phone"

    desc="LG-VX6000"

    wallpaperindexfilename="download/dloadindex/brewImageIndex.map"
    ringerindexfilename="download/dloadindex/brewRingerIndex.map"
    protocolclass=p_lgvx6000
    serialsname='lgvx6000'
    
    def __init__(self, logtarget, commport):
        #com_phone.Phone.__init__(self, logtarget, commport)
	#com_brew.BrewProtocol.__init__(self)
        #com_lg.LGPhonebook.__init__(self)

        # this calls all the above anyway
        com_lgvx4400.Phone.__init__(self,logtarget,commport)
        self.log("Attempting to contact phone")
        self.mode=self.MODENONE

class Profile(com_lgvx4400.Profile):

    serialsname='lgvx6000'

    def __init__(self):
        com_lgvx4400.Profile.__init__(self)
