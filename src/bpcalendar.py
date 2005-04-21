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

Version 3:

The format for the calendar is standardised.  It is a dict with the following
fields:
(Note: hour fields are in 24 hour format)
'string id': CalendarEntry object.

CalendarEntry properties:
description - 'string description'
location - 'string location'
priority - None=no priority, int from 1-10, 1=highest priority
alarm - how many minutes beforehand to set the alarm (use 0 for on-time, None or -1 for no alarm)
allday - True for an allday event, False otherwise
start - (year, month, day, hour, minute) as integers
end - (year, month, day, hour, minute) as integers
serials - list of dicts of serials.
repeat - None, or RepeatEntry object
id - string id of this object.  Created the same way as bpserials IDs for phonebook entries.
notes - string notes
category - [ { 'category': string category }, ... ]
ringtone - string ringtone assignment
wallpaper - string wallpaper assignment.

CalendarEntry methods:
get() - return a copy of the internal dict
get_db_dict()- return a copy of a database.basedataobject dict.
set(dict) - set the internal dict with the supplied dict
set_db_dict(dict) - set internal data with the database.basedataobject dict
is_active(y, m, d) - True if this event is active on (y,m,d)
suppress_repeat_entry(y,m,d) - exclude (y,m,d) from this repeat event.

RepeatEntry properties:
repeat_type - one of daily, weekly, monthly, or yearly.
interval - for daily: repeat every nth day.  For weekly, for every nth week.
dow - bitmap of which day of week are being repeated.
suppressed - list of (y,m,d) being excluded from this series.

--------------------------------------------------------------------------------
Version 2:

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
import datetime
import random
import sha
import time
import webbrowser

# wx stuff
import wx
import wx.lib
import wx.lib.masked.textctrl
import wx.lib.intctrl

# my modules
import bptime
import calendarcontrol
import calendarentryeditor
import common
import database
import guihelper
import helpids
import xyaptu

#-------------------------------------------------------------------------------
class CalendarDataObject(database.basedataobject):
    """
    This class is a wrapper class to enable CalendarEntry object data to be
    stored in the database stuff.  Once the database module is updated, this
    class will also be updated and eventually replace CalendarEntry.
    """
    _knownproperties=['description', 'location', 'priority', 'alarm',
                      'notes', 'ringtone', 'wallpaper',
                      'start', 'end']
    _knownlistproperties=database.basedataobject._knownlistproperties.copy()
    _knownlistproperties.update( {
                                  'repeat': ['type', 'interval', 'dow'],
                                  'suppressed': ['date'],
                                  'categories': ['category'] })
    def __init__(self, data=None):
        if data is None or not isinstance(data, CalendarEntry):
            # empty data, do nothing
            return
        self.update(data.get_db_dict())

