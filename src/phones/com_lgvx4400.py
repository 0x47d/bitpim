### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Communicate with the LG VX4400 cell phone"""

# standard modules
import re
import time
import cStringIO
import sha

# my modules
import common
import copy
import p_lgvx4400
import com_brew
import com_phone
import com_lg
import prototypes



numbertypetab=( 'home', 'home2', 'office', 'office2', 'cell', 'cell2',
                    'pager', 'fax', 'fax2', 'none' )

        
class Phone(com_phone.Phone,com_brew.BrewProtocol,com_lg.LGPhonebook):
    "Talk to the LG VX4400 cell phone"

    desc="LG-VX4400"
    wallpaperindexfilename="dloadindex/brewImageIndex.map"
    ringerindexfilename="dloadindex/brewRingerIndex.map"
    protocolclass=p_lgvx4400
    serialsname='lgvx4400'

    imagelocations=(
        # offset, index file, files location, type, maximumentries
        ( 10, "dloadindex/brewImageIndex.map", "brew/shared", "images", 30),
        )

    ringtonelocations=(
        # offset, index file, files location, type, maximumentries
        ( 50, "dloadindex/brewRingerIndex.map", "user/sound/ringer", "ringers", 30),
        )

    builtinimages=('Balloons', 'Soccer', 'Basketball', 'Bird',
                   'Sunflower', 'Puppy', 'Mountain House', 'Beach')

    builtinringtones=( 'Ring 1', 'Ring 2', 'Ring 3', 'Ring 4', 'Ring 5',
                       'Ring 6', 'Voices of Spring', 'Twinkle Twinkle',
                       'The Toreadors', 'Badinerie', 'The Spring', 'Liberty Bell',
                       'Trumpet Concerto', 'Eine Kleine', 'Silken Ladder', 'Nocturne',
                       'Csikos Post', 'Turkish March', 'Mozart Aria', 'La Traviata',
                       'Rag Time', 'Radetzky March', 'Can-Can', 'Sabre Dance', 'Magic Flute',
                       'Carmen' )

    
    def __init__(self, logtarget, commport):
        "Calls all the constructors and sets initial modes"
        com_phone.Phone.__init__(self, logtarget, commport)
	com_brew.BrewProtocol.__init__(self)
        com_lg.LGPhonebook.__init__(self)
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
        self.log("Retrieving fundamental phone information")
        self.log("Phone serial number")
        results['uniqueserial']=sha.new(self.getfilecontents("nvm/$SYS.ESN")).hexdigest()
        # now read groups
        self.log("Reading group information")
        buf=prototypes.buffer(self.getfilecontents("pim/pbgroup.dat"))
        g=self.protocolclass.pbgroups()
        g.readfrombuffer(buf)
        self.logdata("Groups read", buf.getdata(), g)
        groups={}
        for i in range(len(g.groups)):
            if len(g.groups[i].name): # sometimes have zero length names
                groups[i]={ 'icon': g.groups[i].icon, 'name': g.groups[i].name }
        results['groups']=groups
        self.getwallpaperindices(results)
        self.getringtoneindices(results)
        self.log("Fundamentals retrieved")
        return results

    def getmediaindex(self, builtins, maps, results, key):
        """Gets the media (wallpaper/ringtone) index

        @param builtins: the builtin liston the phone
        @param results: places results in this dict
        @param maps: the list of index files and locations
        @param key: key to place results in
        """

        self.log("Reading "+key)
        media={}

        # builtins
        c=1
        for name in builtins:
            media[c]={'name': name, 'origin': 'builtin' }
            c+=1

        # the maps
        for offset,indexfile,location,type,maxentries in maps:
            if type=="camera": break
            index=self.getindex(indexfile)
            for i in index:
                media[i+offset]={'name': index[i], 'origin': type}

        # camera must be last
        if type=="camera":
            # (we don't do verify on the camera since we assume it is always correct)
            index=self.getcameraindex()
            for i in index:
                media[i+offset]=index[i]

        results[key]=media
        return media

    def getwallpaperindices(self, results):
        return self.getmediaindex(self.builtinimages, self.imagelocations, results, 'wallpaper-index')

    def getringtoneindices(self, results):
        return self.getmediaindex(self.builtinringtones, self.ringtonelocations, results, 'ringtone-index')

    def getphonebook(self,result):
        """Reads the phonebook data.  The L{getfundamentals} information will
        already be in result."""
        pbook={}
        # Bug in the phone.  if you repeatedly read the phone book it starts
        # returning a random number as the number of entries.  We get around
        # this by switching into brew mode which clears that.
        self.mode=self.MODENONE
        self.setmode(self.MODEBREW)
        self.log("Reading number of phonebook entries")
        req=self.protocolclass.pbinforequest()
        res=self.sendpbcommand(req, self.protocolclass.pbinforesponse)
        numentries=res.numentries
        self.log("There are %d entries" % (numentries,))
        for i in range(0, numentries):
            ### Read current entry
            req=self.protocolclass.pbreadentryrequest()
            res=self.sendpbcommand(req, self.protocolclass.pbreadentryresponse)
            self.log("Read entry "+`i`+" - "+res.entry.name)
            entry=self.extractphonebookentry(res.entry, result)
            pbook[i]=entry 
            self.progress(i, numentries, res.entry.name)
            #### Advance to next entry
            req=self.protocolclass.pbnextentryrequest()
            self.sendpbcommand(req, self.protocolclass.pbnextentryresponse)

        self.progress(numentries, numentries, "Phone book read completed")
        result['phonebook']=pbook
        cats=[]
        for i in result['groups']:
            if result['groups'][i]['name']!='No Group':
                cats.append(result['groups'][i]['name'])
        result['categories']=cats
        print "returning keys",result.keys()
        return pbook

    def savegroups(self, data):
        groups=data['groups']
        keys=groups.keys()
        keys.sort()

        g=self.protocolclass.pbgroups()
        for k in keys:
            e=self.protocolclass.pbgroup()
            e.icon=groups[k]['icon']
            e.name=groups[k]['name']
            g.groups.append(e)
        buffer=prototypes.buffer()
        g.writetobuffer(buffer)
        self.logdata("New group file", buffer.getvalue(), g)
        self.writefile("pim/pbgroup.dat", buffer.getvalue())

    def savephonebook(self, data):
        self.savegroups(data)
        # To write the phone book, we scan through all existing entries
        # and record their record number and serials.
        # We then delete any entries that aren't in data
        # We then write out our records, usng overwrite or append
        # commands as necessary
        serialupdates=[]
        existingpbook={} # keep track of the phonebook that is on the phone
        self.mode=self.MODENONE
        self.setmode(self.MODEBREW) # see note in getphonebook() for why this is necessary
        self.setmode(self.MODEPHONEBOOK)
        # similar loop to reading
        req=self.protocolclass.pbinforequest()
        res=self.sendpbcommand(req, self.protocolclass.pbinforesponse)
        numexistingentries=res.numentries
        progressmax=numexistingentries+len(data['phonebook'].keys())
        progresscur=0
        self.log("There are %d existing entries" % (numexistingentries,))
        for i in range(0, numexistingentries):
            ### Read current entry
            req=self.protocolclass.pbreadentryrequest()
            res=self.sendpbcommand(req, self.protocolclass.pbreadentryresponse)
            
            entry={ 'number':  res.entry.entrynumber, 'serial1':  res.entry.serial1,
                    'serial2': res.entry.serial2, 'name': res.entry.name}
            assert entry['serial1']==entry['serial2'] # always the same
            self.log("Reading entry "+`i`+" - "+entry['name'])            
            existingpbook[i]=entry 
            self.progress(progresscur, progressmax, "existing "+entry['name'])
            #### Advance to next entry
            req=self.protocolclass.pbnextentryrequest()
            self.sendpbcommand(req, self.protocolclass.pbnextentryresponse)
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
            req=self.protocolclass.pbdeleteentryrequest()
            req.serial1=ii['serial1']
            req.serial2=ii['serial2']
            req.entrynumber=ii['number']
            self.sendpbcommand(req, self.protocolclass.pbdeleteentryresponse)
            self.progress(progresscur, progressmax, "Deleting "+ii['name'])
            # also remove them from existingpbook
            del existingpbook[i]

        # counter to keep track of record number (otherwise appends don't work)
        counter=0
        # Now rewrite out existing entries
        keys=existingpbook.keys()
        existingserials=[]
        keys.sort()  # do in same order as existingpbook
        for i in keys:
            progresscur+=1
            ii=pbook[self._findserial(existingpbook[i]['serial1'], pbook)]
            self.log("Writing entry "+`i`+" - "+ii['name'])
            self.progress(progresscur, progressmax, "Writing "+ii['name'])
            entry=self.makeentry(counter, ii, data)
            counter+=1
            existingserials.append(existingpbook[i]['serial1'])
            req=self.protocolclass.pbupdateentryrequest()
            req.entry=entry
            res=self.sendpbcommand(req, self.protocolclass.pbupdateentryresponse)
            serialupdates.append( ( ii["bitpimserial"],
                                    {'sourcetype': self.serialsname, 'serial1': res.serial1, 'serial2': res.serial1,
                                     'sourceuniqueid': data['uniqueserial']})
                                  )
            assert ii['serial1']==res.serial1 # serial should stay the same

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
            req=self.protocolclass.pbappendentryrequest()
            req.entry=entry
            res=self.sendpbcommand(req, self.protocolclass.pbappendentryresponse)
            serialupdates.append( ( ii["bitpimserial"],
                                     {'sourcetype': self.serialsname, 'serial1': res.newserial, 'serial2': res.newserial,
                                     'sourceuniqueid': data['uniqueserial']})
                                  )

        data["serialupdates"]=serialupdates



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
        buf=prototypes.buffer(self.getfilecontents("sch/schexception.dat"))
        ex=self.protocolclass.scheduleexceptionfile()
        ex.readfrombuffer(buf)
        self.logdata("Calendar exceptions", buf.getdata(), ex)
        exceptions={}
        for i in ex.items:
            try:
                exceptions[i.pos].append( (i.year,i.month,i.day) )
            except KeyError:
                exceptions[i.pos]=[ (i.year,i.month,i.day) ]

        # Now read schedule
        buf=prototypes.buffer(self.getfilecontents("sch/schedule.dat"))
        sc=self.protocolclass.schedulefile()
        sc.readfrombuffer(buf)
        self.logdata("Calendar", buf.getdata(), sc)
        for event in sc.events:
            entry={}
            entry['pos']=event.pos
            if entry['pos']==-1: continue # blanked entry
            # normal fields
            for field in 'start','end','daybitmap','changeserial','snoozedelay','ringtone','description':
                entry[field]=getattr(event,field)
            # calculated ones
            entry['repeat']=self._calrepeatvalues[event.repeat]
            min=event.alarmminutes
            hour=event.alarmhours
            if min==100 or hour==100:
                entry['alarm']=None # no alarm set
            else:
                entry['alarm']=hour*60+min
            # Exceptions
            if exceptions.has_key(event.pos):
                entry['exceptions']=exceptions[event.pos]
            res[event.pos]=entry

        assert sc.numactiveitems==len(res)
        result['calendar']=res
        return result

    def savecalendar(self, dict, merge):
        # ::TODO:: obey merge param
        # what will be written to the files
        eventsf=self.protocolclass.schedulefile()
        exceptionsf=self.protocolclass.scheduleexceptionfile()

        # what are we working with
        cal=dict['calendar']
        newcal={}
        keys=cal.keys()
        keys.sort()

        # number of entries
        eventsf.numactiveitems=len(keys)
        
        # play with each entry
        for k in keys:
            # entry is what we will return to user
            entry=cal[k]
            data=self.protocolclass.scheduleevent()
            data.pos=eventsf.packetsize()
            entry['pos']=data.pos
            # simple copy of these fields
            for field in 'start', 'end', 'daybitmap', 'changeserial', 'snoozedelay','ringtone','description':
                setattr(data,field,entry[field])
            # And now the special ones
            repeat=None
            for k,v in self._calrepeatvalues.items():
                if entry['repeat']==v:
                    repeat=k
                    break
            assert repeat is not None
            data.repeat=repeat
            # alarm 100 indicates not set
            if entry['alarm'] is None or entry['alarm']<0:
                hour=100
                min=100
            else:
                assert entry['alarm']>=0
                hour=entry['alarm']/60
                min=entry['alarm']%60
            data.alarmminutes=min
            data.alarmhours=hour

            # update exceptions if needbe
            if entry.has_key('exceptions'):
                for y,m,d in entry['exceptions']:
                    de=self.protocolclass.scheduleexception()
                    de.pos=data.pos
                    de.day=d
                    de.month=m
                    de.year=y
                    exceptionsf.items.append(de)

            # put entry in nice shiny new dict we are building
            entry=copy.copy(entry)
            newcal[data.pos]=entry
            eventsf.events.append(data)

        # scribble everything out
        buf=prototypes.buffer()
        eventsf.writetobuffer(buf)
        self.logdata("Writing calendar", buf.getvalue(), eventsf)
        self.writefile("sch/schedule.dat", buf.getvalue())
        buf=prototypes.buffer()
        exceptionsf.writetobuffer(buf)
        self.logdata("Writing calendar exceptions", buf.getvalue(), exceptionsf)
        self.writefile("sch/schexception.dat", buf.getvalue())

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
    

    def getindex(self, indexfile):
        "Read an index file"
        index={}
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
                index[i.index]=i.name
        return index
        
    def getmedia(self, maps, result, key):
        media={}
        # the maps
        for offset,indexfile,location,type,maxentries in maps:
            if type=="camera": break
            index=self.getindex(indexfile)
            for i in index:
                try:
                    media[index[i]]=self.getfilecontents(location+"/"+index[i])
                except com_brew.BrewNoSuchFileException:
                    self.log("It was in the index, but not on the filesystem")
                    
        if type=="camera":
            # now for the camera stuff
            index=self.getcameraindex()
            for i in index:
                try:
                    media[index[i]['name']]=self.getfilecontents("cam/pic%02d.jpg" % (i,))
                except com_brew.BrewNoSuchFileException:
                    self.log("It was in the index, but not on the filesystem")
                    
        result[key]=media
        return result

    def getwallpapers(self, result):
        return self.getmedia(self.imagelocations, result, 'wallpapers')

    def getringtones(self, result):
        return self.getmedia(self.ringtonelocations, result, 'ringtone')

    def savewallpapers(self, results, merge):
        return self.savemedia('wallpapers', 'wallpaper-index', self.imagelocations, results, merge, self.getwallpaperindices)

    def saveringtones(self, results, merge):
        return self.savemedia('ringtone', 'ringtone-index', self.ringtonelocations, results, merge, self.getringtoneindices)

    def savemedia(self, mediakey, mediaindexkey, maps, results, merge, reindexfunction):
        """Actually saves out the media

        @param mediakey: key of the media (eg 'wallpapers' or 'ringtones')
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
                
        # Note that we don't write to the camera area

        # tidy up - reread indices
        del results[mediakey] # done with it
        reindexfunction(results)
        return results


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

    def extractphonebookentry(self, entry, fundamentals):
        """Return a phonebook entry in BitPim format.  This is called from getphonebook."""
        res={}
        # serials
        res['serials']=[ {'sourcetype': self.serialsname, 'serial1': entry.serial1, 'serial2': entry.serial2,
                          'sourceuniqueid': fundamentals['uniqueserial']} ] 
        # only one name
        res['names']=[ {'full': entry.name} ]
        # only one category
        cat=fundamentals['groups'].get(entry.group, {'name': "No Group"})['name']
        if cat!="No Group":
            res['categories']=[ {'category': cat} ]
        # emails
        res['emails']=[]
        for i in entry.emails:
            if len(i.email):
                res['emails'].append( {'email': i.email} )
        if not len(res['emails']): del res['emails'] # it was empty
        # urls
        if len(entry.url):
            res['urls']=[ {'url': entry.url} ]
        # private
        if entry.secret:
            # we only supply secret if it is true
            res['flags']=[ {'secret': entry.secret } ]
        # memos
        if len(entry.memo):
            res['memos']=[ {'memo': entry.memo } ]
        # wallpapers
        if entry.wallpaper>0:
            try:
                paper=fundamentals['wallpaper-index'][entry.wallpaper]['name']
                res['wallpapers']=[ {'wallpaper': paper, 'use': 'call'} ]                
            except:
                print "can't find wallpaper for index",entry.wallpaper
                pass
            
        # ringtones
        res['ringtones']=[]
        if entry.ringtone>0:
            try:
                tone=fundamentals['ringtone-index'][entry.ringtone]['name']
                res['ringtones'].append({'ringtone': tone, 'use': 'call'})
            except:
                print "can't find ringtone for index",entry.ringtone
        if entry.msgringtone>0:
            try:
                tone=fundamentals['ringtone-index'][entry.msgringtone]['name']
                res['ringtones'].append({'ringtone': tone, 'use': 'message'})
            except:
                print "can't find ringtone for index",entry.msgringtone
        if len(res['ringtones'])==0:
            del res['ringtones']
                    
        # numbers
        res['numbers']=[]
        for i in range(entry.numberofphonenumbers):
            num=entry.numbers[i].number
            type=entry.numbertypes[i].numbertype
            if len(num):
                t=numbertypetab[type]
                if t[-1]=='2':
                    t=t[:-1]
                res['numbers'].append({'number': num, 'type': t})
        return res

    def _findmediainindex(self, index, name, pbentryname, type):
        if name is None:
            return 0
        for i in index:
            if index[i]['name']==name:
                return i
        self.log("%s: Unable to find %s %s in the index. Setting to default." % (pbentryname, type, name))
        return 0
                    
    def makeentry(self, counter, entry, dict):
        e=self.protocolclass.pbentry()
        e.entrynumber=counter
        
        for k in entry:
            # special treatment for lists
            if k=='emails' or k=='numbers' or k=='numbertypes':
                l=getattr(e,k)
                for item in entry[k]:
                    l.append(item)
            elif k=='ringtone':
                e.ringtone=self._findmediainindex(dict['ringtone-index'], entry['ringtone'], entry['name'], 'ringtone')
            elif k=='msgringtone':
                e.msgringtone=self._findmediainindex(dict['ringtone-index'], entry['msgringtone'], entry['name'], 'message ringtone')
            elif k=='wallpaper':
                e.wallpaper=self._findmediainindex(dict['wallpaper-index'], entry['wallpaper'], entry['name'], 'wallpaper')
            else:
                # everything else we just set
                setattr(e,k,entry[k])

        return e


def phonize(str):
    """Convert the phone number into something the phone understands
    
    All digits, P, T, * and # are kept, everything else is removed"""
    return re.sub("[^0-9PT#*]", "", str)

    

