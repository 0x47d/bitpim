###
### A wrapper for the libusb wrapper of the libusb library :-)
###
### This code is in the Public Domain.  (libusb and the wrapper
### are LGPL)
###

from __future__ import generators

import libusb as usb

# grab some constants and put them in our namespace

for sym in dir(usb):
    if sym.startswith("USB_CLASS_") or sym.startswith("USB_DT"):
        exec "%s=usb.%s" %(sym, sym)

class USBException(Exception):
    def __init__(self):
        Exception.__init__(self, usb.usb_strerror())

def UpdateLists():
    """Updates the lists of busses and devices

    @return: A tuple of (change in number of busses, change in number of devices)
    """
    return usb.usb_find_busses(), usb.usb_find_devices()

class USBBus:
    "Wraps a bus"
    
    def __init__(self, usb_bus):
        self.bus=usb_bus

    def name(self):
        return self.bus.dirname

    def devices(self):
        dev=self.bus.devices
        while dev is not None:
            yield USBDevice(dev)
            dev=dev.next
        raise StopIteration()

class USBDevice:
    "Wraps a device"

    def __init__(self, usb_device):
        self.usb=usb # save it so that it can't be GC before us
        self.dev=usb_device
        self.handle=usb.usb_open(self.dev)
        if self.handle is None:
            raise USBException()

    def __del__(self):
        self.close()

    def close(self):
        if self.handle is not None:
            self.usb.usb_close(self.handle)
            self.handle=None
        self.usb=None

    def number(self):
        return self.dev.bInterfaceNumber

    def name(self):
        return self.dev.filename

    def vendor(self):
        return self.dev.descriptor.idVendor

    def vendorstring(self):
        return self._getstring("iManufacturer")

    def productstring(self):
        return self._getstring("iProduct")

    def serialnumber(self):
        return self._getstring("iSerialNumber")

    def _getstring(self, fieldname):
        n=getattr(self.dev.descriptor, fieldname)
        if n:
            res,string=usb.usb_get_string_simple(self.handle, n, 1024)
            if res<0:
                raise USBException()
            return string
        return None

    def product(self):
        return self.dev.descriptor.idProduct

    def interfaces(self):
        for i in range(self.dev.config.bNumInterfaces):
            yield USBInterface(self, usb.usb_interface_index(self.dev.config.interface, i))
        raise StopIteration()

    def classdetails(self):
        "returns a tuple of device class, devicesubclass, deviceprotocol (all ints)"
        return self.dev.descriptor.bDeviceClass, \
               self.dev.descriptor.bDeviceSubClass, \
               self.dev.descriptor.bDeviceProtocol

class USBInterface:

    # currently we only deal with first configuration
    def __init__(self, device, iface):
        self.iface=iface
        self.device=device
        self.desc=iface.altsetting

    def number(self):
        return self.desc.bInterfaceNumber

    def classdetails(self):
        return self.desc.bInterfaceClass, \
               self.desc.bInterfaceSubClass, \
               self.desc.bInterfaceProtocol

    def openbulk(self):
        "Returns a filelike object you can use to read and write"
        # find the endpoints
        epin=None
        epout=None
        for ep in self.endpoints():
            if ep.isbulk():
                if ep.direction()==ep.IN:
                    epin=ep
                else:
                    epout=ep
        assert epin is not None
        assert epout is not None

        # grab the interface
        print "claiming"
        res=usb.usb_claim_interface(self.device.handle, self.number())
        if res<0:
            raise USBException()

        # set the configuration
        print "getting configvalue"
        v=self.device.dev.config.bConfigurationValue
        print "value is",v,"now about to set config"
        res=usb.usb_set_configuration(self.device.handle, v)
        print "config set"
        if res<0:
            usb.usb_release_interface(self.device.handle, self.number())
            raise USBException()

        # we now have the file
        return USBFile(self, epin, epout)
        
    def endpoints(self):
       for i in range(self.desc.bNumEndpoints):
           yield USBEndpoint(usb.usb_endpoint_descriptor_index(self.desc.endpoint, i))
       raise StopIteration()

