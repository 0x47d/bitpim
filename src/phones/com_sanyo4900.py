### BITPIM
###
### Copyright (C) 2003 Stephen Wood <sawecw@users.sf.net>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Talk to the Sanyo SCP-4900 cell phone"""
# May also work for 6200, 6400, 5300 and 8100.

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

numbertypetab=( 'home', 'office', 'cell', 'pager',
                    'data', 'fax', 'none' )

class Phone(com_phone.Phone,com_brew.BrewProtocol,com_sanyo.SanyoPhonebook):
    "Talk to the Sanyo SCP-4900 cell phone"
    desc="SCP-4900"

    # phone uses Jan 1, 1980 as epoch.  Python uses Jan 1, 1970.  This is difference
    # plus a fudge factor of 5 days for no reason I can find
    _sanyoepochtounix=315532800+450000

    getwallpapers=None
    getringtones=None
    
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

    def sanyosort(self, x, y):
        "Sanyo sort order.  Case insensitive, letters first"
        if(x[0:1].isalpha() and not y[0:1].isalpha()):
            return -1
        if(y[0:1].isalpha() and not x[0:1].isalpha()):
            return 1
        return cmp(x.lower(), y.lower())
    
    def getphonebook(self,result):
        pbook={}
        # Get Sort buffer so we know which of the 300 phone book slots
        # are in use.
        sortstuff=p_sanyo.pbsortbuffer()
        buf=prototypes.buffer(self.getsanyobuffer(sortstuff.startcommand, sortstuff.bufsize, "sort buffer"))
        sortstuff.readfrombuffer(buf)

        ringpic=p_sanyo.ringerpicbuffer()
        buf=prototypes.buffer(self.getsanyobuffer(ringpic.startcommand, ringpic.bufsize, "ringer/picture assignments"))
        ringpic.readfrombuffer(buf)

        speedslot=[]
        speedtype=[]
        for i in range(p_sanyo._NUMSPEEDDIALS):
            speedslot.append(sortstuff.speeddialindex[i].pbslotandtype & 0xfff)
            numtype=(sortstuff.speeddialindex[i].pbslotandtype>>12)-1
            if(numtype >= 0 and numtype <= len(numbertypetab)):
                speedtype.append(numbertypetab[numtype])
            else:
                speedtype.append("")

        numentries=sortstuff.slotsused
        self.log("There are %d entries" % (numentries,))
        
        count = 0
        for i in range(0, p_sanyo._NUMPBSLOTS):
            if sortstuff.usedflags[i].used:
                ### Read current entry
                req=p_sanyo.phonebookslotrequest()
                req.slot = i
                res=self.sendpbcommand(req, p_sanyo.phonebookslotresponse)
                self.log("Read entry "+`i`+" - "+res.entry.name)

                entry=self.extractphonebookentry(res.entry, result)
                # Speed dials
                for j in range(len(speedslot)):
                    if(speedslot[j]==req.slot):
                        for k in range(len(entry['numbers'])):
                            if(entry['numbers'][k]['type']==speedtype[j]):
                                entry['numbers'][k]['speeddial']=j+2
                                break

                # ringtones
                entry['ringtones']=[{'ringtone': ringpic.ringtones[i].ringtone, 'use': 'call'}]
                # wallpapers
                entry['wallpapers']=[{'index': ringpic.wallpapers[i].wallpaper, 'use': 'call'}]
                    
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
        if len(entry.email):
            res['emails']=[ {'email': entry.email} ]
        # only one url
        if len(entry.url):
            res['urls']=[ {'url': entry.url} ]
        # private
        res['flags']=[ {'secret': entry.secret } ]
        # 7 phone numbers
        res['numbers']=[]
        numberindex = 0
        for type in numbertypetab:
            if len(entry.numbers[numberindex].number):
                res['numbers'].append({'number': entry.numbers[numberindex].number, 'type': type })
            
            numberindex+=1
        return res

    def makeentry(self, entry, dict):
        # dict is unused at moment, will be used later to convert string ringtone/wallpaper to numbers??
        # This is stolen from com_lgvx4400 and modified for the Sanyo as
        # we start to develop a vague understanding of what it is for.
        e=p_sanyo.phonebookentry()
        
        for k in entry:
            # special treatment for lists
            if k=='ringtones' or k=='wallpapers' or k=='numbertypes':
                continue
            if k=='numbers':
                for numberindex in range(7):
                    enpn=p_sanyo.phonenumber()
                    e.numbers.append(enpn)
                    
                for i in range(len(entry[k])):
                    numberindex=entry['numbertypes'][i]
                    e.numbers[numberindex].number=entry[k][i]
                    e.numbers[numberindex].number_len=len(e.numbers[numberindex].number)
                continue
            # everything else we just set
            setattr(e,k,entry[k])
        return e

    def phonize(self, str):
        """Convert the phone number into something the phone understands

        All digits, P, T, * and # are kept, everything else is removed"""
        # Note: when looking at phone numbers on the phone, you will see
        # "H" instead of "P".  However, phone saves this internally as "P".
        return re.sub("[^0-9PT#*]", "", str)

    def savephonebook(self, data):
        # Overwrite the phonebook in the phone with the data.
        # As we write the phone book slots out, we need to build up
        # the indices in the callerid, ringpic and pbsort buffers.
        # We could save some writing by reading the phonebook slots first
        # and then only writing those that are different, but all the buffers
        # would still need to be written.
        #
        newphonebook={}
        self.mode=self.MODENONE
        self.setmode(self.MODEBREW) # see note in getphonebook in com_lgvx4400 for why this is necessary
        self.setmode(self.MODEPHONEBOOK)

