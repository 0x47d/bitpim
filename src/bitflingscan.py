### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Scans the available bitfling ports in the same way as comscan and usbscan work
as well as providing the rest of the BitFling interface"""

import sys

try:
    import bitfling.client as bitfling
except ImportError:
    bitfling=None

def IsBitFlingEnabled():
    if bitfling is None:
        return False
    return True

class BitFlingIsNotConfiguredException(Exception): pass

class flinger:

    def __init__(self, certverifier=None):
        self.certverifier=certverifier
        self.unconfigure()

    def isconfigured(self):
        return self.username is not None and \
               self.password is not None and \
               self.host is not None and \
               self.port is not None

    def _configure(self):
        if not self.isconfigured():
            raise BitFlingIsNotConfiguredException("BitFling needs to be configured")
        if self.client is None:
            self.client=bitfling.client(self.username, self.password, self.host, self.port, self.certverifier)
            
    def configure(self, username, password, host, port):
        self.client=None
        self.username=username
        self.password=password
        self.host=host
        self.port=port

    def unconfigure(self):
        self.username=self.password=self.host=self.port=self.client=None

    def getversion(self):
        self._configure()
        return self.client.getversion()

    def SetCertVerifier(self, certverifier):
        self.certverifier=certverifier

    def scan(self):
        if not self.isconfigured():
            return []
        self._configure()
        ports=self.client.scan()
        for p in range(len(ports)):
            ports[p]['BitFling']=True
        return ports


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

# Unfortunately we have to do some magic to deal with threads
# correctly.  This code is called both from the gui/foreground thread
# (eg when calling the scan function) as well as from the background
# thread (eg when talking to a port over the protocol).  We also have
# to deal with certificate verification issues, since the cert
# verification has to happen in the gui/foreground.

# The way we solve this problem is to have a dedicated thread for
# running the flinger code in.  We hide this from the various callers
# by automatically transferring control to the bitfling thread and
# back again using Queue.Queue's

import thread
import threading
import Queue

class BitFlingWorkerThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.setName("BitFling worker thread")
        self.setDaemon(True)
        self.q=Queue.Queue()
        self.resultqueues={}
        self.eventloops={}

    def run(self):
        while True:
            q,func,args,kwargs=self.q.get()
            try:
                res=func(*args, **kwargs)
                q.put( (res, None) )
            except:
                q.put( (None, sys.exc_info()) )

    def callfunc(self, func, args, kwargs):
        qres=self.getresultqueue()
        self.q.put( (qres, func, args, kwargs) )
        # do we need event loop?
        loopfunc=self.eventloops.get(thread.get_ident(), None)
        if loopfunc is not None:
            while qres.empty():
                loopfunc()
        res, exc = qres.get()
        if exc is not None:
            ex=exc[1]
            ex.gui_exc_info=exc
            raise ex
        return res

    def getresultqueue(self):
        """Return the thread specific result Queue object

        They are automatically allocated on demand"""
        q=self.resultqueues.get(thread.get_ident(), None)
        if q is not None:
            return q
        q=Queue.Queue()
        self.resultqueues[thread.get_ident()]=q
        return q

    def setthreadeventloop(self, eventfunc):
        """Sets the eventloopfunction used for this thread"""
        self.eventloops[thread.get_ident()]=eventfunc

class CallWrapper:
    """Provides proxy method wrappers so that all method calls can be redirected to worker thread

    This works in a very similar way to how xmlrpclib wraps client side xmlrpc
    """

    class MethodIndirect:
        def __init__(self, func):
            self.func=func

        def __call__(self, *args, **kwargs):
            return CallWrapper.worker.callfunc(self.func, args, kwargs)
        
    worker=None
    object=None

    def __init__(self, worker, object):
        CallWrapper.worker=worker
        CallWrapper.object=object

    def __getattr__(self, name):
        if hasattr(self.worker, name):
            return getattr(self.worker, name)
        v=getattr(self.object, name)
        if callable(v):
            return self.MethodIndirect(v)
        return v
    

if IsBitFlingEnabled():
    BitFlingWorkerThread=BitFlingWorkerThread()
    BitFlingWorkerThread.start()

    # wrap it all up
    flinger=CallWrapper(BitFlingWorkerThread, flinger)
else:
    class flinger:
        def __getattr__(self, name):
            raise Exception("BitFling is not enabled")
        def __setattr__(self, name, value):
            raise Exception("BitFling is not enabled")
    flinger=flinger()
