### BITPIM
###
### Copyright (C) 2004-2005 Stephen Wood <saw@bitpim.org>
### Copyright (C) 2005 Todd Imboden
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with a Samsung SPH-A620"""

import sha
import re
import struct

import common
import commport
import p_samsungspha620
import p_brew
import com_brew
import com_phone
import com_samsung_packet
import prototypes

numbertypetab=('home','office','cell','pager','fax','none')

class Phone(com_samsung_packet.Phone):
    "Talk to a Samsung SPH-A620 phone"

    desc="SPH-A620"

    protocolclass=p_samsungspha620
    serialsname='spha620'
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
        self.setmode(self.MODEMODEM)
        results['uniqueserial']=sha.new(self.get_esn()).hexdigest()

        self.log("Reading group information")

        results['groups']=self.read_groups()

        # Comment the next to out if you want to read the phonebook
        #self.getwallpaperindices(results)
        #self.getringtoneindices(results)
        self.log("Fundamentals retrieved")
        return results

    # digital_cam/jpeg Remove first 148 characters
    imagelocations=(
        # offset, index file, files location, type, maximumentries
        (100, "", "digital_cam/jpeg", "camera", 100)
        )
        
    def pblinerepair(self, line):
        "Extend incomplete lines"
        # VGA1000 Firmware WG09 doesn't return a full line unless birthday
        # is set.  Add extra commas so packet decoding works
        nfields=26                      # Can we get this from packet def?
        ncommas=self.countcommas(line)
        if ncommas<0:                   # Un terminated quote
            line+='"'
            ncommas = -ncommas
        if nfields-ncommas>1:
            line=line+","*(nfields-ncommas-1)
        return line

    def countcommas(self, line):
        inquote=False
        ncommas=0
        for c in line:
            if c == '"':
                inquote = not inquote
            elif not inquote and c == ',':
                ncommas+=1

        if inquote:
            ncommas = -ncommas
        
        return ncommas
        
    def getwallpapers(self, result):
        self.getwallpaperindices(result)
        return self.getmedia(self.imagelocations, result, 'wallpapers')

    
    def getmedia(self, maps, results, key):
        """Returns the contents of media as a dicxt where the key is a name
        returned by getindex, and the value is the contents of the media"""
        
        media={}
        for i in range(10000):
            try:
                req=p_brew.listfilerequest()
                req.entrynumber=i
                req.dirname='digital_cam/jpeg'
                res=self.sendbrewcommand(req, p_brew.listfileresponse)
                filename=res.filename
                p=filename.rfind("/")
                basefilename=filename[p+1:]+".jpg"
                print "Getting ",basefilename
                contents=self.getfilecontents(filename)
                media[basefilename]=contents[148:]
            except com_brew.BrewNoMoreEntriesException:
                break

        results[key]=media

    def getwallpaperindices(self, results):
        """Get the index of camera pictures"""
        imagemedia={}
        for i in range(10000):
            try:
                req=p_brew.listfilerequest()
                req.entrynumber=i
                req.dirname='digital_cam/jpeg'
                res=self.sendbrewcommand(req, p_brew.listfileresponse)
                filename=res.filename
                p=filename.rfind("/")
                filename=filename[p+1:]+".jpg"
                # Just a made up index number for now.  Have not studied
                # what phone is using.
                imagemedia[100+i]={'name': filename, 'origin': "camera"}

            except com_brew.BrewNoMoreEntriesException:
                break

        results['wallpaper-index']=imagemedia
        return
        
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
            if k=='numbers':
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
        self.savegroups(data)

        pb=data['phonebook']
        keys=pb.keys()
        keys.sort()
        keys=keys[:self.protocolclass.NUMPHONEBOOKENTRIES]

        progressmax=len(data['phonebook'])

        for i in range(len(keys)):
            slot=keys[i]
            req=self.protocolclass.phonebookslotupdaterequest()
            req.entry=self.makeentry(pb[slot],data)
            self.log('Writing entry '+`slot`+" - "+req.entry.name)
            self.progress(i,progressmax,"Writing "+req.entry.name)
            self.sendpbcommand(req, self.protocolclass.phonebookslotupdateresponse)
        self.progress(progressmax+1,progressmax+1, "Phone book write completed")
        return data
        
    def getamsindices(self, results):
        info_offset=900
        label_offset=14420
        contents=self.getfilecontents(self.__ams_index_file)
        records=ord(contents[37424]) #this tells how many records there are in the ams file
        offset=0
        rt={}
        j=0
        for i in range(records):
            info=struct.unpack('8hl8h',contents[info_offset+offset:info_offset+offset+36])
            if info[9]==12: #ringtone file
                rt_name=self.getamstext(label_offset,info[2],contents)
                rt_dir='ams/'+self.getamstext(label_offset,info[0],contents)
                rt_type=self.getamstext(label_offset,info[10],contents)
                if rt_type=="audio/vnd.qcelp":
                    rt_filetype='.qcp'
                elif rt_type=="audio/midi":
                    rt_filetype='.mid'
                elif rt_type=="application/x-pmd":
                    rt_filetype='.pmd'
                else:
                    rt_filetype=''
                rt_file=rt_name+rt_filetype
                rt[j]={'name':rt_file,'location':rt_dir,'origin':'ringers'}
                j+=1
            offset+=36
        results['ringtone-index']=rt
        return

    def getamstext(self, offset,location,contents): #this reads from the amsregistry file until it hits the spacer which is '00'
        length=1 
        i=0
        while i==0:
            if common.hexify(contents[offset+location+length])=='00':
                i=1
            else:
                length+=1
        amstext=contents[offset+location:offset+location+length]       
        return amstext    

    def getringtones(self, results):
        self.setmode(self.MODEBREW)
        self.getamsindices(results)
        tones={}
        for i in range(len(results['ringtone-index'])):
            tones[results['ringtone-index'][i]['name']]=self.getfilecontents(results['ringtone-index'][i]['location'])
            i+=1
        results['ringtone']=tones
    
class Profile(com_samsung_packet.Profile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    def __init__(self):
        com_samsung_packet.Profile.__init__(self)
        self.numbertypetab=numbertypetab

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        #('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
        ('calendar', 'read', None),   # all calendar reading
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        )

