### BITPIM
###
### Copyright (C) 2003 Stephen Wood <sawecw@users.sf.net>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
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
                # ringtones
                entry['ringtones']=[{'ringtone': ringpic.ringtones[i].ringtone, 'use': 'call'}]
                # wallpapers
                entry['wallpapers']=[{'wallpaper': ringpic.wallpapers[i].wallpaper, 'use': 'call'}]
                    
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

    def fakesendpbcommand(self, request, responseclass, callsetmode=True):
        if callsetmode:
            self.setmode(self.MODEPHONEBOOK)
        buffer=prototypes.buffer()
        request.writetobuffer(buffer)
        data=buffer.getvalue()
        self.logdata("Sanyo phonebook request", data, request)

        # parse data
        buffer=prototypes.buffer(data)
        res=responseclass()
        res.readfrombuffer(buffer)
        return res

    def savephonebook(self, data):
        # We overwrite the phonebook in the phone with the data.
        # As we write the phone book slots out, we need to build up
        # the indices in the callerid, ringpic and pbsort buffers.
        # We could save some writing by reading the phonebook slots first
        # and then only writing those that are different, but all the buffers
        # would still need to be written.
        #
        # Rightnow there is not distinguishing between add and replace
        newphonebook={}
        self.mode=self.MODENONE
        self.setmode(self.MODEBREW) # see note in getphonebook in com_lgvx4400 for why this is necessary
        self.setmode(self.MODEPHONEBOOK)

        sortstuff=p_sanyo.pbsortbuffer()
        ringpic=p_sanyo.ringerpicbuffer()
        callerid=p_sanyo.calleridbuffer()
###
### Initialize lists
###
        for i in range(sortstuff.numpbslots):
            sortstuff.usedflags.append(0)
            sortstuff.firsttypes.append(0)
            sortstuff.sortorder.append(0xffff)
            sortstuff.sortorder2.append(0xffff)
            sortstuff.emails.append(0xffff)
            sortstuff.urls.append(0xffff)
            ringpic.ringtones.append(0)
            ringpic.wallpapers.append(0)

        for i in range(sortstuff.numspeeddials):
            sortstuff.speeddialindex.append(0xffff)

        for i in range(sortstuff.numlongnumbers):
            sortstuff.longnumbersindex.append(0xffff)
        
            
###
### Initialize mappings
###
        namemap={}
        emailmap={}
        urlmap={}

        callerid.numentries=0
        
        pbook=data['phonephonebook']
        self.log("Putting phone into write mode")
        req=p_sanyo.beginendupdaterequest()
        req.beginend=1 # Start update
        res=self.fakesendpbcommand(req, p_sanyo.beginendupdateresponse)

        keys=pbook.keys()
        keys.sort()
        sortstuff.slotsused=len(keys)
        sortstuff.slotsused2=len(keys)
        sortstuff.numemail=0
        sortstuff.numurl=0

        progresscur=0
        progressmax=len(keys)+2+8+14 # Include the buffers
        self.log("Writing %d entries to phone" % (len(keys),))
        nlongphonenumbers=0
        for i in keys:
            ii=pbook[i]
            slot=ii['slot'] # Or should we just use i for the slot
            # Will depend on Profile to keep the serial numbers in range
            progresscur+=1
            self.progress(progresscur, progressmax, "Writing "+ii['name'])
            self.log("Writing entry "+`i`+" - "+ii['name'])
            entry=self.makeentry(ii, data)
            req=p_sanyo.phonebookslotupdaterequest()
            req.entry=entry
            res=self.fakesendpbcommand(req, p_sanyo.phonebookslotresponse)

# Accumulate information in and needed for buffers
            sortstuff.usedflags[slot].used=1
            sortstuff.firsttypes[slot].firsttype=ii['numbertypes'][0]+1
