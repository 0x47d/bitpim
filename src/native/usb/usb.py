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
        self.dev=usb_device
        self.handle=usb.usb_open(self.dev)
        if self.handle is None:
            raise USBException()

    def __del__(self):
        # this is often called after the USB module is unloaded
        # so we don't worry about exceptions
        try:
            self.close()
        except:
            pass

    def close(self):
        if self.handle is not None:
            usb.usb_close(self.handle)
            self.handle=None

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
            yield USBInterface(usb.usb_interface_index(self.dev.config.interface, i))
        raise StopIteration()

    def classdetails(self):
        "returns a tuple of device class, devicesubclass, deviceprotocol (all ints)"
        return self.dev.descriptor.bDeviceClass, \
               self.dev.descriptor.bDeviceSubClass, \
               self.dev.descriptor.bDeviceProtocol

class USBInterface:

    # currently we only deal with first configuration
    def __init__(self, iface):
        self.iface=iface
        self.desc=iface.altsetting

    def number(self):
        return self.desc.bInterfaceNumber

    def classdetails(self):
        return self.desc.bInterfaceClass, \
               self.desc.bInterfaceSubClass, \
               self.desc.bInterfaceProtocol

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
        return self.ep.bEndpointAddress

    def maxpacketsize(self):
        return self.ep.wMaxPacketSize

    def isbulk(self):
        return self.type()==self.TYPE_BULK

    def direction(self):
        assert self.isbulk()
        return self.ep.bEndpointAddress&usb.USB_ENDPOINT_DIR_MASK
        

    
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
usb.usb_set_debug(0)
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
