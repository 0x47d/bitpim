#!/usr/bin/env python
# $Id$

"""Detect and enumerate com(serial) ports

You should close all com ports you have open before calling any
functions in this module.  If you don't they will be detected as in
use.

Call the comscan() function It returns a list with each entry being a
dictionary of useful information.  See the platform notes for what is
in each one.

For your convenience the entries in the list are also sorted into
an order that would make sense to the user.

Platform Notes:
===============

w  Windows9x
W  WindowsNT/2K/XP
L  Linux
M  Mac

wWLM name               string   Serial device name
wWLM available          Bool     True if it is possible to open this device
wW   active             Bool     Is the driver actually running?  An example of when this is False
                                 is USB devices or Bluetooth etc that aren't currently plugged in.
                                 If you are presenting stuff for users, do not show entries where
                                 this is false
w    driverstatus       dict     status is some random number, problem is non-zero if there is some
                                 issue (eg device disabled)
wW   hardwareinstance   string   instance of the device in the registry as named by Windows
wWLM description        string   a friendly name to show users
wW   driverdate         tuple    (year, month, day)
 W   driverversion      string   version string
wW   driverprovider     string   the manufacturer of the device driver
wW   driverdescription  string   some generic description of the driver

"""

version="20 August 2003"

import sys
import os

def _IsWindows():
    return sys.platform=='win32'

def _IsLinux():
    return sys.platform.startswith('linux')

def _IsMac():
    return sys.platform.startswith('darwin')

if _IsWindows():
    import _winreg

    class RegistryAccess:
        """A class that is significantly easier to use to access the Registry"""
        def __init__(self, hive=_winreg.HKEY_LOCAL_MACHINE):
            self.rootkey=_winreg.ConnectRegistry(None, hive)

        def getchildren(self, key):
            """Returns a list of the child nodes of a key"""
            k=_winreg.OpenKey(self.rootkey, key)
            index=0
            res=[]
            while 1:
                try:
                    subkey=_winreg.EnumKey(k, index)
                    res.append(subkey)
                    index+=1
                except:
                    # ran out of keys
                    break
            return res

        def safegetchildren(self, key):
            """Doesn't throw exception if doesn't exist

            @return: A list of zero or more items"""
            try:
                k=_winreg.OpenKey(self.rootkey, key)
            except:
                return []
            index=0
            res=[]
            while 1:
                try:
                    subkey=_winreg.EnumKey(k, index)
                    res.append(subkey)
                    index+=1
                except:
                    # ran out of keys
                    break
            return res


        def getvalue(self, key, node):
            """Gets a value

            The result is returned as the correct type (string, int, etc)"""
            k=_winreg.OpenKey(self.rootkey, key)
            v,t=_winreg.QueryValueEx(k, node)
            if t==2:
                return int(v)
            if t==3:
                # lsb data
                res=0
                mult=1
                for i in v:
                    res+=ord(i)*mult
                    mult*=256
                return res
            # un unicode if possible
            if isinstance(v, type(u"")):
                try:
                    return str(v)
                except:
                    pass
            return v

        def safegetvalue(self, key, node, default=None):
            """Gets a value and if nothing is found returns the default"""
            try:
                return self.getvalue(key, node)
            except:
                return default

        def findkey(self, start, lookfor, prependresult=""):
            """Searches for the named key"""
            res=[]
            for i in self.getchildren(start):
                if i==lookfor:
                    res.append(prependresult+i)
                else:
                    l=self.findkey(start+"\\"+i, lookfor, prependresult+i+"\\")
                    res.extend(l)
            return res

        def getallchildren(self, start, prependresult=""):
            """Returns a list of all child nodes in the hierarchy"""
            res=[]
            for i in self.getchildren(start):
                res.append(prependresult+i)
                l=self.getallchildren(start+"\\"+i, prependresult+i+"\\")
                res.extend(l)
            return res
            
