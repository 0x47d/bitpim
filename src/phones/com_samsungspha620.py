### BITPIM
###
### Copyright (C) 2004-2005 Stephen Wood <saw@bitpim.org>
### Copyright (C) 2005 Todd Imboden
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with a Samsung SPH-A620"""

import sha
import re
import struct

import common
import commport
import p_samsungspha620
import p_brew
import com_brew
import com_phone
import com_samsung_packet
import prototypes

numbertypetab=('home','office','cell','pager','fax','none')

class Phone(com_samsung_packet.Phone):
    "Talk to a Samsung SPH-A620 phone"

    desc="SPH-A620"

    protocolclass=p_samsungspha620
    serialsname='spha620'
    __groups_range=xrange(5)

    imagelocations=()
        # offset, index file, files location, type, maximumentries
    
    __ams_index_file="ams/AmsRegistry"

    def __init__(self, logtarget, commport):
        com_samsung_packet.Phone.__init__(self, logtarget, commport)
        self.numbertypetab=numbertypetab
        self.mode=self.MODENONE

    def getfundamentals(self, results):
        """Gets information fundamental to interopating with the phone and UI."""
        self.amsanalyze(results)

        # use a hash of ESN and other stuff (being paranoid)
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        print "Calling setmode MODEMODEM"
        self.setmode(self.MODEMODEM)
        print "Getting serial number"
        results['uniqueserial']=sha.new(self.get_esn()).hexdigest()

        self.log("Reading group information")
        print "Getting Groups"
        results['groups']=self.read_groups()
        print "Got Groups"
        # Comment the next to out if you want to read the phonebook
        #self.getwallpaperindices(results)
        #self.getringtoneindices(results)
        self.log("Fundamentals retrieved")
        return results

    # digital_cam/jpeg Remove first 148 characters
    imagelocations=(
        # offset, index file, files location, type, maximumentries
        (100, "", "digital_cam/jpeg", "camera", 100)
        )
        
    def amsanalyze(self,results):
        buf=prototypes.buffer(self.getfilecontents(self.protocolclass.AMSREGISTRY))
        ams=self.protocolclass.amsregistry()
        ams.readfrombuffer(buf)
        rt={}   #Todd added for ringtone index
        j=0     #Todd added for ringtone index
        for i in range(ams.nfiles):
            filetype=ams.info[i].filetype
            if filetype:
                dir_ptr=ams.info[i].dir_ptr
                name_ptr=ams.info[i].name_ptr
                mimetype_ptr=ams.info[i].mimetype_ptr
                version_ptr=ams.info[i].version_ptr
                vendor_ptr=ams.info[i].vendor_ptr
                dir=self.getstring(ams.strings,dir_ptr)
                name=self.getstring(ams.strings,name_ptr)
                mimetype=self.getstring(ams.strings,mimetype_ptr)
                version=self.getstring(ams.strings,version_ptr)
                vendor=self.getstring(ams.strings,vendor_ptr)

                #downloaddomain_ptr=ams.info[i].downloaddomain_ptr
                print i, filetype, version, dir, vendor, name, mimetype
                #if downloaddomainptr_ptr:
                # print self.getstring(ams.strings,misc_ptr)
                print j,ams.info[i].num2, ams.info[i].num7, ams.info[i].num8, ams.info[i].num9, ams.info[i].num12, ams.info[i].num13, ams.info[i].num14, ams.info[i].num15, ams.info[i].num16, ams.info[i].num17
                print " "

        # Todd's added info
                if filetype==12:     #this will add the file extension
                    if mimetype=="audio/vnd.qcelp":
                        filetype='.qcp'
                    elif mimetype=="audio/midi":
                        filetype='.mid'
                    elif mimetype=="application/x-pmd":
                        filetype='.pmd'
                    else:
                        filetype=''
                    rt[j]={'name':name+filetype,'location':'ams/'+dir,'origin':'ringers'}
                    j+=1
        results['ringtone-index']=rt
        
    def pblinerepair(self, line):
        "Extend incomplete lines"
        # VGA1000 Firmware WG09 doesn't return a full line unless birthday
        # is set.  Add extra commas so packet decoding works
        nfields=26                      # Can we get this from packet def?
        ncommas=self.countcommas(line)
        if ncommas<0:                   # Un terminated quote
            line+='"'
            ncommas = -ncommas
        if nfields-ncommas>1:
            line=line+","*(nfields-ncommas-1)
        return line

    def countcommas(self, line):
        inquote=False
        ncommas=0
        for c in line:
            if c == '"':
                inquote = not inquote
            elif not inquote and c == ',':
                ncommas+=1

        if inquote:
            ncommas = -ncommas
        
        return ncommas
        
    def getwallpapers(self, result):
        self.getwallpaperindices(result)
        return self.getmedia(self.imagelocations, result, 'wallpapers')

    
    def getmedia(self, maps, results, key):
        """Returns the contents of media as a dicxt where the key is a name
        returned by getindex, and the value is the contents of the media"""
        
        media={}
        for i in range(10000):
            try:
                req=p_brew.listfilerequest()
                req.entrynumber=i
                req.dirname='digital_cam/jpeg'
                res=self.sendbrewcommand(req, p_brew.listfileresponse)
                filename=res.filename
                p=filename.rfind("/")
                basefilename=filename[p+1:]+".jpg"
                contents=self.getfilecontents(filename)

                name_len=ord(contents[5])
                new_basefilename=contents[6:6+name_len]+".jpg"
                duplicate=False
                for k in results['wallpaper-index'].keys():
                    if results['wallpaper-index'][k]['name']==new_basefilename:
                        duplicate=True
                        break
                    if results['wallpaper-index'][k]['name']==basefilename:
                        ksave=k
                if duplicate:
                    new_basefilename=basefilename
                else:
                    self.log("Renaming to "+new_basefilename)
                    results['wallpaper-index'][ksave]['name']=new_basefilename                  
                media[new_basefilename]=contents[148:]

            except com_brew.BrewNoMoreEntriesException:
                break

        results[key]=media

    def getwallpaperindices(self, results):
        """Get the index of camera pictures"""
        imagemedia={}
        for i in range(10000):
            try:
                req=p_brew.listfilerequest()
                req.entrynumber=i
                req.dirname='digital_cam/jpeg'
                res=self.sendbrewcommand(req, p_brew.listfileresponse)
                filename=res.filename
                p=filename.rfind("/")
                filename=filename[p+1:]+".jpg"
                # Just a made up index number for now.  Have not studied
                # what phone is using.
                imagemedia[100+i]={'name': filename, 'origin': "camera"}

            except com_brew.BrewNoMoreEntriesException:
                break

        results['wallpaper-index']=imagemedia
        return
        
    def _findmediaindex(self, index, name, pbentryname, type):
        if name is None:
            return 0
        for i in index:
            if index[i]['name']==name:
                return i
        # Not found in index, assume Vision download
        pos=name.find('_')
        if(pos>=0):
            i=int(name[pos+1:])
            return i
        
        return 0
        
    def getstring(self, contents, start):
        "Get a null terminated string from contents"
        i=start
        while contents[i:i+1]!='\0':
            i+=1
        return contents[start:i]
        
    def getringtones(self, results):
        self.setmode(self.MODEBREW)
        tones={}
        for i in range(len(results['ringtone-index'])):
            print i,results['ringtone-index'][i]['location']
            tones[results['ringtone-index'][i]['name']]=self.getfilecontents(results['ringtone-index'][i]['location'])
            i+=1
        results['ringtone']=tones
    
class Profile(com_samsung_packet.Profile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname
    phone_manufacturer='SAMSUNG'
    phone_model='SPH-A620/152'

    def __init__(self):
        com_samsung_packet.Profile.__init__(self)
        self.numbertypetab=numbertypetab

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
        ('calendar', 'read', None),   # all calendar reading
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('todo', 'read', None),     # all todo list reading
        ('todo', 'write', 'OVERWRITE'),  # all todo list writing
        ('memo', 'read', None),     # all memo list reading
        ('memo', 'write', 'OVERWRITE'),  # all memo list writing
        )

