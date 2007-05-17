#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2007 Nathan Hjelm <hjelmn@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###

"""
Communicate with the LG VX8700 cell phone
"""

# BitPim modules
import common
import com_phone
import com_brew
import prototypes
import commport
import p_brew
import helpids
import com_lgvx8500
import p_lgvx8700

#-------------------------------------------------------------------------------
parentphone=com_lgvx8500.Phone
class Phone(parentphone, com_brew.RealBrewProtocol2):
    "Talk to LG VX-8700 cell phone"

    desc="LG-VX8700"
    helpid=helpids.ID_PHONE_LGVX8700
    protocolclass=p_lgvx8700
    serialsname='lgvx8700'

    my_model='VX8700'

    ringtonelocations= (
        # type           index file             default dir                 external dir  max  type   index
        ('ringers',     'dload/myringtone.dat','brew/mod/10889/ringtones', '',            100, 0x01,  100),
	( 'sounds',     'dload/mysound.dat',   'brew/mod/18067',           '',            100, 0x02,  None),
        ( 'sounds(sd)', 'dload/sd_sound.dat',  'mmc1/my_sounds',           '',            100, 0x02,  None),
        ( 'music',      'dload/efs_music.dat', 'my_music',                 '',            100, 0x104, None),
        ( 'music(sd)',  'dload/sd_music.dat',  'mmc1/my_music',            '',            100, 0x14,  None),
        )

    wallpaperlocations= (
        #  type          index file            default dir     external dir  max  type Index
        ( 'images',     'dload/image.dat',    'brew/mod/10888', '',          100, 0x00, 100),
        ( 'images(sd)', 'dload/sd_image.dat', 'mmc1/my_pix',    '',          100, 0x10, None),
        ( 'video',      'dload/video.dat',    'brew/mod/10890', '',          100, 0x03, None),
        ( 'video(sd)',  'dload/sd_video.dat', 'mmc1/my_flix',   '',          100, 0x13, None),
        )


    def __init__(self, logtarget, commport):
        parentphone.__init__(self, logtarget, commport)
        self._in_DM = False

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
        if not self._in_DM:
            self.enter_DM()
        return parentphone.getfundamentals(self, results)

    def is_mode_brew(self):
        req=p_brew.memoryconfigrequest()
        respc=p_brew.memoryconfigresponse
        
        for baud in 0, 38400, 115200:
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.sendbrewcommand(req, respc, callsetmode=False)
                return True
            except com_phone.modeignoreerrortypes:
                pass
        return False

    def listsubdirs(self, dir='', recurse=0):
        return com_brew.RealBrewProtocol2.getfilesystem(self, dir, recurse, directories=1, files=0)

    def listfiles(self, dir=''):
        if self._in_DM==False and self.my_model=='VX8700':
            # enter DM to enable file reading/writing
            self.enter_DM()
        return com_brew.RealBrewProtocol2.listfiles(self, dir)

    def getfilesystem(self, dir="", recurse=0, directories=1, files=1):
        # BREW2's get filesystem is used here because BREW1's does not appear not to work well on the vx8700
        return com_brew.RealBrewProtocol2.getfilesystem(self, dir, recurse, directories, files)

    def enter_DM (self):
        # request challenge
        req = self.protocolclass.ULReq(unlock_key=0)
        res = self.sendbrewcommand(req, self.protocolclass.ULRes)

        # generate and send response
        key = self.get_challenge_response(res.unlock_key);
        req = self.protocolclass.ULReq(unlock_code=1, unlock_key=key)
        res = self.sendbrewcommand(req, self.protocolclass.ULRes)

        if res.unlock_ok == 1:
            self.log('Phone is now in DM mode')
            self._in_DM=True
        else:
            self.log('Failed to enter DM mode')

    def sendbrewcommand(self, request, responseclass, callsetmode=True):
        if callsetmode:
            self.setmode(self.MODEBREW)
        buffer=prototypes.buffer()
        request.writetobuffer(buffer, logtitle="com_lgvx8700: sendbrewcommand")
        data=buffer.getvalue()

        # the memory config request does not need to be unlocked
        if (data[0]=="\x59" or data[0]=="\x4b") and data[1]!="\x0c":
            # "unlock" the brew command by sending a 0x5c command with the same data
            # unlocking works with the LG vx9400 as well (tested)
            if data[0]=="\x59":
                uldata = "\x5c" + data[1:]
            else:
                # do we need to drop a character from a brew2 command? it works.
                uldata = "\x5c" + data[2:]
            uldata=common.pppescape(uldata+common.crcs(uldata))+common.pppterminator
            self.logdata("Unlock brew command", uldata, None)
            try:
                data=self.comm.writethenreaduntil(uldata, False, common.pppterminator, logreaduntilsuccess=False) 
            except modeignoreerrortypes:
                self.mode=self.MODENONE
                self.raisecommsdnaexception("unlocking filesystem command")
            self.logdata("Unlock brew command response", data, None)
        return com_brew.RealBrewProtocol.sendbrewcommand(self, request, responseclass, callsetmode=False)


#-------------------------------------------------------------------------------
parentprofile=com_lgvx8500.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    BP_Calendar_Version=3
    phone_manufacturer='LG Electronics Inc'
    phone_model='VX8700'
    # inside screen resoluation
    WALLPAPER_WIDTH=240
    WALLPAPER_HEIGHT=320

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images(sd)"))
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "video(sd)"))

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "fullscreen",
                                      {'width': 176, 'height': 220, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 176, 'height': 184, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "outsidelcd",
                                      {'width': 128, 'height': 160, 'format': "JPEG"}))
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "pictureid",
                                      {'width': 128, 'height': 142, 'format': "JPEG"}))

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
        ('call_history', 'read', None),# all call history list reading
        ('sms', 'read', None),         # all SMS list reading
        ('memo', 'read', None),        # all memo list reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'MERGE'),      # merge and overwrite ringtone
        ('ringtone', 'write', 'OVERWRITE'),
        ('sms', 'write', 'OVERWRITE'),        # all SMS list writing
        ('memo', 'write', 'OVERWRITE'),       # all memo list writing
        ('t9_udb', 'read', 'OVERWRITE'),
        ('t9_udb', 'write', 'OVERWRITE'),
        )
