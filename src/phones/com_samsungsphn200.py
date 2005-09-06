### BITPIM
###
### Copyright (C) 2005 Stephen Wood <saw@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with a Samsung SPH-N200"""

import sha
import re
import struct

import common
import commport
import p_samsungsphn200
import p_brew
import com_brew
import com_phone
import com_samsung_packet
import prototypes

numbertypetab=('home','office','cell','pager','fax','none')

class Phone(com_samsung_packet.Phone):
    "Talk to a Samsung SPH-N200 phone"

    desc="SPH-N200"

    protocolclass=p_samsungsphn200
    serialsname='sphn200'
    __groups_range=xrange(5)

    imagelocations=()
        # offset, index file, files location, type, maximumentries
    
    __ams_index_file="ams/AmsRegistry"

    def __init__(self, logtarget, commport):
        com_samsung_packet.Phone.__init__(self, logtarget, commport)
        self.numbertypetab=numbertypetab
        self.mode=self.MODENONE

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI."""

        # use a hash of ESN and other stuff (being paranoid)
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        print "Calling setmode MODEMODEM"
        self.setmode(self.MODEMODEM)
        print "Getting serial number"
        results['uniqueserial']=sha.new(self.get_esn()).hexdigest()

        self.log("Fundamentals retrieved")
        return results

    def _setmodemodem(self):
        self.log("_setmodemodem")
        
        # Just try waking phone up first
        try:
            self.comm.sendatcommand("Z")
            self.comm.sendatcommand('E0V1')
            return True
        except:
            pass

        # Should be in modem mode.  Wake up the interface
        for baud in (0, 19200, 38400, 115200):
            self.log("Baud="+`baud`)
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue

            try:
                self.comm.sendatcommand("Z")
                self.comm.sendatcommand('E0V1')
                return True
            except:
                pass

        return False

    def getphonebook(self, result):
        """Read the phonebook data."""
        pbook={}
        self.setmode(self.MODEPHONEBOOK)

        count=0
        req=self.protocolclass.phonebookslotrequest()
        for slot in range(2,240):
            req.slot=slot
            res=self.sendpbcommand(req, self.protocolclass.phonebookslotresponse, fixup=self.pblinerepair)
            if len(res) > 0:
                lastname=res[0].entry.name
                self.log(`slot`+": "+lastname)
                entry=self.extractphonebookentry(res[0].entry, result)
                pbook[count]=entry
                count+=1
            self.progress(slot, self.protocolclass.NUMPHONEBOOKENTRIES, lastname)
        result['phonebook']=pbook

        return pbook
        
    def extractphonebookentry(self, entry, fundamentals):
        res={}

        res['serials']=[ {'sourcetype': self.serialsname,
                          'slot': entry.slot,
                          'sourceuniqueid': fundamentals['uniqueserial']} ]
        # only one name
        res['names']=[ {'full': entry.name} ]

        res['numbers']=[]
        secret=0

        for i in range(len(entry.numbers)):
            type = self.numbertypetab[entry.numbers[i].numbertype - 1]
            numhash = {'number': entry.numbers[i].number, 'type': type }
            res['numbers'].append(numhash)
            
        # Field after each number is secret flag.  Setting secret on
        # phone sets secret flag for every defined phone number
        res['flags']=[ {'secret': secret} ]

        return res


    getwallpapers=None
    getringtones=None

class Profile(com_samsung_packet.Profile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname
    phone_manufacturer='SAMSUNG'
    phone_model='SPH-N200'
    deviceclasses=("serial",)

    def __init__(self):
        com_samsung_packet.Profile.__init__(self)
        self.numbertypetab=numbertypetab

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        )

