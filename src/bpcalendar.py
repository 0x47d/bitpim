#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Calendar user interface and data for bitpim.

This module has a bp prefix so it doesn't clash with the system calendar module

The format for the calendar is standardised.  It is a dict with the following
fields:

(Note: hour fields are in 24 hour format)

start:

   - (year, month, day, hour, minute) as integers
end:

   - (year, month, day, hour, minute) as integers  # if you want no end, set to the same value as start, or to the year 4000

repeat:

   - one of None, "daily", "monfri", "weekly", "monthly", "yearly"

description:

   - "String description"
   
changeserial:

   - Set to integer 1
   
snoozedelay:

   - Set to an integer number of minutes (default 0)
   
alarm:

   - how many minutes beforehand to set the alarm (use 0 for on-time, None for no alarm)
   
daybitmap:

   - default 0, it will become which days of the week weekly events happen on (eg every monday and friday)
   
ringtone:

   - index number of the ringtone for the alarm (use 0 for none - will become a string)
   
pos:

   - integer that should be the same as the dictionary key for this entry
   
exceptions:

   - (optional) A list of (year,month,day) tuples that repeats are suppressed
"""

# Standard modules
import os
import copy
import calendar
import time

# wx stuff
import wx
import wx.lib
import wx.lib.masked.textctrl
import wx.lib.intctrl

# my modules
import calendarcontrol
import common
import helpids

class Calendar(calendarcontrol.Calendar):
    """A class encapsulating the GUI and data of the calendar (all days).  A seperate L{DayViewDialog} is
    used to edit the content of one particular day."""

    CURRENTFILEVERSION=2
    
    def __init__(self, mainwindow, parent, id=-1):
        """constructor

        @type  mainwindow: gui.MainWindow
        @param mainwindow: Used to get configuration data (such as directory to save/load data.
        @param parent:     Widget acting as parent for this one
        @param id:         id
        """
        self.mainwindow=mainwindow
        self.entrycache={}
        self.entries={}
        self.repeating=[]  # nb this is stored unsorted
        self._data={} # the underlying data
        calendarcontrol.Calendar.__init__(self, parent, rows=5, id=id)
        self.dialog=DayViewDialog(self, self)
        self._nextpos=-1  # pos ids for events we make

    def getdata(self, dict):
        """Return underlying calendar data in bitpim format

        @return:   The modified dict updated with at least C{dict['calendar']}"""
        dict['calendar']=self._data
        return dict

    def updateonchange(self):
        """Called when our data has changed

        The disk, widget and display are all updated with the new data"""
        d={}
        d=self.getdata(d)
        self.populatefs(d)
        self.populate(d)
        # Brute force - assume all entries have changed
        self.RefreshAllEntries()

    def AddEntry(self, entry):
        """Adds and entry into the calendar data.

        The entries on disk are updated by this function.

        @type  entry: a dict containing all the fields.
        @param entry: an entry.  It must contain a C{pos} field. You
                     should call L{newentryfactory} to make
                     an entry that you then modify
        """
        self._data[entry['pos']]=entry
        self.updateonchange()

    def DeleteEntry(self, entry):
        """Deletes an entry from the calendar data.

        The entries on disk are updated by this function.

        @type  entry: a dict containing all the fields.
        @param entry: an entry.  It must contain a C{pos} field
                      corresponding to an existing entry
        """
        del self._data[entry['pos']]
        self.updateonchange()

    def DeleteEntryRepeat(self, entry, year, month, day):
        """Deletes a specific repeat of an entry

        See L{DeleteEntry}"""
        e=self._data[entry['pos']]
        if not e.has_key('exceptions'):
            e['exceptions']=[]
        e['exceptions'].append( (year, month, day) )
        self.updateonchange()
        
    def ChangeEntry(self, oldentry, newentry):
        """Changes an entry in the calendar data.

        The entries on disk are updated by this function.
        """
        assert oldentry['pos']==newentry['pos']
        self._data[newentry['pos']]=newentry
        self.updateonchange()

    def getentrydata(self, year, month, day):
        """return the entry objects for corresponding date

        @rtype: list"""
        # return data from cache if we have it
        res=self.entrycache.get( (year,month,day), None)
        if res is not None:
            return res
        dayofweek=calendar.weekday(year, month, day)
        dayofweek=(dayofweek+1)%7 # normalize to sunday == 0
        res=[]
        # find non-repeating entries
        fixed=self.entries.get((year,month,day), [])
        res.extend(fixed)
        # now find repeating entries
        repeats=[]
        for i in self.repeating:
            y,m,d=i['start'][0:3]
            if year<y or (year<=y and month<m) or (year<=y and month<=m and day<d):
                continue # we are before this entry
            y,m,d=i['end'][0:3]
            if year>y or (year==y and month>m) or (year==y and month==m and day>d):
                continue # we are after this entry
            # look in exception list            
            if (year,month,day) in i.get('exceptions', ()):
                continue # yup, so ignore
            repeating=i['repeat']
            if repeating=='daily':
                repeats.append(i)
                continue
            if repeating=='monfri':
                if dayofweek>0 and dayofweek<6:
                    repeats.append(i)
                continue
            if repeating=='weekly':
                if i['dayofweek']==dayofweek:
                    repeats.append(i)
                continue
            if repeating=='monthly':
                if day==i['start'][2]:
                    repeats.append(i)
                continue
            if repeating=='yearly':
                if day==i['start'][2] and month==i['start'][1]:
                    repeats.append(i)
                continue
            assert False, "Unknown repeat type \""+repeating+"\""

        res.extend(repeats)
        self.entrycache[(year,month,day)] = res
        return res
        
    def newentryfactory(self, year, month, day):
        """Returns a new 'blank' entry with default fields

        @rtype: dict"""
        res={}
        now=time.localtime()
        res['start']=(year, month, day, now.tm_hour, now.tm_min)
        res['end']=[year, month, day, now.tm_hour, now.tm_min]
        # we make end be the next hour, unless it has gone 11pm
        # in which case it is 11:59pm
        if res['end'][3]<23:
            res['end'][3]+=1
            res['end'][4]=0
        else:
            res['end'][3]=23
            res['end'][4]=59
        res['repeat']=None
        res['description']='New event'
        res['changeserial']=1
        res['snoozedelay']=0
        res['alarm']=None
        res['daybitmap']=0
        res['ringtone']=0
        res['pos']=self.allocnextpos()
        return res

    def getdaybitmap(self, start, repeat):
        if repeat!="weekly":
            return 0
        dayofweek=calendar.weekday(*(start[:3]))
        dayofweek=(dayofweek+1)%7 # normalize to sunday == 0
        return [2048,1024,512,256,128,64,32][dayofweek]

    def allocnextpos(self):
        """Allocates a unique id for a new entry

        Negative integers are used to avoid any clashes with existing
        entries from the phone.  The existing data is checked to
        ensure there is no clash.

        @rtype: int"""
        while True:
            self._nextpos,res=self._nextpos-1, self._nextpos
            if res not in self._data:
                return res
        # can't get here but pychecker cant figure that out
        assert False
        return -1
        
    def OnGetEntries(self, year, month, day):
        """return pretty printed sorted entries for date
        as required by the parent L{calendarcontrol.Calendar} for
        display in a cell"""
        res=[(i['start'][3], i['start'][4], i['description']) for i in self.getentrydata(year, month,day)]
        res.sort()
        return res

    def OnEdit(self, year, month, day):
        """Called when the user wants to edit entries for a particular day"""
        if self.dialog.dirty:
            # user is editing a field so we don't allow edit
            wx.Bell()
        else:
            self.dialog.setdate(year, month, day)
            self.dialog.Show(True)
            
    def populate(self, dict):
        """Updates the internal data with the contents of C{dict['calendar']}"""
        self._data=dict['calendar']
        self.entrycache={}
        self.entries={}
        self.repeating=[]

        for entry in self._data:
            entry=self._data[entry]
            y,m,d,h,min=entry['start']
            if entry['repeat'] is None:
                if not self.entries.has_key( (y,m,d) ): self.entries[(y,m,d)]=[]
                self.entries[(y,m,d)].append(entry)
                continue
            if entry['repeat']=='weekly':
                # we could pay attention to daybitmap here ...
                entry['dayofweek']=(calendar.weekday(y,m,d)+1)%7
            self.repeating.append(entry)

        self.RefreshAllEntries()

    def populatefs(self, dict):
        """Saves the dict to disk"""
        self.thedir=self.mainwindow.calendarpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for calendar '"+self.thedir+"'")
        for f in os.listdir(self.thedir):
            # delete them all!
            os.remove(os.path.join(self.thedir, f))

        d={}
        d['calendar']=dict['calendar']
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, self.CURRENTFILEVERSION)
        return dict

    def getfromfs(self, dict):
        """Updates dict with info from disk

        @Note: The dictionary passed in is modified, as well
        as returned
        @rtype: dict
        @param dict: the dictionary to update
        @return: the updated dictionary"""
        self.thedir=self.mainwindow.calendarpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for calendar '"+self.thedir+"'")
        if os.path.exists(os.path.join(self.thedir, "index.idx")):
            d={'result': {}}
            common.readversionedindexfile(os.path.join(self.thedir, "index.idx"), d, self.versionupgrade, self.CURRENTFILEVERSION)
            dict.update(d['result'])
        else:
            dict['calendar']={}
        return dict

    def versionupgrade(self, dict, version):
        """Upgrade old data format read from disk

        @param dict:  The dict that was read in
        @param version: version number of the data on disk
        """

        # version 0 to 1 upgrade
        if version==0:
            version=1  # they are the same

        # 1 to 2 
        if version==1:
            # ?d field renamed daybitmap
            version=2
            for k in dict['result']['calendar']:
                entry=dict['result']['calendar'][k]
                entry['daybitmap']=self.getdaybitmap(entry['start'], entry['repeat'])
                del entry['?d']

        # 2 to 3 etc


class DayViewDialog(wx.Dialog):
    """Used to edit the entries on one particular day"""

    # ids for the various controls
    ID_PREV=1
    ID_NEXT=2
    ID_ADD=3
    ID_DELETE=4
    ID_CLOSE=5
    ID_LISTBOX=6
    ID_START=7
    ID_END=8
    ID_REPEAT=9
    ID_DESCRIPTION=10
    ID_SAVE=11
    ID_HELP=12
    ID_REVERT=13

    # results on asking if the user wants to change the original (repeating) entry, just
    # this instance, or cancel
    ANSWER_ORIGINAL=1
    ANSWER_THIS=2
    ANSWER_CANCEL=3

    def __init__(self, parent, calendarwidget, id=-1, title="Edit Calendar"):
        # This method is a good illustration of why people use gui designers :-)
        self.cw=calendarwidget
        wx.Dialog.__init__(self, parent, id, title, style=wx.DEFAULT_DIALOG_STYLE)

        # overall container
        vbs=wx.BoxSizer(wx.VERTICAL)
        
        prev=wx.Button(self, self.ID_PREV, "<", style=wx.BU_EXACTFIT)
        next=wx.Button(self, self.ID_NEXT, ">", style=wx.BU_EXACTFIT)
        self.title=wx.StaticText(self, -1, "Date here", style=wx.ALIGN_CENTRE|wx.ST_NO_AUTORESIZE)

        # top row container 
        hbs1=wx.BoxSizer(wx.HORIZONTAL)
        hbs1.Add(prev, 0, wx.EXPAND)
        hbs1.Add(self.title, 1, wx.EXPAND)
        hbs1.Add(next, 0, wx.EXPAND)
        vbs.Add(hbs1, 0, wx.EXPAND)

        # list box and two buttons below
        self.listbox=wx.ListBox(self, self.ID_LISTBOX, style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_NEEDED_SB)
        add=wx.Button(self, self.ID_ADD, "New")
        hbs2=wx.BoxSizer(wx.HORIZONTAL)
        hbs2.Add(add, 1, wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT, border=5)
        
        # sizer for listbox
        lbs=wx.BoxSizer(wx.VERTICAL)
        lbs.Add(self.listbox, 1, wx.EXPAND|wx.BOTTOM, border=5)
        lbs.Add(hbs2, 0, wx.EXPAND)

        self.fieldnames=('description', 'start', 'end', 'repeat',
        'alarm', 'ringtone', 'changeserial', 'snoozedelay')
        
        self.fielddesc=( 'Description', 'Start', 'End', 'Repeat',
        'Alarm', 'Ringtone', 'changeserial', 'Snooze Delay' )

        # right hand bit with all fields
        gs=wx.FlexGridSizer(-1,2,5,5)
        gs.AddGrowableCol(1)
        self.fields={}
        for desc,field in zip(self.fielddesc, self.fieldnames):
            t=wx.StaticText(self, -1, desc, style=wx.ALIGN_LEFT)
            gs.Add(t)
            if field=='start':
                c=DVDateTimeControl(self,self.ID_START)
            elif field=='end':
                c=DVDateTimeControl(self,self.ID_END)
            elif field=='repeat':
                c=DVRepeatControl(self, self.ID_REPEAT)
            elif field=='description':
                c=DVTextControl(self, self.ID_DESCRIPTION, "dummy")
            else:
                print "field",field,"needs an id"
                c=DVIntControl(self, -1)
            gs.Add(c,0,wx.EXPAND)
            self.fields[field]=c

        # buttons below fields
        delete=wx.Button(self, self.ID_DELETE, "Delete")
        revert=wx.Button(self, self.ID_REVERT, "Revert")
        save=wx.Button(self, self.ID_SAVE, "Save")

        hbs4=wx.BoxSizer(wx.HORIZONTAL)
        hbs4.Add(delete, 1, wx.ALIGN_CENTRE|wx.LEFT, border=10)
        hbs4.Add(revert, 1, wx.ALIGN_CENTRE|wx.LEFT|wx.RIGHT, border=10)
        hbs4.Add(save, 1, wx.ALIGN_CENTRE|wx.RIGHT, border=10)

        # fields and buttons together
        vbs2=wx.BoxSizer(wx.VERTICAL)
        vbs2.Add(gs, 1, wx.EXPAND|wx.BOTTOM, border=5)
        vbs2.Add(hbs4, 0, wx.EXPAND|wx.ALIGN_CENTRE)

        # container for everything below title row
        hbs3=wx.BoxSizer(wx.HORIZONTAL)
        hbs3.Add(lbs, 1, wx.EXPAND|wx.ALL, 5)
        hbs3.Add(vbs2, 2, wx.EXPAND|wx.ALL, 5)

        vbs.Add(hbs3, 1, wx.EXPAND)

        # horizontal rules plus help and cancel buttons
        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND)
        help=wx.Button(self, self.ID_HELP, "Help")
        close=wx.Button(self, self.ID_CLOSE, "Close")
        hbs4=wx.BoxSizer(wx.HORIZONTAL)
        hbs4.Add(help, 0, wx.ALL, 5)
        hbs4.Add(close, 0, wx.ALL, 5)
        vbs.Add(hbs4, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

        # delete is disabled until an item is selected
        self.FindWindowById(self.ID_DELETE).Enable(False)

        wx.EVT_LISTBOX(self, self.ID_LISTBOX, self.OnListBoxItem)
        wx.EVT_LISTBOX_DCLICK(self, self.ID_LISTBOX, self.OnListBoxItem)
        wx.EVT_BUTTON(self, self.ID_SAVE, self.OnSaveButton)
        wx.EVT_BUTTON(self, self.ID_REVERT, self.OnRevertButton)
        wx.EVT_BUTTON(self, self.ID_CLOSE, self.OnCloseButton)
        wx.EVT_BUTTON(self, self.ID_ADD, self.OnNewButton)
        wx.EVT_BUTTON(self, self.ID_DELETE, self.OnDeleteButton)
        wx.EVT_BUTTON(self, self.ID_HELP, lambda _: wx.GetApp().displayhelpid(helpids.ID_EDITING_CALENDAR_EVENTS))
        wx.EVT_BUTTON(self, self.ID_PREV, self.OnPrevDayButton)
        wx.EVT_BUTTON(self, self.ID_NEXT, self.OnNextDayButton)

        # this is allegedly called automatically but didn't work for me
        wx.EVT_CLOSE(self, self.OnCloseWindow)

        # Tracking of the entries in the listbox.  Each entry is a dict. Entries are just the
        # entries in a random order.  entrymap maps from the order in the listbox to a
        # specific entry
        self.entries=[]
        self.entrymap=[]

        # Dirty tracking.  We restrict what the user can do while editting an
        # entry to only be able to edit that entry.  'dirty' gets fired when
        # they make any updates.  Annoyingly, controls generate change events
        # when they are updated programmatically as well as by user interaction.
        # ignoredirty is set when we are programmatically updating controls
        self.dirty=None
        self.ignoredirty=False 
        self.setdirty(False)

    def AskAboutRepeatDelete(self):
        """Asks the user if they wish to delete the original (repeating) entry, or this instance

        @return: An C{ANSWER_} constant
        """
        return self._AskAboutRecurringEvent("Delete recurring event?", "Do you want to delete all the recurring events, or just this one?", "Delete")

    def AskAboutRepeatChange(self):
        """Asks the user if they wish to change the original (repeating) entry, or this instance

        @return: An C{ANSWER_} constant
        """
        return self._AskAboutRecurringEvent("Change recurring event?", "Do you want to change all the recurring events, or just this one?", "Change")

    def _AskAboutRecurringEvent(self, caption, text, prefix):
        dlg=RecurringDialog(self, caption, text, prefix)
        res=dlg.ShowModal()
        dlg.Destroy()
        if res==dlg.ID_THIS:
            return self.ANSWER_THIS
        if res==dlg.ID_ALL:
            return self.ANSWER_ORIGINAL
        if res==dlg.ID_CANCEL:
            return self.ANSWER_CANCEL
        assert False

    def OnListBoxItem(self, _=None):
        """Callback for when user clicks on an event in the listbox"""
        self.updatefields(self.getcurrententry())
        self.setdirty(False)
        self.FindWindowById(self.ID_DELETE).Enable(True)

    def getcurrententry(self):
        """Returns the entry currently being viewed

        @Note: this returns the unedited form of the entry"""
        return self.getentry(self.listbox.GetSelection())

    def getentry(self, num):
        """maps from entry number in listbox to an entry in entries

        @type num: int
        @rtype: entry(dict)"""
        return self.entries[self.entrymap[num]]

    def OnSaveButton(self, _=None):
        """Callback for when user presses save"""

        # check if the dates are ok
        for x in 'start', 'end':
            if not self.fields[x].IsValid():
                self.fields[x].SetFocus()
                wx.Bell()
                return

        # whine if end is before start
        start=self.fields['start'].GetValue()
        end=self.fields['end'].GetValue()

        # I want metric time!
        if ( end[0]<start[0] ) or \
           ( end[0]==start[0] and end[1]<start[1] ) or \
           ( end[0]==start[0] and end[1]==start[1] and end[2]<start[2] ) or \
           ( end[0]==start[0] and end[1]==start[1] and end[2]==start[2] and end[3]<start[3] ) or \
           ( end[0]==start[0] and end[1]==start[1] and end[2]==start[2] and end[3]==start[3] and end[4]<start[4] ):
            # scold the user
            dlg=wx.MessageDialog(self, "End date and time is before start!", "Time Travel Attempt Detected",
                                wx.OK|wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            dlg.Destroy()
            # move focus
            self.fields['end'].SetFocus()
            return

        # lets roll ..
        entry=self.getcurrententry()

        # is it a repeat?
        res=self.ANSWER_ORIGINAL
        if entry['repeat'] is not None:
            # ask the user
            res=self.AskAboutRepeatChange()
            if res==self.ANSWER_CANCEL:
                return
        # where do we get newentry template from?
        if res==self.ANSWER_ORIGINAL:
            newentry=copy.copy(entry)
            # this will have no effect until we don't display the changeserial field
            newentry['changeserial']=entry['changeserial']+1
        else:
            newentry=self.cw.newentryfactory(*self.date)

        # update the fields
        for f in self.fields:
            control=self.fields[f]
            if isinstance(control, DVDateTimeControl):
                # which date do we use?
                if res==self.ANSWER_ORIGINAL:
                    d=control.GetValue()[0:3]
                else:
                    d=self.date
                v=list(d)+list(control.GetValue())[3:]
            else:
                v=control.GetValue()

            # if we are changing a repeat, reset the new entry's repeat is off
            if f=='repeat' and res==self.ANSWER_THIS:
                v=None
 
            newentry[f]=v

        # update the daybitmap field
        newentry['daybitmap']=self.cw.getdaybitmap(newentry['start'], newentry['repeat'])

        # update calendar widget
        if res==self.ANSWER_ORIGINAL:
            self.cw.ChangeEntry(entry, newentry)
        else:
            # delete the repeat and add this new entry
            self.cw.DeleteEntryRepeat(entry, *self.date)
            self.cw.AddEntry(newentry)

        # tidy up
        self.setdirty(False)
        # did the user change the date on us?
        date=tuple(newentry['start'][:3])
        if tuple(self.date)!=date:
            self.cw.showday(*date)
            self.cw.setselection(*date)
            self.setdate(*date)
        else:
            self.refreshentries()
        self.updatelistbox(newentry['pos'])

    def OnPrevDayButton(self, _):
        y,m,d=self.date
        y,m,d=calendarcontrol.normalizedate(y,m,d-1)
        self.setdate(y,m,d)
        self.cw.setday(y,m,d)

    def OnNextDayButton(self, _):
        y,m,d=self.date
        y,m,d=calendarcontrol.normalizedate(y,m,d+1)
        self.setdate(y,m,d)
        self.cw.setday(y,m,d)

    def OnNewButton(self, _=None):
        entry=self.cw.newentryfactory(*self.date)
        self.cw.AddEntry(entry)
        self.refreshentries()
        self.updatelistbox(entry['pos'])

    def OnRevertButton(self, _=None):
        # We basically pretend the user has selected the item in the listbox again (which they
        # can't actually do as it is disabled)
        self.OnListBoxItem()

    def OnDeleteButton(self, _=None):
        entry=self.getcurrententry()
        # is it a repeat?
        res=self.ANSWER_ORIGINAL
        if entry['repeat'] is not None:
            # ask the user
            res=self.AskAboutRepeatDelete()
            if res==self.ANSWER_CANCEL:
                return
        enum=self.listbox.GetSelection()
        if enum+1<len(self.entrymap):
            # try and find entry after current one
            newpos=self.getentry(enum+1)['pos']
        elif enum-1>=0:
            # entry before as we are deleting last entry
            newpos=self.getentry(enum-1)['pos']
        else:
            newpos=None
        if res==self.ANSWER_ORIGINAL:
            self.cw.DeleteEntry(entry)
        else:
            self.cw.DeleteEntryRepeat(entry, *self.date)
        self.setdirty(False)
        self.refreshentries()
        self.updatelistbox(newpos)
        
    def OnCloseWindow(self, event):
        # only allow closing to happen if the close button is
        # enabled
        if self.FindWindowById(self.ID_CLOSE).IsEnabled():
            self.Show(False)
        else:
            # veto it if allowed
            if event.CanVeto():
                event.Veto()
                wx.Bell()

    def OnCloseButton(self, _=None):
        self.Show(False)

    def setdate(self, year, month, day):
        """Sets the date we are editing entries for

        @Note: The list of entries is updated"""
        d=time.strftime("%A %d %B %Y", (year,month,day,0,0,0, calendar.weekday(year,month,day),1, 0))
        self.date=year,month,day
        self.title.SetLabel(d)
        self.refreshentries()
        self.updatelistbox()
        self.updatefields(None)

    def refreshentries(self):
        """re-requests the list of entries for the currently visible date from the main calendar"""
        self.entries=self.cw.getentrydata(*self.date)

    def updatelistbox(self, entrytoselect=None):
        """
        Updates the contents of the listbox.  It will re-sort the contents.

        @param entrytoselect: The integer id of an entry to select.  Note that
                              this is an event id, not an index
        """
        self.listbox.Clear()
        selectitem=-1
        self.entrymap=[]
        # decorate
        for index, entry in enumerate(self.entries):
            e=( entry['start'][3:5], entry['end'][3:5], entry['description'], entry['pos'],  index)
            self.entrymap.append(e)
        # time ordered
        self.entrymap.sort()
        # now undecorate
        self.entrymap=[index for ign0, ign1, ign2, ign3, index in self.entrymap]
        # add listbox entries
        for curpos, index in enumerate(self.entrymap):
            e=self.entries[index]
            if e['pos']==entrytoselect:
                selectitem=curpos
            if 0: # ampm/miltime config here ::TODO::
                str="%2d:%02d" % (e['start'][3], e['start'][4])
            else:
                hr=e['start'][3]
                ap="am"
                if hr>=12:
                    ap="pm"
                    hr-=12
                if hr==0: hr=12
                str="%2d:%02d %s" % (hr, e['start'][4], ap)
            str+=" "+e['description']
            self.listbox.Append(str)

        # Select an item if requested
        if selectitem>=0:
            self.listbox.SetSelection(selectitem)
            self.OnListBoxItem() # update fields
        else:
            # disable fields since nothing is selected
            self.updatefields(None)
            
        # disable delete if there are no entries!
        if len(self.entries)==0:
            self.FindWindowById(self.ID_DELETE).Enable(False)
            
    def updatefields(self, entry):
        self.ignoredirty=True
        active=True
        if entry is None:
            for i in self.fields:
                self.fields[i].SetValue(None)
            active=False
        else:
            for i in self.fieldnames:
                self.fields[i].SetValue(entry[i])

        # manipulate field widgets
        for i in self.fields:
            self.fields[i].Enable(active)

        self.ignoredirty=False

    # called from various widget update callbacks
    def OnMakeDirty(self, _=None):
        """A public function you can call that will set the dirty flag"""
        self.setdirty(True)

    def setdirty(self, val):
        """Set the dirty flag

        The various buttons in the dialog are enabled/disabled as appropriate
        for the new state.
        
        @type  val: Bool
        @param val: True to mark edit fields as different from entry (ie
                    editing has taken place)
                    False to make them as the same as the entry (ie no
                    editing or the edits have been discarded)
        """
        if self.ignoredirty:
            return
        self.dirty=val
        if self.dirty:
            # The data has been modified, so we only allow working
            # with this data
            
            # enable save, revert, delete
            self.FindWindowById(self.ID_SAVE).Enable(True)
            self.FindWindowById(self.ID_REVERT).Enable(True)
            self.FindWindowById(self.ID_DELETE).Enable(True)
            # disable close, left, right, new
            self.FindWindowById(self.ID_CLOSE).Enable(False)
            self.FindWindowById(self.ID_PREV).Enable(False)
            self.FindWindowById(self.ID_NEXT).Enable(False)
            self.FindWindowById(self.ID_ADD).Enable(False)
            # can't play with listbox now
            self.FindWindowById(self.ID_LISTBOX).Enable(False)
        else:
            # The data is now clean and saved/reverted or deleted
            
            # disable save, revert,
            self.FindWindowById(self.ID_SAVE).Enable(False)
            self.FindWindowById(self.ID_REVERT).Enable(False)

            # enable delete, close, left, right, new
            self.FindWindowById(self.ID_CLOSE).Enable(True)
            self.FindWindowById(self.ID_DELETE).Enable(len(self.entries)>0) # only enable if there are entries
            self.FindWindowById(self.ID_PREV).Enable(True)
            self.FindWindowById(self.ID_NEXT).Enable(True)
            self.FindWindowById(self.ID_ADD).Enable(True)

            # can choose another item in listbox
            self.FindWindowById(self.ID_LISTBOX).Enable(True)



# We derive from wxPanel not the control directly.  If we derive from
# wx.MaskedTextCtrl then all hell breaks loose as our {Get|Set}Value
# methods make the control malfunction big time
class DVDateTimeControl(wx.Panel):
    """A datetime control customised to work in the dayview editor"""
    def __init__(self,parent,id):
        f="EUDATETIMEYYYYMMDD.HHMM"
        wx.Panel.__init__(self, parent, -1)
        self.c=wx.lib.masked.textctrl.TextCtrl(self, id, "",
                                autoformat=f)
        bs=wx.BoxSizer(wx.HORIZONTAL)
        bs.Add(self.c,0,wx.EXPAND)
        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)
        wx.EVT_TEXT(self.c, id, parent.OnMakeDirty)

    def SetValue(self, v):
        if v is None:
            self.c.SetValue("")
            return
        ap="A"
        v=list(v)
        if v[3]>12:
            v[3]-=12
            ap="P"
        elif v[3]==0:
            v[3]=12
        elif v[3]==12:
            ap="P"
        v=v+[ap]

        # we have to supply what the user would type without the punctuation
        # (try figuring that out from the "doc")
        str="%04d%02d%02d%02d%02d%s" % tuple(v)
        self.c.SetValue( str )
        self.c.Refresh()

    def GetValue(self):
        # The actual value including all punctuation is returned
        # GetPlainValue can get it with all digits run together
        str=self.c.GetValue()
        digits="0123456789"

        # turn it back into a list
        res=[]
        val=None
        for i in str:
            if i in digits:
                if val is None: val=0
                val*=10
                val+=int(i)
            else:
                if val is not None:
                    res.append(val)
                    val=None
        # fixup am/pm
        if str[-2]=='P' or str[-2]=='p':
            if res[3]!=12: # 12pm is midday and left alone
                res[3]+=12
        elif res[3]==12: # 12 am
            res[3]=0

        return res

    def IsValid(self):
        return self.c.IsValid()
    
class DVRepeatControl(wx.Choice):
    """Shows the calendar repeat values"""
    vals=[None, "daily", "monfri", "weekly", "monthly", "yearly"]
    desc=["None", "Daily", "Mon - Fri", "Weekly", "Monthly", "Yearly" ]

    def __init__(self, parent, id):
        wx.Choice.__init__(self, parent, id, choices=self.desc)
        wx.EVT_CHOICE(self, id, parent.OnMakeDirty)

    def SetValue(self, v):
        assert v in self.vals
        self.SetSelection(self.vals.index(v))

    def GetValue(self):
        s=self.GetSelection()
        if s<0: s=0
        return self.vals[s]

class DVIntControl(wx.lib.intctrl.IntCtrl):
    # shows integer values
    def __init__(self, parent, id):
        wx.lib.intctrl.IntCtrl.__init__(self, parent, id, limited=True)
        wx.lib.intctrl.EVT_INT(self, id, parent.OnMakeDirty)

    def SetValue(self, v):
        if v is None:
            v=-1
        wx.lib.intctrl.IntCtrl.SetValue(self,v)
        
class DVTextControl(wx.TextCtrl):
    def __init__(self, parent, id, value=""):
        if value is None:
            value=""
        wx.TextCtrl.__init__(self, parent, id, value)
        wx.EVT_TEXT(self, id, parent.OnMakeDirty)

    def SetValue(self, v):
        if v is None: v=""
        wx.TextCtrl.SetValue(self,v)


###
### Dialog box for asking the user what they want to for a recurring event.
### Used when saving changes or deleting entries in the DayViewDialog
###

class RecurringDialog(wx.Dialog):
    """Ask the user what they want to do about a recurring event

    You should only use this as a modal dialog.  ShowModal() will
    return one of:

      - ID_THIS:   change just this event
      - ID_ALL:    change all events
      - ID_CANCEL: user cancelled dialog"""
    ID_THIS=1
    ID_ALL=2
    ID_CANCEL=3
    ID_HELP=4 # hide from epydoc

    def __init__(self, parent, caption, text, prefix):
        """Constructor

        @param parent: frame to parent this to
        @param caption: caption of the dialog (eg C{"Change recurring event?"})
        @param text: text displayed in the dialog (eg C{"This is a recurring event.  What would you like to change?"})
        @param prefix: text prepended to the buttons (eg the button says " this" so the prefix would be "Change" or "Delete")
        """
        wx.Dialog.__init__(self, parent, -1, caption,
                          style=wx.CAPTION)

        # eveything sits inside a vertical box sizer
        vbs=wx.BoxSizer(wx.VERTICAL)

        # the explanatory text
        t=wx.StaticText(self, -1, text)
        vbs.Add(t, 1, wx.EXPAND|wx.ALL,10)

        # horizontal line
        vbs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 3)

        # buttons at bottom
        buttonsizer=wx.BoxSizer(wx.HORIZONTAL)
        for id, label in (self.ID_THIS,   "%s %s" % (prefix, "this")), \
                         (self.ID_ALL,    "%s %s" % (prefix, "all")), \
                         (self.ID_CANCEL, "Cancel"), \
                         (self.ID_HELP,   "Help"):
            b=wx.Button(self, id, label)
            wx.EVT_BUTTON(self, id, self._onbutton)
            buttonsizer.Add(b, 5, wx.ALIGN_CENTER|wx.ALL, 5)

        # plumb in sizers
        vbs.Add(buttonsizer, 0, wx.EXPAND|wx.ALL,2)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)


    def _onbutton(self, evt):
        if evt.GetId()==self.ID_HELP:
            pass # :::TODO::: some sort of help ..
        else:
            self.EndModal(evt.GetId())
