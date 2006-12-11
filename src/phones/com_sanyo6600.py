### BITPIM
###
### Copyright (C) 2006 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Talk to the Sanyo Katana (SCP-6600) cell phone"""
# standard modules
import re
import time
import sha

# my modules
import common
import p_brew
import p_sanyo8300
import p_sanyo4930
import p_sanyo6600
import com_brew
import com_phone
import com_sanyo
import com_sanyomedia
import com_sanyonewer
import com_sanyo3100
import prototypes
import bpcalendar

numbertypetab=( 'cell', 'home', 'office', 'pager',
                    'fax', 'none')

class Phone(com_sanyo3100.Phone):
    "Talk to the Sanyo Katana (SCP-6600) cell phone"

    desc="SCP-6600"

    FIRST_MEDIA_DIRECTORY=1
    LAST_MEDIA_DIRECTORY=2

    imagelocations=(
        # offset, directory #, indexflag, type, maximumentries
        )
    wallpaperexts=(".jpg", ".png", ".mp4", ".3g2",".JPG")


    protocolclass=p_sanyo6600
    serialsname='scp6600'

    builtinringtones=( 'None', 'Vibrate', '', '', '', '', '', '', '', 
                       'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5',
                       'Tone 6', 'Tone 7', 'Tone 8', '', '', '', '', '',
                       '', '', '', '', 
                       'Requiem:Dies Irae', 'Minute Waltz', 'Hungarian Dance',
                       'Military March', 'Ten Little Indians',
                       'Head,Shoulders,Knees&Toes', 'The Moment', 'Asian Jingle',
                       'Kung-fu','','','','','','','','','','','','','','','','','',
                       '','','','','','',
                       'Voice Alarm')


    # f1ff  None    65521
    # FFF2: Vibrate 65522
    calendar_defaultringtone=0
    calendar_defaultcaringtone=0
    calendar_toneoffset=33
    calendar_tonerange=xrange(4,100)

    def __init__(self, logtarget, commport):
        com_sanyo3100.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE
        self.numbertypetab=numbertypetab

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI."""
        req=self.protocolclass.esnrequest()
        res=self.sendpbcommand(req, self.protocolclass.esnresponse)
        results['uniqueserial']=sha.new(self.get_esn()).hexdigest()
        self.getmediaindices(results)

        results['groups']=self.read_groups()

        self.log("Fundamentals retrieved")

        return results

    def read_groups(self):
        g={}

        req=self.protocolclass.grouprequest()
        for slot in range(1,self.protocolclass.NUMGROUPS+1):
            req.slot = slot
            res=self.sendpbcommand(req, self.protocolclass.groupresponse)
            if res.entry.groupname_len:
                g[slot]={'name': res.entry.groupname}
        return g

    def xgetmediaindices(self, results):
        "Just index builtin media for now."

        com_sanyo.SanyoPhonebook.getmediaindices(self, results)
        ringermedia=results['ringtone-index']
        imagemedia=results['wallpaper-index']

        results['ringtone-index']=ringermedia
        results['wallpaper-index']=imagemedia
        return

    def getphonebook(self, result):
        "Code to retrieve packets we have discovered so far so we can work out their formats."
        pbook={}

        sortstuff = self.getsanyobuffer(self.protocolclass.pbsortbuffer)

        speedslot=[]
        speedtype=[]
        for i in range(self.protocolclass._NUMSPEEDDIALS):
            speedslot.append(sortstuff.speeddialindex[i].pbslotandtype & 0xfff)
            numtype=(sortstuff.speeddialindex[i].pbslotandtype>>12)-1
            if(numtype >= 0 and numtype <= len(self.numbertypetab)):
                speedtype.append(self.numbertypetab[numtype])
            else:
                speedtype.append("")

        numentries=sortstuff.slotsused
        self.log("There are %d entries" % (numentries,))

        count = 0 # Number of phonebook entries
        numcount = 0 # Number of phone numbers
        numemail = 0 # Number of emails
        numurl = 0 # Number of urls

        self.log("`sortstuff.groupslotsused` Groups")
        self.log("`sortstuff.slotsused` Contacts")
        self.log("`sortstuff.slotsused2` Duplicate Contacts")
        self.log("`sortstuff.numslotsused` Phone numbers")
        self.log("`sortstuff.emailslotsused` Email addresses")
        self.log("`sortstuff.urlslotsused` URLs")
        self.log("`sortstuff.num_address` Addresses")
        self.log("`sortstuff.num_memo`  Memos")
        numentries=sortstuff.slotsused

        reqindex=self.protocolclass.contactindexrequest()
        reqname=self.protocolclass.namerequest()
        reqnumber=self.protocolclass.numberrequest()
        reqemail=self.protocolclass.emailrequest()
        requrl=self.protocolclass.urlrequest()
        reqmemo=self.protocolclass.memorequest()
        reqaddress=self.protocolclass.addressrequest()
        for slot in range(self.protocolclass.NUMPHONEBOOKENTRIES):
            if sortstuff.usedflags[slot].used:
                entry={}
                reqindex.slot=slot
                resindex=self.sendpbcommand(reqindex,self.protocolclass.contactindexresponse)
                ringerid = resindex.entry.ringerid
                pictureid = resindex.entry.pictureid
                groupid = resindex.entry.groupid

                reqname.slot = resindex.entry.namep
                resname=self.sendpbcommand(reqname,self.protocolclass.nameresponse)
                name=resname.entry.name
                self.log(name)
                cat=result['groups'].get(groupid, {'name': "Unassigned"})['name']
                if cat != 'Unassigned':
                    entry['categories']=[ {'category': cat} ]
                entry['serials']=[ {'sourcetype': self.serialsname,

                                    'slot': slot,
                                    'sourceuniqueid': result['uniqueserial']} ]
                entry['names']=[ {'full': name} ]
                if resindex.entry.secret:
                    entry['flags']=[{'secret': True}]
                entry['numbers']=[]
                for numi in range(self.protocolclass.NUMPHONENUMBERS):
                    nump=resindex.entry.numberps[numi].slot
                    if nump < self.protocolclass.MAXNUMBERS:
                        reqnumber.slot=nump
                        resnumber=self.sendpbcommand(reqnumber,self.protocolclass.numberresponse)
                        numhash={'number':resnumber.entry.number, 'type': self.numbertypetab[resnumber.entry.numbertype-1]}
                        if resindex.entry.defaultnum==numi:
                            entry['numbers'].insert(0,numhash)
                        else:
                            entry['numbers'].append(numhash)

                for j in range(len(speedslot)):
                    if(speedslot[j]==slot):
                        for k in range(len(entry['numbers'])):
                            if(entry['numbers'][k]['type']==speedtype[j]):
                                entry['numbers'][k]['speeddial']=j+2
                                break

                urlp=resindex.entry.urlp
                if urlp<self.protocolclass.MAXURLS:
                    requrl.slot=urlp
                    resurl=self.sendpbcommand(requrl,self.protocolclass.urlresponse)
                    entry['urls']=[ {'url': resurl.entry.url} ]
                memop=resindex.entry.memop
                if memop<self.protocolclass.MAXMEMOS:
                    reqmemo.slot=memop
                    resmemo=self.sendpbcommand(reqmemo,self.protocolclass.memoresponse)
                    self.log("Memo: "+resmemo.entry.memo)
                    entry['memos']=[ {'memo': resmemo.entry.memo} ]
                addressp=resindex.entry.addressp
                if addressp<self.protocolclass.MAXADDRESSES:
                    reqaddress.slot=addressp
                    resaddress=self.sendpbcommand(reqaddress,self.protocolclass.addressresponse)
                    # Need to parse this address for phonebook.py
                    self.log("Address: "+resaddress.entry.address)
                    entry['addresses']=[ {'street': resaddress.entry.address} ]
                entry['emails']=[]
                for emaili in range(self.protocolclass.NUMEMAILS):
                    emaili=resindex.entry.emailps[emaili].slot
                    if emaili < self.protocolclass.MAXEMAILS:
                        reqemail.slot=emaili
                        resemail=self.sendpbcommand(reqemail,self.protocolclass.emailresponse)
                        self.log("Email: "+resemail.entry.email)
                        entry['emails'].append({'email': resemail.entry.email})
                        
                pbook[count]=entry
                self.progress(count, numentries, name)
                count+=1
                numcount+=len(entry['numbers'])
                if entry.has_key('emails'):
                    numemail+=len(entry['emails'])
                if entry.has_key('urls'):
                    numurl+=len(entry['urls'])
                
                
        self.progress(numentries, numentries, "Phone book read completed")
        self.log("Phone contains "+`count`+" contacts, "+`numcount`+" phone numbers, "+`numemail`+" Emails, "+`numurl`+" URLs")
        result['phonebook']=pbook
        cats=[]
        for i in result['groups']:
            cats.append(result['groups'][i]['name'])
        result['categories']=cats
        return pbook

    def savephonebook(self, data):
        newphonebook={}
        self.setmode(self.MODEBREW)
        self.setmode(self.MODEPHONEBOOK)
        sortstuff=self.protocolclass.pbsortbuffer()

        sortstuff=self.protocolclass.pbsortbuffer()

        for i in range(self.protocolclass.NUMGROUPS):
            sortstuff.groupslotusedflags.append(0)
            
        for i in range(self.protocolclass._NUMSPEEDDIALS):
            sortstuff.speeddialindex.append(0xffff)

        for i in range(self.protocolclass.NUMPHONEBOOKENTRIES):
            sortstuff.usedflags.append(0)
            sortstuff.used2flags.append(0)
            sortstuff.sortorder.append(0xffff)
            sortstuff.addressusedflags(0)
            sortstuff.memousedflags(0)

        for i in range(self.protocolclass.MAXNUMBERS):
            sortstuff.numusedflags(0)

        for i in range(self.protocolclass.MAXEMAILS):
            sortstuff.emailusedflags(0)

        for i in range(self.protocolclass.MAXURLS):
            sortstuff.urlusedflags(0)

        indexp=0
        namep=0
        nump=0
        urlp=0
        memop=0
        addressp=0
        emailp=0
        

    my_model='SCP-6600/US'
    my_manufacturer='SANYO'

parentprofile=com_sanyo3100.Profile
class Profile(parentprofile):

    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname
    phone_manufacturer=Phone.my_manufacturer
    phone_model=Phone.my_model

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        #('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
        ('call_history', 'read', None),# all call history list reading
        ('sms', 'read', None), # Read sms messages
        ('todo', 'read', None), # Read todos
    )

    def __init__(self):
        parentprofile.__init__(self)
        com_sanyonewer.Profile.__init__(self)
        self.numbertypetab=numbertypetab