calendarobjectfactory=database.dataobjectfactory(CalendarDataObject)
#-------------------------------------------------------------------------------
class RepeatEntry(object):
    # class constants
    daily='daily'
    weekly='weekly'
    monthly='monthly'
    yearly='yearly'
    __interval=0
    __dow=1
    __dom=0
    __moy=1
    
    def __init__(self, repeat_type=daily):
        self.__type=repeat_type
        self.__data=[0,0]
        self.__suppressed=[]

    def get(self):
        # return a dict representing internal data
        # mainly used for populatefs
        r={}
        if self.__type==self.daily:
            r[self.daily]= { 'interval': self.__data[self.__interval] }
        elif self.__type==self.weekly:
            r[self.weekly]= { 'interval': self.__data[self.__interval],
                                    'dow': self.__data[self.__dow] }
        elif self.__type==self.monthly:
            r[self.monthly]=None
        else:
            r[self.yearly]=None
        s=[]
        for n in self.__suppressed:
            s.append(n.get())
        r['suppressed']=s
        return r

    def get_db_dict(self):
        # return a copy of the dict compatible with the database stuff
        db_r={}
        r={}
        r['type']=self.__type
        if self.__type==self.daily:
            r['interval']=self.__data[self.__interval]
        elif self.__type==self.weekly:
            r['interval']=self.__data[self.__interval]
            r['dow']=self.__data[self.__dow]
        # and the suppressed stuff
        s=[]
        for n in self.__suppressed:
            s.append({ 'date': n.iso_str(True) })
        db_r['repeat']=[r]
        if len(s):
            db_r['suppressed']=s
        return db_r

    def set(self, data):
        # setting data from a dict, mainly used for getfromfs
        if data.has_key(self.daily):
            # daily type
            self.repeat_type=self.daily
            self.interval=data[self.daily]['interval']
        elif data.has_key(self.weekly):
            # weekly type
            self.repeat_type=self.weekly
            self.interval=data[self.weekly]['interval']
            self.dow=data[self.weekly]['dow']
        elif data.has_key(self.monthly):
            self.repeat_type=self.monthly
        else:
            self.repeat_type=self.yearly
        s=[]
        for n in data.get('suppressed', []):
            s.append(bptime.BPTime(n))
        self.suppressed=s

    def set_db_dict(self, data):
        r=data.get('repeat', [{}])[0]
        self.repeat_type=r['type']
        if self.repeat_type==self.daily:
            self.interval=r['interval']
        elif self.repeat_type==self.weekly:
            self.interval=r['interval']
            self.dow=r['dow']
        # now the suppressed stuff
        s=[]
        for n in data.get('suppressed', []):
            s.append(bptime.BPTime(n['date']))
        self.suppressed=s

    def __check_daily(self, s, d):
        if self.interval:
            # every nth day
            return (int((d-s).days)%self.interval)==0
        else:
            # every weekday
            return d.weekday()<5

    def __check_weekly(self, s, d):
        # check if at least one day-of-week is specified, if not default to the
        # start date
        if self.dow==0:
            self.dow=1<<(s.isoweekday()%7)
        # check to see if this is the nth week
        day_of_week=d.isoweekday()%7  # Sun=0, ..., Sat=6
        sun_0=s-datetime.timedelta(s.isoweekday()%7)
        sun_1=d-datetime.timedelta(day_of_week)
        if ((sun_1-sun_0).days/7)%self.interval:
            # wrong week
            return False
        # check for the right weekday
        return ((1<<day_of_week)&self.dow) != 0

    def __check_monthly(self, s, d):
        return d.day==s.day

    def __check_yearly(self, s, d):
        return d.month==s.month and d.day==s.day

    def is_active(self, s, d):
        # check in the suppressed list
        if bptime.BPTime(d) in self.__suppressed:
            # in the list, not part of this repeat
            return False
        # determine if the date is active
        if self.repeat_type==self.daily:
            return self.__check_daily(s, d)
        elif self.repeat_type==self.weekly:
            return self.__check_weekly(s, d)
        elif self.repeat_type==self.monthly:
            return self.__check_monthly(s, d)
        elif self.repeat_type==self.yearly:
            return self.__check_yearly(s, d)
        else:
            return False

    def __get_type(self):
        return self.__type
    def __set_type(self, repeat_type):
        if repeat_type in (self.daily, self.weekly,
                    self.monthly, self.yearly):
            self.__type = repeat_type
        else:
            raise AttributeError, 'type'
    repeat_type=property(fget=__get_type, fset=__set_type)
    
    def __get_interval(self):
        if self.__type in (self.daily, self.weekly):
            return self.__data[self.__interval]
        raise AttributeError, 'interval'
    def __set_interval(self, interval):
        if self.__type in (self.daily, self.weekly):
            self.__data[self.__interval]=interval
        else:
            raise AttributeError, 'interval'
    interval=property(fget=__get_interval, fset=__set_interval)

    def __get_dow(self):
        if self.__type in (self.daily, self.weekly):
            return self.__data[self.__dow]
        raise AttributeError, 'dow'
    def __set_dow(self, dow):
        if self.__type in (self.daily, self.weekly):
            self.__data[self.__dow]=dow
        else:
            raise AttributeError, 'dow'
    dow=property(fget=__get_dow, fset=__set_dow)

    def __get_suppressed(self):
        return self.__suppressed
    def __set_suppressed(self, d):
        if not isinstance(d, list):
            raise TypeError, 'must be a list of string or BPTime'
        if not len(d) or isinstance(d[0], bptime.BPTime):
            # empty list or already a list of BPTime
            self.__suppressed=d
        elif isinstance(d[0], str):
            # list of 'yyyy-mm-dd'
            self.__suppressed=[]
            for n in d:
                self.__suppressed.append(bptime.BPTime(n.replace('-', '')))
    def add_suppressed(self, y, m, d):
        self.__suppressed.append(bptime.BPTime((y, m, d)))
    def get_suppressed_list(self):
        return [x.date_str() for x in self.__suppressed]
    suppressed=property(fget=__get_suppressed, fset=__set_suppressed)

