### BITPIM
###
### Copyright (C) 2003-2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Talk to the Sanyo SCP-4900 cell phone"""

# my modules
import time
import common
import p_sanyo4900
import com_brew
import com_phone
import com_sanyo
import prototypes


class Phone(com_sanyo.Phone):
    "Talk to the Sanyo SCP-4900 cell phone"

    desc="SCP-4900"

    protocolclass=p_sanyo4900
    serialsname='scp4900'

    builtinringtones=( 'None', 'Vibrate', 'Ringer & Voice', '', '', '', '', '', '', 
                       'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5',
                       '', '', '', '', '', '', '', '', '', '', '', '', '', '',
                       '', 'La Bamba', 'Foster Dreamer', 'Schubert March',
                       'Mozart Eine Kleine', 'Debussey Arabesq', 'Nedelka',
                       'Brahms Hungarian', 'Star Spangled Banner', 'Rodeo',
                       'Birds', 'Toy Box' )
                      
    calendar_defaultringtone=0

    def __init__(self, logtarget, commport):
        com_sanyo.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE


    def savewallpapers(self, results, merge):
        print "savewallpapers ",results['wallpaper-index']
        return self.savemedia('wallpapers', 'wallpaper-index', 'images', results, merge)
                              
    # Note:  Was able to write 6 ringers to phone.  If there are ringers
    # already on phone, this counts against the 6.  Don't know yet if the limit
    # is a count limit or a byte limit.
    def saveringtones(self, results, merge):
        return self.savemedia('ringtone', 'ringtone-index', 'ringers', results, merge)
    
    def savemedia(self, mediakey, mediaindexkey, mediatype, results, merge):
        """Actually saves out the media

        @param mediakey: key of the media (eg 'wallpapers' or 'ringtones')
                         Index of media in wallpaper or ringer tab
        @param mediaindexkey:  index key (eg 'wallpaper-index')
                         Index of media on the phone
        @param results: results dict
        """
        wp=results[mediakey].copy()
        wpi=results[mediaindexkey].copy()
        # remove builtins
        for k in wpi.keys():
            if wpi[k]['origin']=='builtin':
                del wpi[k]

        # Don't care about origin since there is only one place to put images
#        print wp
        init={}
        init[mediatype]={}
        for k in wpi.keys():
            if wpi[k]['origin']==mediatype:
                index=k
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
        
        print "C",init.keys()    
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
                             
        index=init[mediatype]

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
                        if stripext(entry['name']) in dirlisting:
                            dellist.append(entry['name'])
                        else:
                            self.log("%s in %s index but not filesystem" % (entry['name'], type))

        maxentries=10

        #  slurp up any from wp we can take
        while len(index)<maxentries and len(wp):
            idx=-1
            while idx in index:
                idx-=1
            k=wp.keys()[0]
            index[idx]=wp[k]
            del wp[k]
        # normalise indices
        # index=self._normaliseindices(index)  # hey look, I called a function!
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
                    
        # write out the content

        ####  index is dict, key is index number, value is dict
        ####  value['name'] = filename
        ####  value['data'] is contents

        for key in index:
            efile=index[key]['name']
            print "Writing "+efile
            content=index[key]['data']
            if content is None:
                continue # in theory we could rewrite .desc file in case index number has changed
            # dirname=stripext(efile)

            self.writesanyofile(efile, content)

        # did we have too many
        if len(wp):
            for k in wp:
                self.log("Unable to put %s on the phone as there weren't any spare index entries" % (wp[k]['name'],))
                
        # Note that we don't write to the camera area

        # tidy up - reread indices
        # del results[mediakey] # done with it
        # reindexfunction(results)
        return results
        

    # Error codes
    # 0x6d on sendfileterminator
    # 0x65 not in sync mode on sendfilename
    # 0x6a on sendfilefragment when buffer full, for ringers  6 max?
    # 0x6c on sendfilefragment when full of pictures         11 max?
    # 0x69 on sendfilefragment.  Invalid file type.  PNG works, jpg, bmp don't
    # 0x68 on sendfilefragment.  Bad picture size
    def writesanyofile(self, name, contents):
        start=time.time()
        self.log("Writing file '"+name+"' bytes "+`len(contents)`)
        desc="Writing "+name

	req=self.protocolclass.sanyosendfilename()
	req.filename=name
        res=self.sendpbcommand(req, self.protocolclass.sanyosendfileresponse, returnerror=True)
        if 'errorcode' in res.getfields():
            if res.errorcode==0x65:
                self.alert("Please put your phone into PC Sync Mode", False)
            else:
                raise SanyoCommandException(res.errorcode)
            # Wait about 5 minutes before giving up
            waitcount=300
            while waitcount>0:
                time.sleep(1.0)
                res=self.sendpbcommand(req, self.protocolclass.sanyosendfileresponse, returnerror=True)
                if not 'errorcode' in res.getfields():
                    break
                waitcount-=1
            if waitcount==0:
                raise SanyoCommandException(res.errorcode)
                
        req=self.protocolclass.sanyosendfilesize()
        req.filesize=len(contents)
        self.sendpbcommand(req, self.protocolclass.sanyosendfileresponse)

        req=self.protocolclass.sanyosendfilefragment()
        packetsize=req.payloadsize

        time.sleep(1.0)
        offset=0
        count=0
        numblocks=len(contents)/packetsize+1
        for offset in range(0, len(contents), packetsize):
            count+=1
            if count % 5==0:
                self.progress(count,numblocks,desc)
            req.header.command=offset
            req.data=contents[offset:min(offset+packetsize,len(contents))]
            # self.sendpbcommand(req, self.protocolclass.sanyosendfileresponse, numsendretry=2)
            self.sendpbcommand(req, self.protocolclass.sanyosendfileresponse, writemode=True)
                
        req=self.protocolclass.sanyosendfileterminator()
        res=self.sendpbcommand(req, self.protocolclass.sanyosendfileresponse, writemode=True)
        # The returned value in res.header.faset may mean something
        
        end=time.time()
        if end-start>3:
            self.log("Wrote "+`len(contents)`+" bytes at "+`int(len(contents)/(end-start))`+" bytes/second")


class Profile(com_sanyo.Profile):

    protocolclass=p_sanyo4900
    serialsname='scp4900'

        
    # WALLPAPER_WIDTH=112
    # WALLPAPER_HEIGHT=120
    WALLPAPER_WIDTH=90
    WALLPAPER_HEIGHT=96
    MAX_WALLPAPER_BASENAME_LENGTH=19
    WALLPAPER_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 ."
    WALLPAPER_CONVERT_FORMAT="png"
    
    MAX_RINGTONE_BASENAME_LENGTH=19
    RINGTONE_FILENAME_CHARS="abcdefghijklmnopqrstuvwyz0123456789 ."
       
    _supportedsyncs=(
        ('phonebook', 'read', None),  # all phonebook reading
        ('calendar', 'read', None),   # all calendar reading
        ('phonebook', 'write', 'OVERWRITE'),  # only overwriting phonebook
        ('calendar', 'write', 'OVERWRITE'),   # only overwriting calendar
        ('wallpaper', 'write', 'OVERWRITE'),
        ('ringtone', 'write', 'OVERWRITE'),
        )


    def __init__(self):
        com_sanyo.Profile.__init__(self)

