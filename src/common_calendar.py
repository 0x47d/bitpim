### BITPIM
###
### Copyright (C) 2004 Joe Pham <djpham@netzero.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Common stuff for the Calendar Import functions"

# system modules
import sys

# wxPython modules
import wx
import wx.calendar
import wx.lib.mixins.listctrl as listmix

# local modules
import guiwidgets

no_end_date=(4000, 1, 1, 0, 0)

def bp_date_str(dict, v):
    if dict.get('allday', False):
        return '%04d-%02d-%02d'%v[:3]
    else:
        return '%04d-%02d-%02d  %02d:%02d'% v

def bp_alarm_str(dict, v):
    if dict.get('alarm', False):
        v=dict.get('alarm_value', 0)
        if v:
            return '-%d min'%v
        else:
            return 'Ontime'
    else:
        return ''

def category_str(dict, v):
    s=''
    for d in v:
        if len(d):
            if len(s):
                s+=', '+d
            else:
                s=d
    return s

#-------------------------------------------------------------------------------
class PreviewDialog(wx.Dialog, listmix.ColumnSorterMixin):
    def __init__(self, parent, id, title, col_labels, data={},
                 config_name=None,
                 style=wx.CAPTION|wx.MAXIMIZE_BOX| \
                 wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER):

        wx.Dialog.__init__(self, parent, id=id, title=title, style=style)
        
        self.__col_labels=col_labels
        self.__config_name=config_name
        self.itemDataMap={}
        # main boxsizer
        main_bs=wx.BoxSizer(wx.VERTICAL)
        # add custom controls here
        self.getcontrols(main_bs)
        # create a data preview list with supplied column labels
        self.__list=wx.ListView(self, wx.NewId())
        self.__image_list=wx.ImageList(16, 16)
        self.__ig_up=self.__image_list.Add(wx.ArtProvider_GetBitmap(wx.ART_GO_UP,
                                                             wx.ART_OTHER,
                                                             (16, 16)))
        self.__ig_dn=self.__image_list.Add(wx.ArtProvider_GetBitmap(wx.ART_GO_DOWN,
                                                             wx.ART_OTHER,
                                                             (16, 16)))
        self.__list.SetImageList(self.__image_list, wx.IMAGE_LIST_SMALL)
        li=wx.ListItem()
        li.m_mask=wx.LIST_MASK_TEXT | wx.LIST_MASK_IMAGE
        li.m_image=-1
        for i, d in enumerate(self.__col_labels):
            # insert a column with specified name and width
            li.m_text=d[1]
            self.__list.InsertColumnInfo(i, li)
            self.__list.SetColumnWidth(i, d[2])
        main_bs.Add(self.__list, 1, wx.EXPAND, 0)
        self.populate(data)
        # the Mixin sorter
        listmix.ColumnSorterMixin.__init__(self, len(col_labels))
        # now the buttons
        self.getpostcontrols(main_bs)
        # handle events
        # all done
        self.SetSizer(main_bs)
        self.SetAutoLayout(True)
        main_bs.Fit(self)
        # save my own size, if specified
        if config_name is not None:
            guiwidgets.set_size(config_name, self)
            wx.EVT_SIZE(self, self.__save_size)

    def getcontrols(self, main_bs):
        # controls to be placed above the preview pane
        # by default, put nothing.
        pass

    def getpostcontrols(self, main_bs):
        # control to be placed below the preview pane
        # by default, just add the OK & CANCEL button
        main_bs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        main_bs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        
    def populate(self, data):
        self.__list.DeleteAllItems()
        m={}
        m_count=0
        for k in data:
            d=data[k]
            col_idx=None
            mm={}
            for i, l in enumerate(self.__col_labels):
                entry=d.get(l[0], None)
                s=''
                if l[3] is None:
                    s=str(entry)
                else:
                    s=l[3](d, entry)
                mm[i]=s
                if i:
                    self.__list.SetStringItem(col_idx, i, s)
                else:
                    col_idx=self.__list.InsertImageStringItem(sys.maxint, s, -1)
            self.__list.SetItemData(col_idx, m_count)
            m[m_count]=mm
            m_count += 1
        self.itemDataMap=m

    def GetListCtrl(self):
        return self.__list

    def GetSortImages(self):
        return (self.__ig_dn, self.__ig_up)

    def __save_size(self, evt):
        if self.__config_name is not None:
            guiwidgets.save_size(self.__config_name, self.GetRect())
        evt.Skip()