###
### Create Sanyo buffers and Initialize lists
###
        sortstuff=p_sanyo.pbsortbuffer()
        ringpic=p_sanyo.ringerpicbuffer()
        callerid=p_sanyo.calleridbuffer()

        for i in range(p_sanyo._NUMPBSLOTS):
            sortstuff.usedflags.append(0)
            sortstuff.firsttypes.append(0)
            sortstuff.sortorder.append(0xffff)
            sortstuff.sortorder2.append(0xffff)
            sortstuff.emails.append(0xffff)
            sortstuff.urls.append(0xffff)
            ringpic.ringtones.append(0)
            ringpic.wallpapers.append(0)

        for i in range(p_sanyo._NUMSPEEDDIALS):
            sortstuff.speeddialindex.append(0xffff)

        for i in range(p_sanyo._NUMLONGNUMBERS):
            sortstuff.longnumbersindex.append(0xffff)
        
            
###
### Initialize mappings
###
        namemap={}
        emailmap={}
        urlmap={}

        callerid.numentries=0
        
        pbook=data['phonephonebook'] # Get converted phonebook
        self.log("Putting phone into write mode")
        req=p_sanyo.beginendupdaterequest()
        req.beginend=1 # Start update
        res=self.sendpbcommand(req, p_sanyo.beginendupdateresponse, writemode=True)

        time.sleep(1)  # Wait a little bit to make sure phone is ready
        
        keys=pbook.keys()
        keys.sort()
        sortstuff.slotsused=len(keys)
        sortstuff.slotsused2=len(keys)
        sortstuff.numemail=0
        sortstuff.numurl=0

        progresscur=0
        progressmax=len(keys)
        self.log("Writing %d entries to phone" % (len(keys),))
        nlongphonenumbers=0
        for ikey in keys:
            ii=pbook[ikey]
            slot=ii['slot'] # Or should we just use i for the slot
            # Will depend on Profile to keep the serial numbers in range
            progresscur+=1
            self.progress(progresscur, progressmax, "Writing "+ii['name'])
            self.log("Writing entry "+`ikey`+" - "+ii['name'])
            entry=self.makeentry(ii, data)
            req=p_sanyo.phonebookslotupdaterequest()
            req.entry=entry
            res=self.sendpbcommand(req, p_sanyo.phonebookslotresponse, writemode=True)
            # Put entry into newphonebooks
            entry=self.extractphonebookentry(entry, data)
            entry['ringtones']=[{'ringtone': ii['ringtone'], 'use': 'call'}]
            entry['wallpapers']=[{'index': ii['wallpaper'], 'use': 'call'}]
            

# Accumulate information in and needed for buffers
            sortstuff.usedflags[slot].used=1
            if(len(ii['numbers'])):
                sortstuff.firsttypes[slot].firsttype=ii['numbertypes'][0]+1
            else:
                if(len(ii['email'])):
                    sortstuff.firsttypes[slot].firsttype=8
                elif(len(ii['url'])):
                    sortstuff.firsttypes[slot].firsttype=9
                else:
                    sortstuff.firsttypes[slot].firsttype=0
                    
