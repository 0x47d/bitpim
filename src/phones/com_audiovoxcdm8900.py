### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the Audiovox CDM 8900 cell phone"""

import com_phone
import com_brew
import prototypes
import p_audiovoxcdm8900

class Phone(com_phone.Phone, com_brew.BrewProtocol):
    "Talk to Audiovox CDM 8900 cell phone"

    desc="Audiovox CDM8900"
    protocolclass=p_audiovoxcdm8900
    serialsname='audiovoxcdm8900'
    pbterminator="~"  # packet terminator
    
    def __init__(self, logtarget, commport):
        "Calls all the constructors and sets initial modes"
        com_phone.Phone.__init__(self, logtarget, commport)
	com_brew.BrewProtocol.__init__(self)
        self.log("Attempting to contact phone")
        self.mode=self.MODENONE

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI.

        Currently this is:

          - 'uniqueserial'     a unique serial number representing the phone
          - 'groups'           the phonebook groups
          - 'wallpaper-index'  map index numbers to names
          - 'ringtone-index'   map index numbers to ringtone names

        This method is called before we read the phonebook data or before we
        write phonebook data.
        """
        # use a hash of ESN and other stuff (being paranoid)
        # self.log("Retrieving fundamental phone information")
        # self.log("Phone serial number")
        # results['uniqueserial']=sha.new(self.getfilecontents("nvm/$SYS.ESN")).hexdigest()
        # now read groups
        return results

    def getcalendar(self, result):
        raise NotImplementedError()

    def getwallpapers(self, result):
        raise NotImplementedError()

    def getringtones(self, result):
        raise NotImplementedError()

    def getphonebook(self, result):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""
        pbook={}
        self.setmode(self.MODEBREW)
        req=self.protocolclass.pbslotsrequest()
        res=self.sendpbcommand(req, self.protocolclass.pbslotsresponse)
        slots=[x for x in range(len(res.present)) if ord(res.present[x])]
        numentries=len(slots)
        for i in range(numentries):
            req=self.protocolclass.readpbentryrequest()
            req.entrynumber=slots[i]
            res=self.sendpbcommand(req, self.protocolclass.readpbentryresponse)
            self.log("Read entry "+`i`+" - "+res.name)
            entry=self.extractphonebookentry(res, result)
            pbook[i]=entry
            self.progress(i, numentries, res.name)
        self.progress(numentries, numentries, "Phone book read completed")
        result['phonebook']=pbook
        return pbook

    def extractphonebookentry(self, entry, result):
        """Return a phonebook entry in BitPim format.  This is called from getphonebook."""
        res={}
        # res['serials']=[ {'sourcetype': self.serialsname, 'serial1': entry.serial1, 'serial2': entry.serial2,
        #                  'sourceuniqueid': fundamentals['uniqueserial']} ]
        # numbers
        numbers=[]
        for t, v in ( ('cell', entry.mobile), ('home', entry.home), ('office', entry.office),
                      ('pager', entry.pager), ('fax', entry.fax) ):
            if len(v)==0:
                continue
            numbers.append( {'number': v, 'type': t} )
        if len(numbers):
            res['numbers']=numbers
        # name
        if len(entry.name): # yes, the audiovox can have a blank name!
            res['names']=[{'full': entry.name}]
        # emails (we treat wireless as email addr)
        emails=[]
        if len(entry.email):
            emails.append({'email': entry.email})
        if len(entry.wireless):
            emails.append({'email': entry.wireless})
        if len(emails):
            res['emails']=emails
        # memo
        if len(entry.memo):
            res['memos']=[{'memo': entry.memo}]
        # secret
        if entry.secret:
            res['flags']=[{'secret': True}]
        # group
        res['categories']=[{'category': 'avox '+`entry.group`}]
        # media
        rt=[]
        if entry.ringtone!=0xffff:
            rt.append({'ringtone': 'avox '+`entry.ringtone`, 'use': 'call'})
        if entry.msgringtone!=0xffff:
            rt.append({'ringtone': 'avox '+`entry.msgringtone`, 'use': 'message'})
        if len(rt):
            res['ringtones']=rt
        if entry.wallpaper!=0xffff:
            res['wallpapers']=[{'wallpaper': 'avox '+`entry.wallpaper`, 'use': 'call'}]
        return res
        
    def sendpbcommand(self, request, responseclass):
        buffer=prototypes.buffer()
        request.writetobuffer(buffer)
        data=buffer.getvalue()
        self.logdata("audiovox cdm8900 phonebook request", data, request)
        data=com_brew.escape(data+com_brew.crcs(data))+self.pbterminator
        first=data[0]
        try:
            data=self.comm.writethenreaduntil(data, False, self.pbterminator, logreaduntilsuccess=False)
        except com_phone.modeignoreerrortypes:
            self.mode=self.MODENONE
            self.raisecommsdnaexception("manipulating the phonebook")
        self.comm.success=True

        origdata=data
        # sometimes there is junk at the begining, eg if the user
        # turned off the phone and back on again.  So if there is more
        # than one 7e in the escaped data we should start after the
        # second to last one
        d=data.rfind(self.pbterminator,0,-1)
        if d>=0:
            self.log("Multiple PB packets in data - taking last one starting at "+`d+1`)
            self.logdata("Original pb data", origdata, None)
            data=data[d+1:]

        # turn it back to normal
        data=com_brew.unescape(data)

        # sometimes there is other crap at the begining
        d=data.find(first)
        if d>0:
            self.log("Junk at begining of pb packet, data at "+`d`)
            self.logdata("Original pb data", origdata, None)
            self.logdata("Working on pb data", data, None)
            data=data[d:]
        # take off crc and terminator
        crc=data[-3:-1]
        data=data[:-3]
        if com_brew.crcs(data)!=crc:
            self.logdata("Original pb data", origdata, None)
            self.logdata("Working on pb data", data, None)
            raise common.CommsDataCorruption("Audiovox phonebook packet failed CRC check", self.desc)
        
        # log it
        self.logdata("Audiovox phonebook response", data, responseclass)

        # parse data
        buffer=prototypes.buffer(data)
        res=responseclass()
        res.readfrombuffer(buffer)
        return res
        
class Profile(com_phone.Profile):

    WALLPAPER_WIDTH=128
    WALLPAPER_HEIGHT=145
    WALLPAPER_CONVERT_FORMAT="jpg"

    MAX_WALLPAPER_BASENAME_LENGTH=16
    WALLPAPER_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 "
    
    MAX_RINGTONE_BASENAME_LENGTH=16
    RINGTONE_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 "

    # which usb ids correspond to us
    usbids=( (0x106c, 0x2101, 1), # VID=Curitel, PID=Audiovox CDM 8900, internal modem interface
        )
    # which device classes we are.
    deviceclasses=("modem",)

    _supportedsyncs=(
        ('phonebook', 'read', None), # all phonebook reading
        )