#-------------------------------------------------------------------------------
class FilterDialog(wx.Dialog):
    def __init__(self, parent, id, caption, categories, style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, id,
                           title=caption, style=style)
        # the main box sizer
        bs=wx.BoxSizer(wx.VERTICAL)
        # the flex grid sizers for the editable items
        fgs=wx.FlexGridSizer(3, 3, 0, 5)
        fgs.Add(wx.StaticText(self, -1, 'Start Date:'), 0, wx.ALIGN_CENTRE, 0)
        self.__start_date_chkbox=wx.CheckBox(self, id=wx.NewId())
        fgs.Add(self.__start_date_chkbox, 0, wx.ALIGN_CENTRE, 0)
        self.__start_date=wx.calendar.CalendarCtrl(self, -1, wx.DateTime_Now(),
                                          style = wx.calendar.CAL_SUNDAY_FIRST
                                          | wx.calendar.CAL_SEQUENTIAL_MONTH_SELECTION)
        self.__start_date.Disable()
        fgs.Add(self.__start_date, 1, wx.ALIGN_LEFT, 5)
        fgs.Add(wx.StaticText(self, -1, 'End Date:'), 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE, 0)
        self.__end_date_chkbox=wx.CheckBox(self, id=wx.NewId())
        fgs.Add(self.__end_date_chkbox, 0, wx.ALIGN_CENTRE, 0)
        self.__end_date=wx.calendar.CalendarCtrl(self, -1, wx.DateTime_Now(),
                                          style = wx.calendar.CAL_SUNDAY_FIRST
                                          | wx.calendar.CAL_SEQUENTIAL_MONTH_SELECTION)
        self.__end_date.Disable()
        fgs.Add(self.__end_date, 1, wx.ALIGN_LEFT, 5)
        fgs.Add(wx.StaticText(self, -1, 'Categories:'), 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE, 0)
        self.__cat_chkbox=wx.CheckBox(self, id=wx.NewId())
        fgs.Add(self.__cat_chkbox, 0, wx.ALIGN_CENTRE, 0)
        for i,c in enumerate(categories):
            if not len(c):
                categories[i]='<None>'
        self.__cats=wx.CheckListBox(self, choices=categories, size=(180, 50))
        self.__cats.Disable()
        fgs.Add(self.__cats, 0, wx.ALIGN_LEFT, 5)
        bs.Add(fgs, 1, wx.EXPAND|wx.ALL, 5)
        # the buttons
        bs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        bs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        # event handles
        wx.EVT_CHECKBOX(self, self.__start_date_chkbox.GetId(), self.OnCheckBox)
        wx.EVT_CHECKBOX(self, self.__end_date_chkbox.GetId(), self.OnCheckBox)
        wx.EVT_CHECKBOX(self, self.__cat_chkbox.GetId(), self.OnCheckBox)
        # all done
        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

    def __set_date(self, chk_box, cal, d):
        if d is None:
            chk_box.SetValue(False)
            cal.Disable()
        else:
            chk_box.SetValue(True)
            cal.Enable()
            dt=wx.DateTime()
            dt.Set(d[2], year=d[0], month=d[1]-1)
            cal.SetDate(dt)

    def __set_cats(self, chk_box, c, data):
        if data is None:
            chk_box.SetValue(False)
            c.Disable()
        else:
            chk_box.SetValue(True)
            c.Enable()
            for i,d in enumerate(data):
                if not len(d):
                    data[i]='<None>'
            for i in range(c.GetCount()):
                c.Check(i, c.GetString(i) in data)
          
    def set(self, data):
        self.__set_date(self.__start_date_chkbox, self.__start_date,
                        data.get('start', None))
        self.__set_date(self.__end_date_chkbox, self.__end_date,
                        data.get('end', None))
        self.__set_cats(self.__cat_chkbox, self.__cats, data.get('categories', None))

    def get(self):
        r={}
        if self.__start_date_chkbox.GetValue():
            dt=self.__start_date.GetDate()
            r['start']=(dt.GetYear(), dt.GetMonth()+1, dt.GetDay())
        else:
            r['start']=None
        if self.__end_date_chkbox.GetValue():
            dt=self.__end_date.GetDate()
            r['end']=(dt.GetYear(), dt.GetMonth()+1, dt.GetDay())
        else:
            r['end']=None
        if self.__cat_chkbox.GetValue():
            c=[]
            for i in range(self.__cats.GetCount()):
                if self.__cats.IsChecked(i):
                    s=self.__cats.GetString(i)
                    if s=='<None>':
                        c.append('')
                    else:
                        c.append(s)
            r['categories']=c
        else:
            r['categories']=None
        return r
    
    def OnCheckBox(self, evt):
        evt_id=evt.GetId()
        if evt_id==self.__start_date_chkbox.GetId():
            w1,w2=self.__start_date_chkbox, self.__start_date
        elif evt_id==self.__end_date_chkbox.GetId():
            w1,w2=self.__end_date_chkbox, self.__end_date
        else:
            w1,w2=self.__cat_chkbox, self.__cats
        if w1.GetValue():
            w2.Enable()
        else:
            w2.Disable()
