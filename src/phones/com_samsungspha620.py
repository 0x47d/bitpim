### BITPIM
###
### Copyright (C) 2003-2004 Stephen Wood <saw@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with a Samsung SCH-A620"""

import sha
import re

import common
import commport
import p_samsungscha620
import com_brew
import com_phone
import com_samsung_packet
import prototypes

numbertypetab=('home','office','cell','pager','fax','none')

class Phone(com_samsung_packet.Phone):
    "Talk to a Samsung SCH-A620 phone"

    desc="SCH-A620"

    protocolclass=p_samsungscha620
    serialsname='scha620'
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
        
    def save_groups(self, data):
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
                    sendpbcommand(req, self.protocolclass.unparsedresponse)

        
    def savephonebook(self, data):
        "Saves out the phonebook"
        self.savegroups(data)

        progressmax=len(data['phonebook'])
        
        return
        
    getringtones=None
    
class Profile(com_samsung_packet.Profile):
    serialsname='scha620'

    def __init__(self):
        com_samsung_packet.Profile.__init__(self)

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        #('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('calendar', 'read', None),   # all calendar reading
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        )