class Profile:
    serialsname='lgvx4400'

    def __init__(self):
        pass

    def makeone(self, list, default):
        "Returns one item long list"
        if len(list)==0:
            return default
        assert len(list)==1
        return list[0]

    def filllist(self, list, numitems, blank):
        "makes list numitems long appending blank to get there"
        l=list[:]
        for dummy in range(len(l),numitems):
            l.append(blank)
        return l

    def _getgroup(self, name, groups):
        for key in groups:
            if groups[key]['name']==name:
                return key,groups[key]
        return None,None
        

    def normalisegroups(self, helper, data):
        "Assigns groups based on category data"

        # find the 9 most popular categories
        freq={}
        for entry in data['phonebook']:
            e=data['phonebook'][entry]
            for cat in e.get('categories', []):
               n=cat['category'][:22] # truncate
               if n != "No Group":
                   freq[n]=1+freq.get(n,0)

        freq=[(count,value) for value,count in freq.items()]
        freq.sort()
        freq.reverse() # most popular first
        if len(freq)>9:
            print "too many groups",freq
            print "removing",freq[9:] # ::TODO:: log this to helper
            freq=freq[:9] # clip to 9 items

        # name only
        freq=[value for count,value in freq]

        # uniqify (since some may have been different after char 22)
        u={}
        for f in freq: u[f]=1
        freq=u.keys()

        # if less than 9 entries, add some back in, using earliest entries first (most likely to be most important to the user)
        keys=data['groups'].keys()
        keys.sort()
        for k in keys:
            if k and len(freq)<9: # ignore key 0 which is 'No Group'
                name=data['groups'][k]['name']
                if name not in freq:
                    freq.append(name)

        # alpha sort
        freq.sort()

        # newgroups
        newgroups={}

        # put in No group
        newgroups[0]={'name': 'No Group', 'icon': 0}

        # populate
        for name in freq:
            # existing entries remain unchanged
            key,value=self._getgroup(name, data['groups'])
            if key is not None and key!=0:
                newgroups[key]=value
        # new entries get whatever numbers are free
        for name in freq:
            key,value=self._getgroup(name, newgroups)
            if key is None or key==0:
                for key in range(1,10):
                    if key not in newgroups:
                        newgroups[key]={'name': name, 'icon': 1}
                        break
                       
        # yay, done
        print data['groups']
        print newgroups
        data['groups']=newgroups

    def convertphonebooktophone(self, helper, data):
        "Converts the data to what will be used by the phone"
        results={}

        self.normalisegroups(helper, data)

        for pbentry in data['phonebook']:
            e={} # entry out
            entry=data['phonebook'][pbentry] # entry in
            try:
                e['name']=helper.getfullname(entry.get('names', []),1,1,22)[0]

                cat=self.makeone(helper.getcategory(entry.get('categories', []),0,1,22), None)
                if cat is None:
                    e['group']=0
                else:
                    key,value=self._getgroup(cat, data['groups'])
                    if key is not None:
                        e['group']=key
                    else:
                        # sorry no space for this category
                        e['group']=0

                e['emails']=self.filllist(helper.getemails(entry.get('emails', []) ,0,3,48), 3, "")

                e['url']=self.makeone(helper.geturls(entry.get('urls', []), 0,1,48), "")

                e['memo']=self.makeone(helper.getmemos(entry.get('memos', []), 0, 1, 32), "")

                numbers=helper.getnumbers(entry.get('numbers', []),1,5)
                e['numbertypes']=[]
                e['numbers']=[]
                for num in numbers:
                    number=phonize(num['number'])
                    if len(number)==0:
                        # no actual digits in the number
                        continue
                    e['numbers'].append(number)
                    type=num['type']
                    for i,t in zip(range(100),numbertypetab):
                        if type==t:
                            # some voodoo to ensure the second home becomes home2
                            if i in e['numbertypes'] and t[-1]!='2':
                                type+='2'
                                continue
                            e['numbertypes'].append(i)
                            break
                        if t=='none': # conveniently last entry
                            e['numbertypes'].append(i)
                            break
                if len(e['numbers'])==0:
                    raise helper.ConversionFailed("The phone numbers didn't have any digits for this entry")

                e['numbertypes']=self.filllist(e['numbertypes'], 5, 0)
                e['numbers']=self.filllist(e['numbers'], 5, "")

                serial1=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial1', 0)
                serial2=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial2', serial1)

                e['serial1']=serial1
                e['serial2']=serial2
                for ss in entry["serials"]:
                    if ss["sourcetype"]=="bitpim":
                        e['bitpimserial']=ss
                assert e['bitpimserial']
                
                e['ringtone']=helper.getringtone(entry.get('ringtones', []), 'call', None)
                e['msgringtone']=helper.getringtone(entry.get('ringtones', []), 'message', None)
                e['wallpaper']=helper.getwallpaper(entry.get('wallpapers', []), 'call', None)

                e['secret']=helper.getflag(entry.get('flags',[]), 'secret', False)

                results[pbentry]=e
                
            except helper.ConversionFailed:
                continue

        data['phonebook']=results
        return data
