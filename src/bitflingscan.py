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

# ensure there is a singleton
flinger=flinger()

# obfuscate pwd
_magic=[ord(x) for x in "IamAhaPp12&s]"]

# the oldies are the best
def encode(str):
    res=[]
    for i in range(len(str)):
        res.append(ord(str[i])^_magic[i%len(_magic)])
    return "".join(["%02x" % (x,) for x in res])

def decode(str):
    res=[]
    for i in range(0, len(str), 2):
        res.append(int(str[i:i+2], 16))
    x=""
    for i in range(len(res)):
        x+=chr(res[i]^_magic[i%len(_magic)])
    return x