class USBEndpoint:
    # type of endpoint
    TYPE_CONTROL=usb.USB_ENDPOINT_TYPE_CONTROL
    TYPE_ISOCHRONOUS=usb.USB_ENDPOINT_TYPE_ISOCHRONOUS
    TYPE_BULK=usb.USB_ENDPOINT_TYPE_BULK
    TYPE_INTERRUPT=usb.USB_ENDPOINT_TYPE_INTERRUPT
    # direction for bulk
    IN=usb.USB_ENDPOINT_IN
    OUT=usb.USB_ENDPOINT_OUT
    def __init__(self, ep):
        self.ep=ep

    def type(self):
        return self.ep.bmAttributes&usb.USB_ENDPOINT_TYPE_MASK

    def address(self):
        return self.ep.bEndpointAddress&usb.USB_ENDPOINT_ADDRESS_MASK

    def maxpacketsize(self):
        return self.ep.wMaxPacketSize

    def isbulk(self):
        return self.type()==self.TYPE_BULK

    def direction(self):
        assert self.isbulk()
        return self.ep.bEndpointAddress&usb.USB_ENDPOINT_DIR_MASK
        
class USBFile:

    def __init__(self, iface, epin, epout):
        self.usb=usb  # save this so that our destructor can run
        self.claimed=True
        self.iface=iface
        self.epin=epin
        self.epout=epout
        self.addrin=epin.address()
        self.addrout=epout.address()
        self.insize=epin.maxpacketsize()
        self.outsize=epout.maxpacketsize()

    def __del__(self):
        self.close()

    def read(self,howmuch=1024, timeout=1000):
        print "reading from addr",self.addrin
        data=""
        while howmuch>0:
            res,str=usb.usb_bulk_read_wrapped(iface.device.handle, self.addrin, min(howmuch,self.insize), timeout)
            if res<0:
                if len(data)>0:
                    return data
                raise USBException()
            if res==0:
                return data
            data+=str
            howmuch-=len(str)

        return data

    def write(self, data, timeout=1000):
        print "writing to addr",self.addrout
        while len(data):
            res=usb.usb_bulk_write(iface.device.handle, self.addrout, data[:min(len(data), self.outsize)], timeout)
            if res<0:
                raise USBException()
            data=data[res:]
            
    def close(self):
        if self.claimed:
            self.usb.usb_release_interface(self.iface.device.handle, self.iface.number())
        self.usb=None
        self.claimed=False

def OpenDevice(vendorid, productid, interfaceid):
    for bus in AllBusses():
        for device in bus.devices():
            if device.vendor()==vendorid and device.product()==productid:
                for iface in device.interfaces():
                    if iface.number()==interfaceid:
                        return iface.openbulk()
    raise ValueError( "vendor 0x%x product 0x%x interface %d not found" % (vendorid, productid, interfaceid))
        
    
def classtostring(klass):
    "Returns the class as a string"
    for sym in dir(usb):
        if sym.startswith("USB_CLASS_") and klass==getattr(usb, sym):
            return sym
    return `klass`

def eptypestring(type):
    for sym in dir(USBEndpoint):
        if sym.startswith("TYPE_") and type==getattr(USBEndpoint, sym):
            return sym
    return `type`
    
def AllBusses():
    bus=usb.usb_get_busses()
    while bus is not None:
        yield USBBus(bus)
        bus=bus.next
    raise StopIteration()

# initialise
usb.usb_set_debug(255)
usb.usb_init() # sadly no way to tell if this has failed

if __name__=='__main__':

    bus,dev=UpdateLists()
    print "%d busses, %d devices" % (bus,dev)

    for bus in AllBusses():
        print bus.name()
        for device in bus.devices():
            print "  %x/%x %s" % (device.vendor(), device.product(), device.name())
            klass,subclass,proto=device.classdetails()
            print "  class %s subclass %d protocol %d" % (classtostring(klass), subclass, proto)
            for i in device.vendorstring, device.productstring, device.serialnumber:
                try:
                    print "  "+i()
                except:
                    pass
            for iface in device.interfaces():
                print "      interface number %d" % (iface.number(),)
                klass,subclass,proto=iface.classdetails()
                print "      class %s subclass %d protocol %d" % (classtostring(klass), subclass, proto)
                for ep in iface.endpoints():
                    print "          endpointaddress 0x%x" % (ep.address(),)
                    print "          "+eptypestring(ep.type()),
                    if ep.isbulk():
                        if ep.direction()==ep.IN:
                            print "IN"
                        else:
                            print "OUT"
                    else:
                        print

                print ""
            print ""
        print ""

    print "opening device"
    cell=OpenDevice(0x1004, 0x6000, 2)
    print "device opened, about to write"
    cell.write("\x59\x0c\xc4\xc1\x7e")
    print "wrote, about to read"
    res=cell.read(10)
    print "read %d bytes" % (len(res),)
    cell.close()
