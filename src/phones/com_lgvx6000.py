### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Communicate with the LG VX6000 cell phone

The VX6000 is substantially similar to the VX4400 except that it supports more
image formats, has wallpapers in no less than 5 locations and puts things in
slightly different directories.

The code in this file mainly inherits from VX4400 code and then extends where
the 6000 has extra functionality

"""

# standard modules
import re
import time
import cStringIO
import sha

# my modules
import common
import copy
import p_lgvx6000
import com_lgvx4400
import com_brew
import com_phone
import com_lg
import prototypes

class Phone(com_lgvx4400.Phone):
    "Talk to the LG VX6000 cell phone"

    desc="LG-VX6000"

    wallpaperindexfilename="download/dloadindex/brewImageIndex.map"
    ringerindexfilename="download/dloadindex/brewRingerIndex.map"
    protocolclass=p_lgvx6000
    serialsname='lgvx6000'

    cameraoffset=0x82
    # more VX6000 indices
    imagelocations=(
        # offset, index file, files location, type, maximumentries
        ( 10, wallpaperindexfilename, "brew/shared", "images", 30) ,
        ( 0xc8, "download/dloadindex/mmsImageIndex.map", "brew/shared/mms", "mms", 20),
        ( 0xdc, "download/dloadindex/mmsDrmImageIndex.map", "brew/shared/mms/d", "drm", 20), 
        ( cameraoffset, None, None, "camera", 20) # special entry to make some loops easier
        )
    
    def __init__(self, logtarget, commport):
        com_lgvx4400.Phone.__init__(self,logtarget,commport)
        self.log("Attempting to contact phone")
        self.mode=self.MODENONE

    def getwallpaperindices(self, results, verify=False):
        """Gets the wallpapers

        @param results: places results in this dict
        @param verify: checks the files exist
        """
        wp={}

        # builtins
        c=1
        for name in 'Beach Ball', 'Towerbridge', 'Sunflower', 'Beach', 'Fish', 'Sea', 'Snowman':
            wp[c]={'name': name, 'origin': 'builtin' }
            c+=1

        # the 3 different maps
        for offset,indexfile,location,type,maxentries in self.imagelocations:
            if type=="camera": continue
            if verify:
                dirlisting=self.getfilesystem(location)
            index=self.getindex(indexfile)
            for i in index:
                if verify:
                    if location+"/"+index[i] not in dirlisting:
                        print "skipping",index[i],"in verify"
                        continue
                wp[i+offset]={'name': index[i], 'origin': type}
                
        # camera

        # (we don't do verify on the camera since we assume it is always correct)
        index=self.getcameraindex()
        for i in index:
            wp[i+self.cameraoffset]=index[i]

        results['wallpaper-index']=wp
        return wp

    def getcameraindex(self):
        buf=prototypes.buffer(self.getfilecontents("cam/pics.dat"))
        index={}
        g=self.protocolclass.campicsdat()
        g.readfrombuffer(buf)
        for i in g.items:
            if len(i.name):
                # index[i.index]={'name': i.name, 'date': i.taken, 'origin': 'camera' }
                # we currently use the filesystem name rather than rename in camera
                # since the latter doesn't include the file extension which then makes
                # life less pleasant once the file ends up on the computer
                index[i.index]={'name': "pic%02d.jpg"%(i.index,), 'date': i.taken, 'origin': 'camera' }
        return index

    def getwallpapers(self, result):
        papers={}
        # the ordinary images
        for offset,indexfile,location,type,maxentries in self.imagelocations:
            if type=="camera": continue
            index=self.getindex(indexfile)
            for i in index:
                try:
                    papers[index[i]]=self.getfilecontents(location+"/"+index[i])
                except com_brew.BrewNoSuchFileException:
                    self.log("It was in the index, but not on the filesystem")
        # now for the camera stuff
        index=self.getcameraindex()
        for i in index:
            try:
                papers[index[i]['name']]=self.getfilecontents("cam/pic%02d.jpg" % (i,))
            except com_brew.BrewNoSuchFileException:
                self.log("It was in the index, but not on the filesystem")
        result['wallpapers']=papers
        return result
                
    def savewallpapers(self, results, merge):
        "Actually saves out the wallpapers"
        print results.keys()
        # I humbly submit this as the longest function in the bitpim code ...
        wp=results['wallpapers'].copy()
        wpi=results['wallpaper-index'].copy()
        # remove builtins
        for k in wpi.keys():
            if wpi[k]['origin']=='builtin':
                del wpi[k]

        # sort results['wallpapers'+'-index'] into origin buckets

        # build up list into init
        init={}
        for offset,indexfile,location,type,maxentries in self.imagelocations:
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
        for offset,indexfile,location,type,maxentries in self.imagelocations:
            if type=="camera": break
            index=init[type]
            dirlisting=self.getfilesystem(location)
            # rename keys to basename
            for i in dirlisting.keys():
                dirlisting[i[len(location)+1:]]=dirlisting[i]
                del dirlisting[i]
            # what we will be deleting
            dellist=[]
            if not merge:
                # get existing wpi for this location
                wpi=results['wallpaper-index']
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
                            if entry['name'] in dirlisting:
                                dellist.append(entry['name'])
                            else:
                                print "%s in %s index but not filesystem" % (entry['name'], type)
            # go ahead and delete unwanted files
            print "deleting",dellist
            for f in dellist:
                self.rmfile(location+"/"+f)
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
                entry.name=index[k]['name']
                ifile.items.append(entry)
            while len(ifile.items)<maxentries:
                ifile.items.append(self.protocolclass.indexentry())
            buffer=prototypes.buffer()
            ifile.writetobuffer(buffer)
            self.logdata("Updated index file "+indexfile, buffer.getvalue(), ifile)
            self.writefile(indexfile, buffer.getvalue())
            # Write out files - we compare against existing dir listing and don't rewrite if they
            # are the same size
            for k in keys:
                entry=index[k]
                data=entry.get("data", None)
                if data is None:
                    if entry['name'] not in dirlisting:
                        self.log("Logic error.  I have no data for "+entry['name']+" and it isn't already in the filesystem")
                    continue
                if entry['name'] in dirlisting and len(data)==dirlisting[entry['name']]['size']:
                    self.log("Skipping writing %s/%s as there is already a file of the same length" % (location,entry['name']))
                    continue
                self.writefile(location+"/"+entry['name'], data)
        # did we have too many
        if len(wp):
            for k in wp:
                self.log("Unable to put %s on the phone as there weren't any spare index entries" % (wp[k]['name'],))
                
                    
        # ::TODO:: write out camera stuff

        # tidy up - reread indices
        del results['wallpapers'] # done with it
        self.getwallpaperindices(results)
        return data
                

    def _normaliseindices(self, d):
        "turn all negative keys into positive ones for index"
        res={}
        keys=d.keys()
        keys.sort()
        keys.reverse()
        for k in keys:
            if k<0:
                for c in range(999999):
                    if c not in keys and c not in res:
                        break
                res[c]=d[k]
            else:
                res[k]=d[k]
        return res
            

class Profile(com_lgvx4400.Profile):

    serialsname='lgvx6000'

    def __init__(self):
        com_lgvx4400.Profile.__init__(self)
