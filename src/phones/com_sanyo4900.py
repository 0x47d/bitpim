### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
### Maybe Scott Craig and Alan Gonzalez belong here too??
### Copyright (C) 2003 Stephen Wood <sawecw@users.>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

"""Talk to the Sanyo SCP-4900 cell phone"""

# standard modules
import re
import time
import cStringIO
import sha

# my modules
import common
import commport
import copy
import p_sanyo
import com_brew
import com_phone
import com_sanyo
import prototypes

class Phone(com_phone.Phone,com_brew.BrewProtocol,com_sanyo.SanyoPhonebook):
    "Talk to the Sanyo SCP-4900 cell phone"
    desc="SCP-4900"

    getwallpapers=None
    getringtones=None
    getcalendar=None
    
    def __init__(self, logtarget, commport):
        com_phone.Phone.__init__(self, logtarget, commport)
	com_brew.BrewProtocol.__init__(self)
        com_sanyo.SanyoPhonebook.__init__(self)
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
        # For now, just read a handful of entries to get the hang of things.
        # There are potentially 300 entries.  To know which one are actually
        # in use we have to read in some buffers first.  
        buf=prototypes.buffer(self.getsanyobuffer(0x3c, 0x43, "sort buffer"))
        sortstuff=p_sanyo.pbsortbuffer()
        sortstuff.readfrombuffer(buf)
        buf=prototypes.buffer(self.getsanyobuffer(0x46, 0x47, "ringer/picture assignments"))
        ringpic=p_sanyo.ringerpicbuffer()
        ringpic.readfrombuffer(buf)

        numentries=sortstuff.slotsused
        self.log("There are %d entries" % (numentries,))
        
        count = 0
        for i in range(0, sortstuff.numpbslots):
            if sortstuff.usedflags[i].used:
                ### Read current entry
                req=p_sanyo.phonebookslotrequest()
                req.slot = i
                res=self.sendpbcommand(req, p_sanyo.phonebookslotresponse)
                self.log("Read entry "+`i`+" - "+res.entry.name)

                entry=self.extractphonebookentry(res.entry, result)
                pbook[i]=entry 
                self.progress(count, numentries, res.entry.name)
                count+=1
        
        self.progress(numentries, numentries, "Phone book read completed")
        result['phonebook']=pbook
        return pbook

    def extractphonebookentry(self, entry, fundamentals):
        """Return a phonebook entry in BitPim format"""
        res={}
        # serials
        res['serials']=[ {'sourcetype': 'scp4900', 'serial1': entry.slot, 'serial2': entry.slotdup,
                          'sourceuniqueid': fundamentals['uniqueserial']} ]
        # only one name
        res['names']=[ {'full': entry.name} ]
        # only one email
        res['emails']=[]
        if len(entry.email):
            res['emails']=[ {'email': entry.email} ]
        # only one url
        res['urls']=[]
        if len(entry.url):
            res['urls']=[ {'url': entry.url} ]
        # private
        res['flags']=[ {'secret': entry.secret } ]
        # 7 phone numbers
        res['numbers']=[]
        numberindex = 0
        for type in ['home', 'office', 'mobile', 'pager', 'data','fax','other']:
            if len(entry.numbers[numberindex].number):
                res['numbers'].append({'number': entry.numbers[numberindex].number, 'type': type })
            
            numberindex+=1
        return res

class Profile:
    pass
