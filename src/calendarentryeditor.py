### BITPIM
###
### Copyright (C) 2003-2004 Joe Pham <djpham@netzero.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

import calendar
import copy
import datetime
import time

import wx
import wx.lib
import wx.lib.masked.textctrl
import wx.lib.intctrl
import wx.lib.scrolledpanel as scrolled

import bpcalendar
import helpids
import phonebookentryeditor as pb_editor
import pubsub

class RepeatEditor(pb_editor.DirtyUIBase):
    __repeat_type= {
        'daily': 1,
        'weekly': 2,
        'monthly': 3,
        'yearly': 4 }
    __repeat_options=('None', 'Daily', 'Weekly', 'Monthly', 'Yearly')
    __dow=('Sun', 'Mon', 'Tues', 'Wed',' Thu', 'Fri', 'Sat')
    __daily_option_index=0
    __weekly_option_index=1
    
    def __init__(self, parent, _):
        pb_editor.DirtyUIBase.__init__(self, parent)
        # overall container
        self.__main_bs=wx.BoxSizer(wx.HORIZONTAL)
        # vertical sizebox & checkboxes for different repreat options
        self.__repeat_option_rb = wx.RadioBox(
                self, -1, "Repeat Types:", wx.DefaultPosition, wx.DefaultSize,
                self.__repeat_options, 1, wx.RA_SPECIFY_COLS)
        wx.EVT_RADIOBOX(self, self.__repeat_option_rb.GetId(), self.OnRepeatType)
        self.__main_bs.Add(self.__repeat_option_rb, 0, wx.LEFT, 5)
        # daily options widgets
        self.__option_bs=wx.BoxSizer(wx.VERTICAL)
        vbs=wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Daily Options:'), wx.VERTICAL)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        self.__dl_every_nday=wx.RadioButton(self, -1, 'Every ', style=wx.RB_GROUP)
        self.__dl_every_nday.SetValue(True)
        self.__dl_every_wday=wx.RadioButton(self, -1, 'Every Weekday')
        wx.EVT_RADIOBUTTON(self, self.__dl_every_nday.GetId(), self.OnDirtyUI)
        wx.EVT_RADIOBUTTON(self, self.__dl_every_wday.GetId(), self.OnDirtyUI)
        hbs.Add(self.__dl_every_nday, 0, wx.LEFT, 0)
        self.__dl_interval=wx.TextCtrl(self, -1, '1')
        wx.EVT_TEXT(self, self.__dl_interval.GetId(), self.OnDirtyUI)
        hbs.Add(self.__dl_interval, 0, wx.LEFT, 0)
        hbs.Add(wx.StaticText(self, -1, ' day(s)'), 0, wx.LEFT, 0)
        vbs.Add(hbs, 0, wx.LEFT|wx.TOP, 10)
        vbs.Add(self.__dl_every_wday, 0, wx.LEFT, 10)
        self.__option_bs.Add(vbs, 0, wx.LEFT, 5)
        self.__daily_option_bs=vbs
        # weekly options widgets
        vbs=wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Weekly Options:'), wx.VERTICAL)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, 'Every '),0, wx.LEFT, 0)
        self.__wl_interval=wx.TextCtrl(self, -1, '1')
        wx.EVT_TEXT(self, self.__wl_interval.GetId(), self.OnDirtyUI)
        hbs.Add(self.__wl_interval, 0, wx.LEFT, 0)
        hbs.Add(wx.StaticText(self, -1, ' week(s)'), 0, wx.LEFT, 0)
        vbs.Add(hbs, 0, wx.LEFT|wx.TOP, 10)
        vbs.Add(wx.StaticText(self, -1, 'On:'), 0, wx.LEFT, 10)
        hbs=wx.GridSizer(2, 4)
        self.__wl_dow={}
        for i, n in enumerate(self.__dow):
            self.__wl_dow[i]=wx.CheckBox(self, -1, n)
            wx.EVT_CHECKBOX(self, self.__wl_dow[i].GetId(), self.OnDirtyUI)
            hbs.Add(self.__wl_dow[i], 0, wx.LEFT|wx.TOP, 5)
        vbs.Add(hbs, 0, wx.LEFT, 5)
        self.__option_bs.Add(vbs, 0, wx.LEFT, 5)
        self.__weekly_option_bs=vbs
        self.__main_bs.Add(self.__option_bs, 0, wx.LEFT, 5)
        # all done
        self.SetSizer(self.__main_bs)
        self.SetAutoLayout(True)
        self.__main_bs.Fit(self)
        self.OnRepeatType(None)

    def populate(self, data):
        if data is None:
            self.__repeat_option_rb.SetSelection(0)
            self.OnRepeatType(None)
            return
        rt=data.repeat_type
        if rt==data.daily:
            self.__repeat_option_rb.SetSelection(1)
            if data.interval:
                self.__dl_every_nday.SetValue(True)
                self.__dl_interval.SetValue(`data.interval`)
            else:
                self.__dl_every_wday.SetValue(True)
                self.__dl_interval.SetValue('')
        elif rt==data.weekly:
            self.__repeat_option_rb.SetSelection(2)
            self.__wl_interval.SetValue(`data.interval`)
            dow_mask=data.dow
            for i in range(len(self.__wl_dow)):
                b=((1<<i)&dow_mask)!=0
                self.__wl_dow[i].SetValue(b)
        elif rt==data.monthly:
            self.__repeat_option_rb.SetSelection(3)
        else:
            self.__repeat_option_rb.SetSelection(4)
        self.OnRepeatType(None)

    def Set(self, data):
        self.ignore_dirty=True
        self.populate(data)
        self.dirty=self.ignore_dirty=False

    def Get(self):
        self.dirty=self.ignore_dirty=False
        rt=self.__repeat_option_rb.GetSelection()
        if rt==0:
            # No repeat
            return None
        r=bpcalendar.RepeatEntry()
        if rt==1:
            # daily
            r.repeat_type=r.daily
            try:
                b=self.__dl_every_nday.GetValue()
            except:
                b=False
                self.__dl_every_nday.SetValue(False)
            if b:
                try:
                    r.interval=int(self.__dl_interval.GetValue())
                except:
                    # default to 1
                    r.interval=1
            else:
                r.interval=0
        elif rt==2:
            # weekly
            r.repeat_type=r.weekly
            try:
                r.interval=int(self.__wl_interval.GetValue())
            except:
                # default to 1
                r.interval=1
            m=0
            for i in range(len(self.__wl_dow)):
                if self.__wl_dow[i].GetValue():
                    m=m|(1<<i)
            r.dow=m
        elif rt==3:
            # monthly
            r.repeat_type=r.monthly
        else:
            r.repeat_type=r.yearly
        return r

    def OnRepeatType(self, evt):
        s=self.__repeat_option_rb.GetSelection()
        self.__option_bs.Hide(self.__weekly_option_index)
        self.__option_bs.Hide(self.__daily_option_index)
        if s==1:
            self.__option_bs.Show(self.__daily_option_index)
        elif s==2:
            self.__option_bs.Show(self.__weekly_option_index)
        self.__option_bs.Layout()
        self.OnDirtyUI(evt)

