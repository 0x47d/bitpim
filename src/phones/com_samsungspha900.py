### BITPIM
###
### Copyright (C) 2005 Stephen Wood <saw@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id: com_samsungspha900.py 3918 2007-01-19 05:15:12Z djpham $

"""Communicate with a Samsung SPH-A900"""

import sha
import re
import struct

import common
import commport
import p_brew
import p_samsungspha900
import com_brew
import com_phone
import prototypes
import helpids

numbertypetab=('cell','home','office','pager','none')

class Phone(com_phone.Phone, com_brew.BrewProtocol):
    "Talk to a Samsung SPH-A900 phone"

    desc="SPH-A900"
    helpid=helpids.ID_PHONE_SAMSUNGOTHERS
    protocolclass=p_samsungspha900
    serialsname='spha900'

    MODEPHONEBOOK="modephonebook" # can speak the phonebook protocol

    # jpeg Remove first 124 characters

    imagelocations=(
        # offset, index file, files location, origin, maximumentries, header offset
        # Offset is arbitrary.  100 is reserved for amsRegistry indexed files
        (400, "cam/dldJpeg", "camera", 100, 124),
        (300, "cam/jpeg", "camera", 100, 124),
        )

    ringtonelocations=(
        # offset, index file, files location, type, maximumentries, header offset
        )
        

    def __init__(self, logtarget, commport):
        com_phone.Phone.__init__(self, logtarget, commport)
        com_brew.BrewProtocol.__init__(self)
        self.numbertypetab=numbertypetab
        self.mode=self.MODENONE

    def _setmodephonebook(self):
        self.setmode(self.MODEBREW)
        req=self.protocolclass.firmwarerequest()
        respc=self.protocolclass.firmwareresponse
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
        return 0

    def sendpbcommand(self, request, responseclass, callsetmode=True, writemode=False, numsendretry=0, returnerror=False):
        if writemode:
            numretry=3
        else:
            numretry=0
            
        if callsetmode:
            self.setmode(self.MODEPHONEBOOK)
        buffer=prototypes.buffer()

        request.writetobuffer(buffer, logtitle="Samsung phonebook request")
        data=buffer.getvalue()
        firsttwo=data[:2]
        data=common.pppescape(data+common.crcs(data))+common.pppterminator
        isendretry=numsendretry
        while isendretry>=0:
            try:
                rdata=self.comm.writethenreaduntil(data, False, common.pppterminator, logreaduntilsuccess=False, numfailures=numretry)
                break
            except com_phone.modeignoreerrortypes:
                if isendretry>0:
                    self.log("Resending request packet...")
                    time.sleep(0.3)
                else:
                    self.comm.success=False
                    self.mode=self.MODENONE
                    self.raisecommsdnaexception("manipulating the phonebook")
                isendretry-=1

        self.comm.success=True

        origdata=rdata
        # sometimes there is junk at the beginning, eg if the user
        # turned off the phone and back on again.  So if there is more
        # than one 7e in the escaped data we should start after the
        # second to last one
        d=rdata.rfind(common.pppterminator,0,-1)
        if d>=0:
            self.log("Multiple Samsung packets in data - taking last one starting at "+`d+1`)
            self.logdata("Original Samsung data", origdata, None)
            rdata=rdata[d+1:]

        # turn it back to normal
        data=common.pppunescape(rdata)

        # Sometimes there is other crap at the beginning.  But it might
        # be a Sanyo error byte.  So strip off bytes from the beginning
        # until the crc agrees, or we get to the first two bytes of the
        # request packet.
        d=data.find(firsttwo)
        crc=data[-3:-1]
        crcok=False
        for i in range(0,d+1):
            trydata=data[i:-3]
            if common.crcs(trydata)==crc:
                crcok=True
                break

        if not crcok:
            self.logdata("first two",firsttwo, None)
            self.logdata("Original Sanyo data", origdata, None)
            self.logdata("Working on Sanyo data", data, None)
            raise common.CommsDataCorruption("Sanyo packet failed CRC check", self.desc)

        res=responseclass()
        if d>0:
            if d==i:
                self.log("Junk at beginning of Sanyo packet, data at "+`d`)
                self.logdata("Original Sanyo data", origdata, None)
                self.logdata("Working on Sanyo data", data, None)
            else:
                if returnerror:
                    res=self.protocolclass.sanyoerror()
                else:
                    self.log("Sanyo Error code "+`ord(data[0])`)
                    self.logdata("sanyo phonebook response", data, None)
                    raise SanyoCommandException(ord(data[0]))
            
        data=trydata

        # parse data
        buffer=prototypes.buffer(data)
        res.readfrombuffer(buffer, logtitle="sanyo phonebook response")
        return res

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI."""
        results['uniqueserial']=1
        return results

    def getphonebook(self,result):
        pbook={}

        count = 0
        numcount = 0
        numemail = 0
        numurl = 0

        reqname=self.protocolclass.namerequest()
        reqnumber=self.protocolclass.numberrequest()
        for slot in range(1,self.protocolclass.NUMPHONEBOOKENTRIES+1):
            reqname.slot=slot
            resname=self.sendpbcommand(reqname, self.protocolclass.nameresponse)
            bitmask=resname.bitmask
            if bitmask:
                entry={}
                name=resname.name
                entry['serials']=[ {'sourcetype': self.serialsname,

                                    'slot': slot,
                                    'sourceuniqueid': result['uniqueserial']} ]
                entry['names']=[{'full':name}]
                entry['numbers']=[]
                bit=1
                print resname.p2,name
                for num in range(self.protocolclass.NUMPHONENUMBERS):
                    bit <<= 1
                    if bitmask & bit:
                        numslot=resname.numberps[num].slot
                        reqnumber.slot=numslot
                        resnumber=self.sendpbcommand(reqnumber, self.protocolclass.numberresponse)
                        numhash={'number':resnumber.num, 'type' : self.numbertypetab[resnumber.numbertype-1]}
                        entry['numbers'].append(numhash)

                        print " ",self.numbertypetab[resnumber.numbertype-1]+": ",numslot,resnumber.num
                bit <<= 1
                if bitmask & bit:
                    reqnumber.slot=resname.emailp
                    resnumber=self.sendpbcommand(reqnumber, self.protocolclass.numberresponse)
                    print " Email: ",resname.emailp,resnumber.num
                    entry['emails']=[]
                    entry['emails'].append({'email':resnumber.num})
                bit <<= 1
                if bitmask & bit:
                    reqnumber.slot=resname.urlp
                    resnumber=self.sendpbcommand(reqnumber, self.protocolclass.numberresponse)
                    print " URL:   ",resname.urlp,resnumber.num
                    entry['urls']=[{'url':resnumber.num}]
                if resname.nickname:
                    print " Nick:  ",resname.nickname
                if resname.memo:
                    print " Memo   ",resname.memo
                    entry['memos']=[{'memo':resname.memo}]

                pbook[count]=entry
                self.progress(slot, self.protocolclass.NUMPHONEBOOKENTRIES+1, name)
                count+=1
                numcount+=len(entry['numbers'])
                if entry.has_key('emails'):
                    numemail+=len(entry['emails'])
                if entry.has_key('urls'):
                    numurl+=len(entry['urls'])

        self.progress(slot,slot,"Phonebook read completed")
        self.log("Phone contains "+`count`+" contacts, "+`numcount`+" phone numbers, "+`numemail`+" Emails, "+`numurl`+" URLs")
        result['phonebook']=pbook

        return pbook

    def getcalendar(self, results):
        return result

    getwallpapers=None
    getringtones=None


class Profile(com_phone.Profile):
    deviceclasses=("modem",)

    usbids=( ( 0x04e8, 0x6601, 1),  # Samsung internal USB interface
        )
    # which device classes we are.
    deviceclasses=("modem","serial")

    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname
    phone_manufacturer='SAMSUNG'
    phone_model='SPH-A900/154'

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
    )
    
    def __init__(self):
        self.numbertypetab=numbertypetab
        com_phone.Profile.__init__(self)

