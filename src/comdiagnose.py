#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

"""Generate opinions on the attached com devices"""

import comscan

def diagnose(portlist):
    """Returns data suitable for use in com port settings dialog

    @param portlist: A list of ports as returned by L{comscan.comscan}()
    @return: A list of tuples (whattodisplay, portselected, htmldiagnosis)
    """
    res=[]
    # we sort into 3 lists
    # available
    # not available but active
    # the rest
    available=[]
    notavailablebutactive=[]
    therest=[]
    for port in portlist:
        if port.has_key("available") and port["available"]:
            available.append(port)
            continue
        if port.has_key("available") and port.has_key("active") and port["active"]:
            notavailablebutactive.append(port)
            continue
        therest.append(port)

    if len(available):
        whattodisplay="===== Available Ports ===== "
        portselected=None
        htmldiagnosis="<p>These ports are open and can be selected"
        res.append( (whattodisplay, portselected, htmldiagnosis) )
        for port in available:
            whattodisplay=port['description']
            portselected=port['name']
            htmldiagnosis="<p>This port is open and can be selected.<p>"+genhtml(port)
            res.append( (whattodisplay, portselected, htmldiagnosis) )

    if len(notavailablebutactive):
        whattodisplay="===== Ports in use ====="
        portselected=None
        htmldiagnosis="<p>These ports are active, but are in use by another program, or you do not have permissions to access them."
        res.append( (whattodisplay, portselected, htmldiagnosis) )
        for port in notavailablebutactive:
            whattodisplay=port['description']
            portselected=port['name']
            htmldiagnosis="<p>This port is active but not available for use.<p>"+genhtml(port)
            res.append( (whattodisplay, portselected, htmldiagnosis) )
        
    if len(therest):
        whattodisplay="===== Inoperable Ports ====="
        portselected=None
        htmldiagnosis="""<p>These ports are known to your operating system, but cannot be used.  
        This may be because the device is not plugged in (such as on a USB to serial cable) or because 
        you don't have sufficient permissions to use them."""
        res.append( (whattodisplay, portselected, htmldiagnosis) )
        for port in therest:
            whattodisplay=port['description']
            portselected=port['name']
            htmldiagnosis="""<p>This port should not be selected.  If you believe it is the correct
            port, you should cause it to become available such as by plugging in the cable or ensuring
            you have correct permissions.  Press refresh once you have done so and it should be listed
            under available. Note that the name may change as it becomes available.<p>"""+genhtml(port)
            res.append( (whattodisplay, portselected, htmldiagnosis) )

    return res

def genhtml(port):
    """Returns nice html describing a port dict"""
    sfont='<font size="-1">'
    efont='</font>'
    res='<table width="100%"><tr><th width="20%">Property<th width="40%">Value<th width="40%">Description</tr>\n'
    keys=port.keys()
    keys.sort()
    for k in keys:
        # property
        res+="<tr><td>"+sfont+k+efont+"</td><td>\n"
        # value
        if k=='active' or k=='available':
            if port[k]:
                res+=sfont+"True"+efont
            else:
                res+=sfont+"False"+efont
        elif k=='driverdate':
            res+=sfont+("%d-%d-%d" % port[k])+efont
        elif k=='driverstatus':
            res+=sfont+`port[k]`+efont # should print it nicer at some point
        else:
            res+=sfont+`port[k]`+efont
        res+="</td><td>"
        # description
        if k=='name':
            res+=sfont+"This is the name the port is known to your operating system as"+efont
        elif k=='available':
            if port[k]:
                res+=sfont+"It was possible to open this port"+efont
            else:
                res+=sfont+"It was not possible to open this port"+efont
        elif k=='active':
            if port[k]:
                res+=sfont+"Your operating system shows this driver and port is correctly configured and a device attached"+efont
            else:
                res+=sfont+"This driver/port combination is not currently running"+efont
        elif k=='driverstatus':
            res+=sfont+"""This is low level detail.  If problem is non-zero then you need to look in the
            control panel for an explanation as to why this driver/device is not working."""+efont
        elif k=='hardwareinstance':
            res+=sfont+"""This is how the device is named internally.  For example USB devices include
            the vendor (VID) and product (PID) identities"""+efont
        else:
            res+="&nbsp;"

        # tail it
        res+="</td></tr>\n"

    res+="\n</table>"

    return res

# A list of USB vendor and product ids we look for
usbdb=( ( 0x1004, 0x6000), # VID=LG Electronics, PID=LG VX4400 -internal USB interface
        ( 0x067b, 0x2303), # VID=Prolific, PID=USB to serial
        )

            
def autoguessports():
    """Returns a list of ports (most likely first) for finding the phone on"""
    res=[]
    # we only care about available ports
    ports=filter(lambda x: x['available'], comscan.comscan())

    # some special cases
    np=[]
    for p in ports:
        if p.has_key('hardwareinstance'):
            v=p['hardwareinstance'].lower()
            if v.find("lgatcr")>=0:
                res.append(p)
                continue
        np.append(p)
    ports=np

    # look through usbdb
    for vid,pid in usbdb:
        np=[]
        for p in ports:
            if p['hardwareinstance']:
                v=p['hardwareinstance'].lower()
                str="vid_%04x&pid_%04x" % (vid,pid)
                if v.find(str)>=0:
                    res.append(p)
                    continue
            np.append(p)
        ports=np

    # at the end, we now have res containing a list of ports we
    # recommend, and ports containing a list of remaining available
    # ports

    # return ['com17', 'com1']+map(lambda x: x['name'], res)+['com12', 'com2']
    return map(lambda x: (x['name'], x), res)

if __name__=='__main__':
    print autoguessports()
