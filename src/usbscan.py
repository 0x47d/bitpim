### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"Scans the USB busses in the same way that comscan scans comm ports"

version="7 December 2003"

try:
    import native.usb as usb
except ImportError:
    usb=None

import guihelper
import usb_ids

ids=usb_ids.usb_ids()
ids.add_data(guihelper.getresourcefile("usb.ids"))
ids.add_data(guihelper.getresourcefile("bitpim_usb.ids"))


def usbscan(*args, **kwargs):

    if usb is None:
        return []

    res=[]
    usb.UpdateLists()
    for bus in usb.AllBusses():
        for device in bus.devices():
            for iface in device.interfaces():
                seenin=False
                seenout=False
                for ep in iface.endpoints():
                    if ep.isbulk():
                        if ep.direction()==ep.IN:
                            seenin=True
                        else:
                            seenout=True
                if seenin and seenout:
                    # we now have a device/interface that has bidirectional bulk endpoints
                    name="usb::%s::%s::%d" % (bus.name(), device.name(), iface.number())
                    active=True
                    available=False
                    try:
                        iface.openbulk().close()
                        available=True
                    except:
                        pass
                    v={'name': name, 'active': active, 'available': available,
                       'libusb': True,
                       'usb-vendor#': device.vendor(), 'usb-product#': device.product(),
                       'usb-interface#': iface.number()}
                    vend,prod,i=ids.lookupdevice(device.vendor(), device.product(), iface.number())
                    if vend is None:
                        vend="#%04X" % (device.vendor(),)
                    else:
                        v['usb-vendor']=vend
                    if prod is None:
                        prod="#%04X" % (device.product(),)
                    else:
                        v['usb-product']=prod
                    if i is None:
                        i="#%02X" % (iface.number(),)
                    else:
                        v['usb-interface']=i
                    hwinstance="USB Device - Vendor %s Product %s (Interface %s)" % (vend, prod, i)
                    v['description']=hwinstance

                    prot=" / ".join([val for val in ids.lookupclass(*(iface.classdetails())) if val is not None])
                    if len(prot):
                        v["protocol"]=prot
                        
                    for n,i in ("usb-vendorstring", device.vendorstring), \
                        ("usb-productstring", device.productstring), \
                        ("usb-serialnumber", device.serialnumber):
                        try:
                            x=i()
                            if x is not None:
                                v[n]=x
                        except:
                            pass
                    res.append(v)
    return res

def isusbsupported():
    return usb is not None

if __name__=="__main__":
    res=usbscan()

    output="UsbScan "+version+"\n\n"

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
        