#-------------------------------------------------------------------------------
class CalendarEntry(object):
    # priority const
    priority_high=1
    priority_normal=5
    priority_low=10

    def __init__(self, year=None, month=None, day=None):
        self.__data={}
        # setting default values
        if day is not None:
            self.__data['start']=bptime.BPTime((year, month, day))
            self.__data['end']=bptime.BPTime((year, month, day))
        else:
            self.__data['start']=bptime.BPTime()
            self.__data['end']=bptime.BPTime()
        self.__data['serials']=[]
        self.__create_id()

    def get(self):
        r=copy.deepcopy(self.__data, _nil={})
        if self.repeat is not None:
            r['repeat']=self.repeat.get()
        r['start']=self.__data['start'].iso_str()
        r['end']=self.__data['end'].iso_str()
        return r

    def get_db_dict(self):
        # return a dict compatible with the database stuff
        r=copy.deepcopy(self.__data, _nil={})
        # adjust for start & end
        r['start']=self.__data['start'].iso_str(self.allday)
        r['end']=self.__data['end'].iso_str(self.allday)
        # adjust for repeat & suppressed
        if self.repeat is not None:
            r.update(self.repeat.get_db_dict())
        # take out uneeded keys
        if r.has_key('allday'):
            del r['allday']
        return r

    def set(self, data):
        self.__data={}
        self.__data.update(data)
        self.__data['start']=bptime.BPTime(data['start'])
        self.__data['end']=bptime.BPTime(data['end'])
        if self.repeat is not None:
            r=RepeatEntry()
            r.set(self.repeat)
            self.repeat=r
        # try to clean up the dict
        for k, e in self.__data.items():
            if e is None or e=='' or e==[]:
                del self.__data[k]

    def set_db_dict(self, data):
        # update our data with dict return from database
        self.__data={}
        self.__data.update(data)
        # adjust for allday
        self.allday=len(data['start'])==8
        # adjust for start and end
        self.__data['start']=bptime.BPTime(data['start'])
        self.__data['end']=bptime.BPTime(data['end'])
        # adjust for repeat
        if data.has_key('repeat'):
            rp=RepeatEntry()
            rp.set_db_dict(data)
            self.repeat=rp

    def is_active(self, y, m ,d):
        # return true if if this event is active on this date,
        # mainly used for repeating events.
        s=self.__data['start'].date
        e=self.__data['end'].date
        d=datetime.date(y, m, d)
        if d<s or d>e:
            # before start date, after end date
            return False
        if self.repeat is None:
            # not a repeat event, within range so it's good
            return True
        # repeat event: check if it's in range.
        return self.repeat.is_active(s, d)

    def suppress_repeat_entry(self, y, m, d):
        if self.repeat is None:
            # not a repeat entry, do nothing
            return
        self.repeat.add_suppressed(y, m, d)

    def __set_or_del(self, key, v, v_list=()):
        if v is None or v in v_list:
            if self.__data.has_key(key):
                del self.__data[key]
        else:
            self.__data[key]=v
        
    def __get_description(self):
        return self.__data.get('description', '')
    def __set_description(self, desc):
        self.__set_or_del('description', desc, ('',))
    description=property(fget=__get_description, fset=__set_description)

    def __get_location(self):
        return self.__data.get('location', '')
    def __set_location(self, location):
        self.__set_or_del('location', location, ('',))
    location=property(fget=__get_location, fset=__set_location)

    def __get_priority(self):
        return self.__data.get('priority', None)
    def __set_priority(self, priority):
        self.__set_or_del('priority', priority)
    priority=property(fget=__get_priority, fset=__set_priority)

    def __get_alarm(self):
        return self.__data.get('alarm', -1)
    def __set_alarm(self, alarm):
        self.__set_or_del('alarm', alarm)
    alarm=property(fget=__get_alarm, fset=__set_alarm)

    def __get_allday(self):
        return self.__data.get('allday', False)
    def __set_allday(self, allday):
        self.__data['allday']=allday
    allday=property(fget=__get_allday, fset=__set_allday)

    def __get_start(self):
        return self.__data['start'].get()
    def __set_start(self, datetime):
        self.__data['start'].set(datetime)
    start=property(fget=__get_start, fset=__set_start)
    
    def __get_end(self):
        return self.__data['end'].get()
    def __set_end(self, datetime):
        self.__data['end'].set(datetime)
    end=property(fget=__get_end, fset=__set_end)

    def __get_serials(self):
        return self.__data.get('serials', None)
    def __set_serials(self, serials):
        self.__data['serials']=serials
    serials=property(fget=__get_serials, fset=__set_serials)

    def __get_repeat(self):
        return self.__data.get('repeat', None)
    def __set_repeat(self, repeat):
        self.__set_or_del('repeat', repeat)
    repeat=property(fget=__get_repeat, fset=__set_repeat)

    def __get_id(self):
        s=self.__data.get('serials', [])
        for n in s:
            if n.get('sourcetype', None)=='bitpim':
                return n.get('id', None)
        return None
    def __set_id(self, id):
        s=self.__data.get('serials', [])
        for n in s:
            if n.get('sourcetype', None)=='bitpim':
                n['id']=id
                return
        self.__data['serials'].append({'sourcetype': 'bitpim', 'id': id } )
    id=property(fget=__get_id, fset=__set_id)

    def __get_notes(self):
        return self.__data.get('notes', '')
    def __set_notes(self, s):
        self.__set_or_del('notes', s, ('',))
    notes=property(fget=__get_notes, fset=__set_notes)

    def __get_categories(self):
        return self.__data.get('categories', [])
    def __set_categories(self, s):
        self.__set_or_del('categories', s,([],))
        if s==[] and self.__data.has_key('categories'):
            del self.__data['categories']
    categories=property(fget=__get_categories, fset=__set_categories)

    def __get_ringtone(self):
        return self.__data.get('ringtone', '')
    def __set_ringtone(self, rt):
        self.__set_or_del('ringtone', rt, ('',))
    ringtone=property(fget=__get_ringtone, fset=__set_ringtone)

    def __get_wallpaper(self):
        return self.__data.get('wallpaper', '',)
    def __set_wallpaper(self, wp):
        self.__set_or_del('wallpaper', wp, ('',))
    wallpaper=property(fget=__get_wallpaper, fset=__set_wallpaper)

    # we use two random numbers to generate the serials.  _persistrandom
    # is seeded at startup
    _persistrandom=random.Random()
    def __create_id(self):
        "Create a BitPim serial for this entry"
        rand2=random.Random() # this random is seeded when this function is called
        num=sha.new()
        num.update(`self._persistrandom.random()`)
        num.update(`rand2.random()`)
        self.__data["serials"].append({"sourcetype": "bitpim", "id": num.hexdigest()})

    def __get_print_data(self):
        """ return a list of strings used for printing this event:
        [0]: start time, [1]: '', [2]: end time, [3]: Description
        [4]: Repeat Type, [5]: Alarm
        """
        if self.allday:
            t0='All'
            t1='Day'
        else:
            t0=self.__data['start'].time_str()
            t1=self.__data['end'].time_str()
        rp=self.repeat
        if rp is None:
            rp_str=''
        else:
            rp_str=rp.repeat_type[0].upper()
        if self.alarm==-1:
            alarm_str=''
        else:
            alarm_str='%d:%02d'%(self.alarm/60, self.alarm%60)
        return [t0, '', t1, self.description, rp_str, alarm_str]
    print_data=property(fget=__get_print_data)
    def cmp_by_time(a, b):
        """ compare 2 objects by start times.
        -1 if a<b, 0 if a==b, and 1 if a>b
        allday is always less than having start times.
        Mainly used for sorting list of events
        """
        if not isinstance(a, CalendarEntry) or \
           not isinstance(b, CalendarEntry):
            raise TypeError, 'must be a CalendarEntry object'
        if a.allday and b.allday:
            return 0
        if a.allday and not b.allday:
            return -1
        if not a.allday and b.allday:
            return 1
        t0=a.start[3:]
        t1=b.start[3:]
        if t0<t1:
            return -1
        if t0==t1:
            return 0
        if t0>t1:
            return 1
    cmp_by_time=staticmethod(cmp_by_time)

