### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Code if you want to be a client of BitFling"""

# Standard imports
import sys
from xmlrpclib import Binary

# My imports
import xmlrpcstuff

class client:
    "A BitFling client"

    # although we could just inherit straight from
    # ServerProxy, this code is here to help ensure
    # calling convention, and in the future deal with
    # backwards compatibility issues
    
    def __init__(self, username, password, host, port, certverifier=None):
        "The URL should include username and password if any"
        self.server=xmlrpcstuff.ServerProxy(username, password, host, port, certverifier)

    def getversion(self):
        return self.server.getversion()

    def scan(self):
        return self.server.scan()

    def deviceopen(self, port, baud, timeout, hardwareflow, softwareflow):
        return self.server.deviceopen(port, baud, timeout, hardwareflow, softwareflow)

    def deviceclose(self, handle):
        return self.server.deviceclose(handle)

    def devicesetbaudrate(self, handle, rate):
        return self.server.devicesetbaudrate(handle, rate)

    def devicewrite(self, handle, data):
        return self.server.devicewrite(handle, Binary(data))

    def devicereaduntil(self, handle, char, numfailures):
        return self.server.devicereaduntil(handle, char, numfailures).data

    def deviceread(self, handle, numchars):
        return self.server.deviceread(handle, numchars).data

    def devicereadsome(self, handle):
        return self.server.devicereadsome(handle).data