def _comscanwindows():
    """Get detail about all com ports on Windows

    This code functions on both win9x and nt/2k/xp"""
    # give results back
    results={}
    resultscount=0
    
    # list of active drivers on win98
    activedrivers={}
    
    reg=RegistryAccess(_winreg.HKEY_DYN_DATA)
    k=r"Config Manager\Enum"
    for device in reg.safegetchildren(k):
        hw=reg.getvalue(k+"\\"+device, "hardwarekey")
        status=reg.getvalue(k+"\\"+device, "status")
        problem=reg.getvalue(k+"\\"+device, "problem")
        activedrivers[hw.upper()]={ 'status': status, 'problem': problem }

    # list of active drivers on win2k
    reg=RegistryAccess(_winreg.HKEY_LOCAL_MACHINE)
    k=r"SYSTEM\CurrentControlSet\Services"
    for service in reg.safegetchildren(k):
        # we will just take largest number
        count=reg.safegetvalue(k+"\\"+service+"\\Enum", "Count", 0)
        next=reg.safegetvalue(k+"\\"+service+"\\Enum", "NextInstance", 0)
        for id in range(max(count,next)):
            hw=reg.getvalue(k+"\\"+service+"\\Enum", `id`)
            activedrivers[hw.upper()]=None


    # scan through everything listed in Enum
    reg=RegistryAccess(_winreg.HKEY_LOCAL_MACHINE)

    for enumstr, driverlocation, portnamelocation in ( \
            (r"SYSTEM\CurrentControlSet\Enum", r"SYSTEM\CurrentControlSet\Control\Class", r"\Device Parameters"), \
            (r"Enum", r"System\CurrentControlSet\Services\Class", ""), \
            ):
        for category in reg.safegetchildren(enumstr):
            catstr=enumstr+"\\"+category
            for driver in reg.getchildren(catstr):
                drvstr=catstr+"\\"+driver
                for instance in reg.getchildren(drvstr):
                    inststr=drvstr+"\\"+instance
                    try:
                        klass=reg.getvalue(inststr, "Class")
                    except:
                        continue

                    if klass.lower()=="ports":
                        # see if there is a portname
                        name=reg.safegetvalue(inststr+portnamelocation, "PORTNAME", "")

                        if len(name)<4 or name.lower()[:3]!="com":
                            continue

                        # ::Todo:: - verify COM is followed by digits only
                        # we now have some sort of match

                        res={}

                        res['name']=name.upper()

                        # is the device active?
                        kp=inststr[len(enumstr)+1:].upper()
                        if kp in activedrivers:
                            res['active']=True
                            if activedrivers[kp] is not None:
                                res['driverstatus']=activedrivers[kp]
                            # available?
                            try:
                                f=open(name, "rw")
                                f.close()
                                res['available']=True
                            except:
                                res['available']=False
                        else:
                            res['active']=False
                            res['available']=False

                        # hardwareinstance
                        res['hardwareinstance']=kp

                        # friendly name
                        res['description']=reg.getvalue(inststr, "FriendlyName")

                        # driver information key
                        drv=reg.getvalue(inststr, "Driver")
                        driverkey=driverlocation+"\\"+drv

                        # get some useful driver information
                        for subkey, reskey in \
                            ("driverdate", "driverdate"), \
                            ("providername", "driverprovider"), \
                            ("driverdesc", "driverdescription"), \
                            ("driverversion", "driverversion"):
                            val=reg.safegetvalue(driverkey, subkey, None)
                            if val is None:
                                continue
                            if reskey=="driverdate":
                                val2=val.split('-')
                                val=int(val2[2]), int(val2[0]), int(val2[1])
                            res[reskey]=val
                            
                        
                        results[resultscount]=res
                        resultscount+=1


    return results

