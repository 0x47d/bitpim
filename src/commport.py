### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

import serial
import common
import time

class CommTimeout(Exception):
    def __init__(self, str=None, partial=None):
        Exception.__init__(self, str)
        self.partial=partial

class CommConnection:
    def __init__(self, logtarget, port, baud=115200, timeout=3, hardwareflow=0, softwareflow=0):
        self.logtarget=logtarget
        self.clearcounters()
        self.port=port
        self.log("Connecting to port %s, %d baud, timeout %f, hardwareflow %d, softwareflow %d" %
                 (port, baud, float(timeout), hardwareflow, softwareflow) )
        # we try twice since some platforms fail the first time
        for dummy in range(2):
            try:
                self.ser=serial.Serial(port, baud, timeout=timeout, rtscts=hardwareflow, xonxoff=softwareflow)
                self.log("Connection to comm port suceeded")
                return
            except serial.serialutil.SerialException,e:
                ex=common.CommsOpenFailure(port, e.__str__())
                time.sleep(2)
        raise ex

    def clearcounters(self):
        self.readbytes=0
        self.readrequests=0
        self.writebytes=0
        self.writerequests=0

    def log(self, str):
        if self.logtarget:
            self.logtarget.log(self.port+": "+str)

    def logdata(self, str, data):
        if self.logtarget:
            self.logtarget.logdata(self.port+": "+str, data)

    def setbaudrate(self, rate):
        self.log("Changing rate to "+`rate`)
        self.ser.setBaudrate(rate)
        time.sleep(.5)

    def write(self, data, log=1):
        self.writerequests+=1
        if log:
            self.logdata("Writing", data)
        self.ser.write(data)
        self.writebytes+=len(data)

    def read(self, numchars=1, log=1):
        self.readrequests+=1
        res=self.ser.read(numchars)
        if log:
            self.logdata("Reading exact data - requested "+`numchars`, res)
        self.readbytes+=len(res)
        return res

    def readsome(self, log=1):
        self.readrequests+=1
        res=""
        while 1:
            b=self.ser.inWaiting()
            if b:
                res=res+self.read(b,0)
                continue
            r=self.read(1,0)
            if len(r):
                res=res+r
                continue
            break
        if len(res)==0:
            raise CommTimeout()
        self.readbytes+=len(res)
        if log:
            self.logdata("Reading remaining data", res)
        return res

    def readuntil(self, char, log=1):
        # Keeps reading until it hits char
        self.readrequests+=1
        if log:
            self.logdata("Begin reading until", char)

        # set to non-zero for retries on timeouts
        numfailures=0
        res=''
        while len(res)==0 or res[-1]!=char:
            b=self.ser.inWaiting()
            if b<1: b=1
            res2=self.read(b,0)
            if len(res2)<1:
                if numfailures==0:
                    if log:
                        self.log("Timed out waiting for %02x, requested bytes %d  - %d bytes read" % 
                                 (ord(char), b, len(res)))
                        self.logdata("Incomplete read was", res)
                    self.readbytes+=len(res)
                    raise CommTimeout(partial=res)
                else:
                    numfailures-=1
                    self.ser.flushInput()
                    self.log("Timed out - flushing and trying again")
            res=res+res2

        self.readbytes+=len(res)
        if log:
            self.logdata("Read completed", res)
        return res
        
