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
    protocolclass=p_lgtm520
    serialsname='lgtm520'

    builtinringtones=( 'Standard1', 'Standard2', 'Standard3', 'Standard4',
                       'Standard5', 'Radetzky March', 'Nocturn', 'Carmen',
                       'La Traviata', 'Liberty Bell', 'Semper Fidelis',
                       'Take Me Out', 'Turkey In The Straw', 'We Wish...',
                       'Csikos Post', 'Bumble Bee Twist', 'Badinerie',
                       'Silken Ladder', 'Chestnut' )

    # phone uses Jan 1, 1980 as epoch.  Python uses Jan 1, 1970.  This is difference
    # plus a fudge factor of 5 days, 20 hours for no reason I can find
    _tm520epochtounix=315532800+460800
    _brewepochtounix=315532800+460800  # trying to override inherited entry
    _calrepeatvalues={ 0: None, 1: None, 2: 'daily' }

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
        res['serials']=[ {'sourcetype': self.serialsname, 'serial1': entry.serial1, 'serial2': entry.serial2,
                          'sourceuniqueid': fundamentals['uniqueserial']} ]
        # only one name
        res['names']=[ {'full': entry.name} ]
        # only one email
        res['emails']=[ {'email': entry.email} ]
	# private
        if entry.secret:
            # we only supply secret if it is true
            res['flags']=[ {'secret': entry.secret }]
        # 5 phone numbers
        res['numbers']=[]
        numbernumber=0
        for type in ['home', 'office', 'mobile', 'pager', 'data/fax']:
                res['numbers'].append({'number': entry.numbers[numbernumber].number, 'type': type })
                numbernumber+=1
        return res

    def savephonebook(self, data):
        # To write the phone book, we scan through all existing entries
        # and record their record number and serials.
        # We then delete any entries that aren't in data
        # We then write out our records, usng overwrite or append
        # commands as necessary
        serialupdates=[]
        existingpbook={} # keep track of the phonebook that is on the phone

        req=p_lgtm520.pbstartsyncrequest()
        self.sendpbcommand(req, p_lgtm520.pbstartsyncresponse)

        # similar loop to reading
        req=p_lgtm520.pbinitrequest()
        res=self.sendpbcommand(req, p_lgtm520.pbinitresponse)
        numexistingentries=res.numentries
        progressmax=numexistingentries+len(data['phonebook'].keys())
        progresscur=0
        self.log("There are %d existing entries" % (numexistingentries,))

        ### Advance to first entry
        req=self.protocolclass.pbinforequest()
        res=self.sendpbcommand(req, p_lgtm520.pbnextentryresponse) ## NOT inforesponse

        for i in range(0, numexistingentries):
            ### Read current entry
            req=self.protocolclass.pbreadentryrequest()
            res=self.sendpbcommand(req, self.protocolclass.pbreadentryresponse)

            entry={ 'number':  res.entry.entrynumber, 'serial1':  res.entry.serial1,
                    'serial2': res.entry.serial2, 'name': res.entry.name}
            assert entry['serial1']==entry['serial2'] # always the same
            self.log("Reading entry "+`i`+" - "+entry['name'])            
            existingpbook[i]=entry 

            self.progress(progresscur, progressmax, "existing "+entry['name'])
            #### Advance to next entry
            req=self.protocolclass.pbnextentryrequest()
            self.sendpbcommand(req, self.protocolclass.pbnextentryresponse)
            progresscur+=1
        # we have now looped around back to begining

        # Find entries that have been deleted
        pbook=data['phonebook']
        dellist=[]
        for i in range(0, numexistingentries):
            ii=existingpbook[i]
            serial=ii['serial1']
            item=self._findserial(serial, pbook)
            if item is None:
                dellist.append(i)

        progressmax+=len(dellist) # more work to do

        # Delete those entries
        for i in dellist:
            progresscur+=1
            numexistingentries-=1  # keep count right
            ii=existingpbook[i]
            self.log("Deleting entry "+`i`+" - "+ii['name'])
            req=self.protocolclass.pbdeleteentryrequest()
            req.serial1=ii['serial1']
            req.serial2=ii['serial2']
            req.entrynumber=ii['number']
            self.sendpbcommand(req, self.protocolclass.pbdeleteentryresponse)
            self.progress(progresscur, progressmax, "Deleting "+ii['name'])
            # also remove them from existingpbook
            del existingpbook[i]

        # counter to keep track of record number (otherwise appends don't work)
        counter=0
        # Now rewrite out existing entries
        keys=existingpbook.keys()
        existingserials=[]
        keys.sort()  # do in same order as existingpbook
        for i in keys:
            progresscur+=1
            ii=pbook[self._findserial(existingpbook[i]['serial1'], pbook)]
            self.log("Rewriting entry "+`i`+" - "+ii['name'])
            self.progress(progresscur, progressmax, "Rewriting "+ii['name'])
            entry=self.makeentry(counter, ii, data)
            counter+=1
            existingserials.append(existingpbook[i]['serial1'])
            req=self.protocolclass.pbupdateentryrequest()
            req.entry=entry
            res=self.sendpbcommand(req, self.protocolclass.pbupdateentryresponse)
            serialupdates.append( ( ii["bitpimserial"],
                                    {'sourcetype': self.serialsname, 'serial1': res.serial1, 'serial2': res.serial1,
                                     'sourceuniqueid': data['uniqueserial']})
                                  )
            assert ii['serial1']==res.serial1 # serial should stay the same

        # Finally write out new entries
        keys=pbook.keys()
        keys.sort()
        for i in keys:
            ii=pbook[i]
            if ii['serial1'] in existingserials:
                continue # already wrote this one out
            progresscur+=1
            entry=self.makeentry(counter, ii, data)
            counter+=1
            self.log("Appending entry "+ii['name'])
            self.progress(progresscur, progressmax, "Writing "+ii['name'])
            req=self.protocolclass.pbappendentryrequest()
            req.entry=entry
            res=self.sendpbcommand(req, self.protocolclass.pbappendentryresponse)
            serialupdates.append( ( ii["bitpimserial"],
                                     {'sourcetype': self.serialsname, 'serial1': res.newserial, 'serial2': res.newserial,
                                     'sourceuniqueid': data['uniqueserial']})
                                  )

        data["serialupdates"]=serialupdates

    def _findserial(self, serial, dict):
        """Searches dict to find entry with matching serial.  If not found,
        returns None"""
        for i in dict:
            if dict[i]['serial1']==serial:
                return i
        return None

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
            if event.state == 0 or event.repeat == 0: continue    # deleted entry
            if date == 0x11223344: continue  # blanked entry
            date += self._tm520epochtounix
            entry['start'] = self.decodedate(date)
            entry['end'] = self.decodedate(date)
            entry['description'] = event.description
            if event.pos == 0: entry['description'] = 'Wake Up'
            entry['alarm'] = 0
            if event.alarm & 0xB0 == 0xB0: entry['alarm'] = 1
            entry['ringtone'] = 0
            entry['changeserial'] = time.localtime(date)[8]
            entry['snoozedelay'] = 0
            entry['repeat'] = self._calrepeatvalues[event.repeat]
            res[event.pos]=entry

        result['calendar']=res
        return result

    def savecalendar(self, dict, merge):
        # ::TODO:: obey merge param
        # what will be written to the files
        eventsf=self.protocolclass.schedulefile()

        # what are we working with
        cal=dict['calendar']
        newcal={}
        keys=cal.keys()
        keys.sort()

        # number of entries
        numactiveitems=len(keys)
        self.log("There are %d calendar entries" % (numactiveitems,))
        counter = 1

        # Write out dummy alarm entry
        dummy=self.protocolclass.scheduleevent()
        dummy.pos = 0
        dummy.date = 0x11223344
        dummy.state = 0
        dummy.alarm = 0x80
        dummy.repeat = 0
        dummy.description = " NO ENTRY        NO ENTRY      "

        eventsf.events.append(dummy)
        # play with each entry
        for k in keys:
            # entry is what we will return to user
            entry=cal[k]
            data=self.protocolclass.scheduleevent()
            if counter >= 50:
                self.log("More than 49 entries in calendar, only writing out the first 49")
                break
            data.pos=counter
            counter+=1
            entry['pos']=data.pos
            # simple copy of these fields
            for field in 'start','description':
                setattr(data,field,entry[field])
            # And now the special ones
            # alarm 100 indicates not set
            if entry['alarm'] is None or entry['alarm']<=0:
                data.state = 2
                data.alarm = 0
	        data.repeat = 1
            else:
                data.state = 1
                data.alarm = 0xB0
                if entry['repeat'] is None: data.repeat = 1
                else: data.repeat = 2
            dst = -1
            if entry['changeserial']: dst = entry['changeserial']
            data.date = self.encodedate(entry['start'],dst)-self._tm520epochtounix

            # put entry in nice shiny new dict we are building
            newcal[data.pos]=entry
            eventsf.events.append(data)

        if counter < 50:
            for i in range(counter, 50):
                dummy=self.protocolclass.scheduleevent()
                dummy.pos = i
                dummy.date = 0x11223344
                dummy.state = 0
                dummy.alarm = 0x80
                dummy.repeat = 0
                dummy.description = " NO ENTRY        NO ENTRY      "
                eventsf.events.append(dummy)

        # scribble everything out
        buf=prototypes.buffer()
        eventsf.writetobuffer(buf)
        self.logdata("Writing calendar", buf.getvalue(), eventsf)
        self.writefile("sch/sch_00.dat", buf.getvalue())

        # fix passed in dict
        dict['calendar']=newcal

        return dict

    def decodedate(self,val):
        """Unpack 32 bit value into date/time

        @rtype: tuple
        @return: (year, month, day, hour, minute)
        """
        return time.localtime(val)[:5]

    def encodedate(self,val,dst):
        tmp = []
        for i in val: tmp.append(i)
        tmp += [0, 0, 0, dst]
        return time.mktime(tmp)

    def makeentry(self, counter, entry, dict):
        e=self.protocolclass.pbentry()
        e.entrynumber=counter
        
        for k in entry:
            # special treatment for lists
            if k=='emails' or k=='numbers' or k=='numbertypes':
                l=getattr(e,k)
                for item in entry[k]:
                    l.append(item)
            else:
                # everything else we just set
                setattr(e,k,entry[k])

        return e

class Profile:
    WALLPAPER_WIDTH=100
    WALLPAPER_HEIGHT=100

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
#        ('ringtone', 'read', None),   # all ringtone reading
#        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
#        ('ringtone', 'write', 'MERGE'),      # merge and overwrite ringtone
#        ('ringtone', 'write', 'OVERWRITE'),
        )

    def SyncQuery(self, source, action, type):
        if (source, action, type) in self._supportedsyncs or \
           (source, action, None) in self._supportedsyncs:
            return True
        return False