#-------------------------------------------------------------------------------
class Calendar(calendarcontrol.Calendar):
    """A class encapsulating the GUI and data of the calendar (all days).  A seperate L{DayViewDialog} is
    used to edit the content of one particular day."""

    CURRENTFILEVERSION=3
    
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
        self.dialog=calendarentryeditor.Editor(self)

    def OnPrintDialog(self, mainwindow, config):
        dlg=CalendarPrintDialog(self, mainwindow, config)
        dlg.ShowModal()
        dlg.Destroy()

    def get_print_data(self, dt_start, dt_end):
        """ generate a dict suitable for printing"""
        dt_index=dt_start
        one_day=wx.DateSpan(days=1)
        current_month=None
        res=a_month=month_events=[]
        while dt_index<=dt_end:
            y=dt_index.GetYear()
            m=dt_index.GetMonth()
            d=dt_index.GetDay()
            entries=self.getentrydata(y, m+1, d)
            dt_index+=one_day
            if not len(entries):
                # no events on this day
                continue
            entries.sort(CalendarEntry.cmp_by_time)
            if m!=current_month:
                # save the current month
                if len(month_events):
                    a_month.append(month_events)
                    res.append(a_month)
                # start a new month
                current_month=m
                a_month=['%s %d'%(dt_index.GetMonthName(m), y)]
                month_events=[]
            # go through the entries and build a list of print data
            for i,e in enumerate(entries):
                if i:
                    date_str=day_str=''
                else:
                    date_str=str(d)
                    day_str=dt_index.GetWeekDayName(
                        dt_index.GetWeekDay()-1, wx.DateTime.Name_Abbr)
                month_events.append([date_str, day_str]+e.print_data)
        if len(month_events):
            # data left in the list
            a_month.append(month_events)
            res.append(a_month)
        return res

    def getdata(self, dict):
        """Return underlying calendar data in bitpim format

        @return:   The modified dict updated with at least C{dict['calendar']}"""
        if dict.get('calendar_version', None)==2:
            # return a version 2 dict
            dict['calendar']=self.__convert3to2(self._data,
                                                dict.get('ringtone-index', None))
        else:
            dict['calendar']=copy.deepcopy(self._data, _nil={})
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
        self._data[entry.id]=entry
        self.updateonchange()

    def DeleteEntry(self, entry):
        """Deletes an entry from the calendar data.

        The entries on disk are updated by this function.

        @type  entry: a dict containing all the fields.
        @param entry: an entry.  It must contain a C{pos} field
                      corresponding to an existing entry
        """
        del self._data[entry.id]
        self.updateonchange()

    def DeleteEntryRepeat(self, entry, year, month, day):
        """Deletes a specific repeat of an entry
        See L{DeleteEntry}"""
        self._data[entry.id].suppress_repeat_entry(year, month, day)
        self.updateonchange()
        
    def ChangeEntry(self, oldentry, newentry):
        """Changes an entry in the calendar data.

        The entries on disk are updated by this function.
        """
        assert oldentry.id==newentry.id
        self._data[newentry.id]=newentry
        self.updateonchange()

    def getentrydata(self, year, month, day):
        """return the entry objects for corresponding date

        @rtype: list"""
        # return data from cache if we have it
        res=self.entrycache.get( (year,month,day), None)
        if res is not None:
            return res
        # find non-repeating entries
        res=self.entries.get((year,month,day), [])
        for i in self.repeating:
            if i.is_active(year, month, day):
                res.append(i)
        self.entrycache[(year,month,day)] = res
        return res
        
    def newentryfactory(self, year, month, day):
        """Returns a new 'blank' entry with default fields

        @rtype: CalendarEntry
        """
        # create a new entry
        res=CalendarEntry(year, month, day)
        # fill in default start & end data
        now=time.localtime()
        event_start=(year, month, day, now.tm_hour, now.tm_min)
        event_end=[year, month, day, now.tm_hour, now.tm_min]
        # we make end be the next hour, unless it has gone 11pm
        # in which case it is 11:59pm
        if event_end[3]<23:
            event_end[3]+=1
            event_end[4]=0
        else:
            event_end[3]=23
            event_end[4]=59
        res.start=event_start
        res.end=event_end
        res.description='New Event'
        return res

    def getdaybitmap(self, start, repeat):
        if repeat!="weekly":
            return 0
        dayofweek=calendar.weekday(*(start[:3]))
        dayofweek=(dayofweek+1)%7 # normalize to sunday == 0
        return [2048,1024,512,256,128,64,32][dayofweek]

    def OnGetEntries(self, year, month, day):
        """return pretty printed sorted entries for date
        as required by the parent L{calendarcontrol.Calendar} for
        display in a cell"""
        entry_list=self.getentrydata(year, month, day)
        res=[ (i.start[3], i.start[4], i.description) \
              for i in entry_list if not i.allday ]
        res += [ (None, None, i.description) \
                 for i in entry_list if i.allday ]
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

    def OnTodayButton(self, evt):
        """ Called when the user goes to today cell"""
        super(Calendar, self).OnTodayButton(evt)
        if self.dialog.IsShown():
            # editor dialog is up, update it
            self.OnEdit(*self.selecteddate)
            
    def populate(self, dict):
        """Updates the internal data with the contents of C{dict['calendar']}"""
        if dict.get('calendar_version', None)==2:
            # Cal dict version 2, need to convert to current ver(3)
            self._data=self.__convert2to3(dict.get('calendar', {}),
                                          dict.get('ringtone-index', {}))
        else:
            self._data=dict.get('calendar', {})
        self.entrycache={}
        self.entries={}
        self.repeating=[]

        for entry in self._data:
            entry=self._data[entry]
            y,m,d,h,min=entry.start
            if entry.repeat is None:
                self.entries.setdefault((y,m,d), []).append(entry)
            else:
                self.repeating.append(entry)

        self.RefreshAllEntries()

    def populatefs(self, dict):
        """Saves the dict to disk"""

        if dict.get('calendar_version', None)==2:
            # Cal dict version 2, need to convert to current ver(3)
            cal_dict=self.__convert2to3(dict.get('calendar', {}),
                                        dict.get('ringtone-index', {}))
        else:
            cal_dict=dict.get('calendar', {})

        db_rr={}
        for k, e in cal_dict.items():
            db_rr[k]=CalendarDataObject(e)
        database.ensurerecordtype(db_rr, calendarobjectfactory)
        db_rr=database.extractbitpimserials(db_rr)
        self.mainwindow.database.savemajordict('calendar', db_rr)
        return dict

    def getfromfs(self, dict):
        """Updates dict with info from disk

        @Note: The dictionary passed in is modified, as well
        as returned
        @rtype: dict
        @param dict: the dictionary to update
        @return: the updated dictionary"""
        self.thedir=self.mainwindow.calendarpath
        if os.path.exists(os.path.join(self.thedir, "index.idx")):
            # old index file exists: read, convert, and discard file
            dct={'result': {}}
            common.readversionedindexfile(os.path.join(self.thedir, "index.idx"),
                                          dct, self.versionupgrade,
                                          self.CURRENTFILEVERSION)
            converted=dct['result'].has_key('converted')
            db_r={}
            for k,e in dct['result'].get('calendar', {}).items():
                if converted:
                    db_r[k]=CalendarDataObject(e)
                else:
                    ce=CalendarEntry()
                    ce.set(e)
                    db_r[k]=CalendarDataObject(ce)
            # save it in the new database
            database.ensurerecordtype(db_r, calendarobjectfactory)
            db_r=database.extractbitpimserials(db_r)
            self.mainwindow.database.savemajordict('calendar', db_r)
            # now that save is succesful, move file out of the way
            os.rename(os.path.join(self.thedir, "index.idx"), os.path.join(self.thedir, "index-is-now-in-database.bak"))
        # read data from the database
        cal_dict=self.mainwindow.database.getmajordictvalues('calendar',
                                                      calendarobjectfactory)
        #if __debug__:
        #    print 'Calendar.getfromfs: dicts returned from Database:'
        r={}
        for k,e in cal_dict.items():
            #if __debug__:
            #    print e
            ce=CalendarEntry()
            ce.set_db_dict(e)
            r[ce.id]=ce
        dict.update({ 'calendar': r })

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
        if version==2:
            version=3
            dict['result']['calendar']=self.convert_dict(dict['result'].get('calendar', {}), 2, 3)
            dict['result']['converted']=True    # already converted

        # 3 to 4 etc

    def convert_dict(self, dict, from_version, to_version, ringtone_index={}):
        """
        Convert the calendatr dict from one version to another.
        Currently only support conversion between version 2 and 3.
        """
        if dict is None:
            return None
        if from_version==2 and to_version==3:
            return self.__convert2to3(dict, ringtone_index)
        elif from_version==3 and to_version==2:
            return self.__convert3to2(dict, ringtone_index)
        else:
            raise 'Invalid conversion'

    def __convert2to3(self, dict, ringtone_index):
        """
        Convert calendar dict from version 2 to 3.
        """
        r={}
        for k,e in dict.items():
            ce=CalendarEntry()
            ce.start=e['start']
            ce.end=e['end']
            ce.description=e['description']
            ce.alarm=e['alarm']
            ce.ringtone=ringtone_index.get(e['ringtone'], {}).get('name', '')
            repeat=e['repeat']
            if repeat is None:
                ce.repeat=None
            else:
                repeat_entry=RepeatEntry()
                if repeat=='daily':
                    repeat_entry.repeat_type=repeat_entry.daily
                    repeat_entry.interval=1
                elif repeat=='monfri':
                    repeat_entry.repeat_type=repeat_entry.daily
                    repeat_entry.interval=0
                elif repeat=='weekly':
                    repeat_entry.repeat_type=repeat_entry.weekly
                    repeat_entry.interval=1
                    dow=datetime.date(*e['start'][:3]).isoweekday()%7
                    repeat_entry.dow=1<<dow
                elif repeat=='monthly':
                    repeat_entry.repeat_type=repeat_entry.monthly
                else:
                    repeat_entry.repeat_type=repeat_entry.yearly
                s=[]
                for n in e.get('exceptions',[]):
                    s.append(bptime.BPTime(n))
                repeat_entry.suppressed=s
                ce.repeat=repeat_entry
            r[ce.id]=ce
        return r

    def __convert_daily_events(self, e, d):
        """ Conver a daily event from v3 to v2 """
        rp=e.repeat
        if rp.interval==1:
            # repeat everyday
            d['repeat']='daily'
        elif rp.interval==0:
            # repeat every weekday
            d['repeat']='monfri'
        else:
            # the interval is every nth day, with n>1
            # generate exceptions for those dates that are N/A
            d['repeat']='daily'
            t0=datetime.date(*e.start[:3])
            t1=datetime.date(*e.end[:3])
            delta_t=datetime.timedelta(1)
            while t0<=t1:
                if not e.is_active(t0.year, t0.month, t0.day):
                    d['exceptions'].append((t0.year, t0.month, t0.day))
                t0+=delta_t

    def __convert_weekly_events(self, e, d, idx):
        """
        Convert a weekly event from v3 to v2
        """
        rp=e.repeat
        dow=rp.dow
        t0=datetime.date(*e.start[:3])
        t1=t3=datetime.date(*e.end[:3])
        delta_t=datetime.timedelta(1)
        delta_t7=datetime.timedelta(7)
        if (t1-t0).days>6:
            # end time is more than a week away
            t1=t0+datetime.timedelta(6)
        d['repeat']='weekly'
        res={}
        while t0<=t1:
            dow_0=t0.isoweekday()%7
            if (1<<dow_0)&dow:
                # we have a hit, generate a weekly repeat event here
                dd=copy.deepcopy(d)
                dd['start']=(t0.year, t0.month, t0.day, e.start[3], e.start[4])
                dd['daybitmap']=self.getdaybitmap(dd['start'], dd['repeat'])
                # generate exceptions for every nth week case
                t2=t0
                while t2<=t3:
                    if not e.is_active(t2.year, t2.month, t2.day):
                        dd['exceptions'].append((t2.year, t2.month, t2.day))
                    t2+=delta_t7
                # done, add it to the dict
                dd['pos']=idx
                res[idx]=dd
                idx+=1
            t0+=delta_t
        return idx, res

    def __convert3to2(self, dict, ringtone_index):
        """Convert calendar dict from version 3 to 2."""
        r={}
        idx=0
        for k,e in dict.items():
            d={}
            d['start']=e.start
            d['end']=e.end
            d['description']=e.description
            d['alarm']=e.alarm
            d['changeserial']=1
            d['snoozedelay']=0
            d['ringtone']=0 # by default
            try:
                d['ringtone']=[i for i,r in ringtone_index.items() \
                               if r.get('name', '')==e.ringtone][0]
            except:
                pass
            rp=e.repeat
            if rp is None:
                d['repeat']=None
                d['exceptions']=[]
                d['daybitmap']=0
            else:
                s=[]
                for n in rp.suppressed:
                    s.append(n.get()[:3])
                d['exceptions']=s
                if rp.repeat_type==rp.daily:
                    self.__convert_daily_events(e, d)
                elif rp.repeat_type==rp.weekly:
                    idx, rr=self.__convert_weekly_events(e, d, idx)
                    r.update(rr)
                    continue
                elif rp.repeat_type==rp.monthly:
                    d['repeat']='monthly'
                elif rp.repeat_type==rp.yearly:
                    d['repeat']='yearly'
                d['daybitmap']=self.getdaybitmap(d['start'], d['repeat'])
            d['pos']=idx
            r[idx]=d
            idx+=1
        if __debug__:
            print 'Calendar.__convert3to2: V2 dict:'
            print r
        return r

