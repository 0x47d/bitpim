### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$


# standard modules
import string

# generic comms exception and then various specialisations
class CommsException(Exception):
     def __init__(self, device, message):
        Exception.__init__(self, "%s: %s" % (device, message))
        self.device=device
        self.message=message

class CommsNeedConfiguring(CommsException):
     def __init__(self, device, message):
        CommsException.__init__(self, device, message)
        self.device=device
        self.message=message

class CommsDeviceNeedsAttention(CommsException):
    def __init__(self, device, message):
        CommsException.__init__(self, device, message)
        self.device=device
        self.message=message

class CommsTimeout(CommsException):
    def __init__(self, device, message):
        CommsException.__init__(self, device, message)
        self.device=device
        self.message=message

class CommsOpenFailure(CommsException):
    def __init__(self, device, message):
        CommsException.__init__(self, device, message)
        self.device=device
        self.message=message


# mostly useful for debugging
def datatohexstring(data):
    res=""
    lchar=""
    lhex="00000000 "
    for count in range(0, len(data)):
        b=ord(data[count])
        lhex=lhex+"%02x " % (b,)
        if b>=32 and string.printable.find(chr(b))>=0:
            lchar=lchar+chr(b)
        else:
            lchar=lchar+'.'

        if (count+1)%16==0:
            res=res+lhex+"    "+lchar+"\n"
            lhex="%08x " % (count+1,)
            lchar=""
    if len(data):
        while (count+1)%16!=0:
            count=count+1
            lhex=lhex+"   "
        res=res+lhex+"    "+lchar+"\n"
    return res

