### BITPIM
###
### Copyright (C) 2003 Stephen Wood <sawecw@users.sf.net>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Phonebook conversations with Sanyo phones"""

# standard modules
import re
import time
import cStringIO
import sha

import wx

# BitPim modules
import com_brew
import com_phone
import p_sanyo
import prototypes
import common
import cStringIO
import time

numbertypetab=( 'home', 'office', 'cell', 'pager',
                    'data', 'fax', 'none' )

class SanyoPhonebook:
    "Talk to a Sanyo Sprint Phone such as SCP-4900, SCP-5300, or SCP-8100"
    
    # phone uses Jan 1, 1980 as epoch.  Python uses Jan 1, 1970.  This is difference
    # plus a fudge factor of 5 days for no reason I can find
    _sanyoepochtounix=315532800+432000;

    pbterminator="\x7e"
    MODEPHONEBOOK="modephonebook" # can speak the phonebook protocol

    def __init__(self):
        pass
    
    def _setmodelgdmgo(self):
        # see if we can turn on dm mode
        for baud in (0, 115200, 19200, 38400, 230400):
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.comm.write("AT$LGDMGO\r\n")
            except:
                self.mode=self.MODENONE
                self.comm.shouldloop=True
                raise
            try:
                self.comm.readsome()
                self.comm.setbaudrate(38400) # dm mode is always 38400
                return 1
            except com_phone.modeignoreerrortypes:
                self.log("No response to setting DM mode")
        self.comm.setbaudrate(38400) # just in case it worked
        return 0
        

    def _setmodephonebook(self):
        req=p_sanyo.firmwarerequest()
        respc=p_sanyo.firmwareresponse
        try:
            self.sendpbcommand(req, respc, callsetmode=False)
            return 1
        except com_phone.modeignoreerrortypes:
            pass
        try:
            self.comm.setbaudrate(38400)
            self.sendpbcommand(req, respc, callsetmode=False)
            return 1
        except com_phone.modeignoreerrortypes:
            pass
        self._setmodelgdmgo()
        try:
            self.sendpbcommand(req, respc, callsetmode=False)
            return 1
        except com_phone.modeignoreerrortypes:
            pass
        return 0
        
    def getmediaindex(self, builtins, maps, results, key):
        """Gets the media (wallpaper/ringtone) index

        @param builtins: the builtin list on the phone
        @param results: places results in this dict
        @param maps: the list of index files and locations
        @param key: key to place results in
        """

        self.log("Reading "+key)
        media={}

        # builtins
        c=1
        for name in builtins:
            if name:
                media[c]={'name': name, 'origin': 'builtin' }
                print c,name
            c+=1

        # the maps
        type=''
        for offset,indexfile,location,type,maxentries in maps:
            if type=="camera": break
            index=self.getindex(indexfile)
            for i in index:
                media[i+offset]={'name': index[i], 'origin': type}

        # camera must be last
        if type=="camera":
            index=self.getcameraindex()
            for i in index:
                media[i+offset]=index[i]

        results[key]=media
        return media

    def getwallpaperindices(self, results):
        return self.getmediaindex(self.builtinimages, self.imagelocations, results, 'wallpaper-index')

    def getringtoneindices(self, results):
        return self.getmediaindex(self.builtinringtones, self.ringtonelocations, results, 'ringtone-index')

    def getsanyobuffer(self, startcommand, buffersize, comment):
        # Read buffer parts and concatenate them together
        desc="Reading "+comment
        data=cStringIO.StringIO()
        bufp=0
        command=startcommand
        for offset in range(0, buffersize, 500):
            self.progress(data.tell(), buffersize, desc)
            req=p_sanyo.bufferpartrequest()
            req.header.command=command
            res=self.sendpbcommand(req, p_sanyo.bufferpartresponse);
            data.write(res.data)
            command+=1

        self.progress(1,1,desc)

        data=data.getvalue()
        self.log("expected size "+`buffersize`+"  actual "+`len(data)`)
        assert buffersize==len(data)
        return data

    def sendsanyobuffer(self, buffer, startcommand, comment):
        self.log("Writing "+comment+" "+` len(buffer) `+" bytes")
        desc="Writing "+comment
        numblocks=len(buffer)/500
        offset=0
        command=startcommand
        for offset in range(0, len(buffer), 500):
            self.progress(offset/500, numblocks, desc)
            req=p_sanyo.bufferpartupdaterequest()
            req.header.command=command
            block=buffer[offset:]
            l=min(len(block), 500)
            block=block[:l]
            req.data=block
            command+=1
            self.sendpbcommand(req, p_sanyo.bufferpartresponse, writemode=True)
        
    def sendpbcommand(self, request, responseclass, callsetmode=True, writemode=False, numsendretry=0):
        if writemode:
            numretry=2
        else:
            numretry=0
            
        if callsetmode:
            self.setmode(self.MODEPHONEBOOK)
        buffer=prototypes.buffer()

        request.writetobuffer(buffer)
        data=buffer.getvalue()
        self.logdata("Sanyo phonebook request", data, request)
        data=com_brew.escape(data+com_brew.crcs(data))+self.pbterminator
        firsttwo=data[:2]
        isendretry=numsendretry
        while isendretry>=0:
            try:
                self.comm.write(data, log=False) # we logged above
                rdata=self.comm.readuntil(self.pbterminator, logsuccess=False, numfailures=numretry)
                break
            except com_phone.modeignoreerrortypes:
                if isendretry>0:
                    self.log("Resending request packet...")
                    time.sleep(0.3)
                else:
                    self.comm.success=False
                    self.mode=self.MODENONE
                    self.raisecommsdnaexception("manipulating the phonebook")
                isendretry-=1

        self.comm.success=True

        origdata=rdata
        # sometimes there is junk at the begining, eg if the user
        # turned off the phone and back on again.  So if there is more
        # than one 7e in the escaped data we should start after the
        # second to last one
        d=rdata.rfind(self.pbterminator,0,-1)
        if d>=0:
            self.log("Multiple Sanyo packets in data - taking last one starting at "+`d+1`)
            self.logdata("Original Sanyo data", origdata, None)
            rdata=rdata[d+1:]

        # turn it back to normal
        data=com_brew.unescape(rdata)

        # sometimes there is other crap at the begining
        d=data.find(firsttwo)
        if d>0:
            self.log("Junk at begining of Sanyo packet, data at "+`d`)
            self.logdata("Original Sanyo data", origdata, None)
            self.logdata("Working on Sanyo data", data, None)
            data=data[d:]
        # take off crc and terminator
        crc=data[-3:-1]
        data=data[:-3]
        if com_brew.crcs(data)!=crc:
            self.logdata("Original Sanyo data", origdata, None)
            self.logdata("Working on Sanyo data", data, None)
            raise common.CommsDataCorruption(self.desc, "Sanyo packet failed CRC check")

        # log it
        self.logdata("sanyo phonebook response", data, responseclass)

        # parse data
        buffer=prototypes.buffer(data)
        res=responseclass()
        res.readfrombuffer(buffer)
        return res

    # This function isn't actually used
    def getphoneinfo(self, results):
        "Extracts manufacturer and version information in modem mode"
        self.setmode(self.MODEMODEM)
        d={}
        self.progress(0,4, "Switching to modem mode")
        self.progress(1,4, "Reading manufacturer")
        self.comm.write("AT+GMI\r\n")  # manuf
        d['Manufacturer']=cleanupstring(self.comm.readsome())[2][6:]
        self.log("Manufacturer is "+d['Manufacturer'])
        self.progress(2,4, "Reading model")
        self.comm.write("AT+GMM\r\n")  # model
        d['Model']=cleanupstring(self.comm.readsome())[2][6:]
        self.log("Model is "+d['Model'])
        self.progress(3,4, "Software version")
        self.comm.write("AT+GMR\r\n")  # software revision
        d['Software']=cleanupstring(self.comm.readsome())[2][6:]
        self.log("Software is "+d['Software'])
        self.progress(4,4, "Done reading information")
        results['info']=d
        return results

    def cleanupstring(str):
        str=str.replace("\r", "\n")
        str=str.replace("\n\n", "\n")
        str=str.strip()
        return str.split("\n")


    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI."""

        # use a hash of ESN and other stuff (being paranoid)
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        results['uniqueserial']=sha.new(self.getfilecontents("nvm/$SYS.ESN")).hexdigest()

        self.getwallpaperindices(results)
        self.getringtoneindices(results)
        self.log("Fundamentals retrieved")
        1
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
        sortstuff=self.protocolclass.pbsortbuffer()
        buf=prototypes.buffer(self.getsanyobuffer(sortstuff.startcommand, sortstuff.bufsize, "sort buffer"))
        sortstuff.readfrombuffer(buf)

        ringpic=self.protocolclass.ringerpicbuffer()
        buf=prototypes.buffer(self.getsanyobuffer(ringpic.startcommand, ringpic.bufsize, "ringer/picture assignments"))
        ringpic.readfrombuffer(buf)

        speedslot=[]
        speedtype=[]
        for i in range(self.protocolclass._NUMSPEEDDIALS):
            speedslot.append(sortstuff.speeddialindex[i].pbslotandtype & 0xfff)
            numtype=(sortstuff.speeddialindex[i].pbslotandtype>>12)-1
            if(numtype >= 0 and numtype <= len(numbertypetab)):
                speedtype.append(numbertypetab[numtype])
            else:
                speedtype.append("")

        numentries=sortstuff.slotsused
        self.log("There are %d entries" % (numentries,))
        
        count = 0
        for i in range(0, self.protocolclass._NUMPBSLOTS):
            if sortstuff.usedflags[i].used:
                ### Read current entry
                req=self.protocolclass.phonebookslotrequest()
                req.slot = i
                res=self.sendpbcommand(req, self.protocolclass.phonebookslotresponse)
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
                if ringpic.ringtones[i].ringtone>0:
                    try:
                        tone=result['ringtone-index'][ringpic.ringtones[i].ringtone]['name']
                    except:
                        tone=self.serialsname+"Index_"+`ringpic.ringtones[i].ringtone`
                    entry['ringtones']=[{'ringtone': tone, 'use': 'call'}]

                # wallpapers
                if ringpic.wallpapers[i].wallpaper>0:
                    try:
                        paper=result['wallpaper-index'][ringpic.wallpapers[i].wallpaper]['name']
                    except:
                        paper=self.serialsname+"Index_"+`ringpic.wallpapers[i].wallpaper`
                    entry['wallpapers']=[{'wallpaper': paper, 'use': 'call'}]
                    
                pbook[count]=entry 
                self.progress(count, numentries, res.entry.name)
                count+=1
        
        self.progress(numentries, numentries, "Phone book read completed")
        result['phonebook']=pbook
        return pbook

    def extractphonebookentry(self, entry, fundamentals):
        """Return a phonebook entry in BitPim format"""
        res={}
        # serials
        res['serials']=[ {'sourcetype': self.serialsname, 'serial1': entry.slot, 'serial2': entry.slotdup,
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

    def _findmediaindex(self, index, name, pbentryname, type):
        if name is None:
            return 0
        for i in index:
            if index[i]['name']==name:
                return i
        # Not found in index, assume Vision download
        pos=name.find('_')
        if(pos>=0):
            i=int(name[pos+1:])
            return i
        
        return 0
        
    def makeentry(self, entry, dict):
        # dict is unused at moment, will be used later to convert string ringtone/wallpaper to numbers??
        # This is stolen from com_lgvx4400 and modified for the Sanyo as
        # we start to develop a vague understanding of what it is for.
        e=self.protocolclass.phonebookentry()
        
        for k in entry:
            # special treatment for lists
            if k=='ringtones' or k=='wallpapers' or k=='numbertypes':
                continue
            if k=='numbers':
                for numberindex in range(7):
                    enpn=self.protocolclass.phonenumber()
                    e.numbers.append(enpn)
                    
                for i in range(len(entry[k])):
                    numberindex=entry['numbertypes'][i]
                    e.numbers[numberindex].number=entry[k][i]
                    e.numbers[numberindex].number_len=len(e.numbers[numberindex].number)
                continue
            # everything else we just set
            setattr(e,k,entry[k])
        return e

    def writewait(self):
        """Loop until phone status indicates ready to write"""
        for i in range(100):
            req=self.protocolclass.statusrequest()
            res=self.sendpbcommand(req, self.protocolclass.statusresponse)
            # print res.flag0, res.ready, res.flag2, res.flag3
            if res.ready==res.readyvalue:
                return
            time.sleep(0.1)

        self.log("Phone did not transfer to ready to write state")
        self.log("Waiting a bit longer and trying anyway")
        return
    
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
        sortstuff=self.protocolclass.pbsortbuffer()
        ringpic=self.protocolclass.ringerpicbuffer()
        callerid=self.protocolclass.calleridbuffer()

        for i in range(self.protocolclass._NUMPBSLOTS):
            sortstuff.usedflags.append(0)
            sortstuff.firsttypes.append(0)
            sortstuff.sortorder.append(0xffff)
            sortstuff.sortorder2.append(0xffff)
            sortstuff.emails.append(0xffff)
            sortstuff.urls.append(0xffff)
            ringpic.ringtones.append(0)
            ringpic.wallpapers.append(0)

        for i in range(self.protocolclass._NUMSPEEDDIALS):
            sortstuff.speeddialindex.append(0xffff)

        for i in range(self.protocolclass._NUMLONGNUMBERS):
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
        req=self.protocolclass.beginendupdaterequest()
        req.beginend=1 # Start update
        res=self.sendpbcommand(req, self.protocolclass.beginendupdateresponse, writemode=True)

        self.writewait()
        
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
            req=self.protocolclass.phonebookslotupdaterequest()
            req.entry=entry
            self.writewait()
            res=self.sendpbcommand(req, self.protocolclass.phonebookslotresponse, writemode=True)
            # Put entry into newphonebooks
            entry=self.extractphonebookentry(entry, data)
            entry['ringtones']=[{'ringtone': ii['ringtone'], 'use': 'call'}]
            entry['wallpapers']=[{'wallpaper': ii['wallpaper'], 'use': 'call'}]
            

# Accumulate information in and needed for buffers
            sortstuff.usedflags[slot].used=1
            if(len(ii['numbers'])):
                sortstuff.firsttypes[slot].firsttype=min(ii['numbertypes'])+1
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
# first number for each name in this buffer.
# If more than 500 numbers are in phone, the phone won't let you add
# any more. So we should probably respect this limit.
            for i in range(len(ii['numbers'])):
                nindex=ii['numbertypes'][i]
                speeddial=ii['speeddials'][i]
                code=slot+((nindex+1)<<12)
                if(speeddial>=2 and speeddial<=self.protocolclass._NUMSPEEDDIALS+1):
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
                    if(len(phonenumber)>self.protocolclass._LONGPHONENUMBERLEN):
                        if(nlongphonenumbers<self.protocolclass._NUMLONGNUMBERS):
                            sortstuff.longnumbersindex[nlongphonenumbers].pbslotandtype=code

            namemap[ii['name']]=slot
            if(len(ii['email'])):
                emailmap[ii['email']]=slot
                sortstuff.numemail+=1
            if(len(ii['url'])):
                urlmap[ii['url']]=slot
                sortstuff.numurl+=1
            # Add ringtone and wallpaper
            ringpic.ringtones[slot].ringtone=self._findmediaindex(data['ringtone-index'], ii['ringtone'],ii['name'],'ringtone')
            ringpic.wallpapers[slot].wallpaper=self._findmediaindex(data['wallpaper-index'], ii['wallpaper'],ii['name'],'wallpaper')

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
        req=self.protocolclass.beginendupdaterequest()
        req.beginend=2 # Stop update
        res=self.sendpbcommand(req, self.protocolclass.beginendupdateresponse, writemode=True)

    def makecidentry(self, number, slot, nindex):
        "Prepare entry for caller ID lookup buffer"
        
        numstripped=re.sub("[^0-9PT#*]", "", number)
        numonly=re.sub("^(\\d*).*$", "\\1", numstripped)

        cidentry=self.protocolclass.calleridentry()
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
        #   
        calres={}

        req=self.protocolclass.eventrequest()
        count=0
        for i in range(0, self.protocolclass._NUMEVENTSLOTS):
            req.slot = i
            res=self.sendpbcommand(req, self.protocolclass.eventresponse)
            if(res.entry.flag):
                self.log("Read calendar event "+`i`+" - "+res.entry.eventname)
                self.log("Extra numbers: "+`res.entry.dunno1`+" "+`res.entry.dunno2`+" "+`res.entry.dunno3`)
                entry={}
                entry['pos']=i
                entry['changeserial']=res.entry.serial
                if(len(res.entry.location) > 0):
                    entry['description']=res.entry.eventname+"/"+res.entry.location
                else:
                   entry['description']=res.entry.eventname
               
                starttime=res.entry.start
                entry['start']=self.decodedate(starttime)
                entry['end']=self.decodedate(res.entry.end)
                entry['repeat']=self._calrepeatvalues[res.entry.period]
                alarmtime=res.entry.alarm
                entry['alarm']=(starttime-alarmtime)/60
                entry['ringtone']=res.entry.alarm_type
                entry['snoozedelay']=0
                calres[count]=entry
                count+=1

        req=self.protocolclass.callalarmrequest()
        for i in range(0, self.protocolclass._NUMCALLALARMSLOTS):
            req.slot=i
            res=self.sendpbcommand(req, self.protocolclass.callalarmresponse)
            if(res.entry.flag):
                self.log("Read call alarm entry "+`i`+" - "+res.entry.phonenum)
                self.log("Extra number: "+`res.entry.dunno1`)
                entry={}
                entry['pos']=i+self.protocolclass._NUMEVENTSLOTS # Make unique
                entry['changeserial']=res.entry.serial
                entry['description']=res.entry.phonenum
                starttime=res.entry.date
                entry['start']=self.decodedate(starttime)
                entry['end']=entry['start']
                entry['repeat']=self._calrepeatvalues[res.entry.period]
                entry['alarm']=0
                entry['ringtone']=0
                entry['snoozedelay']=0
                calres[count]=entry
                count+=1

        result['calendar']=calres
        return result

    def savecalendar(self, dict, merge):
        # ::TODO:: obey merge param
        # what will be written to the files
        #   Handle Change Serial better.
        #   Advance date on repeating entries to after now so that they
        #     won't all go off when the phone gets turned on.
        #   Sort by date so that that already happened entries don't get
        #     loaded if we don't have room
        #
        cal=dict['calendar']
        newcal={}
        keys=cal.keys()

        # Value to subtract from mktime results since there is no inverse
        # of gmtime
        zonedif=time.mktime(time.gmtime(0))-time.mktime(time.localtime(0))

        eventslot=0
        callslot=0
        progressmax=self.protocolclass._NUMEVENTSLOTS+self.protocolclass._NUMCALLALARMSLOTS
        for k in keys:
            entry=cal[k]
            
            descloc=entry['description']
            self.progress(eventslot+callslot, progressmax, "Writing "+descloc)

            repeat=None
            for k,v in self._calrepeatvalues.items():
                if entry['repeat']==v:
                    repeat=k
                    break
            if repeat is None:
                self.log(descloc+": Repeat type "+`entry['repeat']`+" not valid for this phone")
                repeat=0

            phonenum=re.sub("\-","",descloc)
            now=time.mktime(time.localtime(time.time()))-zonedif
            if(phonenum.isdigit()):  # This is a phone number, use call alarm
                self.log("Write calendar call alarm slot "+`callslot`+ " - "+descloc)
                e=self.protocolclass.callalarmentry()
                e.slot=callslot
                e.phonenum=phonenum
                e.phonenum_len=len(e.phonenum)
                

                timearray=entry['start']+[0,0,0,0]
                starttimelocal=time.mktime(timearray)-zonedif
                if(starttimelocal<now and repeat==0):
                    e.flag=2 # In the past
                else:
                    e.flag=1 # In the future
                e.date=starttimelocal-self._sanyoepochtounix
                e.datedup=e.date
                e.phonenumbertype=0
                e.phonenumberslot=0
                e.name="" # Could get this by reading phone book
                          # But it would take a lot more time
                e.name_len=len(e.name)

                req=self.protocolclass.callalarmupdaterequest()
                callslot+=1
                respc=self.protocolclass.callalarmresponse
            else: # Normal calender event
                self.log("Write calendar event slot "+`eventslot`+ " - "+descloc)
                e=self.protocolclass.evententry()
                e.slot=eventslot

                slashpos=descloc.find('/')
                if(slashpos >= 0):
                    eventname=descloc[0:slashpos]
                    location=descloc[slashpos+1:]
                else:
                    eventname=descloc
                    location=''
            
                e.eventname=eventname
                e.eventname_len=len(e.eventname)
                e.location=location
                e.location_len=len(e.location)

                timearray=entry['start']+[0,0,0,0]
                starttimelocal=time.mktime(timearray)-zonedif
                if(starttimelocal<now and repeat==0):
                    e.flag=2 # In the past
                else:
                    e.flag=1 # In the future
                e.start=starttimelocal-self._sanyoepochtounix

                timearray=entry.get('end', entry['start'])+[0,0,0,0]
                e.end=time.mktime(timearray)-self._sanyoepochtounix-zonedif

                alarmdiff=entry.get('alarm',0)
                e.alarm=starttimelocal-self._sanyoepochtounix-60*alarmdiff
                e.location=location
                e.location_len=len(e.location)

                e.alarm_type=entry.get('ringtone',0)

# What we should do is first find largest changeserial, and then increment
# whenever we have one that is undefined or zero.
            
                req=self.protocolclass.eventupdaterequest()
                eventslot+=1
                respc=self.protocolclass.eventresponse

            e.period=repeat
            e.dom=entry['start'][2]
            e.serial=entry.get('changeserial',0)
            req.entry=e
            res=self.sendpbcommand(req, respc, writemode=True)


# Blank out unused slots
        e=self.protocolclass.evententry()
        e.flag=0 # Unused slot
        e.eventname=""
        e.eventname_len=0
        e.location=""
        e.location_len=0
        e.start=0
        e.end=0
        e.alarm_type=0
        e.period=0
        e.dom=0
        e.alarm=0
        req=self.protocolclass.eventupdaterequest()
        req.entry=e
        for eventslot in range(eventslot,self.protocolclass._NUMEVENTSLOTS):
            self.progress(eventslot+callslot, progressmax, "Writing unused")
            self.log("Write calendar event slot "+`eventslot`+ " - Unused")
            req.entry.slot=eventslot
            res=self.sendpbcommand(req, self.protocolclass.eventresponse, writemode=True)

        e=self.protocolclass.callalarmentry()
        e.flag=0 # Unused slot
        e.name=""
        e.name_len=0
        e.phonenum=""
        e.phonenum_len=0
        e.date=0
        e.datedup=0
        e.period=0
        e.dom=0
        e.phonenumbertype=0
        e.phonenumberslot=0
        req=self.protocolclass.callalarmupdaterequest()
        req.entry=e
        for callslot in range(callslot,self.protocolclass._NUMCALLALARMSLOTS):
            self.progress(eventslot+callslot, progressmax, "Writing unused")
            self.log("Write calendar call alarm slot "+`callslot`+ " - Unused")
            req.entry.slot=callslot
            res=self.sendpbcommand(req, self.protocolclass.callalarmresponse, writemode=True)

        self.progress(progressmax, progressmax, "Calendar write done")

#        dict['calendar'] = cal
#        Not mucking with passed in calendar yet

    def decodedate(self,val):
        """Unpack 32 bit value into date/time

        @rtype: tuple
        @return: (year, month, day, hour, minute)
        """
        return list(time.gmtime(val+self._sanyoepochtounix)[:5])

    _calrepeatvalues={
        0: None,
        1: 'daily',
        2: 'weekly',
        3: 'monthly',
        4: 'yearly'
        }


def phonize(str):
    """Convert the phone number into something the phone understands

    All digits, P, T, * and # are kept, everything else is removed"""
    # Note: when looking at phone numbers on the phone, you will see
    # "H" instead of "P".  However, phone saves this internally as "P".
    return re.sub("[^0-9PT#*]", "", str)