#------------------------------------------------------------------------------
class GeneralEditor(pb_editor.DirtyUIBase):
    __dict_key_index=0
    __label_index=1
    __class_index=2
    __get_index=3
    __set_index=4
    __w_index=5
    def __init__(self, parent, _):
        # base clase
        pb_editor.DirtyUIBase.__init__(self, parent)
        # structure to hold all the widgets of this panel
        self.__fields=[
            ['description', 'Summary:', DVTextControl, None, None, None],
            ['location', 'Location:', DVTextControl, None, None, None],
            ['allday', 'All-Day:', wx.CheckBox, None, None, None],
            ['start', 'From:', DVDateTimeControl, None, self.__set_start_datetime, None],
            ['end', 'To:', DVDateTimeControl, None, self.__set_end_datetime, None],
            ['priority', 'Priority:', None, self.__get_priority, self.__set_priority, None],
            ['alarm', 'Alarm:', DVIntControl, None, None, None]
            ]
        # overall container
        vbs=wx.StaticBoxSizer(wx.StaticBox(self, -1), wx.VERTICAL)
        # instantiate the widgets
        self.__w={}
        gs=wx.FlexGridSizer(-1,2,5,5)
        gs.AddGrowableCol(1)
        for n in self.__fields:
            desc=n[self.__label_index]
            t=wx.StaticText(self, -1, desc, style=wx.ALIGN_LEFT)
            gs.Add(t)
            if desc=='Priority:':
                c=wx.ComboBox(self, -1, "", (-1, -1), (-1, -1),
                              ['<None>', '1 - Highest', '2', '3', '4', '5 - Normal',
                               '6', '7' ,'8', '9', '10 - Lowest'], wx.CB_DROPDOWN)
            else:
                c=n[self.__class_index](self, -1)
            gs.Add(c, 0, wx.EXPAND, 0)
            n[self.__w_index]=self.__w[n[self.__dict_key_index]]=c
        vbs.Add(gs, 0, wx.EXPAND|wx.ALL, 5)
        # event handlers
        wx.EVT_CHECKBOX(self, self.__w['allday'].GetId(), self.OnAllday)
        wx.EVT_COMBOBOX(self, self.__w['priority'].GetId(), self.OnDirtyUI)
        # all done
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def OnMakeDirty(self, evt):
        self.OnDirtyUI(evt)

    def OnAllday(self, evt):
        v=evt.IsChecked()
        self.__w['start'].SetAllday(v)
        self.__w['end'].SetAllday(v)
        self.OnDirtyUI(evt)

    def IsValid(self):
        # validate and return T if so or F otherwise
        # check for valid date/time entries
        for w in (self.__w['start'], self.__w['end']):
            if not w.IsValid() or w.IsEmpty():
                w.SetFocus()
                wx.Bell()
                return False
        # whine if end is before start
        start=datetime.datetime(*self.__w['start'].GetValue())
        end=datetime.datetime(*self.__w['end'].GetValue())
        if start>end:
            # scold the user
            dlg=wx.MessageDialog(self, "End date and time is before start!", "Time Travel Attempt Detected",
                                wx.OK|wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            dlg.Destroy()
            # move focus
            self.__w['end'].SetFocus()
            return False
        return True

    def Set(self, data):
        self.ignore_dirty=True
        if data is None:
            for n in self.__fields:
                n[self.__w_index].Enable(False)
        else:
            for n in self.__fields:
                w=n[self.__w_index]
                w.Enable(True)
                if n[self.__set_index] is None:
                    w.SetValue(getattr(data, n[self.__dict_key_index]))
                else:
                    n[self.__set_index](w, data)
        self.ignore_dirty=self.dirty=False

    def Get(self, data):
        self.ignore_dirty=self.dirty=False
        if data is None:
            return
        for n in self.__fields:
            w=n[self.__w_index]
            if n[self.__get_index] is None:
                v=w.GetValue()
            else:
                v=n[self.__get_index](w, None)
            setattr(data, n[self.__dict_key_index], v)
        
    def __set_priority(self, w, entry):
        p=entry.priority
        if p is None:
            w.SetSelection(0)
        else:
            w.SetSelection(p)
    def __get_priority(self, w, _):
        s=w.GetSelection()
        if s:
            return s
        else:
            return None

    def __set_start_datetime(self, w, entry):
        w.SetAllday(entry.allday, entry.start)

    def __set_end_datetime(self, w, entry):
        w.SetAllday(entry.allday, entry.end)

#------------------------------------------------------------------------------
class CategoryEditor(pb_editor.DirtyUIBase):

    # we have to have an entry with a special string for the unnamed string

    unnamed="Select:"

    def __init__(self, parent, pos):
        pb_editor.DirtyUIBase.__init__(self, parent)
        hs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Category"), wx.HORIZONTAL)

        self.categories=[]
        self.category=wx.ListBox(self, -1, choices=self.categories)
        pubsub.subscribe(self.OnUpdateCategories, pubsub.ALL_CATEGORIES)
        pubsub.publish(pubsub.REQUEST_CATEGORIES)
        # a boxsizer for the master category list
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(wx.StaticText(self, -1, 'Master Category'), 0,
                wx.TOP|wx.LEFT, 5)
        vbs.Add(self.category, 1, wx.EXPAND|wx.ALL, 5)
        hs.Add(vbs, 1, wx.EXPAND|wx.ALL, 5)
        # a boxsizer for the buttons
        vbs=wx.BoxSizer(wx.VERTICAL)
        self.but=wx.Button(self, wx.NewId(), "Manage Categories:")
        add_btn=wx.Button(self, -1, 'Add ->')
        del_btn=wx.Button(self, -1, '<- Remove')
        vbs.Add(self.but, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        vbs.Add(add_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        vbs.Add(del_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        hs.Add(vbs, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        wx.EVT_BUTTON(self, add_btn.GetId(), self.OnAddCategory)
        wx.EVT_BUTTON(self, del_btn.GetId(), self.OnDelCategory)
        # box sizer for the selected category
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(wx.StaticText(self, -1, 'Selected Category:'), 0,
                wx.TOP|wx.LEFT, 5)
        self.__my_category=wx.ListBox(self, -1)
        vbs.Add(self.__my_category, 1, wx.EXPAND|wx.ALL, 5)
        hs.Add(vbs, 1, wx.EXPAND|wx.ALL, 5)
        wx.EVT_BUTTON(self, self.but.GetId(), self.OnManageCategories)

        self.SetSizer(hs)
        hs.Fit(self)

    def OnManageCategories(self, _):
        dlg=pb_editor.CategoryManager(self)
        dlg.ShowModal()

    def OnUpdateCategories(self, msg):
        cats=msg.data[:]
        if self.categories!=cats:
            self.categories=cats
            sel=self.category.GetStringSelection()
            self.category.Clear()
            for i in cats:
                self.category.Append(i)
            try:
                if len(sel):
                    self.category.SetStringSelection(sel)
            except:
                pass

    def Get(self):
        self.ignore_dirty=self.dirty=False
        r=[]
        count=self.__my_category.GetCount()
        if count==0:
            return r
        for i in range(count):
            r.append({ 'category': self.__my_category.GetString(i) })
        return r

    def Set(self, data):
        self.ignore_dirty=True
        self.__my_category.Clear()
        if data is None or len(data)==0:
            # none or empty list, do nothing
            return
        for n in data:
            v=n.get('category', None)
            if v is not None:
                self.__my_category.Append(v)
        self.ignore_dirty=self.dirty=False

    def OnAddCategory(self, evt):
        v=self.category.GetStringSelection()
        if not len(v):
            # no selection made, do nothing
            return
        self.ignore_dirty=True
        self.__my_category.Append(v)
        self.__my_category.SetStringSelection(v)
        self.ignore_dirty=False
        self.OnDirtyUI(evt)

    def OnDelCategory(self, evt):
        v=self.__my_category.GetSelection()
        if v==wx.NOT_FOUND:
            # no selection, do nothing
            return
        self.ignore_dirty=True
        self.__my_category.Delete(v)
        self.ignore_dirty=False
        self.OnDirtyUI(evt)

#------------------------------------------------------------------------------
class Editor(wx.Dialog):

    # ids for the various controls
    ID_PREV=1
    ID_NEXT=2
    ID_ADD=3
    ID_DELETE=4
    ID_CLOSE=5
    ID_LISTBOX=6
    ID_SAVE=11
    ID_HELP=12
    ID_REVERT=13

    # results on asking if the user wants to change the original (repeating) entry, just
    # this instance, or cancel
    ANSWER_ORIGINAL=1
    ANSWER_THIS=2
    ANSWER_CANCEL=3
    __dict_key_index=0
    __label_index=1
    __get_index=2
    __set_index=3
    __w_index=4
    # notebook items
    __general_page=0
    __repeat_page=1
    __notes_page=2
    __categories_page=3
    __wallpapers_page=4
    __ringtones_page=5
    __last_page=6
    __items=[
        ("General", None, GeneralEditor),
        ("Repeat", 'repeat', RepeatEditor),
        ("Notes", "notes", pb_editor.MemoEditor),
        ("Categories", "categories", CategoryEditor),
        ("Wallpapers", "wallpapers", pb_editor.WallpaperEditor),
        ("Ringtones", "ringtones", pb_editor.RingtoneEditor),
        ]
    def __init__(self, parent):

        wx.Dialog.__init__(self, parent, -1, 'Calendar Entry Editor',
                           wx.DefaultPosition, wx.Size(760, 580),
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        # the parent is the BPCalenda widget, save it
        self.cw=parent  # also the BPCalendar object
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
        self.ignoredirty=True
        
        # overall container
        vbs=wx.BoxSizer(wx.VERTICAL)
        
        self.__prev_btn=wx.Button(self, self.ID_PREV, "<", style=wx.BU_EXACTFIT)
        self.__next_btn=wx.Button(self, self.ID_NEXT, ">", style=wx.BU_EXACTFIT)
        self.title=wx.StaticText(self, -1, "Date here", style=wx.ALIGN_CENTRE|wx.ST_NO_AUTORESIZE)

        # top row container 
        hbs1=wx.BoxSizer(wx.HORIZONTAL)
        hbs1.Add(self.__prev_btn, 0, wx.EXPAND)
        hbs1.Add(self.title, 1, wx.EXPAND)
        hbs1.Add(self.__next_btn, 0, wx.EXPAND)
        vbs.Add(hbs1, 0, wx.TOP|wx.EXPAND, 10)

        # list box and two buttons below
        self.listbox=wx.ListBox(self, self.ID_LISTBOX, style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_NEEDED_SB)
        self.__add_btn=wx.Button(self, self.ID_ADD, "New")
        hbs2=wx.BoxSizer(wx.HORIZONTAL)
        hbs2.Add(self.__add_btn, 1, wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT, border=5)
        
        # sizer for listbox
        lbs=wx.BoxSizer(wx.VERTICAL)
        lbs.Add(self.listbox, 1, wx.EXPAND|wx.BOTTOM, border=5)
        lbs.Add(hbs2, 0, wx.EXPAND)

        # right hand bit with all fields
        self.__nb=wx.Notebook(self, -1)
        self.__widgets=[]
        for i, (name, key, klass) in enumerate(self.__items):
            if name in ('Ringtones', 'Wallpapers'):
                self.__widgets.append(klass(self.__nb, parent, False))
            else:
                self.__widgets.append(klass(self.__nb, parent))
            self.__nb.AddPage(self.__widgets[i], name)
            
        # buttons below fields
        self.__delete_btn=wx.Button(self, self.ID_DELETE, "Delete")
        self.__revert_btn=wx.Button(self, self.ID_REVERT, "Revert")
        self.__save_btn=wx.Button(self, self.ID_SAVE, "Save")

        hbs4=wx.BoxSizer(wx.HORIZONTAL)
        hbs4.Add(self.__delete_btn, 1, wx.ALIGN_CENTRE|wx.LEFT, border=10)
        hbs4.Add(self.__revert_btn, 1, wx.ALIGN_CENTRE|wx.LEFT|wx.RIGHT, border=10)
        hbs4.Add(self.__save_btn, 1, wx.ALIGN_CENTRE|wx.RIGHT, border=10)

        # fields and buttons together
        vbs2=wx.BoxSizer(wx.VERTICAL)
        vbs2.Add(self.__nb, 1, wx.EXPAND|wx.BOTTOM, border=5)
        vbs2.Add(hbs4, 0, wx.EXPAND|wx.ALIGN_CENTRE)

        # container for everything below title row
        hbs3=wx.BoxSizer(wx.HORIZONTAL)
        hbs3.Add(lbs, 1, wx.EXPAND|wx.ALL, 5)
        hbs3.Add(vbs2, 2, wx.EXPAND|wx.ALL, 5)
        vbs.Add(hbs3, 1, wx.EXPAND)
        # the standard buttons
        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)
        self.SetSize((560, 380))
        # delete is disabled until an item is selected
        self.__delete_btn.Enable(False)

        wx.EVT_LISTBOX(self, self.ID_LISTBOX, self.OnListBoxItem)
        wx.EVT_LISTBOX_DCLICK(self, self.ID_LISTBOX, self.OnListBoxItem)
        wx.EVT_BUTTON(self, self.ID_SAVE, self.OnSaveButton)
        wx.EVT_BUTTON(self, self.ID_REVERT, self.OnRevertButton)
        wx.EVT_BUTTON(self, self.ID_ADD, self.OnNewButton)
        wx.EVT_BUTTON(self, self.ID_DELETE, self.OnDeleteButton)
        wx.EVT_BUTTON(self, self.ID_PREV, self.OnPrevDayButton)
        wx.EVT_BUTTON(self, self.ID_NEXT, self.OnNextDayButton)
        # callbacks for the standard buttons
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)
        wx.EVT_BUTTON(self, wx.ID_CANCEL, self.OnCancel)
        wx.EVT_BUTTON(self, wx.ID_HELP, lambda _: wx.GetApp().displayhelpid(helpids.ID_EDITING_CALENDAR_EVENTS))
        # DIRTY UI Event handlers
        for w in self.__widgets:
            pb_editor.EVT_DIRTY_UI(self, w.GetId(), self.OnMakeDirty)
        self.ignoredirty=False
        self.setdirty(False)

    def OnListBoxItem(self, evt=None):
        """Callback for when user clicks on an event in the listbox"""
        self.updatefields(self.getcurrententry())
        self.setdirty(False)
        self.__delete_btn.Enable(True)

    def getcurrententry(self):
        """Returns the entry currently being viewed

        @Note: this returns the unedited form of the entry"""
        i=self.listbox.GetSelection()
        if i==-1:
            return None
        return self.getentry(i)

    def getentry(self, num):
        """maps from entry number in listbox to an entry in entries

        @type num: int
        @rtype: entry(dict)"""
        return self.entries[self.entrymap[num]]

    def OnSaveButton(self, evt):
        """Callback for when user presses save"""

        # check if the dates are ok
        if not self.__widgets[self.__general_page].IsValid():
            return

        # lets roll ..
        entry=self.getcurrententry()

        # is it a repeat?
        res=self.ANSWER_ORIGINAL
        if entry.repeat is not None:
            # ask the user
            res=self.AskAboutRepeatChange()
            if res==self.ANSWER_CANCEL:
                return
        # where do we get newentry template from?
        if res==self.ANSWER_ORIGINAL:
            newentry=copy.copy(entry)
        else:
            newentry=self.cw.newentryfactory(*self.date)

        # update the fields from the general tab
        self.__widgets[self.__general_page].Get(newentry)
        if res==self.ANSWER_THIS:
            # change this event only, change the start & end date to this date
            newentry.start=list(self.date)+list(newentry.start[3:])
            newentry.end=list(self.date)+list(newentry.end[3:])
            # if we are changing a repeat, reset the new entry's repeat is off
            newentry.repeat=None
        else:
            # get data from the repeat tab
            old_repeat=newentry.repeat
            newentry.repeat=self.__widgets[self.__repeat_page].Get()
            if old_repeat is not None:
                newentry.repeat.suppressed=old_repeat.suppressed
        # and other tabs as well
        newentry.notes=self.__widgets[self.__notes_page].Get().get('memo', None)
        newentry.categories=self.__widgets[self.__categories_page].Get()
        newentry.wallpaper=self.__widgets[self.__wallpapers_page].Get().get('wallpaper', None)
        newentry.ringtone=self.__widgets[self.__ringtones_page].Get().get('ringtone', None)
        # got the data
        # update calendar widget
        if res==self.ANSWER_ORIGINAL:
            self.cw.ChangeEntry(entry, newentry)
        else:
            # delete the repeat and add this new entry
            self.cw.DeleteEntryRepeat(entry, *self.date)
            self.cw.AddEntry(newentry)
        if __debug__:
            print 'Editor.OnSaveButton: updated entry:'
            print newentry.get()
            print 'Equivalent DB dict:'
            print bpcalendar.CalendarDataObject(newentry)
        # tidy up
        self.setdirty(False)
        # did the user change the date on us?
        date=tuple(newentry.start[:3])
        if tuple(self.date)!=date:
            self.cw.showday(*date)
            self.cw.setselection(*date)
            self.setdate(*date)
        else:
            self.refreshentries()
        self.updatelistbox(newentry.id)

    def OnOk(self, evt):
        # save the current entry & exit
        if self.dirty:
            self.OnSaveButton(None)
        self.setdirty(False)
        evt.Skip()

    def OnCancel(self, evt):
        # just exit
        self.setdirty(False)
        evt.Skip()
    
    def OnRevertButton(self, evt):
        # We basically pretend the user has selected the item in the listbox again (which they
        # can't actually do as it is disabled)
        self.OnListBoxItem()

    def OnNewButton(self, evt):
        entry=self.cw.newentryfactory(*self.date)
        self.cw.AddEntry(entry)
        self.refreshentries()
        self.updatelistbox(entry.id)

    def OnDeleteButton(self, evt):
        entry=self.getcurrententry()
        # is it a repeat?
        res=self.ANSWER_ORIGINAL
        if entry.repeat is not None:
            # ask the user
            res=self.AskAboutRepeatDelete()
            if res==self.ANSWER_CANCEL:
                return
        enum=self.listbox.GetSelection()
        if enum+1<len(self.entrymap):
            # try and find entry after current one
            newpos=self.getentry(enum+1).id
        elif enum-1>=0:
            # entry before as we are deleting last entry
            newpos=self.getentry(enum-1).id
        else:
            newpos=None
        if res==self.ANSWER_ORIGINAL:
            self.cw.DeleteEntry(entry)
        else:
            self.cw.DeleteEntryRepeat(entry, *self.date)
        self.setdirty(False)
        self.refreshentries()
        self.updatelistbox(newpos)

    def OnPrevDayButton(self, evt):
        d=datetime.date(*self.date)-datetime.timedelta(1)
        self.setdate(d.year, d.month, d.day)
        self.cw.setday(d.year, d.month, d.day)

    def OnNextDayButton(self, evt):
        d=datetime.date(*self.date)+datetime.timedelta(1)
        self.setdate(d.year, d.month, d.day)
        self.cw.setday(d.year, d.month, d.day)
    
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
            if entry.allday:
                e=( entry.start[3:5], entry.end[3:5], entry.description, index)
            else:
                e=(None, None, entry.description, index)
            self.entrymap.append(e)
        # time ordered
        self.entrymap.sort()
        # now undecorate
        self.entrymap=[index for ign0, ign1, ign2, index in self.entrymap]
        # add listbox entries
        for curpos, index in enumerate(self.entrymap):
            e=self.entries[index]
            if e.id==entrytoselect:
                selectitem=curpos
##            if 0: # ampm/miltime config here ::TODO::
##                str="%2d:%02d" % (e['start'][3], e['start'][4])
##            else:
            if e.allday:
                str=e.description
            else:
                hr=e.start[3]
                ap="am"
                if hr>=12:
                    ap="pm"
                    hr-=12
                if hr==0: hr=12
                str="%2d:%02d %s" % (hr, e.start[4], ap)
                str+=" "+e.description
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
            self.__delete_btn.Enable(False)

    def updatefields(self, entry):
        self.ignoredirty=True
        self.__widgets[self.__general_page].Set(entry)
        # populate the other tabs with current entry data
        if entry is None:
            # clear everything out
            for i in range(self.__repeat_page, self.__last_page):
                self.__widgets[i].Set(None)
                self.__widgets[i].Enable(False)
            return
        # there's data, setting each page accordingly
        for i in range(self.__repeat_page, self.__last_page):
            self.__widgets[i].Enable(True)
        self.__widgets[self.__repeat_page].Set(entry.repeat)
        self.__widgets[self.__notes_page].Set({ 'memo': entry.notes })
        self.__widgets[self.__categories_page].Set(entry.categories)
        self.__widgets[self.__wallpapers_page].Set( \
            { 'wallpaper': entry.wallpaper, 'type': 'calendar' })
        self.__widgets[self.__ringtones_page].Set( \
            { 'ringtone': entry.ringtone, 'type': 'calendar' })
        self.ignoredirty=False

    # called from various widget update callbacks
    def OnMakeDirty(self, _=None):
        """A public function you can call that will set the dirty flag"""
        if self.dirty or self.ignoredirty or not self.IsShown():
            # already dirty, no need to make it worse
            return
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
            self.__save_btn.Enable(True)
            self.__revert_btn.Enable(True)
            # disable close, left, right, new
            self.__prev_btn.Enable(False)
            self.__next_btn.Enable(False)
            self.__add_btn.Enable(False)
            # can't play with listbox now
            self.listbox.Enable(False)
        else:
            # The data is now clean and saved/reverted or deleted
            
            # disable save, revert,
            self.__save_btn.Enable(False)
            self.__revert_btn.Enable(False)

            # enable delete, close, left, right, new
            self.__delete_btn.Enable(len(self.entries)>0) # only enable if there are entries
            self.__prev_btn.Enable(True)
            self.__next_btn.Enable(True)
            self.__add_btn.Enable(True)

            # can choose another item in listbox
            self.listbox.Enable(True)

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
#------------------------------------------------------------------------------    
# We derive from wxPanel not the control directly.  If we derive from
# wx.MaskedTextCtrl then all hell breaks loose as our {Get|Set}Value
# methods make the control malfunction big time
class DVDateTimeControl(wx.Panel):
    """A datetime control customised to work in the dayview editor"""
    def __init__(self,parent,id):
        self.__allday=False
        self.__datetime_format="EUDATETIMEYYYYMMDD.HHMM"
        self.__date_format='EUDATEYYYYMMDD.'
        wx.Panel.__init__(self, parent, -1)
        self.c=wx.lib.masked.textctrl.TextCtrl(\
            self, id, "", autoformat=self.__datetime_format,
            emptyInvalid=True,
            emptyBackgroundColour='Red',
            invalidBackgroundColour='Red')
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
        if self.__allday:
            str="%04d%02d%02d" % tuple(v[:3])
        else:
            ap="AM"
            v=list(v)
            if v[3]>12:
                v[3]-=12
                ap="PM"
            elif v[3]==0:
                v[3]=12
            elif v[3]==12:
                ap="PM"
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
        if val is not None:
            res.append(val)
        if len(res)==3:
            res += [0,0]
        elif len(res)==5:
            # fixup am/pm
            if str[-2]=='P' or str[-2]=='p':
                if res[3]!=12: # 12pm is midday and left alone
                    res[3]+=12
            elif res[3]==12: # 12 am
                res[3]=0

        return res

    def IsValid(self):
        return self.c.IsValid()
    def IsEmpty(self):
        return self.c.IsEmpty()

    def SetAllday(self, allday, v=None):
        if allday==self.__allday and v is None:
            return
        if v is None:
            v=self.GetValue()
        if allday != self.__allday:
            self.__allday=allday
            if self.__allday:
                self.c.SetCtrlParameters(autoformat=self.__date_format)
            else:
                self.c.SetCtrlParameters(autoformat=self.__datetime_format)
        self.SetValue(v)

#------------------------------------------------------------------------------    
class DVIntControl(wx.lib.intctrl.IntCtrl):
    # shows integer values
    def __init__(self, parent, id):
        wx.lib.intctrl.IntCtrl.__init__(self, parent, id, limited=True)
        wx.lib.intctrl.EVT_INT(self, id, parent.OnMakeDirty)

    def SetValue(self, v):
        if v is None:
            v=-1
        wx.lib.intctrl.IntCtrl.SetValue(self,v)
        
#------------------------------------------------------------------------------    
class DVTextControl(wx.TextCtrl):
    def __init__(self, parent, id, value=""):
        if value is None:
            value=""
        wx.TextCtrl.__init__(self, parent, id, value)
        wx.EVT_TEXT(self, id, parent.OnMakeDirty)

    def SetValue(self, v):
        if v is None: v=""
        wx.TextCtrl.SetValue(self,v)

#-------------------------------------------------------------------------------
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
