### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Scans the available bitfling ports in the same way as comscan and usbscan work"

try:
    import bitfling.client as bitfling
except ImportError:
    bitfling=None

def IsBitFlingEnabled():
    if bitfling is None:
        return False
    return True

class flinger:

    def __init__(self):
        self.username=self.password=self.url=None

    def connect(self, username, password, host, port):
        "Connects and returns version info of remote end, or an exception"
        if bitfling is None: return None
        # try and connect by getting version info
        self.client=bitfling.client("https://%s:%s@%s:%d" % (username, password, host, port))
        return self.client.getversion()
            
        
