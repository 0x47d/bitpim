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
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'read', None),   # all calendar reading
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        )

