### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

import common
import commport

class BrewCommandException(Exception):
    def __init__(self, errnum, str=None):
        if str is None:
            str="Brew Error 0x%02x" % (errnum,)
        Exception.__init__(self, str)
        self.errnum=errnum

class BrewNoMoreEntriesException(BrewCommandException):
    def __init__(self, errnum=0x1c):
        BrewCommandException.__init__(self, errnum, "No more directory entries")

class BrewNoSuchDirectoryException(BrewCommandException):
    def __init__(self, errnum=0x08):
        BrewCommandException.__init__(self, errnum, "No such directory")

class BrewNoSuchFileException(BrewCommandException):
    def __init__(self, errnum=0x06):
        BrewCommandException.__init__(self, errnum, "No such file")

class PhoneBookCommandException(Exception):
    def __init__(self, errnum):
        Exception.__init__(self, "Phonebook Command Error 0x%02x" % (errnum,))
        self.errnum=errnum

class Phone:
    "Talk to the LG VX4400 cell phone"

    MODENONE=0  # not talked to yet
    MODEPHONEBOOK=1 # can speak the phonebook protocol
    MODEBREW=2  # speaking brew
    MODEMODEM=3 # modem mode
    desc="LG-VX4400"
    terminator="\x7e"
    
    def __init__(self, logtarget, commport):
        self.logtarget=logtarget
        self.comm=commport
        self.log("Phone initialised")
        self.mode=self.MODENONE
        self.seq=0

    def log(self, str):
        if self.logtarget:
            self.logtarget.log("%s: %s" % (self.desc, str))

    def progress(self, pos, max, desc):
        if self.logtarget:
            self.logtarget.progress(pos, max, desc)
        
    def getphoneinfo(self, results):
        d={}
        self.progress(0,4, "Switching to modem mode")
        self.setmode(self.MODEMODEM)
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
            pbook[i]=entry 
            self.progress(i, numentries, entry['name'])
            #### Advance to next entry
            self.sendpbcommand(0x12, "\x01\x00\x00\x00\x00\x00\x00")

        self.progress(numentries, numentries, "Phone book read completed")
        result['phonebook']=pbook
        # now read groups
        self.setmode(self.MODEBREW)
        self.log("Reading group information")
        res=self.getfilecontents("pim/pbgroup.dat")
        groups={}
        for i in range(0, len(res), 24):
            groups[i/24]={ 'icon': readlsb(res[i]), 'name': readstring(res[i+1:i+24]) }
        result['groups']=groups
        self.log(`groups`)
        return pbook

    def savephonebook(self, data):
        print "savephonebookcalled"
        # To write the phone book, we scan through all existing entries
        # and record their record number and serials.
        # We then delete any entries that aren't in data
        # We then write out our records, usng overwrite or append
        # commands as necessary
        existingpbook={}
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
        self.setmode(self.MODEBREW)
        return result

    def getwallpapers(self, result):
        # we have to retreive both the wallpapers and the index file
        wallpapers={}
        self.setmode(self.MODEBREW)
        try:
            entries=self.getfilesystem("brew/shared")
        except BrewNoSuchDirectoryException:
            entries={}
        for file in entries:
            f=entries[file]
            if f['type']=='file':
                wallpapers[brewbasename(file)]=self.getfilecontents(file)
        result['wallpaper']=wallpapers

        index={}
        data=self.getfilecontents("dloadindex/brewImageIndex.map")
        for i in range(0,readlsb(data[:2])):
            offset=2+42*i
            num=readlsb(data[offset:offset+2])
            name=readstring(data[offset+2:offset+42])
            index[num]=name

        result['wallpaper-index']=index
        return result

    def saveprettystuff(self, data, directory, indexfile, stuffkey, stuffindexkey):
        self.setmode(self.MODEBREW)
        dirs=directory.split('/')
        for i in range(0,len(dirs)):
            try:
                self.mkdir("/".join(dirs[:i+1]))  # basically mkdir -p
            except:
                pass
        # clean out any existing entries that we aren't overwriting
        files=data[stuffkey]
        entries=self.getfilesystem(directory)
        for file in entries:
            f=entries[file]
            if f['type']=='file' and brewbasename(f['name']) not in files:
                self.rmfile(file)
        # Write out the files
        keys=files.keys()
        keys.sort()
        for file in keys:
            self.writefile(directory+"/"+file, files[file])
        # Check all the indexes actually point at files
        index=data[stuffindexkey]
        keys=index.keys()
        for i in keys:
            if index[i] not in data[stuffkey]:
                self.log("removing index "+`i`+" that points to non-existent file "+index[i])
                del index[i]

        # Generate the index entries
        for f in files:
            num=-1
            for key in index.keys():
                if index[key]==file:
                    num=key
                    break
            if num==-1:
                num=self._firstfree(index)
                index[num]=file

        # Now write out index
        keys=index.keys()
        keys.sort() # ... in sorted order
        if len(keys)>30: keys=keys[:30] # maximum of 30 entries
        newdata=makelsb(len(keys),2)
        for i in keys:
            newdata+=makelsb(i,2)
            newdata+=makestring(index[i], 40)
        for dummy in range(len(keys), (1262-2)/42):
            newdata+="\xff\xff"
            newdata+=makestring("", 40)
        self.writefile(indexfile, newdata)
        return data


    def savewallpapers(self, data):
        return self.saveprettystuff(data, "brew/shared", "dloadindex/brewImageIndex.map",
                                    'wallpaper', 'wallpaper-index')
        
    def saveringtones(self,data):
        return self.saveprettystuff(data, "user/sound/ringer", "dloadindex/brewRingerIndex.map",
                                    'ringtone', 'user/sound/ringer')


    def _firstfree(self, index):
        for i in range(0,255):
            if i not in index:
                return i
        return -1

    def getringtones(self, result):
        # we have to retreive both the midis and the index file
        ringers={}
        self.setmode(self.MODEBREW)
        try:
            entries=self.getfilesystem("user/sound/ringer")
        except BrewNoSuchDirectoryException:
            entries={}
            
        for file in entries:
            f=entries[file]
            if f['type']=='file':
                ringers[brewbasename(file)]=self.getfilecontents(file)
        result['ringtone']=ringers

        index={}
        data=self.getfilecontents("dloadindex/brewRingerIndex.map")
        for i in range(0,readlsb(data[:2])):
            offset=2+42*i
            num=readlsb(data[offset:offset+2])
            name=readstring(data[offset+2:offset+42])
            index[num]=name

        result['ringtone-index']=index
        return result

    def mkdir(self, name):
        self.log("Making directory '"+name+"'")
        self.setmode(self.MODEBREW)
        d=chr(len(name)+1)+name+"\x00"
        self.sendbrewcommand(0x00, d)

    def rmdir(self,name):
        self.log("Deleting directory '"+name+"'")
        self.setmode(self.MODEBREW)
        d=chr(len(name)+1)+name+"\x00"
        self.sendbrewcommand(0x01, d)

    def rmfile(self,name):
        self.log("Deleting file '"+name+"'")
        self.setmode(self.MODEBREW)
        d=chr(len(name)+1)+name+"\x00"
        self.sendbrewcommand(0x06, d)

    def getfilesystem(self, dir="", recurse=0):
        results={}

        self.log("Getting dir '"+dir+"'")
        self.setmode(self.MODEBREW)

        
        d=chr(len(dir)+1)+dir+"\x00"
        d2=d
        if len(dir)==0: # to list files on root, must start with /
            d2=chr(len("/")+1)+"/"+"\x00"

        # self.log("file listing 0x0b command")
        for i in range(0,1000):
            data=makelsb(i,4)+d2
            try:
                res=self.sendbrewcommand(0x0b, data)
                name=res[0x19:-3]
                results[name]={ 'name': name, 'type': 'file', 'data': readhex(res) }
            except BrewNoMoreEntriesException:
                break

        # i tried using 0x0a command to list subdirs but that fails when
        # mingled with 0x0b commands
        # self.log("dir listing 0x02 command")
        res=self.sendbrewcommand(0x02, d)
        pos=7
        while pos<len(res):
            subdir=readstring(res[pos:])
            pos=pos+len(subdir)+1
            if len(subdir)==0:
                break
            if len(dir):
                subdir=dir+"/"+subdir
            results[subdir]={ 'name': subdir, 'type': 'directory' }
            if recurse>0:
                results.update(self.getfilesystem(subdir, recurse-1))
        return results

    def writefile(self, name, contents):
        self.log("Writing file '"+name+"' bytes "+`len(contents)`)
        if len(contents)>65534:
            raise Exception(name+" is too large at "+`len(contents)`+" bytes - limit is 64kb")
        self.setmode(self.MODEBREW)
        desc="Writing "+name
        d="\x00" # probably block number
        if len(contents)<256:
            d+="\x00"
        else:
            d+="\x01"
        d+="\x01" # dunno
        d+=makelsb(len(contents), 2) # size
        d+="\x00\x00" # dunno
        d+="\xff\x00" # dunno
        d+="\x01\x00" # dunno
        d+=chr(len(name)+1)  # length of name pls null
        d+=name              # the name
        d+="\x00"            # null term
        l=min(len(contents), 0x100) 
        d+=makelsb(l,2)      # length of remaining data
        d+=contents[:l]      # data
        self.sendbrewcommand(0x05, d)
        # do remaining blocks
        numblocks=len(contents)/0x100
        for offset in range(0x100, len(contents), 0x100):
            d=offset/0x100  # block number
            if d%5==0:
                self.progress(d,numblocks,desc)
            d=chr(d)
            if offset+0x100<len(contents):
                   d+="\x01"  # there is more
            else:  d+="\x00"  # no more after this block
            block=contents[offset:]
            l=min(len(block), 0x100)
            block=block[:l]
            d+=makelsb(l,2)
            d+=block
            self.sendbrewcommand(0x05, d)


    def getfilecontents(self, file):
        self.log("Getting file contents '"+file+"'")
        self.setmode(self.MODEBREW)
        desc="Reading "+file
        d=chr(len(file)+1)+file+"\x00"
        res=self.sendbrewcommand(0x04, "\x00"+d)
        size=readlsb(res[5:7])
        numblocks=size/0x100
        if size%0x100:
            numblocks+=1
        data=res[0xb:-3]
        for i in range(1,numblocks):
            if i%5==0:
                self.progress(i,numblocks,desc)
            res=self.sendbrewcommand(0x04, chr(i))
            res=res[0x7:-3]
            data=data+res
        self.progress(numblocks,numblocks,desc)
        self.log("expected size "+`size`+"  actual "+`len(data)`)
        return data


    def raisecommsexception(self, str):
        raise common.CommsDeviceNeedsAttention(self.desc+" on "+self.comm.port, "The phone is not responding while "+str+".  Check that the port on the phone is set correctly (Menu -> 8 -> 6 -> 2: It is normally set to RS-232 COM port).  Also check that you have selected the correct communications port on your computer and the cable is still firmly plugged in (currently using "+self.comm.port+")")
        

    def setmode(self, desiredmode):
        if self.mode==desiredmode: return

        strmode=None
        strdesiredmode=None
        for v in self.__class__.__dict__:
            if len(v)>len('MODE') and v[:4]=='MODE':
                if self.mode==getattr(self, v):
                    strmode=v[4:]
                if desiredmode==getattr(self,v):
                    strdesiredmode=v[4:]
        if strmode is None:
            raise Exception("No mode for %d" %(self.mode,))
        if strdesiredmode is None:
            raise Exception("No desired mode for %d" %(desiredmode,))
        strmode=strmode.lower()
        strdesiredmode=strdesiredmode.lower()

        for func in ( '_setmode%sto%s' % (strmode, strdesiredmode),
                        '_setmode%s' % (strdesiredmode,)):
            print "setmode: looking for", func
            if hasattr(self,func):
                print "setmode: running "+func
                res=getattr(self, func)()
                if res: # mode changed!
                    self.mode=desiredmode
                    return

        # failed
        self.mode=self.MODENONE
        self.raisecommsexception("transitioning mode from %s to %s" \
                                 % (strmode, strdesiredmode))
        

    def _setmodebrew(self):
        try:
            # might already be?
            self.sendbrewcommand(0x0c, "")
            return 1
        except: pass
        try:
            # try again at 38400
            self.comm.setbaudrate(38400)
            self.sendbrewcommand(0x0c, "")
            return 1
        except: pass
        self._setmodelgdmgo() # brute force into data mode
        try:
            # should work in lgdmgo mode
            self.sendbrewcommand(0x0c, "")
            return 1
        except:
            return 0

    def _setmodelgdmgo(self):
        # see if we can turn on dm mode
        for baud in (0, 115200, 19200, 230400, 38400):
            if baud:
                self.comm.setbaudrate(baud)
            self.comm.write("AT$QCDMG\r\n")
            try:
                self.comm.readsome()
                self.comm.setbaudrate(38400) # dm mode is always 38400
                return 1
            except:
                pass
        return 0
        

    def _setmodephonebook(self):
        try:
            self.sendpbcommand(0x15, "\x00\x00\x00\x00\x00\x00\x00")
            return 1
        except: pass
        try:
            self.comm.setbaudrate(38400)
            self.sendpbcommand(0x15, "\x00\x00\x00\x00\x00\x00\x00")
            return 1
        except: pass
        self._setmodelgdmgo()
        try:
            self.sendpbcommand(0x15, "\x00\x00\x00\x00\x00\x00\x00")
            return 1
        except: pass
        return 0
        
    def _setmodemodem(self):
        for baud in (0, 115200, 38400, 19200, 230400):
            if baud:
                self.comm.setbaudrate(baud)
            self.comm.write("AT\r\n")
            try:
                self.comm.readsome()
                return 1
            except: pass
        return 0        
        
    def sendpbcommand(self, cmd, data):
        d="\xff"+chr(cmd)+chr(self.seq&0xff)+data
        d=self.escape(d+self.crcs(d))+self.terminator
        self.comm.write(d)
        self.seq+=1
        try:
            d=self.unescape(self.comm.readuntil(self.terminator))[:-3] # strip crc
            if 0: # cmd!=0x15 and d[3]!="\x00":
                raise PhoneBookCommandException(ord(d[3]))
            # ::TODO:: we should check crc
            return d
        except commport.CommTimeout:
            self.raisecommsexception("using the phonebook")
            return None # keep pychecker happy

    def sendbrewcommand(self, cmd, data):
        d="\x59"+chr(cmd)+data
        d=self.escape(d+self.crcs(d))+self.terminator
        self.comm.write(d)
        try:
            d=self.unescape(self.comm.readuntil(self.terminator))
            # ::TODO:: we should check crc
            if d[2]!="\x00":
                err=ord(d[2])
                if err==0x1c:
                    raise BrewNoMoreEntriesException()
                if err==0x08:
                    raise BrewNoSuchDirectoryException()
                if err==0x06:
                    raise BrewNoSuchFileException()
                raise BrewCommandException(err)
            return d
        except commport.CommTimeout:
            self.raisecommsexception("manipulating the filesystem")
            return None # keep pychecker happy
        
    
    def escape(self, data):
        if data.find("\x7e")<0 and data.find("\x7d")<0:
            return data
        res=""
        for d in data:
            if d=="\x7e": res+="\x7d\x5e"
            elif d=="\x7d": res+="\x7d\x5d"
            else: res+=d
        return res

    def unescape(self, d):
        d=d.replace("\x7d\x5e", "\x7e")
        d=d.replace("\x7d\x5d", "\x7d")
        return d

    # See http://www.repairfaq.org/filipg/LINK/F_crc_v35.html for more info
    # on CRC
    _crctable=(
        0x0000, 0x1189, 0x2312, 0x329b, 0x4624, 0x57ad, 0x6536, 0x74bf,   # 0 - 7
        0x8c48, 0x9dc1, 0xaf5a, 0xbed3, 0xca6c, 0xdbe5, 0xe97e, 0xf8f7,   # 8 - 15
        0x1081, 0x0108, 0x3393, 0x221a, 0x56a5, 0x472c, 0x75b7, 0x643e,   # 16 - 23
        0x9cc9, 0x8d40, 0xbfdb, 0xae52, 0xdaed, 0xcb64, 0xf9ff, 0xe876,   # 24 - 31
        0x2102, 0x308b, 0x0210, 0x1399, 0x6726, 0x76af, 0x4434, 0x55bd,   # 32 - 39
        0xad4a, 0xbcc3, 0x8e58, 0x9fd1, 0xeb6e, 0xfae7, 0xc87c, 0xd9f5,   # 40 - 47
        0x3183, 0x200a, 0x1291, 0x0318, 0x77a7, 0x662e, 0x54b5, 0x453c,   # 48 - 55
        0xbdcb, 0xac42, 0x9ed9, 0x8f50, 0xfbef, 0xea66, 0xd8fd, 0xc974,   # 56 - 63
        0x4204, 0x538d, 0x6116, 0x709f, 0x0420, 0x15a9, 0x2732, 0x36bb,   # 64 - 71
        0xce4c, 0xdfc5, 0xed5e, 0xfcd7, 0x8868, 0x99e1, 0xab7a, 0xbaf3,   # 72 - 79
        0x5285, 0x430c, 0x7197, 0x601e, 0x14a1, 0x0528, 0x37b3, 0x263a,   # 80 - 87
        0xdecd, 0xcf44, 0xfddf, 0xec56, 0x98e9, 0x8960, 0xbbfb, 0xaa72,   # 88 - 95
        0x6306, 0x728f, 0x4014, 0x519d, 0x2522, 0x34ab, 0x0630, 0x17b9,   # 96 - 103
        0xef4e, 0xfec7, 0xcc5c, 0xddd5, 0xa96a, 0xb8e3, 0x8a78, 0x9bf1,   # 104 - 111
        0x7387, 0x620e, 0x5095, 0x411c, 0x35a3, 0x242a, 0x16b1, 0x0738,   # 112 - 119
        0xffcf, 0xee46, 0xdcdd, 0xcd54, 0xb9eb, 0xa862, 0x9af9, 0x8b70,   # 120 - 127
        0x8408, 0x9581, 0xa71a, 0xb693, 0xc22c, 0xd3a5, 0xe13e, 0xf0b7,   # 128 - 135
        0x0840, 0x19c9, 0x2b52, 0x3adb, 0x4e64, 0x5fed, 0x6d76, 0x7cff,   # 136 - 143
        0x9489, 0x8500, 0xb79b, 0xa612, 0xd2ad, 0xc324, 0xf1bf, 0xe036,   # 144 - 151
        0x18c1, 0x0948, 0x3bd3, 0x2a5a, 0x5ee5, 0x4f6c, 0x7df7, 0x6c7e,   # 152 - 159
        0xa50a, 0xb483, 0x8618, 0x9791, 0xe32e, 0xf2a7, 0xc03c, 0xd1b5,   # 160 - 167
        0x2942, 0x38cb, 0x0a50, 0x1bd9, 0x6f66, 0x7eef, 0x4c74, 0x5dfd,   # 168 - 175
        0xb58b, 0xa402, 0x9699, 0x8710, 0xf3af, 0xe226, 0xd0bd, 0xc134,   # 176 - 183
        0x39c3, 0x284a, 0x1ad1, 0x0b58, 0x7fe7, 0x6e6e, 0x5cf5, 0x4d7c,   # 184 - 191
        0xc60c, 0xd785, 0xe51e, 0xf497, 0x8028, 0x91a1, 0xa33a, 0xb2b3,   # 192 - 199
        0x4a44, 0x5bcd, 0x6956, 0x78df, 0x0c60, 0x1de9, 0x2f72, 0x3efb,   # 200 - 207
        0xd68d, 0xc704, 0xf59f, 0xe416, 0x90a9, 0x8120, 0xb3bb, 0xa232,   # 208 - 215
        0x5ac5, 0x4b4c, 0x79d7, 0x685e, 0x1ce1, 0x0d68, 0x3ff3, 0x2e7a,   # 216 - 223
        0xe70e, 0xf687, 0xc41c, 0xd595, 0xa12a, 0xb0a3, 0x8238, 0x93b1,   # 224 - 231
        0x6b46, 0x7acf, 0x4854, 0x59dd, 0x2d62, 0x3ceb, 0x0e70, 0x1ff9,   # 232 - 239
        0xf78f, 0xe606, 0xd49d, 0xc514, 0xb1ab, 0xa022, 0x92b9, 0x8330,   # 240 - 247
        0x7bc7, 0x6a4e, 0x58d5, 0x495c, 0x3de3, 0x2c6a, 0x1ef1, 0x0f78,   # 248 - 255
        )

    def crc(self, data, initial=0xffff):
        "CRC calculation - returns 16 bit integer"
        res=initial
        for byte in data:
            curres=res
            res=res>>8  # zero extended
            val=(ord(byte)^curres) & 0xff
            val=self._crctable[val]
            res=res^val

        res=(~res)&0xffff
        return res

    def crcs(self, data, initial=0xffff):
        "CRC calculation - returns 2 byte string LSB"
        r=self.crc(data, initial)
        return "%c%c" % ( r& 0xff, (r>>8)&0xff)

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

        # Bytes 10-26 null terminated name
        res['name']=readstring(packet[0x10:0x27])

        # Byte 27 group
        b=packet[0x27]
        res['group']=ord(b)

        # byte 28 some sort of number
        res['?offset028']=readlsb(packet[0x28:0x29])

        # bytes 29-59 null terminated email1
        res['email1']=readstring(packet[0x29:0x60])

        # bytes 5a-8a null terminated email2
        res['email2']=readstring(packet[0x5a:0x8b])

        # bytes 8b-bb null terminated email3
        res['email3']=readstring(packet[0x8b:0xbc])

        # bytes bc-ec null terminated url
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

        # bytes f0-110 null terminated memo
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

        # Bytes 10-26 null terminated name
        assert len(res)==0x10
        res+=makestring(entry.get('name', "<unnamed>"), 23)

        # Byte 27 group
        assert len(res)==0x27
        res+=makelsb(entry.get('group', 0), 1)
        
        # byte 28 some sort of number - always 0
        assert len(res)==0x28
        res+=makelsb(0, 1)

        # bytes 29-59 null terminated email1
        assert len(res)==0x29
        res+=makestring(entry.get('email1', ""), 49)

        # bytes 5a-8a null terminated email2
        assert len(res)==0x5a
        res+=makestring(entry.get('email2', ""), 49)

        # bytes 8b-bb null terminated email3
        assert len(res)==0x8b
        res+=makestring(entry.get('email3', ""), 49)

        # bytes bc-ec null terminated url
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
        
        # bytes f0-110 null terminated memo
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
        res+=makestring(entry.get('number1', ""), 49)

        # bytes 148-178 number 2
        assert len(res)==0x148
        res+=makestring(entry.get('number2', ""), 49)

        # bytes 179-1a9 number 3
        assert len(res)==0x179
        res+=makestring(entry.get('number3', ""), 49)
        
        # bytes 1aa-1da number 4
        assert len(res)==0x1aa
        res+=makestring(entry.get('number4', ""), 49)

        # bytes 1db-20b number 5
        assert len(res)==0x1db
        res+=makestring(entry.get('number5', ""), 49)

        # bytes 20c-210 five zeros
        assert len(res)==0x20c
        res+=makelsb(0, 5)

        # done
        assert len(res)==0x211

        return res[4:]  # chop off cosmetic first bit
    
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
    # reads null terminated string
    res=""
    for i in data:
        if i=='\x00':
            return res
        res=res+i
    raise Exception(" NOT NULL TERMINATED!!!! "+common.datatohexstring(data))
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

def brewbasename(str):
    # returns basename of str
    if str.rfind("/")>0:
        return str[str.rfind("/")+1:]
    return str

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