class Profile:
    serialsname='sanyo'

    WALLPAPER_WIDTH=100
    WALLPAPER_HEIGHT=100
    MAX_WALLPAPER_BASENAME_LENGTH=19
    WALLPAPER_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 "
    WALLPAPER_CONVERT_FORMAT="bmp"
    
    # which usb ids correspond to us
    usbids=( ( 0x0474, 0x0701, 1),  # VID=Sanyo, PID=4900 internal USB interface
        )
    # which device classes we are.
    deviceclasses=("modem",)

    def __init__(self):
        pass

    # which sync types we deal with
    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        )

    def SyncQuery(self, source, action, type):
        if (source, action, type) in self._supportedsyncs or \
           (source, action, None) in self._supportedsyncs:
            return True
        return False

    
### Some drop in replacement routines for phonebook.py that can be moved
### if they look OK.
    def _getentries(self, list, min, max, name):
        candidates=[]
        for i in list:
            # ::TODO:: possibly ensure that a key appears in each i
            candidates.append(i)
        if len(candidates)<min:
            # ::TODO:: log this
            raise ConversionFailed("Too few %s.  Need at least %d but there were only %d" % (name,min,len(candidates)))
        if len(candidates)>max:
            # ::TODO:: mention this to user
            candidates=candidates[:max]
        return candidates

    def _getfield(self,list,name):
        res=[]
        for i in list:
            res.append(i[name])
        return res

    def _makefullnames(self, list, lastnamefirst=False):
        res=[]
        for i in list:
            first=i.get('first','')
            last=i.get('last','')
            full=i.get('full','')
            if len(last)>0:
                if(lastnamefirst):
                    res.append(last+", "+first)
                else:
                    res.append(first+" "+last)
            elif len(first)>0:
                res.append(first)
            else:
                res.append(full)

        return res
        
    def _truncatefields(self, list, truncateat, compresscomma=False):
        if truncateat is None:
            return list
        res=[]
        for i in list:
            if len(i)>truncateat:
                # ::TODO:: log truncation
                res.append(i[:truncateat])
            else:
                res.append(i)
        return res

    def getfullname(self, names, min, max, truncateat=None, lastnamefirst=False):
        "Return at least min and at most max fullnames from the names list"
        if(lastnamefirst):
            return self._truncatefields(self._makefullnames(self._getentries(names,min,max,"names"),lastnamefirst),truncateat,compresscomma=True)
        else:
            return self._truncatefields(self._makefullnames(self._getentries(names,min,max,"names")),truncateat)

