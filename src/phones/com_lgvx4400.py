### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

"""Communicate with the LG VX4400 cell phone"""

import common
import commport
import copy
import re
import time
import cStringIO
import p_lgvx4400
import com_brew
import com_phone
import prototypes


class PhoneBookCommandException(Exception):
    def __init__(self, errnum):
        Exception.__init__(self, "Phonebook Command Error 0x%02x" % (errnum,))
        self.errnum=errnum



class Phone(com_phone.Phone,com_brew.BrewProtocol):
    "Talk to the LG VX4400 cell phone"

    MODEPHONEBOOK="modephonebook" # can speak the phonebook protocol
    desc="LG-VX4400"
    terminator="\x7e"


    
    def __init__(self, logtarget, commport):
        com_phone.Phone.__init__(self, logtarget, commport)
	com_brew.BrewProtocol.__init__(self)
        self.log("Attempting to contact phone")
        self.mode=self.MODENONE
        self.seq=0
        self.retries=2  # how many retries when we get no response

        
    def getphoneinfo(self, results):
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


    def getphonebook(self,result):
        pbook={}
        # Bug in the phone.  if you repeatedly read the phone book it starts
        # returning a random number as the number of entries.  We get around
        # this by switching into brew mode which clears that.
        self.mode=self.MODENONE
        self.setmode(self.MODEBREW)
        self.setmode(self.MODEPHONEBOOK)
        self.log("Reading number of phonebook entries")
        res=self.sendpbcommand(0x11, "\x01\x00\x00\x00\x00\x00\x00")
        ### Response 0x11
        # Byte 0x12 is number of entries
        try:
            numentries=ord(res[0x12])
        except:
            numentries=0
        self.log("There are %d entries" % (numentries,))
        for i in range(0, numentries):
            ### Read current entry
            self.log("Reading entry "+`i`)
            res=self.sendpbcommand(0x13, "\x01\x00\x00\x00\x00\x00\x00")
            entry=self.extractphonebookentry(res)
            xx=p_lgvx4400.readphoneentryresponse()
            xx.readfrombuffer(prototypes.buffer(res))
            self.logdata("Read entry", res, xx)
            pbook[i]=entry 
            self.progress(i, numentries, entry['name'])
            #### Advance to next entry
            self.sendpbcommand(0x12, "\x01\x00\x00\x00\x00\x00\x00")

        self.progress(numentries, numentries, "Phone book read completed")
        result['phonebook']=pbook
        # now read groups
        self.log("Reading group information")
        res=self.getfilecontents("pim/pbgroup.dat")
        groups={}
        for i in range(0, len(res), 24):
            groups[i/24]={ 'icon': readlsb(res[i]), 'name': readstring(res[i+1:i+24]) }
        result['groups']=groups
        self.log(`groups`)
        return pbook

    def savephonebook(self, data):
        # To write the phone book, we scan through all existing entries
        # and record their record number and serials.
        # We then delete any entries that aren't in data
        # We then write out our records, usng overwrite or append
        # commands as necessary
        existingpbook={}
        self.mode=self.MODENONE
        self.setmode(self.MODEBREW) # see note in getphonebook() for why this is necessary
        self.setmode(self.MODEPHONEBOOK)
        # similar loop to reading
        self.log("Reading number of phonebook entries before writing")
        res=self.sendpbcommand(0x11, "\x01\x00\x00\x00\x00\x00\x00")
        ### Response 0x11
        # Byte 0x12 is number of entries
        try:
            numexistingentries=ord(res[0x12])
        except:
            numexistingentries=0
        progressmax=numexistingentries+len(data['phonebook'].keys())
        progresscur=0
        self.log("There are %d existing entries" % (numexistingentries,))
        for i in range(0, numexistingentries):
            ### Read current entry
            res=self.sendpbcommand(0x13, "\x01\x00\x00\x00\x00\x00\x00")
            entry={ 'number':  readlsb(res[0xe:0xf]), 'serial1':  readlsb(res[0x04:0x08]),
                    'serial2': readlsb(res[0xa:0xe]), 'name': readstring(res[0x10:0x27])}
            assert entry['serial1']==entry['serial2'] # always the same
            self.log("Reading entry "+`i`+" - "+entry['name'])            
            existingpbook[i]=entry 
            self.progress(progresscur, progressmax, "existing "+`progresscur`)
            #### Advance to next entry
            self.sendpbcommand(0x12, "\x01\x00\x00\x00\x00\x00\x00")
            progresscur+=1
        # we have now looped around back to begining

        # Find entries that have been deleted
        pbook=data['phonebook']
        dellist=[]
        for i in range(0, numexistingentries):
            ii=existingpbook[i]
            serial=ii['serial1']
            item=self._findserial(serial, pbook)
            if item is None:
                dellist.append(i)

        progressmax+=len(dellist) # more work to do

        # Delete those entries
        for i in dellist:
            progresscur+=1
            numexistingentries-=1  # keep count right
            ii=existingpbook[i]
            self.log("Deleting entry "+`i`+" - "+ii['name'])
            cmddata="\x01"+makelsb(ii['serial1'],4)+ \
                  "\0x00\x00" + \
                  makelsb(ii['serial2'],4) + \
                  makelsb(ii['number'],2)
            self.sendpbcommand(0x05, cmddata)
            self.progress(progresscur, progressmax, "Deleting "+`i`)
            # also remove them from existingpbook
            del existingpbook[i]

        # counter to keep track of record number (otherwise appends don't work)
        counter=0
        # Now rewrite out existing entries
        keys=existingpbook.keys()
        existingserials=[]
        keys.sort()
        for i in keys:
            progresscur+=1
            ii=pbook[self._findserial(existingpbook[i]['serial1'], pbook)]
            self.log("Writing entry "+`i`+" - "+ii['name'])
            self.progress(progresscur, progressmax, "Writing "+ii['name'])
            entry=self.makeentry(counter, ii, data)
            counter+=1
            existingserials.append(existingpbook[i]['serial1'])
            res=self.sendpbcommand(0x04, "\x01"+entry)  # overwrite
            assert ii['serial1']==readlsb(res[0x04:0x08]) # serial should stay the same
            # ii['serial1']=readlsb(res[0x04:0x08])
            # ii['serial2']=ii['serial1']

        # Finally write out new entries
        keys=pbook.keys()
        keys.sort()
        for i in keys:
            ii=pbook[i]
            if ii['serial1'] in existingserials:
                continue # already wrote this one out
            progresscur+=1
            entry=self.makeentry(counter, ii, data)
            counter+=1
            self.log("Appending entry "+ii['name'])
            self.progress(progresscur, progressmax, "Writing "+ii['name'])
            res=self.sendpbcommand(0x03, "\x01"+entry)  # append
            ii['serial1']=readlsb(res[0x04:0x08])
            ii['serial2']=ii['serial1']
            if ii['serial1']==0:
                self.log("Failed to add "+ii['name']+" - make sure the entry has at least one phone number")
           


    def _findserial(self, serial, dict):
        """Searches dict to find entry with matching serial.  If not found,
        returns None"""
        for i in dict:
            if dict[i]['serial1']==serial:
                return i
        return None
            
    def getcalendar(self,result):
        res={}
        # Read exceptions file first
        data=self.getfilecontents("sch/schexception.dat")
        exceptions={}
        for i in range(0,len(data)/8):
            pos=8*i
            offset=readlsb(data[pos:pos+4])
            d=ord(data[pos+4])
            m=ord(data[pos+5])
            y=readlsb(data[pos+6:pos+8])
            try:
                exceptions[offset].append( (y,m,d) )
            except KeyError:
                exceptions[offset]=[ (y,m,d) ]

        # Now read schedule
        data=self.getfilecontents("sch/schedule.dat")
        numentries=readlsb(data[0:2])
        for i in range(0, (len(data)-2)/60):
            entry={}
            pos=2+i*60
            entry['pos']=readlsb(data[pos+0:pos+4])  # hex offset of entry within schedule file
            if entry['pos']==-1: continue # blanked entry
            if exceptions.has_key(pos):
                entry['exceptions']=exceptions[pos]
            entry['start']=brewdecodedate(readlsb(data[pos+4:pos+8]))
            entry['end']=brewdecodedate(readlsb(data[pos+8:pos+0xc]))
            repeat=ord(data[pos+0xc])
            entry['repeat']=self._calrepeatvalues[repeat]
            entry['daybitmap']=readlsb(data[pos+0xd:pos+0x10])
            min=ord(data[pos+0x10])
            hour=ord(data[pos+0x11])
            if min==100 or hour==100:
                entry['alarm']=None # no alarm set
            else:
                entry['alarm']=hour*60+min
            entry['changeserial']=readlsb(data[pos+0x12:pos+0x13])
            entry['snoozedelay']=readlsb(data[pos+0x13:pos+0x14])
            entry['ringtone']=ord(data[pos+0x14])
            entry['description']=readstring(data[pos+0x15:pos+0x3d])
            res[pos]=entry

        assert numentries==len(res)
        result['calendar']=res
        return result

    def savecalendar(self, dict, merge):
        # ::TODO:: obey merge param
        # what will be written to the files
        data=""
        dataexcept=""

        # what are we working with
        cal=dict['calendar']
        newcal={}
        keys=cal.keys()
        keys.sort()

        # number of entries
        data+=makelsb(len(keys), 2)
        
        # play with each entry
        for k in keys:
            entry=cal[k]
            pos=len(data)
            entry['pos']=pos

            # 4 bytes of offset
            assert len(data)-pos==0
            data+=makelsb(pos, 4)
            # start
            assert len(data)-pos==4
            data+=makelsb(brewencodedate(*entry['start']),4)
            # end
            assert len(data)-pos==8
            data+=makelsb(brewencodedate(*entry['end']), 4)
            # repeat
            assert len(data)-pos==0xc
            repeat=None
            for k,v in self._calrepeatvalues.items():
                if entry['repeat']==v:
                    repeat=k
                    break
            assert repeat is not None
            data+=makelsb(repeat, 1)
            # daybitmap
            assert len(data)-pos==0xd
            data+=makelsb(entry['daybitmap'],3)
            # alarm - first byte is mins, next is hours.  100 indicates not set
            assert len(data)-pos==0x10
            if entry['alarm'] is None or entry['alarm']<0:
                hour=100
                min=100
            else:
                assert entry['alarm']>=0
                hour=entry['alarm']/60
                min=entry['alarm']%60
            data+=makelsb(min,1)
            data+=makelsb(hour,1)
            # changeserial
            assert len(data)-pos==0x12
            data+=makelsb(entry['changeserial'], 1)
            # snoozedelay
            data+=makelsb(entry['snoozedelay'], 1)
            # ringtone
            assert len(data)-pos==0x14
            data+=makelsb(entry['ringtone'], 1)
            # description
            assert len(data)-pos==0x15
            data+=makestring( entry['description'], 39)

            # sanity check
            assert (len(data)-2)%60==0

            # update exceptions if needbe
            if entry.has_key('exceptions'):
                for y,m,d in entry['exceptions']:
                    dataexcept+=makelsb(pos,4)
                    dataexcept+=makelsb(d,1)
                    dataexcept+=makelsb(m,1)
                    dataexcept+=makelsb(y,2)
                    # sanity check
                    assert len(dataexcept)%8==0

            # put entry in nice shiny new dict we are building
            entry=copy.copy(entry)
            entry['pos']=pos
            newcal[pos]=entry

        # scribble everything out
        self.writefile("sch/schedule.dat", data)
        self.writefile("sch/schexception.dat", dataexcept)

        # fix passed in dict
        dict['calendar']=newcal

        return dict
        

    _calrepeatvalues={
        0x10: None,
        0x11: 'daily',
        0x12: 'monfri',
        0x13: 'weekly',
        0x14: 'monthly',
        0x15: 'yearly'
        }
    
    def writeindex(self, indexfile, index, maxentries=30):
        keys=index.keys()
        keys.sort()
        writing=min(len(keys), maxentries)
        if len(keys)>maxentries:
            self.log("Warning:  You have too many entries (%d) for index %s.  Only writing out first %d." % (len(keys), indexfile, writing))
        newdata=makelsb(writing,2)
        for i in keys[:writing]:
            newdata+=makelsb(i,2)
            newdata+=makestring(index[i], 40)
        for dummy in range(writing, maxentries):
            newdata+="\xff\xff"
            newdata+=makestring("", 40)
        self.log("Writing %d index entries" % (writing,))
        self.writefile(indexfile, newdata)

    def getindex(self, indexfile):
        # Read an index file
        index={}
        data=self.getfilecontents(indexfile)
        for i in range(0,(len(data)-2)/42):
            offset=2+42*i
            num=readlsb(data[offset:offset+2])
            name=readstring(data[offset+2:offset+42])
            if num==0xffff or len(name)==0:
                continue
            index[num]=name
        self.log("There are %d index entries" % (len(index.keys()),))
        return index
        
    def getprettystuff(self, result, directory, datakey, indexfile, indexkey):
        """Get wallpaper/ringtone etc"""
        # we have to be careful because files from other stuff could be
        # in the directory.  Consequently we ONLY consult the index.  However
        # the index may be corrupt so we cope with it having entries for
        # files that don't exist
        index=self.getindex(indexfile)
        result[indexkey]=index

        stuff={}
        for i in index:
            try:
                file=self.getfilecontents(directory+"/"+index[i])
                stuff[index[i]]=file
            except p_brew.BrewNoSuchFileException:
                self.log("It was in the index, but not on the filesystem")
        result[datakey]=stuff

        return result

    def getwallpapers(self, result):
        return self.getprettystuff(result, "brew/shared", "wallpaper", "dloadindex/brewImageIndex.map",
                                   "wallpaper-index")

    def saveprettystuff(self, data, directory, indexfile, stuffkey, stuffindexkey, merge):
        f=data[stuffkey].keys()
        f.sort()
        self.log("Saving %s.  Merge=%d.  Files supplied %s" % (stuffkey, merge, ", ".join(f)))
        self.mkdirs(directory)

        # get existing index
        index=self.getindex(indexfile)

        # Now the only files we care about are those named in the index and in data[stuffkey]
        # The operations below are specially ordered so that we don't reuse index keys
        # from existing entries (even those we are about to delete).  This seems like
        # the right thing to do.

        # Get list of existing files
        entries=self.getfilesystem(directory)

        # if we aren't merging, delete all files in index we aren't going to overwrite
        # we do this first to make space for new entrants
        if not merge:
            for i in index:
                if self._fileisin(entries, index[i]) and index[i] not in data[stuffkey]:
                    fullname=directory+"/"+index[i]
                    self.rmfile(fullname)
                    del entries[fullname]

        # Write out the files
        files=data[stuffkey]
        keys=files.keys()
        keys.sort()
        for file in keys:
            fullname=directory+"/"+file
            self.writefile(fullname, files[file])
            entries[fullname]={'name': fullname}
                    
        # Build up the index
        for i in files:
            # entries in the existing index take priority
            if self._getindexof(index, i)<0:
                # Look in new index
                num=self._getindexof(data[stuffindexkey], i)
                if num<0 or num in index: # if already in index, allocate new one
                    num=self._firstfree(index, data[stuffindexkey])
                assert not index.has_key(num)
                index[num]=i

        # Delete any duplicate index entries, keeping lowest numbered one
        seen=[]
        keys=index.keys()
        keys.sort()
        for i in keys:
            if index[i] in seen:
                del index[i]
            else:
                seen.append( index[i] )

        # Verify all index entries are present
        for i in index.keys():
            if not self._fileisin(entries, index[i]):
                del index[i]

        # Write out index
        self.writeindex(indexfile, index)

        data[stuffindexkey]=index
        return data


    def savewallpapers(self, data, merge):
        return self.saveprettystuff(data, "brew/shared", "dloadindex/brewImageIndex.map",
                                    'wallpaper', 'wallpaper-index', merge)
        
    def saveringtones(self,data, merge):
        return self.saveprettystuff(data, "user/sound/ringer", "dloadindex/brewRingerIndex.map",
                                    'ringtone', 'ringtone-index', merge)


    def _fileisin(self, entries, file):
        # see's if file is in entries (entries has full pathname, file is just filename)
        for i in entries:
            if com_brew.brewbasename(entries[i]['name'])==file:
                return True
        return False

    def _getindexof(self, index, file):
        # gets index number of file from index
        for i in index:
            if index[i]==file:
                return i
        return -1

    def _firstfree(self, index1, index2):
        # finds first free index number taking into account both indexes
        l=index1.keys()
        l.extend(index2.keys())
        for i in range(0,255):
            if i not in l:
                return i
        return -1

    def getringtones(self, result):
        return self.getprettystuff(result, "user/sound/ringer", "ringtone", "dloadindex/brewRingerIndex.map",
                                   "ringtone-index")


    def _setmodelgdmgo(self):
        # see if we can turn on dm mode
        for baud in (0, 115200, 19200, 38400, 230400):
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            try:
                self.comm.write("AT$QCDMG\r\n")
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
        try:
            self._sendpbcommand(0x15, "\x00\x00\x00\x00\x00\x00\x00", wantto=True)
            return 1
        except com_phone.modeignoreerrortypes:
            pass
        try:
            self.comm.setbaudrate(38400)
            self._sendpbcommand(0x15, "\x00\x00\x00\x00\x00\x00\x00", wantto=True)
            return 1
        except com_phone.modeignoreerrortypes:
            pass
        self._setmodelgdmgo()
        try:
            self._sendpbcommand(0x15, "\x00\x00\x00\x00\x00\x00\x00", wantto=True)
            return 1
        except com_phone.modeignoreerrortypes:
            pass
        return 0
        
    def _setmodemodem(self):
        for baud in (0, 115200, 38400, 19200, 230400):
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue
            self.comm.write("AT\r\n")
            try:
                self.comm.readsome()
                return 1
            except com_phone.modeignoreerrortypes:
                pass
        return 0        

    def checkresult(self, firstbyte, res):
        if res[0]!=firstbyte:
            return

    def sendpbcommand(self, cmd, data):
        self.setmode(self.MODEPHONEBOOK)
        if self.comm.configparameters is None or \
           not self.comm.configparameters['retryontimeout']:
            return self._sendpbcommand(cmd, data)
        try:
            return self._sendpbcommand(cmd, data, wantto=True)
        except commport.CommTimeout, e:
            if e.partial is None or len(e.partial)==0:
                raise e
            # resend command
            self.log("Phonebook command timed out with partial data.  Retrying")
            self.comm.reset()
            res=self._sendpbcommand(cmd,data)
            x=res.find('\x7f')
            if x<0:
                raise e
            res=res[x+1]
            if len(res)==0:
                raise e
            return res

    def _sendpbcommand(self, cmd, data, wantto=False):
        d="\xff"+chr(cmd)+chr(self.seq&0xff)+data
        d=self.escape(d+self.crcs(d))+self.terminator
        try:
            self.comm.write(d)
        except:
            self.mode=self.MODENONE
            self.comm.shouldloop=True
            raise
        self.seq+=1
        try:
            d=self.unescape(self.comm.readuntil(self.terminator))
            d=d[:-3] # strip crc
            self.comm.success=True
            if 0: # cmd!=0x15 and d[3]!="\x00":
                raise PhoneBookCommandException(ord(d[3]))
            # ::TODO:: we should check crc
            return d
        except commport.CommTimeout, e:
            if wantto:
                raise e
            self.raisecommsexception("using the phonebook")
            return None # keep pychecker happy
        

        


    def extractphonebookentry(self, packet):
        # currently work with first four bytes on data (ff cmd seq flag) to
        # make working with hexdumps easier.  this will be fixed later on
        # note that python subscripting is 'off by one' (upper bounds is
        # NOT included)
        res={}

        # bytes 0-3  ff cmd seq flag
        # pass

        # bytes 4-7 serial
        res['serial1']=readlsb(packet[4:8])

        # bytes 8-9  entry size => 0x0202
        # res['?offset008']=readlsb(packet[8:0xa])

        # bytes a-d another serial
        res['serial2']=readlsb(packet[0xa:0xe])

        # byte e is entry number - we don't expose
        # res['#']=readlsb(packet[0xe:0xf])

        # byte f is unknown
        res['?offset00f']=readlsb(packet[0xf:0x10])

        # Bytes 10-26 null padded name
        res['name']=readstring(packet[0x10:0x27])

        # Byte 27 group
        b=packet[0x27]
        res['group']=ord(b)

        # byte 28 some sort of number
        res['?offset028']=readlsb(packet[0x28:0x29])

        # bytes 29-59 null padded email1
        res['email1']=readstring(packet[0x29:0x60])

        # bytes 5a-8a null padded email2
        res['email2']=readstring(packet[0x5a:0x8b])

        # bytes 8b-bb null padded email3
        res['email3']=readstring(packet[0x8b:0xbc])

        # bytes bc-ec null padded url
        res['url']=readstring(packet[0xbc:0xed])

        # byte ed is ringtone
        b=packet[0xed]
        res['ringtone']=ord(b)

        # byte ee is message ringtone
        b=packet[0xee]
        res['msgringtone']=ord(b)

        # byte ef is secret
        b=ord(packet[0xef])
        res['secret']=b

        # bytes f0-110 null padded memo
        res['memo']=readstring(packet[0xf0:0x111])

        # byte 111
        res['?offset111']=readlsb(packet[0x111:0x112])
        
        # bytes 112-116 are phone number types
        n=0
        for b in packet[0x112:0x117]:
            n+=1
            res['type'+chr(n+ord('0'))]=ord(b)
                

        # bytes 117-147 number 1
        res['number1']=readstring(packet[0x117:0x148])

        # bytes 148-178 number 2
        res['number2']=readstring(packet[0x148:0x179])

        # bytes 179-1a9 number 3
        res['number3']=readstring(packet[0x179:0x1aa])

        # bytes 1aa-1da number 4
        res['number4']=readstring(packet[0x1aa:0x1db])

        # bytes 1db-20b
        res['number5']=readstring(packet[0x1db:0x20c])

        # bytes 20c-210
        res['?offset20c']=readlsb(packet[0x20c:0x211])

        return res

    def makeentry(self, num, entry, dict):
        # ::TODO:: we need to update fields in entry/dict
        # eg when removing non-numerics from phone numbers
        # or chang ringtone names into ringtone numbers
        res=""
        # skip first four bytes - they are part of command
        res+="aaaa"  # added to help assertions
        
        # bytes 4-7 serial1
        assert len(res)==4
        res+=makelsb(entry.get('serial1', 0), 4)

        # bytes 8-9  length - always 0202
        assert len(res)==8
        res+=makelsb(0x0202, 2)

        # bytes a-d serial2
        assert len(res)==0x0a
        res+=makelsb(entry.get('serial2', 0), 4)

        # byte e is entry number
        # we ignore what user supplied
        assert len(res)==0xe
        res+=makelsb(num,1) 

        # byte f is unknown - always 0
        assert len(res)==0xf
        res+=makelsb(0, 1)

        # Bytes 10-26 null padded name
        assert len(res)==0x10
        res+=makestring(entry.get('name', "<unnamed>"), 23)

        # Byte 27 group
        assert len(res)==0x27
        res+=makelsb(entry.get('group', 0), 1)
        
        # byte 28 some sort of number - always 0
        assert len(res)==0x28
        res+=makelsb(0, 1)

        # bytes 29-59 null padded email1
        assert len(res)==0x29
        res+=makestring(entry.get('email1', ""), 49)

        # bytes 5a-8a null padded email2
        assert len(res)==0x5a
        res+=makestring(entry.get('email2', ""), 49)

        # bytes 8b-bb null padded email3
        assert len(res)==0x8b
        res+=makestring(entry.get('email3', ""), 49)

        # bytes bc-ec null padded url
        assert len(res)==0xbc
        res+=makestring(entry.get('url', ""), 49)

        # byte ed is ringtone
        assert len(res)==0xed
        res+=makelsb(entry.get('ringtone', 0), 1)

        # byte ee is message ringtone
        assert len(res)==0xee
        res+=makelsb(entry.get('msgringtone', 0) , 1)

        # byte ef is secret
        assert len(res)==0xef
        if entry.get('secret',0):
            res+="\x01"
        else: res+="\x00"
        
        # bytes f0-110 null padded memo
        assert len(res)==0xf0
        res+=makestring(entry.get('memo', ""), 33)

        # byte 111 - always zero or one entry is 0x0d
        assert len(res)==0x111
        res+=makelsb(0,1)
        
        # bytes 112-116 are phone number types
        assert len(res)==0x112
        for n in range(1,6):
            res+=makelsb( entry.get('type'+`n`, 0), 1)

        # bytes 117-147 number 1
        assert len(res)==0x117
        number=self.phonize(entry.get('number1', ""))
        entry['number1']=number
        res+=makestring(number, 49)

        # bytes 148-178 number 2
        assert len(res)==0x148
        number=self.phonize(entry.get('number2', ""))
        entry['number2']=number
        res+=makestring(number, 49)

        # bytes 179-1a9 number 3
        assert len(res)==0x179
        number=self.phonize(entry.get('number3', ""))
        entry['number3']=number
        res+=makestring(number, 49)
        
        # bytes 1aa-1da number 4
        assert len(res)==0x1aa
        number=self.phonize(entry.get('number4', ""))
        entry['number4']=number
        res+=makestring(number, 49)

        # bytes 1db-20b number 5
        assert len(res)==0x1db
        number=self.phonize(entry.get('number5', ""))
        entry['number5']=number
        res+=makestring(number, 49)

        # bytes 20c-210 five zeros
        assert len(res)==0x20c
        res+=makelsb(0, 5)

        # done
        assert len(res)==0x211

        return res[4:]  # chop off cosmetic first bit

    def phonize(self, str):
        """Convert the phone number into something the phone understands

        All non-digits are removed"""
        return re.sub("[^0-9PT#*]", "", str)

    
    tonetab=( 'Default', 'Ring 1', 'Ring 2', 'Ring 3', 'Ring 4', 'Ring 5',
              'Ring 6', 'Voices of Spring', 'Twinkle Twinkle',
              'The Toreadors', 'Badinerie', 'The Spring',
              'Liberty Bell', 'Trumpet Concerto', 'Eine Kleine',
              'Silken Ladder', 'Nocturne', 'Csikos Post', 'Turkish March',
              'Mozart Aria', 'La Traviata', 'Rag Time', 'Radetzky March',
              'Can-Can', 'Sabre Dance', 'Magic Flute', 'Carmen' )


        

