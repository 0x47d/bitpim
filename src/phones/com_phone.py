### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$


"""Generic phone stuff that all models inherit from"""


import common
import commport
import copy
import re
import sys
import time


# when trying to setmode, we ignore various exception types
# since the types are platform specific (eg on windows we get pywintypes.error)
# so we have to construct the list here of which ones we ignore
modeignoreerrortypes=[ commport.CommTimeout,common.CommsDeviceNeedsAttention ]
try:
    import pywintypes
    modeignoreerrortypes.append(pywintypes.error)
except:
    pass

# has to be tuple or it doesn't work
modeignoreerrortypes=tuple(modeignoreerrortypes) 


class Phone:
    """Base class for all phones"""
    
    MODENONE="modenone"  # not talked to yet
    MODEMODEM="modemodem" # modem mode

    desc="Someone forget to set desc in derived class"

    def __init__(self, logtarget, commport):
        self.logtarget=logtarget
        self.comm=commport
        self.mode=self.MODENONE
        self.__msg=None

    def close(self):
        self.comm.close()
        self.comm=None

    def log(self, str):
        "Log a message"
        if self.logtarget:
            self.logtarget.log("%s: %s" % (self.desc, str))

    def logdata(self, str, data, klass=None):
        "Log some data with option data object/class for the analyser"
        if self.logtarget:
            self.logtarget.logdata("%s: %s" % (self.desc, str), data, klass)

    def alert(self, message, wait):
        """Raises an alert in the main thread

        @param message: The message to display
        @param wait:  Should this function block until the user confirms the message
        """
        assert wait == False
        assert self.logtarget
        self.logtarget.log("<!= alert wait=%s =!>%s: %s" % (`wait`, self.desc, message))

    def progress(self, pos, max, desc):
        "Update the progress meter"
        if self.logtarget:
            self.logtarget.progress(pos, max, desc)

    def raisecommsdnaexception(self, str):
        "Raise a comms DeviceNeedsAttention Exception"
        self.mode=self.MODENONE
        self.comm.shouldloop=True
        raise common.CommsDeviceNeedsAttention( "The phone is not responding while "+str+".\n\nSee the help for troubleshooting tips", self.desc+" on "+self.comm.port)

    def raisecommsexception(self, str, klass):
        self.mode=self.MODENONE
        raise klass(str, self.desc+" on "+self.comm.port)

    def setmode(self, desiredmode):
        "Ensure the phone is in the right mode"
        if self.mode==desiredmode: return

        strmode=None
        strdesiredmode=None
        for v in dir(self):
            if len(v)>len('MODE') and v[:4]=='MODE':
                if self.mode==getattr(self, v):
                    strmode=v[4:]
                if desiredmode==getattr(self,v):
                    strdesiredmode=v[4:]
        if strmode is None:
            raise Exception("No mode for %s" %(self.mode,))
        if strdesiredmode is None:
            raise Exception("No desired mode for %s" %(desiredmode,))
        strmode=strmode.lower()
        strdesiredmode=strdesiredmode.lower()

        for func in ( '_setmode%sto%s' % (strmode, strdesiredmode),
                        '_setmode%s' % (strdesiredmode,)):
            if hasattr(self,func):
                try:
                    res=getattr(self, func)()
                except modeignoreerrortypes:
                    res=False
                if res: # mode changed!
                    self.mode=desiredmode
                    self.log("Now in "+strdesiredmode+" mode")
                    return

        # failed
        self.mode=self.MODENONE
        while self.comm.IsAuto():
            self.comm.NextAutoPort()
            return self.setmode(desiredmode)
        self.raisecommsdnaexception("transitioning mode from %s to %s" \
                                 % (strmode, strdesiredmode))
        

    def _setmodemodem(self):
        for baud in (0, 115200, 38400, 19200, 230400):
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            self.comm.write("AT\r\n")
            try:
                self.comm.readsome()
                return True
            except modeignoreerrortypes:
                pass
        return False       


class Profile:

    WALLPAPER_WIDTH=100
    WALLPAPER_HEIGHT=100
    MAX_WALLPAPER_BASENAME_LENGTH=64
    WALLPAPER_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="bmp"

    MAX_RINGTONE_BASENAME_LENGTH=64
    RINGTONE_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 ."

    # which usb ids correspond to us
    usbids=( 
        )
    # which device classes we are.
    deviceclasses=("modem", "serial")

    def __init__(self):
        pass

    _supportedsyncs=(
        )

    def SyncQuery(self, source, action, type):
        if (source, action, type) in self._supportedsyncs or \
           (source, action, None) in self._supportedsyncs:
            return True
        return False


class NoFilesystem:

    def __raisefna(self, desc):
        raise common.FeatureNotAvailable(self.desc+" on "+self.comm.port, desc+" is not available with this model phone")

    def getfirmwareinformation(self):
        self.__raisefna("getfirmwareinformation")

    def offlinerequest(self, reset=False):
        self.__raisefna("offlinerequest")

    def modemmoderequest(self):
        self.__raisefna("modemmoderequest")

    def mkdir(self, name):
        self.__raisefna("filesystem (mkdir)")
        
    def mkdirs(self, name):
        self.__raisefna("filesystem (mkdirs)")

    def rmdir(self, name):
        self.__raisefna("filesystem (rmdir)")

    def rmfile(self, name):
        self.__raisefna("filesystem (rmfile)")

    def getfilesystem(self, dir="", recurse=0):
        self.__raisefna("filesystem (getfilesystem)")

    def writefile(self, name, contents):
        self.__raisefna("filesystem (writefile)")

    def getfilecontents(self, name):
        self.__raisefna("filesystem (getfilecontents)")
