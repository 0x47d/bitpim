### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

"""Generic phone stuff that all models inherit from"""


import common
import commport
import copy
import re
import time

# when trying to setmode, we ignore various exception types
# since the types are platform specific (eg on windows we get pywintypes.error)
# so we have to construct the list here of which ones we ignore
modeignoreerrortypes=[ commport.CommTimeout ]
try:
    import pywintypes
    modeignoreerrortypes.append(pywintypes.error)
except:
    pass

# has to be tuple or it doesn't work
modeignoreerrortypes=tuple(modeignoreerrortypes) 


class Phone:
    MODENONE="modenone"  # not talked to yet
    MODEMODEM="modemodem" # modem mode

    desc="Someone forget to set desc in derived class"

    def __init__(self, logtarget, commport):
        self.logtarget=logtarget
        self.comm=commport

    def close(self):
        self.comm.close()
        self.comm=None

    def log(self, str):
        if self.logtarget:
            self.logtarget.log("%s: %s" % (self.desc, str))

    def logdata(self, str, data, klass=None):
        if self.logtarget:
            self.logtarget.logdata("%s: %s" % (self.desc, str), data, klass)

    def progress(self, pos, max, desc):
        if self.logtarget:
            self.logtarget.progress(pos, max, desc)

    def raisecommsexception(self, str):
        self.mode=self.MODENONE
        self.comm.shouldloop=True
        raise common.CommsDeviceNeedsAttention(self.desc+" on "+self.comm.port, "The phone is not responding while "+str+".\n\nSee the help for troubleshooting tips")
        

    def setmode(self, desiredmode):
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
            print "looking for",func
            if hasattr(self,func):
                try:
                    print "executing", func
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
        self.raisecommsexception("transitioning mode from %s to %s" \
                                 % (strmode, strdesiredmode))
        