# There follows a demonstration of how user friendly Linux is.
# Users are expected by some form of magic to know exactly what
# the names of their devices are.  We can't even tell the difference
# between a serial port not existing, and there not being sufficient
# permission to open it
def _comscanlinux(maxnum=9):
    """Get all the ports on Linux

    Note that Linux doesn't actually provide any way to enumerate actual ports.
    Consequently we just look for device nodes.  It still isn't possible to
    establish if there are actual device drivers behind them.  The availability
    testing is done however.

    @param maxnum: The highest numbered device to look for (eg maxnum of 17
                   will look for ttyS0 ... ttys17)
    """
    
    resultscount=0
    results={}
    for prefix, description in ( 
        ("/dev/cua", "Standard serial port"), 
        ("/dev/ttyUSB", "USB to serial convertor"), 
        ("/dev/usb/ttyUSB", "USB to serial convertor"), 
        ("/dev/usb/tts/", "USB to serial convertor") 
        ):
        for num in range(maxnum+1):
            name=prefix+`num`
            if not os.path.exists(name):
                continue
            res={}
            res['name']=name
            res['description']=description+" ("+name+")"
            try:
                f=open(name, "rw")
                f.close()
                res['available']=True
            except:
                res['available']=False
            results[resultscount]=res
            resultscount+=1
    return results


def _comscanmac(maxnum=9):
    """Get all the ports on Mac

    Since I don't have a Mac, I would welcome correct code for this.  It
    currently just looks for /dev/tty.usbserial99
    
    @param maxnum: The highest numbered device to look for (eg maxnum of 17
                   will look for ttyS0 ... ttys17)
    """
    
    resultscount=0
    results={}
    for prefix, description in ( 
        ("/dev/cuaa", "Standard serial port"), 
        ("/dev/tty.usbserial", "USB to serial port"), 
        ):
        for num in range(maxnum+1):
            name=prefix+`num`
            if not os.path.exists(name):
                continue
            res={}
            res['name']=name
            res['description']=description+" ("+name+")"
            try:
                f=open(name, "rw")
                f.close()
                res['available']=True
            except:
                res['available']=False
            results[resultscount]=res
            resultscount+=1
    return results

##def availableports():
##    """Gets list of available ports

##    It is verified that the ports can be opened.

##    @note:   You must close any ports you have open before calling this function, otherwise they
##             will not be considered available.

##    @return: List of tuples.  Each tuple is (port name, port description) - the description is user
##             friendly.  The list is sorted.
##    """
##    pass

def _stringint(str):
    """Seperate a string and trailing number into a tuple

    For example "com10" returns ("com", 10)
    """
    prefix=str
    suffix=""

    while len(prefix) and prefix[-1]>='0' and prefix[-1]<='9':
        suffix=prefix[-1]+suffix
        prefix=prefix[:-1]

    if len(suffix):
        return (prefix, int(suffix))
    else:
        return (prefix, None)
        
def _cmpfunc(a,b):
    """Comparison function for two port names

    In particular it looks for a number on the end, and sorts by the prefix (as a
    string operation) and then by the number.  This function is needed because
    "com9" needs to come before "com10"
    """

    aa=_stringint(a[0])
    bb=_stringint(b[0])

    if aa==bb:
        if a[1]==b[1]:
            return 0
        if a[1]<b[1]:
            return -1
        return 1
    if aa<bb: return -1
    return 1

def comscan(*args, **kwargs):
    """Call platform specific version of comscan function"""
    res={}
    if _IsWindows():
        res=_comscanwindows(*args, **kwargs)
    elif _IsLinux():
        res=_comscanlinux(*args, **kwargs)
    elif _IsMac():
        res=_comscanmac(*args, **kwargs)
    else:
        raise Exception("unknown platform "+sys.platform)

    # sort by name
    keys=res.keys()
    declist=[ (res[k]['name'], k) for k in keys]
    declist.sort(_cmpfunc)

    return [res[k[1]] for k in declist]
    

if __name__=="__main__":
    res=comscan()

    output="ComScan "+version+"\n\n"

    for r in res:
        rkeys=r.keys()
        rkeys.sort()

        output+=r['name']+":\n"
        offset=0
        for rk in rkeys:
            if rk=='name': continue
            v=r[rk]
            if not isinstance(v, type("")): v=`v`
            op=' %s: %s ' % (rk, v)
            if offset+len(op)>78:
                output+="\n"+op
                offset=len(op)+1
            else:
                output+=op
                offset+=len(op)

        if output[-1]!="\n":
            output+="\n"
        output+="\n"
        offset=0

    print output
        
