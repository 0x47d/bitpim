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
        # wallpaper index
        self.log("Reading wallpaper indices")
        results['wallpaper-index']=self.getindex(self.wallpaperindexfilename)
        # ringtone index
        self.log("Reading ringtone indices")
        results['ringtone-index']=self.getindex(self.ringerindexfilename)
        self.log("Fundamentals retrieved")
        return results
        
    def getphonebook(self,result):
        """Reads the phonebook data.  The L{getfundamentals} informatation will
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
        newphonebook={}
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
            newphonebook[counter-1]=self.extractphonebookentry(entry, data)
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
            entry.serial1=res.newserial
            entry.serial2=res.newserial
            newphonebook[counter-1]=self.extractphonebookentry(entry, data)

        data['phonebook']=newphonebook


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
    
    def writeindex(self, indexfile, index, maxentries=30):
        keys=index.keys()
        keys.sort()
        writing=min(len(keys), maxentries)
        if len(keys)>maxentries:
            self.log("Warning:  You have too many entries (%d) for index %s.  Only writing out first %d." % (len(keys), indexfile, writing))
        ifile=self.protocolclass.indexfile()
        ifile.numactiveitems=writing
        for i in keys[:writing]:
            entry=self.protocolclass.indexentry()
            entry.index=i
            entry.name=index[i]
            ifile.items.append(entry)
        buf=prototypes.buffer()
        ifile.writetobuffer(buf)
        self.logdata("Writing %d index entries to %s" % (writing,indexfile), buf.getvalue(), ifile)
        self.writefile(indexfile, buf.getvalue())

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
        for i in range(g.maxitems):
            if g.items[i].index!=0xffff:
                index[g.items[i].index]=g.items[i].name
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
            except com_brew.BrewNoSuchFileException:
                self.log("It was in the index, but not on the filesystem")
        result[datakey]=stuff

        return result

    def getwallpapers(self, result):
        return self.getprettystuff(result, "brew/shared", "wallpaper", self.wallpaperindexfilename,
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
        return self.saveprettystuff(data, "brew/shared", self.wallpaperindexfilename,
                                    'wallpaper', 'wallpaper-index', merge)
        
    def saveringtones(self,data, merge):
        return self.saveprettystuff(data, "user/sound/ringer", self.ringerindexfilename,
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
        return self.getprettystuff(result, "user/sound/ringer", "ringtone", self.ringerindexfilename,
                                   "ringtone-index")

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
        # ringtones
        res['ringtones']=[ {'ringtone': entry.ringtone, 'use': 'call'},
                           {'ringtone': entry.msgringtone, 'use': 'message' } ] # ::TODO:: turn these into strings
        # private
        res['flags']=[ {'secret': entry.secret } ]
        # memos
        if len(entry.memo):
            res['memos']=[ {'memo': entry.memo } ]
        # wallpapers
        wp=entry.wallpaper
        paper=None
        # 0-9 are builtin wallpapers (except phone doesn't let you select them anyway)
        if wp>=10:
            try:
                paper=fundamentals['wallpaper-index'][wp-10]
            except:
                pass

        if paper is not None:
            res['wallpapers']=[ {'wallpaper': paper, 'use': 'call'} ]
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
                    
    def makeentry(self, counter, entry, dict):
        # dict is unused at moment, will be used later to convert string ringtone/wallpaper to numbers
        e=self.protocolclass.pbentry()
        e.entrynumber=counter
        
        for k in entry:
            # special treatment for lists
            if k=='emails' or k=='numbers' or k=='numbertypes':
                l=getattr(e,k)
                for item in entry[k]:
                    if k=='numbers':
                        item=self.phonize(item)
                    l.append(item)
                continue
            # everything else we just set
            setattr(e,k,entry[k])

        return e

            
    def phonize(self, str):
        """Convert the phone number into something the phone understands

        All digits, P, T, * and # are kept, everything else is removed"""
        return re.sub("[^0-9PT#*]", "", str)

    
    tonetab=( 'Default', 'Ring 1', 'Ring 2', 'Ring 3', 'Ring 4', 'Ring 5',
              'Ring 6', 'Voices of Spring', 'Twinkle Twinkle',
              'The Toreadors', 'Badinerie', 'The Spring',
              'Liberty Bell', 'Trumpet Concerto', 'Eine Kleine',
              'Silken Ladder', 'Nocturne', 'Csikos Post', 'Turkish March',
              'Mozart Aria', 'La Traviata', 'Rag Time', 'Radetzky March',
              'Can-Can', 'Sabre Dance', 'Magic Flute', 'Carmen' )

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
            if key is not None:
                newgroups[key]=value
        # new entries get whatever numbers are free
        for name in freq:
            key,value=self._getgroup(name, newgroups)
            if key is None:
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
                    e['numbers'].append(num['number'])
                e['numbertypes']=self.filllist(e['numbertypes'], 5, 0)
                e['numbers']=self.filllist(e['numbers'], 5, "")

                serial1=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial1', 0)
                serial2=helper.getserial(entry.get('serials', []), self.serialsname, data['uniqueserial'], 'serial2', serial1)

                e['serial1']=serial1
                e['serial2']=serial2
                
                # e['ringtone']=helper.getringtone(entry.get('ringtones', []), 'call', 0)
                # e['msgringtone']=helper.getringtone(entry.get('ringtones', []), 'message', 0)
                # e['wallpaper']=helper.getwallpaper(entry.get('wallpapers', []), 'call', 0)
                e['ringtone']=e['msgringtone']=e['wallpaper']=0

                e['secret']=helper.getflag(entry.get('flags',[]), 'secret', False)

                results[pbentry]=e
                
            except helper.ConversionFailed:
                continue

        data['phonebook']=results
        return data