### Various random functions

def cleanupstring(str):
    str=str.replace("\r", "\n")
    str=str.replace("\n\n", "\n")
    str=str.strip()
    return str.split("\n")

def readlsb(data):
    # Read binary data in lsb
    res=0
    shift=0
    for i in data:
        res|=ord(i)<<shift
        shift+=8
    return res

def makelsb(num, numbytes):
    res=""
    for dummy in range(0,numbytes):
        res+=chr(num&0xff)
        num>>=8
    return res

def readstring(data):
    # reads null padded string
    res=""
    for i in data:
        if i=='\x00':
            return res
        res=res+i
    return res

def makestring(str, length):
    if len(str)>length:
        raise Exception("name too long")
    res=str
    while len(res)<length:
        res+="\x00"
    return res

def readhex(data):
    # outputs binary data as hexstring
    res=""
    for i in data:
        if len(res): res+=" "
        res+="%02x" % (ord(i),)
    return res

def brewdecodedate(val):
    """Unpack 32 bit value into date/time

    @rtype: tuple
    @return: (year, month, day, hour, minute)
    """
    min=val&0x3f # 6 bits
    val>>=6
    hour=val&0x1f # 5 bits (uses 24 hour clock)
    val>>=5
    day=val&0x1f # 5 bits
    val>>=5
    month=val&0xf # 4 bits
    val>>=4
    year=val&0xfff # 12 bits
    return (year, month, day, hour, min)

def brewencodedate(year, month, day, hour, minute):
    """Pack date/time into 32 bit value

    @rtype: int
    """
    if year>4095:
        year=4095
    val=year
    val<<=4
    val|=month
    val<<=5
    val|=day
    val<<=5
    val|=hour
    val<<=6
    val|=minute
    return val

# Some notes
#
# phonebook command numbers
#
# 0x15   get phone info (returns stuff about vx400 connector)
# 0x00   start sync (phones display changes)
# 0x11   select phonebook (goes back to first entry, returns how many left)
# 0x12   advance one entry
# 0x13   get current entry
# 0x07   quit (phone will restart)
# 0x06   ? parameters maybe
# 0x05   delete entry
# 0x04   write entry  (advances to next entry)
# 0x03   append entry  (advances to next entry)
