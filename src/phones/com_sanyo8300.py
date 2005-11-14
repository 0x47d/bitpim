### BITPIM
###
### Copyright (C) 2005 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Talk to the Sanyo SCP-8300 cell phone"""
# standard modules
import re
import time
import sha

# my modules
import common
import p_brew
import p_sanyo8300
import com_brew
import com_phone
import com_sanyo
import com_sanyomedia
import com_sanyonewer
import prototypes
import bpcalendar

numbertypetab=( 'cell', 'home', 'office', 'pager',
                    'fax', 'data', 'none' )

class Phone(com_sanyonewer.Phone):
    "Talk to the Sanyo PM8300 cell phone"

    desc="PM8300"

    FIRST_MEDIA_DIRECTORY=1
    LAST_MEDIA_DIRECTORY=3

    wallpaperexts=(".jpg", ".png", ".mp4", "3g2")
    ringerexts=(".mid", ".qcp", ".mp3", ".m4a",".pmd",".bin")

    imagelocations=(
        # offset, directory #, indexflag, type, maximumentries
        )    

    protocolclass=p_sanyo8300
    serialsname='mm8300'

    builtinringtones=( 'None', 'Vibrate', 'Ringer & Voice', '', '', '', '', '', '', 
                       'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5',
                       'Tone 6', 'Tone 7', 'Tone 8', '', '', '', '', '',
                       '', '', '', '', '', '', '',
                       'Tschaik.Swanlake', 'Satie Gymnop.#1',
                       'Hungarian Dance', 'Beethoven Sym.5', 'Greensleeves',
                       'Foster Ky. Home', 'The Moment', 'Asian Jingle',
                       'Disco')

    # Calendar ringer info
    # e8 02 Tone 1  744
    # f9 02 Melody 1  761
    # fe 02 Melody 6  766
    # ff 02 Melody 7  767
    # 00 03 Melody 8  768
    # 01 03 Melody 9  769
    # 00 00 Normal
    # f1 ff None
    # f2 ff Vibrate
    # 19 03 Voice
    calendar_defaultringtone=0
    calendar_defaultcaringtone=0

    def __init__(self, logtarget, commport):
        com_sanyonewer.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE
        self.numbertypetab=numbertypetab

    def _setmodebrew(self):
        req=p_brew.firmwarerequest()
        respc=p_brew.testing0cresponse
        
        for baud in 0, 38400,115200:
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.sendbrewcommand(req, respc, callsetmode=False)
                return True
            except com_phone.modeignoreerrortypes:
                pass

        # send AT$QCDMG at various speeds
        for baud in (0, 115200, 19200, 230400):
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            print "Baud="+`baud`

            try:
                self.comm.write("AT$QCDMG\r\n")
            except:
                # some issue during writing such as user pulling cable out
                self.mode=self.MODENONE
                self.comm.shouldloop=True
                raise
            try:
                # if we got OK back then it was success
                if self.comm.readsome().find("OK")>=0:
                    break
            except com_phone.modeignoreerrortypes:
                self.log("No response to setting QCDMG mode")

        # verify if we are in DM mode
        for baud in 0,38400,115200:
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.sendbrewcommand(req, respc, callsetmode=False)
                return True
            except com_phone.modeignoreerrortypes:
                pass
        return False

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI."""
        req=self.protocolclass.esnrequest()
        res=self.sendpbcommand(req, self.protocolclass.esnresponse)
        results['uniqueserial']=sha.new('%8.8X' % res.esn).hexdigest()
        self.getmediaindices(results)

        self.log("Fundamentals retrieved")

        return results

class Profile(com_sanyonewer.Profile):

    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname
    phone_manufacturer='SANYO'
    phone_model='SCP-8300/US'
    # GMR: 1.115SP   ,10019

    WALLPAPER_WIDTH=176
    WALLPAPER_HEIGHT=220

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'MERGE'),
        ('ringtone', 'write', 'MERGE'),
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
    )

    def __init__(self):
        com_sanyonewer.Profile.__init__(self)
        self.numbertypetab=numbertypetab