###

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

        lastnamefirst=wx.GetApp().config.ReadInt("lastnamefirst")

        slotsused={}
        for pbentry in data['phonebook']:
            entry=data['phonebook'][pbentry]
            serial1=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial1', -1)
            if(serial1 >= 0 and serial1 < self.protocolclass._NUMPBSLOTS):
                slotsused[serial1]=1

        lastunused=0 # One more than last unused slot
        
        for pbentry in data['phonebook']:
            e={} # entry out
            entry=data['phonebook'][pbentry] # entry in
            try:
                e['name']=self.getfullname(entry.get('names', []),1,1,16,lastnamefirst)[0]
                e['name_len']=len(e['name'])

                serial1=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial1', -1)

                if(serial1 >= 0 and serial1 < self.protocolclass._NUMPBSLOTS):
                    e['slot']=serial1
                else:  # A new entry.  Must find unused slot
                    while(slotsused.has_key(lastunused)):
                        lastunused+=1
                        if(lastunused >= self.protocolclass._NUMPBSLOTS):
                            raise helper.ConversionFailed()
                    e['slot']=lastunused
                    slotsused[lastunused]=1
                
                e['slotdup']=e['slot']

                e['email']=self.makeone(helper.getemails(entry.get('emails', []),0,1,self.protocolclass._MAXEMAILLEN), "")
                e['email_len']=len(e['email'])

                e['url']=self.makeone(helper.geturls(entry.get('urls', []), 0,1,self.protocolclass._MAXEMAILLEN), "")
                e['url_len']=len(e['url'])
