### BITPIM
###
### Copyright (C) 2005 Stephen Wood <saw@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with a Samsung SPH-A460"""

import sha
import re
import struct

import common
import commport
import p_samsungspha460
import p_brew
import com_brew
import com_phone
import com_samsung_packet
import prototypes

numbertypetab=('home','office','cell','pager','fax','none')

class Phone(com_samsung_packet.Phone):
    "Talk to a Samsung SPH-A460 phone"

    desc="SPH-A460"

    protocolclass=p_samsungspha460
    serialsname='spha460'
    __groups_range=xrange(5)

    imagelocations=()
        # offset, index file, files location, type, maximumentries
    
    __cal_entries_range=xrange(70)
    __cal_num_of_read_fields=7
    __cal_num_of_write_fields=6
    __cal_entry=0
    __cal_start_datetime=1
    __cal_end_datetime=2
    __cal_datetime_stamp=3
    __cal_alarm_type=4
    __cal_read_name=6
    __cal_write_name=5
    __cal_alarm_values={
        '0': -1, '1': 0, '2': 10, '3': 30, '4': 60 }
    __cal_end_datetime_value=None
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

        self.log("Reading group information")
        print "Getting Groups"
        results['groups']=self.read_groups()
        print "Got Groups"

        self.log("Fundamentals retrieved")
        return results

    def savegroups(self, data):
        """Write the groups, sending only those groups that have had
        a name change.  (So that ringers don't get messed up)"""
        groups=data['groups']

        groups_onphone=self.read_groups() # Get groups on phone

        keys=groups.keys()
        keys.sort()

        for k in keys:
            if groups[k]['name']!=groups_onphone[k]['name']:
                if groups[k]['name']!="Unassigned":
                    req=self.protocolclass.groupnamesetrequest()
                    req.gid=k
                    req.groupname=groups[k]['name']
                    # Response will have ERROR, even though it works
                    self.sendpbcommand(req, self.protocolclass.unparsedresponse, ignoreerror=True)
        
    def makeentry(self, entry, data):
        e=self.protocolclass.pbentry()

        for k in entry:
            # special treatment for lists
            if k=='numbertypes' or k=='secrets':
                continue
            if k=='ringtone':
            #    e.ringtone=self._findmediaindex(data['ringtone-index'], entry['ringtone'], entry['name'], 'ringtone')
                continue
            elif k=='wallpaper':
            #    e.wallpaper=self._findmediaindex(data['wallpaper-index'], entry['wallpaper'], entry['name'], 'wallpaper')
                continue
            elif k=='numbers':
                #l=getattr(e,k)
                for numberindex in range(self.protocolclass.NUMPHONENUMBERS):
                    enpn=self.protocolclass.phonenumber()
                    # l.append(enpn)
                    e.numbers.append(enpn)
                for i in range(len(entry[k])):
                    numberindex=entry['numbertypes'][i]
                    e.numbers[numberindex].number=entry[k][i]
                    e.numbers[numberindex].secret=entry['secrets'][i]
                continue
            # everything else we just set
            setattr(e, k, entry[k])
        return e

    def savephonebook(self, data):
        "Saves out the phonebook"

        pb=data['phonebook']
        keys=pb.keys()
        keys.sort()
        keys=keys[:self.protocolclass.NUMPHONEBOOKENTRIES]

        #
        # Read the existing phonebook so that we cache birthdays
        # Erase all entries, being carefull to modify entries with
        # with URL's first
        #
        uslots={}
        names={}
        birthdays={}
        req=self.protocolclass.phonebookslotrequest()

        self.log('Erasing '+self.desc+' phonebook')
        progressmax=self.protocolclass.NUMPHONEBOOKENTRIES+len(keys)
        for slot in range(1,self.protocolclass.NUMPHONEBOOKENTRIES+1):
            req.slot=slot
            self.progress(slot,progressmax,"Erasing  "+`slot`)
            try:
                res=self.sendpbcommand(req,self.protocolclass.phonebookslotresponse, fixup=self.pblinerepair)
                if len(res) > 0:
                    names[slot]=res[0].entry.name
                    birthdays[slot]=res[0].entry.birthday
                    if len(res[0].entry.url)>0:
                        reqhack=self.protocolclass.phonebookslotupdaterequest()
                        reqhack.entry=res[0].entry
                        reqhack.entry.url=""
                        reqhack.entry.wallpaper=20
                        reqhack.entry.timestamp=[1900,1,1,0,0,0]
                        self.sendpbcommand(reqhack, self.protocolclass.phonebookslotupdateresponse)
                else:
                    names[slot]=""
            except:
                names[slot]=""
                self.log("Slot "+`slot`+" read failed")
            reqerase=self.protocolclass.phonebooksloterase()
            reqerase.slot=slot
            self.sendpbcommand(reqerase, self.protocolclass.phonebookslotupdateresponse)
                
        self.savegroups(data)

        for i in range(len(keys)):
            slot=keys[i]
            req=self.protocolclass.phonebookslotupdaterequest()
            req.entry=self.makeentry(pb[slot],data)
            if names[slot]==req.entry.name:
                req.entry.birthday=birthdays[slot]
            self.log('Writing entry '+`slot`+" - "+req.entry.name)
            self.progress(i+self.protocolclass.NUMPHONEBOOKENTRIES,progressmax,"Writing "+req.entry.name)
            self.sendpbcommand(req, self.protocolclass.phonebookslotupdateresponse)
        self.progress(progressmax+1,progressmax+1, "Phone book write completed")
        return data
        
    getwallpapers=None
    getringtones=None

class Profile(com_samsung_packet.Profile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    def __init__(self):
        com_samsung_packet.Profile.__init__(self)
        self.numbertypetab=numbertypetab

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        #('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'read', None),   # all calendar reading
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        )

