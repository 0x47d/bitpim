### BITPIM
###
### Copyright (C) 2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Common code for Sanyo Media transfers"""

# standard modules

import wx

# BitPim Modules
import com_sanyo
import com_brew
import com_phone
import p_sanyomedia
import prototypes

class SanyoMedia:
    "Download and upload media (ringers/wallpaper) from Sanyo Phones"

    NUM_MEDIA_DIRECTORIES=4
    
    def __init__(self, logtarget, commport):
        pass

    def getmediaindex(self, builtins, maps, results, key):
        media=com_sanyo.SanyoPhonebook.getmediaindex(self, builtins, maps, results, key)
        # the maps
        type=''
        for offset,indexfile,location,type,maxentries in maps:
            if type=="camera": break
            index=self.getindex(indexfile)
            for i in index:
                media[i+offset]={'name': index[i], 'origin': type}

        # camera must be last
        if type=="camera":
            index=self.getcameraindex()
            for i in index:
                media[i+offset]=index[i]

        results[key]=media
        return media

    def getwallpapers(self, results):
        # Test code to list files on phone
        for idir in range(1,self.NUM_MEDIA_DIRECTORIES):
            req=self.protocolclass.sanyochangedir()
            req.dirindex=idir

            res=self.sendpbcommand(req, self.protocolclass.sanyomediaresponse)

            req=self.protocolclass.sanyonumpicsrequest()
            res=self.sendpbcommand(req, self.protocolclass.sanyonumpicsresponse)
            self.log("Directory "+`idir`+", File Count="+`res.count`)
            nfiles=res.count
            try:
                os.makedirs(`idir`)
            except:
                pass
            for ifile in range(nfiles):
                req=self.protocolclass.sanyomediafilenamerequest()
                req.index=ifile
                res=self.sendpbcommand(req, self.protocolclass.sanyomediafilenameresponse)
                self.log(res.filename+": "+`res.num1`+" "+`res.num2`+" "+`res.num3`)
                fout=open(`idir`+"/"+res.filename, "wb")
                more=1
                while more==1:
                    req=self.protocolclass.sanyomediafragmentrequest()
                    req.fileindex=ifile
                    res=self.sendpbcommand(req,self.protocolclass.sanyomediafragmentresponse)
                    fout.write(res.data[0:res.length])
                    fout.flush()
                    more=res.more
                fout.close()
                
        return
                     
            
        req=self.protocolclass.sanyomediaheader()
        req.command=0x10
        req.subcommand=0
        self.sendpbcommand(req, self.protocolclass.sanyomediaresponse, writemode=True)
        req.command=0x13
        req.subcommand=0
        self.sendpbcommand(req, self.protocolclass.sanyomediaresponse, writemode=True)

        req=self.protocolclass.sanyomediafilename()
        req.filename="testimage.jpg"
        self.sendpbcommand(req, self.protocolclass.sanyomediaresponse, writemode=True)
    
        return 

        