# Fill in Caller ID buffer
            for i in range(len(ii['numbers'])):
                if(callerid.numentries<callerid.maxentries):
                    phonenumber=ii['numbers'][i]
                    nindex=ii['numbertypes'][i]
                    cidentry=self.makecidentry(phonenumber,slot,nindex)
                    callerid.items.append(cidentry)
                    callerid.numentries+=1
                    if(len(phonenumber)>sortstuff.longphonenumberlen):
                        if(nlongphonenumbers<sortstuff.numlongnumbers):
                            sortstuff.longnumbersindex[nlongphonenumbers].pbslotandtype=slot+((nindex+1)>>12)

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
                    
        # Sort Names, Emails and Urls for the sort buffer
        # The phone sorts case insensitive and puts numbers after the
        # letters.  Yuk.
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
        # Write buffer.getvalue() to phone
        buffer=prototypes.buffer()
        callerid.writetobuffer(buffer)
        self.logdata("Write caller id buffer", buffer.getvalue(), callerid)
        # Write buffer.getvalue() to phone
        buffer=prototypes.buffer()
        ringpic.writetobuffer(buffer)
        self.logdata("Write ringer picture buffer", buffer.getvalue(), ringpic)
        # Write buffer.getvalue() to phone

        
        self.log("Taking phone out of write mode")
        req=p_sanyo.beginendupdaterequest()
        req.beginend=2 # Stop update
        res=self.fakesendpbcommand(req, p_sanyo.beginendupdateresponse)
        self.log("Please exit BITPIM and power cycle the phone")
        del data['phonephonebook']

    def makecidentry(self, number, slot, nindex):
        "Prepare entry for caller ID lookup buffer"
        
        numstripped=re.sub("[^0-9HT#*]", "", number)
        numonly=re.sub("^(\\d*).*$", "\\1", numstripped)

        cidentry=p_sanyo.calleridentry()
        cidentry.pbslotandtype=slot+((nindex+1)>>12)
        cidentry.actualnumberlen=len(numonly)
        cidentry.numberfragment=numonly[-10:]

        return cidentry
    
class Profile:

    def makeone(self, list, default):
        "Returns one item long list"
        if len(list)==0:
            return default
        assert len(list)==1
        return list[0]

# LGVX4400 code, need to fix
# Need to calculcate most string lengths.  Will truncate strings to
# know maximum lengths.
    def convertphonebooktophone(self, helper, data):
        "Converts the data to what will be used by the phone"
        results={}
        for pbentry in data['phonebook']:
            e={} # entry out
            entry=data['phonebook'][pbentry] # entry in
            try:
                e['name']=helper.getfullname(entry['names'],1,1,16)[0]
                e['name_len']=len(e['name'])

                if(entry.has_key('emails')):
                    e['email']=self.makeone(helper.getemails(entry['emails'],0,1,48), "")
                else:
                    e['email']=""
                e['email_len']=len(e['email'])

                if(entry.has_key('urls')):
                    e['url']=self.makeone(helper.geturls(entry['urls'], 0,1,48), "")
                else:
                    e['url']=""
                e['url_len']=len(e['url'])
# Could put memo in email or url

# Just copy numbers with exact matches now.  Later try to fit in entries
# that don't match (or duplicates of a type) into ununused places.
                numbers=helper.getnumbers(entry['numbers'],1,7)
                e['numbertypes']=[]
                e['numbers']=[]
                for num in numbers:
                    typename=num['type']
                    for typenum,tnsearch in zip(range(100),numbertypetab):
                        if typename==tnsearch:
                            e['numbertypes'].append(typenum)
                            e['numbers'].append(num['number'])

                            break

                serial1=helper.getserial(entry['serials'], 'scp4900', data['uniqueserial'], 'serial1', 0)
                serial2=helper.getserial(entry['serials'], 'scp4900', data['uniqueserial'], 'serial2', serial1)

                e['slot']=serial1
                e['slotdup']=serial2
                
                e['ringtone']=helper.getringtone(entry['ringtones'], 'call', 0)

                e['wallpaper']=helper.getwallpaper(entry['wallpapers'], 'call', 0)

                e['secret']=helper.getflag(entry['flags'], 'secret', False)

                results[pbentry]=e
                
            except helper.ConversionFailed:
                continue

        data['phonephonebook']=results
        return data
