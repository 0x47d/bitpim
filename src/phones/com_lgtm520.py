### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2003 Scott Craig <scott.craig@shaw.ca>
### Copyright (C) 2003 Alan Gonzalez <agonzalez@yahoo.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"Talk to the LG TM520/VX10 cell phone"

# standard modules
import time
import cStringIO
import sha

# my modules
import common
import p_lgtm520
import com_brew
import com_phone
import com_lg
import prototypes

class Phone(com_phone.Phone,com_brew.BrewProtocol,com_lg.LGPhonebook):
    "Talk to the LG TM520/VX10 cell phone"
    desc="LG-TM520/VX10"

    # phone uses Jan 1, 1980 as epoch.  Python uses Jan 1, 1970.  This is difference
    # plus a fudge factor of 5 days, 16 hours for no reason I can find
    _tm520epochtounix=315532800+446400
    _brewepochtounix=315532800+446400  # trying to override inherited entry

    getwallpapers=None
    getringtones=None
    
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
        req=p_lgtm520.pbstartsyncrequest()
        self.sendpbcommand(req, p_lgtm520.pbstartsyncresponse)
        
        self.log("Reading number of phonebook entries")
        req=p_lgtm520.pbinitrequest()
        res=self.sendpbcommand(req, p_lgtm520.pbinitresponse)
        numentries=res.numentries
        self.log("There are %d entries" % (numentries,))
        
        ### Advance to first entry
        req=p_lgtm520.pbinforequest()
        res=self.sendpbcommand(req, p_lgtm520.pbnextentryresponse) ## NOT inforesponse
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
            res=self.sendpbcommand(req, p_lgtm520.pbnextentryresponse)

        req=p_lgtm520.pbendsyncrequest()
        self.sendpbcommand(req, p_lgtm520.pbendsyncresponse)

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
        numbernumber=0
        for type in ['home', 'office', 'mobile', 'pager', 'data/fax']:
                res['numbers'].append({'number': entry.numbers[numbernumber].number, 'type': type })
        return res

    def getcalendar(self,result):
        res={}
        # Now read schedule
        buf=prototypes.buffer(self.getfilecontents("sch/sch_00.dat"))
        sc=p_lgtm520.schedulefile()
        sc.readfrombuffer(buf)
        self.logdata("Calendar", buf.getdata(), sc)
        for event in sc.events:
            entry={}
            entry['pos']=event.pos
            date = event.date
            if date == 0x11223344: continue  # blanked entry
            date += self._tm520epochtounix
            entry['start'] = self.decodedate(date)
            entry['description'] = event.description
            entry['repeat'] = None
            res[event.pos]=entry

        result['calendar']=res
        return result

    def decodedate(self,val):
        """Unpack 32 bit value into date/time

        @rtype: tuple
        @return: (year, month, day, hour, minute)
        """
        return time.localtime(val)[:5]

class Profile:
    WALLPAPER_WIDTH=100
    WALLPAPER_HEIGHT=100