#-------------------------------------------------------------------------------
class CalendarPrintDialog(wx.Dialog):
    __regular_template='cal_regular.xy'
    def __init__(self, calwidget, mainwindow, config):
        super(CalendarPrintDialog, self).__init__(mainwindow, -1, 'Print Calendar')
        self.__cal_widget=calwidget
        self.__xcp=self.__html=self.__dns=None
        self.__date_changed=False
        self.__tmp_file=common.gettempfilename("htm")
        # main box sizer
        vbs=wx.BoxSizer(wx.VERTICAL)
        # the print range box
        sbs=wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Print Range'),
                               wx.VERTICAL)
        gs=wx.FlexGridSizer(-1, 2, 5, 5)
        gs.AddGrowableCol(1)
        gs.Add(wx.StaticText(self, -1, 'Start:'), 0, wx.ALL, 0)
        self.__start_date=wx.DatePickerCtrl(self, style=wx.DP_DROPDOWN | wx.DP_SHOWCENTURY)
        wx.EVT_DATE_CHANGED(self, self.__start_date.GetId(),
                            self.OnDateChanged)
        gs.Add(self.__start_date, 0, wx.ALL, 0)
        gs.Add(wx.StaticText(self, -1, 'End:'), 0, wx.ALL, 0)
        self.__end_date=wx.DatePickerCtrl(self, style=wx.DP_DROPDOWN | wx.DP_SHOWCENTURY)
        wx.EVT_DATE_CHANGED(self, self.__end_date.GetId(),
                            self.OnDateChanged)
        gs.Add(self.__end_date, 0, wx.ALL, 0)
        sbs.Add(gs, 1, wx.EXPAND|wx.ALL, 5)
        vbs.Add(sbs, 1, wx.EXPAND|wx.ALL, 5)
        # and the bottom buttons
        vbs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        for b in (('Print', -1, self.OnPrint),
                  ('Page Setup', -1, self.OnPageSetup),
                  ('Print Preview', -1, self.OnPrintPreview),
                  ('Help', wx.ID_HELP, self.OnHelp),
                  ('Close', wx.ID_CANCEL, self.OnClose)):
            btn=wx.Button(self, b[1], b[0])
            hbs.Add(btn, 0, wx.ALIGN_CENTER|wx.ALL, 5)
            if b[2] is not None:
                wx.EVT_BUTTON(self, btn.GetId(), b[2])
        # all done
        vbs.Add(hbs, 0, wx.ALIGN_CENTRE|wx.EXPAND|wx.ALL, 5)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def __gen_print_data(self):
        if not self.__date_changed and self.__html is not None:
            # already generate the print data, no changes needed
            return
        dt_start=self.__start_date.GetValue()
        dt_end=self.__end_date.GetValue()
        if not dt_start.IsValid() or not dt_end.IsValid():
            # invalid print range
            return
        # tell the calendar widget to give me the dict I need
        print_dict=self.__cal_widget.get_print_data(dt_start, dt_end)
        # generate the html data
        if self.__xcp is None:
            self.__xcp=xyaptu.xcopier(None)
            tmpl=open(guihelper.getresourcefile(self.__regular_template),
                      'rt').read()
            self.__xcp.setupxcopy(tmpl)
        if self.__dns is None:
            self.__dns={ 'common': __import__('common') }
            self.__dns['guihelper']=__import__('guihelper')
            self.__dns['events']=[]
        self.__dns['events']=print_dict
        self.__html=self.__xcp.xcopywithdns(self.__dns.copy())
        self.__date_changed=False

    def OnDateChanged(self, _):
        self.__date_changed=True
    def OnPrint(self, _):
        self.__gen_print_data()
        wx.GetApp().htmlprinter.PrintText(self.__html)
    def OnPageSetup(self, _):
        wx.GetApp().htmlprinter.PageSetup()
    def OnPrintPreview(self, _):
        self.__gen_print_data()
##        wx.GetApp().htmlprinter.PreviewText(self.__html)
        file(self.__tmp_file, 'wt').write(self.__html)
        webbrowser.open('file://localhost/'+self.__tmp_file)
    def OnHelp(self, _):
        pass
    def OnClose(self, _):
        try:
            # remove the temp file, ignore exception if file does not exist
            os.remove(self.__tmp_file)
        except:
            pass
        self.EndModal(wx.ID_CANCEL)
