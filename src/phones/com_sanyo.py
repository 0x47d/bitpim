### BITPIM
###
### Copyright (C) 2003 Stephen Wood <saw@genhomepage.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

"""Phonebook conversations with Sanyo phones"""

import com_brew
import com_phone
import p_sanyo
import prototypes
import cStringIO

class SanyoPhonebook:

    pbterminator="\x7e"
    MODEPHONEBOOK="modephonebook" # can speak the phonebook protocol

    def __init__(self):
        self.pbseq=0
    
    def _setmodelgdmgo(self):
        # see if we can turn on dm mode
        for baud in (0, 115200, 19200, 38400, 230400):
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.comm.write("AT$LGDMGO\r\n")
            except:
                self.mode=self.MODENONE
                self.comm.shouldloop=True
                raise
            try:
                self.comm.readsome()
                self.comm.setbaudrate(38400) # dm mode is always 38400
                return 1
            except com_phone.modeignoreerrortypes:
                self.log("No response to setting DM mode")
        self.comm.setbaudrate(38400) # just in case it worked
        return 0
        

    def _setmodephonebook(self):
        req=p_sanyo.firmwarerequest()
        respc=p_sanyo.firmwareresponse
        try:
            self.sendpbcommand(req, respc, callsetmode=False)
            return 1
        except com_phone.modeignoreerrortypes:
            pass
        try:
            self.comm.setbaudrate(38400)
            self.sendpbcommand(req, respc, callsetmode=False)
            return 1
        except com_phone.modeignoreerrortypes:
            pass
        self._setmodelgdmgo()
        try:
            self.sendpbcommand(req, respc, callsetmode=False)
            return 1
        except com_phone.modeignoreerrortypes:
            pass
        return 0
        
    def getsanyobuffer(self, startcommand, stopcommand, comment):
        # Read buffer parts and concatenate them together
        desc="Reading "+comment
        buffersize=(stopcommand-startcommand+1)*500
        data=cStringIO.StringIO()
        for command in range(startcommand, stopcommand+1):
            self.progress(data.tell(), buffersize, desc)
            req=p_sanyo.bufferpartrequest()
            req.header.command=command
            res=self.sendpbcommand(req, p_sanyo.bufferpartresponse);
            data.write(res.data)

        self.progress(1,1,desc)

        data=data.getvalue()
        self.log("expected size "+`buffersize`+"  actual "+`len(data)`)
        assert buffersize==len(data)
        return data
        
    def sendpbcommand(self, request, responseclass, callsetmode=True):
        if callsetmode:
            self.setmode(self.MODEPHONEBOOK)
        buffer=prototypes.buffer()
        request.writetobuffer(buffer)
        data=buffer.getvalue()
        self.logdata("Sanyo phonebook request", data, request)
        data=com_brew.escape(data+com_brew.crcs(data))+self.pbterminator
        firsttwo=data[:2]
        try:
            self.comm.write(data, log=False) # we logged above
	    data=self.comm.readuntil(self.pbterminator, logsuccess=False)
        except com_phone.modeignoreerrortypes:
            self.mode=self.MODENONE
            self.raisecommsexception("manipulating the phonebook")
        self.comm.success=True
        data=com_brew.unescape(data)
        # get rid of leading junk
        d=data.find(firsttwo)
        if d>0:
            data=data[d:]
        # take off crc and terminator ::TODO:: check the crc
        data=data[:-3]
        
        # log it
        self.logdata("sanyo phonebook response", data, responseclass)

        # parse data
        buffer=prototypes.buffer(data)
        res=responseclass()
        res.readfrombuffer(buffer)
        return res

    # This function isn't actually used
    def getphoneinfo(self, results):
        "Extracts manufacturer and version information in modem mode"
        self.setmode(self.MODEMODEM)
        d={}
        self.progress(0,4, "Switching to modem mode")
        self.progress(1,4, "Reading manufacturer")
        self.comm.write("AT+GMI\r\n")  # manuf
        d['Manufacturer']=cleanupstring(self.comm.readsome())[2][6:]
        self.log("Manufacturer is "+d['Manufacturer'])
        self.progress(2,4, "Reading model")
        self.comm.write("AT+GMM\r\n")  # model
        d['Model']=cleanupstring(self.comm.readsome())[2][6:]
        self.log("Model is "+d['Model'])
        self.progress(3,4, "Software version")
        self.comm.write("AT+GMR\r\n")  # software revision
        d['Software']=cleanupstring(self.comm.readsome())[2][6:]
        self.log("Software is "+d['Software'])
        self.progress(4,4, "Done reading information")
        results['info']=d
        return results



def cleanupstring(str):
    str=str.replace("\r", "\n")
    str=str.replace("\n\n", "\n")
    str=str.strip()
    return str.split("\n")