# Could put memo in email or url

                numbers=helper.getnumbers(entry.get('numbers', []),0,7)
                e['numbertypes']=[]
                e['numbers']=[]
                e['speeddials']=[]
                unusednumbers=[] # Hold duplicate types here
                typesused={}
                for num in numbers:
                    typename=num['type']
                    if(typesused.has_key(typename)):
                        unusednumbers.append(num)
                        continue
                    typesused[typename]=1
                    for typenum,tnsearch in zip(range(100),numbertypetab):
                        if typename==tnsearch:
                            number=phonize(num['number'])
                            if len(number)>self.protocolclass._MAXNUMBERLEN: # get this number from somewhere sensible
                                # :: TODO:: number is too long and we have to either truncate it or ignore it?
                                number=number[:self.protocolclass._MAXNUMBERLEN]
                            e['numbers'].append(number)
                            if(num.has_key('speeddial')):
                                e['speeddials'].append(num['speeddial'])
                            else:
                                e['speeddials'].append(-1)

                            e['numbertypes'].append(typenum)

                            break

# Now stick the unused numbers in unused types
                trytype=len(numbertypetab)
                for num in unusednumbers:
                    while trytype>0:
                        trytype-=1
                        if not typesused.has_key(numbertypetab[trytype]):
                            break
                    else:
                        break
                    number=phonize(num['number'])
                    if len(number)>self.protocolclass._MAXNUMBERLEN: # get this number from somewhere sensible
                        # :: TODO:: number is too long and we have to either truncate it or ignore it?
                        number=number[:self.protocolclass._MAXNUMBERLEN]
                    e['numbers'].append(number)
                    e['numbertypes'].append(trytype)
                    if(num.has_key('speeddial')):
                        e['speeddials'].append(num['speeddial'])
                    else:
                        e['speeddials'].append(-1)


                e['ringtone']=helper.getringtone(entry.get('ringtones', []), 'call', None)
                e['wallpaper']=helper.getwallpaper(entry.get('wallpapers', []), 'call', None)

                e['secret']=helper.getflag(entry.get('flags', []), 'secret', False)

                results[pbentry]=e
                
            except helper.ConversionFailed:
                self.log("No Free Slot for "+e['name'])
                continue

        data['phonephonebook']=results
        return data


class Phone(com_phone.Phone,com_brew.BrewProtocol,SanyoPhonebook):
    "Talk to a Sanyo Sprint Phone such as SCP-4900, SCP-5300, or SCP-8100"
    desc="Sanyo"
    
    imagelocations=()
    
    ringtonelocations=()

    builtinimages=()

    builtinringtones=()

    def __init__(self, logtarget, commport):
        "Call all the contructors and sets initial modes"
        com_phone.Phone.__init__(self, logtarget, commport)
        com_brew.BrewProtocol.__init__(self)
        SanyoPhonebook.__init__(self)
        self.log("Attempting to contact phone")
        self.mode=self.MODENONE

    getwallpapers=None
    getringtones=None