# Fill in Caller ID buffer
# Want to move this out of this loop.  Callerid buffer is 500 numbers, but
# can potentially hold 2100 numbers.  Would like to preferentially put the
# first number for each name in this buffer
            for i in range(len(ii['numbers'])):
                nindex=ii['numbertypes'][i]
                speeddial=ii['speeddials'][i]
                code=slot+((nindex+1)<<12)
                if(speeddial>=2 and speeddial<=p_sanyo._NUMSPEEDDIALS+1):
                    sortstuff.speeddialindex[speeddial-2]=code
                    for k in range(len(entry['numbers'])):
                        if(entry['numbers'][k]['type']==nindex):
                            entry['numbers'][k]['speeddial']=speeddial
                            break
                if(callerid.numentries<callerid.maxentries):
                    phonenumber=ii['numbers'][i]
                    cidentry=self.makecidentry(phonenumber,slot,nindex)
                    callerid.items.append(cidentry)
                    callerid.numentries+=1
                    if(len(phonenumber)>p_sanyo._LONGPHONENUMBERLEN):
                        if(nlongphonenumbers<p_sanyo._NUMLONGNUMBERS):
                            sortstuff.longnumbersindex[nlongphonenumbers].pbslotandtype=code

            namemap[ii['name']]=slot
            if(len(ii['email'])):
                emailmap[ii['email']]=slot
                sortstuff.numemail+=1
            if(len(ii['url'])):
                urlmap[ii['url']]=slot
                sortstuff.numurl+=1
            # Add ringtone and wallpaper
            ringpic.wallpapers[slot].wallpaper=ii['wallpaper']
            ringpic.ringtones[slot].ringtone=ii['ringtone']

            newphonebook[slot]=entry

                    
        # Sort Names, Emails and Urls for the sort buffer
        # The phone sorts case insensitive and puts numbers after the
        # letters.
        i=0
        sortstuff.pbfirstletters=""
        keys=namemap.keys()
        keys.sort(self.sanyosort)
        for name in keys:
            sortstuff.sortorder[i].pbslot=namemap[name]
            sortstuff.sortorder2[i].pbslot=namemap[name]
            sortstuff.pbfirstletters+=name[0:1]
            i+=1

        i=0
        sortstuff.emailfirstletters=""
        keys=emailmap.keys()
        keys.sort(self.sanyosort)
        for email in keys:
            sortstuff.emails[i].pbslot=emailmap[email]
            sortstuff.emailfirstletters+=email[0:1]
            i+=1

        i=0
        sortstuff.urlfirstletters=""
        keys=urlmap.keys()
        keys.sort(self.sanyosort)
        for url in keys:
            sortstuff.urls[i].pbslot=urlmap[url]
            sortstuff.urlfirstletters+=url[0:1]
            i+=1

        # Now write out the 3 buffers
        buffer=prototypes.buffer()
        sortstuff.writetobuffer(buffer)
        self.logdata("Write sort buffer", buffer.getvalue(), sortstuff)
        self.sendsanyobuffer(buffer.getvalue(),sortstuff.startcommand,"sort buffer")

        buffer=prototypes.buffer()
        ringpic.writetobuffer(buffer)
        self.logdata("Write ringer picture buffer", buffer.getvalue(), ringpic)
        self.sendsanyobuffer(buffer.getvalue(),ringpic.startcommand,"ringer/pictures assignments")
        
        buffer=prototypes.buffer()
        callerid.writetobuffer(buffer)
        self.logdata("Write caller id buffer", buffer.getvalue(), callerid)
        self.sendsanyobuffer(buffer.getvalue(),callerid.startcommand,"callerid")

        time.sleep(1.0)


        data['phonebook']=newphonebook
        del data['phonephonebook']

        self.log("Taking phone out of write mode")
        self.log("Please wait for phone to restart before doing other phone operations")
        req=p_sanyo.beginendupdaterequest()
        req.beginend=2 # Stop update
        res=self.sendpbcommand(req, p_sanyo.beginendupdateresponse, writemode=True)

    def makecidentry(self, number, slot, nindex):
        "Prepare entry for caller ID lookup buffer"
        
        numstripped=re.sub("[^0-9PT#*]", "", number)
        numonly=re.sub("^(\\d*).*$", "\\1", numstripped)

        cidentry=p_sanyo.calleridentry()
        cidentry.pbslotandtype=slot+((nindex+1)<<12)
        cidentry.actualnumberlen=len(numonly)
        cidentry.numberfragment=numonly[-10:]

        return cidentry
    
    def getcalendar(self,result):
        # Read the event list from the phone.  Proof of principle code.
        # For now, join the event name and location into a single event.
        # description.
        # Todo:
        #   Read Call Alarms (reminder to call someone)
        #   Read call history into calendar.
        calres={}

        req=p_sanyo.eventrequest()
        maxevents=req.maxevents
        for i in range(0, maxevents):
            req.slot = i
            res=self.sendpbcommand(req, p_sanyo.eventresponse)
            if(res.entry.flag):
                self.log("Read calendar event "+`i`+" - "+res.entry.eventname)
                self.log("Extra numbers: "+`res.entry.dunno1`+" "+`res.entry.dunno2`+" "+`res.entry.dunno3`+" "+`res.entry.dunno4`)
                entry={}
                entry['pos']=i
                if(len(res.entry.location) > 0):
                    entry['description']=res.entry.eventname+"/"+res.entry.location
                else:
                   entry['description']=res.entry.eventname
               
                starttime=res.entry.start
                entry['start']=self.decodedate(starttime)
                entry['end']=self.decodedate(res.entry.end)
                entry['repeat']=self._calrepeatvalues[0]
                alarmtime=res.entry.alarm
                entry['alarm']=(starttime-alarmtime)/60
                calres[i]=entry

        result['calendar']=calres
        return result

    def decodedate(self,val):
        """Unpack 32 bit value into date/time

        @rtype: tuple
        @return: (year, month, day, hour, minute)
        """
        return time.localtime(val+self._sanyoepochtounix)[:5]

    _calrepeatvalues={
        0: None,
        1: 'daily',
        2: 'weekly',
        3: 'monthly',
        4: 'yearly'
        }



