### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

# standard modules
import re
import time
import cStringIO
import sha

# my modules
import common
import commport
import copy
import p_lgtm520
import com_brew
import com_phone
import com_lg
import prototypes

class Phone(com_phone.Phone,com_brew.BrewProtocol,com_lg.LGPhonebook):
    "Talk to the LG VX4400 cell phone"

    desc="LG-TM520/VX10"
    
    def __init__(self, logtarget, commport):
        com_phone.Phone.__init__(self, logtarget, commport)
	com_brew.BrewProtocol.__init__(self)
        com_lg.LGPhonebook.__init__(self)
        self.log("Attempting to contact phone")
        self.mode=self.MODENONE

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI."""

        # use a hash of ESN and other stuff (being paranoid)
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        results['uniqueserial']=sha.new(self.getfilecontents("nvm/$SYS.ESN")).hexdigest()
        self.log("Fundamentals retrieved")
        return results

    def getphonebook(self,result):
        pbook={}
        self.log("Reading number of phonebook entries")
        req=p_lgtm520.pbinitrequest()
        res=self.sendpbcommand(req, p_lgvx4400.pbinitresponse)
        numentries=res.numentries
        self.log("There are %d entries" % (numentries,))
        for i in range(0, numentries):
            ### Read current entry
            req=p_lgtm520.pbreadentryrequest()
            res=self.sendpbcommand(req, p_lgtm520.pbreadentryresponse)
            self.log("Read entry "+`i`+" - "+res.entry.name)
            entry=self.extractphonebookentry(res.entry, result)
            pbook[i]=entry 
            self.progress(i, numentries, res.entry.name)
            #### Advance to next entry
            req=p_lgtm520.pbnextentryrequest()
            self.sendpbcommand(req, p_lgtm520.pbnextentryresponse)

        self.progress(numentries, numentries, "Phone book read completed")
        result['phonebook']=pbook
        return pbook

    def extractphonebookentry(self, entry, fundamentals):
        """Return a phonebook entry in BitPim format"""
        res={}
        # serials
        res['serials']=[ {'sourcetype': 'lgtm520', 'serial1': entry.serial1, 'serial2': entry.serial2,
                          'sourceuniqueid': fundamentals['uniqueserial']} ]
        # only one name
        res['names']=[ {'full': entry.name} ]
        # only one email
        res['emails']=[ {'email': entry.email} ]
        # 5 phone numbers
        res['numbers']=[]
        for number in entry.numbers:
            res['numbers'].append({'number': number.number, 'type': 'home' })
