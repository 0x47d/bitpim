### BITPIM
###
### Copyright (C) 2005      Bruce Schurmann <austinbp@schurmann.org>
### Copyright (C) 2003-2005 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with the LG VX3200 cell phone

The VX3200 is somewhat similar to the VX4400

"""

# standard modules
import time
import cStringIO
import sha
import re

# my modules
import common
import copy
import p_lgvx3200
import com_lgvx4400
import com_brew
import com_phone
import com_lg
import prototypes
import phone_media_codec
import conversions

media_codec=phone_media_codec.codec_name

class SimpleFileCache(com_brew.BrewProtocol,com_lgvx4400.Phone):
    "Trivial phone file cache"

    def __init__(self, logtarget, commport):
        com_brew.BrewProtocol.__init__(self)
        com_lgvx4400.Phone.__init__(self,logtarget,commport)
        self.cache={}

    def flush(self):
        self.cache={}

    def _readfile(self,filename):
        try:
            tempfile=self.getfilecontents(filename)
        except com_brew.BrewNoSuchFileException:
            # file may not exist - dummy as a zero len file
            tempfile=''
        # special case for zero len files - these can only be .bit files
        if len(tempfile)==0:
            self.cache[filename]=("bit",tempfile)
            self.log("SimpleFileCache: encountered zero len file: "+filename)
            return
        # quicky test for file
        if tempfile[0:4]!='MThd':
            self.cache[filename]=("mp3",tempfile)
        elif tempfile[0:4]=="\x80\x00\x80\x00":
            self.cache[filename]=("bit",tempfile)
        else:
            self.cache[filename]=("mid",tempfile)

    def getdata(self,filename):
        if not self.cache.has_key(filename):
            self._readfile(filename)
        return self.cache[filename][1]

    def gettype(self,filename):
        if not self.cache.has_key(filename):
            self._readfile(filename)
        return self.cache[filename][0]

    def rmentry(self,filename):
        if self.cache.has_key(filename):
            del self.cache[filename]

    def writeentry(self,filename,data):
        if self.cache.has_key(filename):
            self.cache[filename]=(self.cache[filename][0],data)
        else:
            if len(data)==0:
                self.cache[filename]=("bit",data)
                self.log("SimpleFileCache: encountered zero len file: "+filename)
                return
            if data[0:4]!='MThd':
                self.cache[filename]=("mp3",data)
            elif data[0:4]=="\x80\x00\x80\x00":
                self.cache[filename]=("bit",data)
            else:
                self.cache[filename]=("mid",data)
            
        

class Phone(com_lgvx4400.Phone,SimpleFileCache):
    "Talk to the LG VX3200 cell phone"

    desc="LG-VX3200"

    wallpaperindexfilename="download/dloadindex/brewImageIndex.map"
    ringerindexfilename="download/dloadindex/brewRingerIndex.map"

    protocolclass=p_lgvx3200
    serialsname='lgvx3200'

    # more VX3200 indices
    imagelocations=(
        # offset, index file, files location, type, maximumentries
        ( 11, "download/dloadindex/brewImageIndex.map", "download", "images", 3) ,
        )

    ringtonelocations=(
        # offset, index file, files location, type, maximumentries
        ( 37, "download/dloadindex/brewRingerIndex.map", "user/sound/ringer", "ringers", 30),
        )


    builtinimages= ('Sport 1', 'Sport 2', 'Nature 1', 'Nature 2',
                    'Animal', 'Martini', 'Goldfish', 'Umbrellas',
                    'Mountain climb', 'Country road')

    builtinringtones= ('Ring 1', 'Ring 2', 'Ring 3', 'Ring 4', 'Ring 5', 'Ring 6',
                       'Ring 7', 'Ring 8', 'Annen Polka', 'Pachelbel Canon', 
                       'Hallelujah', 'La Traviata', 'Leichte Kavallerie Overture', 
                       'Mozart Symphony No.40', 'Bach Minuet', 'Farewell', 
                       'Mozart Piano Sonata', 'Sting', 'O solemio', 
                       'Pizzicata Polka', 'Stars and Stripes Forever', 
                       'Pineapple Rag', 'When the Saints Go Marching In', 'Latin', 
                       'Carol 1', 'Carol 2', 'Chimes high', 'Chimes low', 'Ding', 
                       'TaDa', 'Notify', 'Drum', 'Claps', 'Fanfare', 'Chord high', 
                       'Chord low') 
                       
    def __init__(self, logtarget, commport):
        com_lgvx4400.Phone.__init__(self,logtarget,commport)
        #SimpleFileCache.__init__(self,logtarget,commport)
        self.mode=self.MODENONE
        self.mediacache=SimpleFileCache(logtarget,commport)

    def makeentry(self, counter, entry, dict):
        e=com_lgvx4400.Phone.makeentry(self, counter, entry, dict)
        e.entrysize=0x202
        return e

    def getindex(self, indexfile):
        "Read an index file"
        index={}
        # Hack for LG-VX3200 - wallpaper index file is not real
        if re.search("ImageIndex", indexfile) is not None:
            ind=0
            for ifile in 'wallpaper', 'poweron', 'poweroff':
                ifilefull="download/"+ifile+".bit"
                mediafiledata=self.mediacache.getdata(ifilefull)
                if len(mediafiledata)!=0:
                    index[ind]=ifile+".bmp"
                    ind = ind + 1
                    self.log("Index file "+indexfile+" entry added: "+ifile+".bmp")
        else:
            try:
                buf=prototypes.buffer(self.getfilecontents(indexfile))
            except com_brew.BrewNoSuchFileException:
                # file may not exist
                return index
            g=self.protocolclass.indexfile()
            g.readfrombuffer(buf)
            self.logdata("Index file %s read with %d entries" % (indexfile,g.numactiveitems), buf.getdata(), g)
            for i in g.items:
                if i.index!=0xffff:
                    # Horribly tedious but I need to sneek a peek at the actual
                    # ringer files so I can determine if the file suffix needs to
                    # be twiddled.
                    mediafiledata=self.mediacache.getdata(self.ringtonelocations[0][2]+"/"+i.name)
                    mediafiletype=self.mediacache.gettype(self.ringtonelocations[0][2]+"/"+i.name)
                    if mediafiletype=="mp3":
                        i.name=re.sub("\.mid|\.MID", ".mp3", i.name)
                        self.log("getindex() mapped a mid file to mp3, "+i.name+", "+mediafiledata[0:4])
                    index[i.index]=i.name
        return index
        
    def getmedia(self, maps, result, key):
        """Returns the contents of media as a dict where the key is a name as returned
        by getindex, and the value is the contents of the media"""
        media={}
        # the maps
        type=None
        for offset,indexfile,location,type,maxentries in maps:
            if type=="images":
                # Long story short - wallpaper is actually hardwired to the single file wallpaper.bit
                index=self.getindex(indexfile)
                for i in index:
                    # undo the hack that can from getindex() for wallpaper
                    mediafilename=re.sub("\.bmp|\.BMP", ".bit", index[i])
                    mediafiledata=self.mediacache.getdata(location+"/"+mediafilename)
                    media[index[i]]=conversions.convertlgbittobmp(mediafiledata)
                self.log("Spoofed the VX3200 wallpaper related files")
            else:
                index=self.getindex(indexfile)
                for i in index:
                    # undo the hack that can from getindex() for ringers
                    mediafilename=re.sub("\.mp3|\.MP3", ".mid", index[i])
                    media[index[i]]=self.mediacache.getdata(location+"/"+mediafilename)
        result[key]=media
        return result

    def savemedia(self, mediakey, mediaindexkey, maps, results, merge, reindexfunction):
        """Actually saves out the media

        @param mediakey: key of the media (eg 'wallpapers' or 'ringtone')
        @param mediaindexkey:  index key (eg 'wallpaper-index')
        @param maps: list index files and locations
        @param results: results dict
        @param merge: are we merging or overwriting what is there?
        @param reindexfunction: the media is re-indexed at the end.  this function is called to do it
        """
        print results.keys()
        # I humbly submit this as the longest function in the bitpim code ...
        # wp and wpi are used as variable names as this function was originally
        # written to do wallpaper.  it works just fine for ringtones as well
        #
        # LG-VX3200 special notes:
        # The index entries for both the wallpaper and ringers are
        # hacked just a bit AND are hacked in slightly different
        # ways. In addition to that the media for the wallpapers is
        # currently in BMP format inside the program and must be
        # converted to BIT (LG proprietary) on the way out.
        wp=results[mediakey].copy()
        wpi=results[mediaindexkey].copy()
        # remove builtins
        for k in wpi.keys():
            if wpi[k]['origin']=='builtin':
                del wpi[k]

        # sort results['mediakey'+'-index'] into origin buckets

        # build up list into init
        init={}
        for offset,indexfile,location,type,maxentries in maps:
            init[type]={}
            for k in wpi.keys():
                if wpi[k]['origin']==type:
                    index=k-offset
                    name=wpi[k]['name']
                    data=None
                    del wpi[k]
                    for w in wp.keys():
                        if wp[w]['name']==name:
                            data=wp[w]['data']
                            del wp[w]
                    if not merge and data is None:
                        # delete the entry
                        continue
                    init[type][index]={'name': name, 'data': data}

        # init now contains everything from wallpaper-index
        print init.keys()
        # now look through wallpapers and see if anything remaining was assigned a particular
        # origin
        for w in wp.keys():
            o=wp[w].get("origin", "")
            if o is not None and len(o) and o in init:
                idx=-1
                while idx in init[o]:
                    idx-=1
                init[o][idx]=wp[w]
                del wp[w]
            
        # we now have init[type] with the entries and index number as key (negative indices are
        # unallocated).  Proceed to deal with each one, taking in stuff from wp as we have space
        for offset,indexfile,location,type,maxentries in maps:
            if type=="camera": break
            index=init[type]
            try:
                dirlisting=self.getfilesystem(location)
            except com_brew.BrewNoSuchDirectoryException:
                self.mkdirs(location)
                dirlisting={}
            # rename keys to basename
            for i in dirlisting.keys():
                dirlisting[i[len(location)+1:]]=dirlisting[i]
                del dirlisting[i]
            # what we will be deleting
            dellist=[]
            if not merge:
                # get existing wpi for this location
                wpi=results[mediaindexkey]
                for i in wpi:
                    entry=wpi[i]
                    if entry['origin']==type:
                        # it is in the original index, are we writing it back out?
                        delit=True
                        for idx in index:
                            if index[idx]['name']==entry['name']:
                                delit=False
                                break
                        if delit:
                            # More VX3200 chicanery
                            if type=="ringers":
                                entryname=re.sub("\.mp3|\.MP3", ".mid", entry['name'])
                            else:
                                entryname=entry['name']
                            if entryname in dirlisting:
                                dellist.append(entryname)
                            else:
                                self.log("%s in %s index but not filesystem" % (entryname, type))
            # go ahead and delete unwanted files
            print "deleting",dellist
            for f in dellist:
                self.rmfile(location+"/"+f)
                # Keep our mediacache up-to-date
                self.mediacache.rmentry(location+"/"+f)
            # LG-VX3200 special case:
            # We only keep (upload) wallpaper images if there was a legit
            # one on the phone to begin with. This code will weed out any
            # attempts to the contrary.
            if type=="images":
                losem=[]
                # get existing wpi for this location
                wpi=results[mediaindexkey]
                for idx in index:
                    delit=True
                    for i in wpi:
                        entry=wpi[i]
                        if entry['origin']==type:
                            if index[idx]['name']==entry['name']:
                                delit=False
                                break
                    if delit:
                        self.log("Inhibited upload of illegit image (not originally on phone): "+index[idx]['name'])
                        losem.append(idx)
                # Now actually remove any illegit images from upload attempt
                for idx in losem:
                    del index[idx]
            #  slurp up any from wp we can take
            while len(index)<maxentries and len(wp):
                idx=-1
                while idx in index:
                    idx-=1
                k=wp.keys()[0]
                index[idx]=wp[k]
                del wp[k]
            # normalise indices
            index=self._normaliseindices(index)  # hey look, I called a function!
            # move any overflow back into wp
            if len(index)>maxentries:
                keys=index.keys()
                keys.sort()
                for k in keys[maxentries:]:
                    idx=-1
                    while idx in wp:
                        idx-=1
                    wp[idx]=index[k]
                    del index[k]
            # write out the new index
            keys=index.keys()
            keys.sort()
            ifile=self.protocolclass.indexfile()
            ifile.numactiveitems=len(keys)
            for k in keys:
                entry=self.protocolclass.indexentry()
                entry.index=k
                # Now we need to undo some of the index mutations from earlier
                if type=="ringers":
                    entry.name=re.sub("\.mp3|\.MP3", ".mid", index[k]['name'])
                else:
                    entry.name=index[k]['name']
                ifile.items.append(entry)
            while len(ifile.items)<maxentries:
                ifile.items.append(self.protocolclass.indexentry())
            buffer=prototypes.buffer()
            ifile.writetobuffer(buffer)
            if type!="images":
                # The images index file on the LG-VX3200 is a noop - don't write
                self.logdata("Updated index file "+indexfile, buffer.getvalue(), ifile)
                self.writefile(indexfile, buffer.getvalue())
            # Write out files - we compare against existing dir listing and don't rewrite if they
            # are the same size
            for k in keys:
                entry=index[k]
                data=entry.get("data", None)
                # Now we need to undo some of the index mutations from earlier
                if type=="ringers":
                    entryname=re.sub("\.mp3|\.MP3", ".mid", entry['name'])
                elif type=="images":
                    entryname=re.sub("\.bmp|\.BMP", ".bit", entry['name'])
                    # Special test for wallpaper files - LG-VX3200 will ONLY accpet these files
                    if entryname!="wallpaper.bit" and entryname!="poweron.bit" and entryname!="poweroff.bit":
                        self.log("The wallpaper files can only be wallpaper.bmp, poweron.bmp or poweroff.bmp. "+entry['name']+" does not conform - skipping upload.")
                        continue
                else:
                    entryname=entry['name']
                # wallpaper files are currently in the program as BMP files
                # these must be translated to BIT files before going anywhere with them
                if type=="images":
                    data=conversions.convertbmptolgbit(data)
                    if data is None:
                        self.log("The wallpaper images must be 128x128 24bpp BMP files, "+entry['name']+", does not comply - skipping upload.")
                        continue
                    # Now determine if this wallpaper image is actually a blank.
                    bit_is_blank=True
                    for i in range(128*128):
                        ind=i*2+2
                        if common.LSBUint16(data[ind:ind+2])!=0xffff:
                            bit_is_blank=False
                            continue
                if data is None:
                    if entryname not in dirlisting:
                        self.log("Index error.  I have no data for "+entryname+" and it isn't already in the filesystem - skipping upload.")
                    continue
                # This following test does not apply to wallpaper - it is always the same size on the LG-VX3200!
                if type!="images":
                    if entryname in dirlisting and len(data)==dirlisting[entryname]['size']:
                        self.log("Skipping writing %s/%s as there is already a file of the same length" % (location,entryname))
                        continue
                else:
                    # If the file on the phone was zero length then I substituted a blank picture.
                    # I do NOT want to create a blank image on the phone if nothing has changed.
                    if ((entryname not in dirlisting) or (dirlisting[entryname]['size']==0)) and bit_is_blank:
                        self.log("Skipping the blank image, "+entry['name'])
                        continue
                self.writefile(location+"/"+entryname, data)
                # Keep our mediacache up-to-date
                self.mediacache.writeentry(location+"/"+entryname, data)
                self.log("Wrote media file: "+location+"/"+entryname)
        # did we have too many
        if len(wp):
            for k in wp:
                self.log("Unable to put %s on the phone as there weren't any spare index entries" % (wp[k]['name'],))
                
        # Note that we don't write to the camera area

        # tidy up - reread indices
        del results[mediakey] # done with it
        # This excessive and expensive so do not do
        # self.mediacache.flush()
        # self.log("Flushed ringer cache")
        reindexfunction(results)
        return results

                   

parentprofile=com_lgvx4400.Profile
class Profile(parentprofile):
    protocolclass=Phone.protocolclass
    serialsname=Phone.serialsname

    # use for auto-detection
    phone_manufacturer='LG Electronics Inc.'
    phone_model='VX3200 107'

    # no direct usb interface
    usbids=com_lgvx4400.Profile.usbids_usbtoserial

    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
     #   ('calendar', 'read', None),   # all calendar reading
        ('wallpaper', 'read', None),  # all wallpaper reading
        ('ringtone', 'read', None),   # all ringtone reading
     #   ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
     #   ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
     #   ('wallpaper', 'write', 'MERGE'),      # merge and overwrite wallpaper
        ('wallpaper', 'write', 'OVERWRITE'),   # merge and overwrite wallpaper
        ('ringtone', 'write', 'MERGE'),      # merge and overwrite ringtone
        ('ringtone', 'write', 'OVERWRITE'),
        )

    WALLPAPER_WIDTH=128
    WALLPAPER_HEIGHT=128
    MAX_WALLPAPER_BASENAME_LENGTH=19
    WALLPAPER_FILENAME_CHARS="abcdefghijklmnopqrstuvwxyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="bmp"

    MAX_RINGTONE_BASENAME_LENGTH=19
    RINGTONE_FILENAME_CHARS="abcdefghijklmnopqrstuvxwyz0123456789 ."

    imageorigins={}
    imageorigins.update(common.getkv(parentprofile.stockimageorigins, "images"))

    def GetImageOrigins(self):
        return self.imageorigins

    # our targets are the same for all origins
    imagetargets={}
    imagetargets.update(common.getkv(parentprofile.stockimagetargets, "wallpaper",
                                      {'width': 128, 'height': 128, 'format': "BMP"}))

    def GetTargetsForImageOrigin(self, origin):
        return self.imagetargets
    
    def __init__(self):
        parentprofile.__init__(self)