class Profile:

    def makeone(self, list, default):
        "Returns one item long list"
        if len(list)==0:
            return default
        assert len(list)==1
        return list[0]

    # Processes phone book for writing to Sanyo.  But does not leave phone book
    # in a bitpim compatible format.  Need to understand exactly what bitpim
    # is expecting the method to do.

    def convertphonebooktophone(self, helper, data):
        "Converts the data to what will be used by the phone"
        results={}

        slotsused={}
        for pbentry in data['phonebook']:
            entry=data['phonebook'][pbentry]
            serial1=helper.getserial(entry.get('serials', []), 'scp4900', data['uniqueserial'], 'serial1', -1)
            if(serial1 >= 0 and serial1 < p_sanyo._NUMPBSLOTS):
                slotsused[serial1]=1

        lastunused=0 # One more than last unused slot
        
        for pbentry in data['phonebook']:
            e={} # entry out
            entry=data['phonebook'][pbentry] # entry in
            try:
                e['name']=helper.getfullname(entry.get('names', []),1,1,16)[0]
                e['name_len']=len(e['name'])

                serial1=helper.getserial(entry.get('serials', []), 'scp4900', data['uniqueserial'], 'serial1', -1)

                if(serial1 >= 0 and serial1 < p_sanyo._NUMPBSLOTS):
                    e['slot']=serial1
                else:  # A new entry.  Must find unused slot
                    while(slotsused.has_key(lastunused)):
                        lastunused+=1
                        if(lastunused >= p_sanyo._NUMPBSLOTS):
                            raise helper.ConversionFailed()
                    e['slot']=lastunused
                    slotsused[lastunused]=1
                
                e['slotdup']=e['slot']

                e['email']=self.makeone(helper.getemails(entry.get('emails', []),0,1,48), "")
                e['email_len']=len(e['email'])

                e['url']=self.makeone(helper.geturls(entry.get('urls', []), 0,1,48), "")
                e['url_len']=len(e['url'])
# Could put memo in email or url

# Just copy numbers with exact matches now.  Later try to fit in entries
# that don't match (or duplicates of a type) into ununused places.
                numbers=helper.getnumbers(entry.get('numbers', []),0,7)
                e['numbertypes']=[]
                e['numbers']=[]
                e['speeddials']=[]
                for num in numbers:
                    typename=num['type']
                    for typenum,tnsearch in zip(range(100),numbertypetab):
                        if typename==tnsearch:
                            e['numbertypes'].append(typenum)
                            e['numbers'].append(num['number'])
                            if(num.has_key('speeddial')):
                                e['speeddials'].append(num['speeddial'])
                            else:
                                e['speeddials'].append(-1)

                            break


                e['ringtone']=helper.getringtone(entry.get('ringtones', []), 'call', 0)

                e['wallpaper']=helper.getwallpaperindex(entry.get('wallpapers', []), 'call', 0)

                e['secret']=helper.getflag(entry.get('flags', []), 'secret', False)

                results[pbentry]=e
                
            except helper.ConversionFailed:
                self.log("No Free Slot for "+e['name'])
                continue

        data['phonephonebook']=results
        return data
