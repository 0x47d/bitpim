### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###

"""Communicate with the LG VX9800 cell phone
"""

# standard modules
import re
import time
import cStringIO
import sha

# my modules
import common
import commport
import copy
import com_lgvx4400
import p_brew
import p_lgvx9800
import com_lgvx8100
import com_brew
import com_phone
import com_lg
import prototypes
import bpcalendar
import call_history
import sms
import memo

class Phone(com_lg.LGNewIndexedMedia2,com_lgvx8100.Phone):
    "Talk to the LG VX9800 cell phone"

    desc="LG-VX9800"

    protocolclass=p_lgvx9800
    serialsname='lgvx9800'
    my_model='VX9800'

    builtinringtones= ('Low Beep Once', 'Low Beeps', 'Loud Beep Once', 'Loud Beeps', 'VZW Default Tone') + \
                      tuple(['Ringtone '+`n` for n in range(1,11)]) + \
                      ('No Ring',)

    ringtonelocations= (
        # type       index-file   size-file directory-to-use lowest-index-to-use maximum-entries type-major icon
        ( 'ringers', 'dload/my_ringtone.dat', 'dload/my_ringtonesize.dat', 'brew/16452/lk/mr', 100, 150, 0x201, 1),
        # the sound index file uses the same index as the ringers, bitpim does not support this (yet)
        #( 'sounds', 'dload/mysound.dat', 'dload/mysoundsize.dat', 'brew/16452/ms', 100, 150, 2, 0),
        )

    calendarlocation="sch/schedule.dat"
    calendarexceptionlocation="sch/schexception.dat"
    calenderrequiresreboot=0
    memolocation="sch/memo.dat"

    builtinwallpapers = () # none

    wallpaperlocations= (
        ( 'images', 'dload/image.dat', 'dload/imagesize.dat', 'brew/16452/mp', 100, 50, 0, 0),
        )
        
    def __init__(self, logtarget, commport):
        com_lgvx8100.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE

    def get_esn(self, data=None):
        # return the ESN of this phone
        return '%0X'%self.sendbrewcommand(self.protocolclass.ESN_req(),
                                          self.protocolclass.ESN_resp).esn

    def get_detect_data(self, res):
        com_lgvx8100.Phone.get_detect_data(self, res)
        res[self.esn_file_key]=self.get_esn()

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI.

        Currently this is:

          - 'uniqueserial'     a unique serial number representing the phone
          - 'groups'           the phonebook groups
          - 'wallpaper-index'  map index numbers to names
          - 'ringtone-index'   map index numbers to ringtone names

        This method is called before we read the phonebook data or before we
        write phonebook data.
        """

        # use a hash of ESN and other stuff (being paranoid)
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        results['uniqueserial']=sha.new(self.get_esn()).hexdigest()
        # now read groups
        self.log("Reading group information")
        buf=prototypes.buffer(self.getfilecontents("pim/pbgroup.dat"))
        g=self.protocolclass.pbgroups()
        g.readfrombuffer(buf)
        self.logdata("Groups read", buf.getdata(), g)
        groups={}
        for i in range(len(g.groups)):
            if len(g.groups[i].name): # sometimes have zero length names
                groups[i]={'name': g.groups[i].name }
        results['groups']=groups
        self.getwallpaperindices(results)
        self.getringtoneindices(results)
        self.log("Fundamentals retrieved")
        return results

    # Phonebook stuff-----------------------------------------------------------

    # SMS Stuff-----------------------------------------------------------------
    def _readsms(self):
        res={}
        # go through the sms directory looking for messages
        for item in self.listfiles("sms").values():
            folder=None
            for f,pat in self.protocolclass.SMS_PATTERNS.items():
                if pat.match(item['name']):
                    folder=f
                    break
            if folder:
                buf=prototypes.buffer(self.getfilecontents(item['name'], True))
                self.logdata("SMS message file " +item['name'], buf.getdata())
            if folder=='Inbox':
                sf=self.protocolclass.sms_in()
                sf.readfrombuffer(buf)
                entry=self._getinboxmessage(sf)
                res[entry.id]=entry
            elif folder=='Sent':
                sf=self.protocolclass.sms_out()
                sf.readfrombuffer(buf)
                entry=self._getoutboxmessage(sf)
                res[entry.id]=entry
            elif folder=='Saved':
                sf=self.protocolclass.sms_saved()
                sf.readfrombuffer(buf)
                if sf.inboxmsg:
                    entry=self._getinboxmessage(sf.inbox)
                else:
                    entry=self._getoutboxmessage(sf.outbox)
                entry.folder=entry.Folder_Saved
                res[entry.id]=entry
        return res 


#-------------------------------------------------------------------------------
parentprofile=com_lgvx8100.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='VX9800'

    WALLPAPER_WIDTH=320
    WALLPAPER_HEIGHT=256
    MAX_WALLPAPER_BASENAME_LENGTH=32
    WALLPAPER_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="jpg"

    # the 9800 uses "W" for wait in the dialstring, it does not support "T"
    DIALSTRING_CHARS="[^0-9PW#*]"
   
    MAX_RINGTONE_BASENAME_LENGTH=32
    RINGTONE_FILENAME_CHARS="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ."

    # there is an origin named 'aod' - no idea what it is for except maybe
    # 'all other downloads'

    # the vx8100 supports bluetooth for connectivity to the PC, define the "bluetooth_mgd_id"
    # to enable bluetooth discovery during phone detection
    # the bluetooth address starts with LG's the three-octet OUI, all LG phone
    # addresses start with this, it provides a way to identify LG bluetooth devices
    # during phone discovery
    # OUI=Organizationally Unique Identifier
    # see http://standards.ieee.org/regauth/oui/index.shtml for more info
    bluetooth_mfg_id="001256"

    # the 8100 doesn't have seperate origins - they are all dumped in "images"
    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    def GetImageOrigins(self):
        return self.imageorigins

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 320, 'height': 230, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 320, 'height': 198, 'format': "JPEG"}))

    def GetTargetsForImageOrigin(self, origin):
        return self.imagetargets

 
    def __init__(self):
        parentprofile.__init__(self)

    _supportedsyncs=(
        ('phonebook', 'read', None),   # all phonebook reading
        ('calendar', 'read', None),    # all calendar reading
        ('wallpaper', 'read', None),   # all wallpaper reading
        ('ringtone', 'read', None),    # all ringtone reading
        ('call_history', 'read', None),# all call history list reading
        ('sms', 'read', None),         # all SMS list reading
        ('memo', 'read', None),        # all memo list reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'MERGE'),       # merge and overwrite ringtone
        ('ringtone', 'write', 'OVERWRITE'),
        ('sms', 'write', 'OVERWRITE'),        # all SMS list writing
        ('memo', 'write', 'OVERWRITE'),       # all memo list writing
        )
