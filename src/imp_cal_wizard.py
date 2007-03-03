#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

""" Handle Import Calendar wizard
"""

# System

# wx
import wx
import wx.wizard as wiz
import  wx.lib.scrolledpanel as scrolled

# BitPim
import common_calendar
import importexport
import setphone_wizard

# modules constants
IMP_OPTION_REPLACEALL=0
IMP_OPTION_ADD=1

#-------------------------------------------------------------------------------
class ImportTypePage(setphone_wizard.MyPage):
    def __init__(self, parent):
        self._data=importexport.GetCalendarImports()
        super(ImportTypePage, self).__init__(parent,
                                             'Select Calendar Import Type')
        self._populate()

    def GetMyControls(self):
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(wx.StaticText(self, -1, 'Import Calendar Type:'), 0,
                wx.EXPAND|wx.ALL, 5)
        self._type_lb=wx.ListBox(self, -1,
                                 style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_ALWAYS_SB)
        vbs.Add(self._type_lb, 0, wx.EXPAND|wx.ALL, 5)
        return vbs

    def _populate(self):
        # populate the listbox with data
        self._type_lb.Clear()
        for _l in self._data:
            self._type_lb.Append(_l['type'], _l)

    def ok(self):
        # ready to move to the next page?  By default, yes
        return self._type_lb.GetSelection()!=wx.NOT_FOUND

    def get(self, data):
        # return data to the main wizard, data is a dict
        _idx=self._type_lb.GetSelection()
        _type=self._type_lb.GetString(_idx)
        _new_type=data.get('type', None)!=_type
        if _new_type or not data.has_key('data'):
            data['type']=_type
            _info=self._type_lb.GetClientData(_idx)
            data['data']=_info['data']
            data['data_obj']=_info['data']()
            data['source_class']=_info['source']
            data['source_obj']=_info['source']()
        if _new_type:
            # new type selected
            data['type']=_type
            if data.has_key('source_id'):
                del data['source_id']

    def set(self, data):
        # pass current data to this page
        if data.get('type', None):
            self._type_lb.SetStringSelection(data['type'])

#-------------------------------------------------------------------------------
class ImportSourcePage(setphone_wizard.MyPage):
    def __init__(self, parent):
        self._source=None
        super(ImportSourcePage, self).__init__(parent,
                                               'Select Import Source')
    def GetMyControls(self):
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(wx.StaticText(self, -1, 'Source of data:'), 0,
                wx.ALL|wx.EXPAND, 5)
        # set the label in a scrolled panel, so the user can scroll to view
        # the file name if it's too long.
        sp=scrolled.ScrolledPanel(self, -1, size=(-1, 50))
        boxsizer=wx.BoxSizer(wx.VERTICAL)
        self._source_lbl=wx.StaticText(sp, -1, '')
        boxsizer.Add(self._source_lbl, 1, wx.ALL|wx.EXPAND, 5)
        sp.SetSizer(boxsizer)
        sp.SetAutoLayout(True)
        sp.SetupScrolling(scroll_y=False)
        vbs.Add(sp, 0, wx.ALL|wx.EXPAND, 5)
        self.sp=sp
        _btn=wx.Button(self, -1, 'Browse')
        wx.EVT_BUTTON(self, _btn.GetId(), self._OnBrowse)
        vbs.Add(_btn, 0, wx.ALL, 5)
        return vbs

    def setlabel(self):
        self._source_lbl.SetLabel(self._source.name())
        # update the scrolled panel
        self.sp.SetVirtualSize(self.sp.GetBestVirtualSize())

    def _OnBrowse(self, _=None):
        if not self._source:
            return
        self._source.browse(self)
        self.setlabel()
            
    def ok(self):
        return self._source and self._source.get()
    def get(self, data):
        data['source_obj']=self._source
        data['source_id']=self._source.id
        data['imported']=False
    def set(self, data):
        self._source=data['source_obj']
        if self._source:
            if data.has_key('source_id'):
                self._source.id=data['source_id']
            self.setlabel()
    def GetActiveDatabase(self):
        return self.GetParent().GetActiveDatabase()

#-------------------------------------------------------------------------------
class ImportDataAll(setphone_wizard.MyPage):
    def __init__(self, parent):
        self._type=None
        self._source=None
        super(ImportDataAll, self).__init__(parent, 'Import Data Preview')

    def GetMyControls(self):
        vbs=wx.BoxSizer(wx.VERTICAL)
        self._data_lb=wx.ListBox(self, -1,
                                 style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_ALWAYS_SB)
        vbs.Add(self._data_lb, 1, wx.EXPAND|wx.ALL, 5)
        _btn=wx.Button(self, -1, 'Data Filtering Parameters')
        vbs.Add(_btn, 0, wx.ALL, 5)
        wx.EVT_BUTTON(self, _btn.GetId(), self._OnFilter)
        return vbs

    def _populate_lb(self):
        self._data_lb.Clear()
        for _key, _entry in self._type.get_display_data().items():
            self._data_lb.Append('%s - %s'%(common_calendar.bp_date_str(_entry, _entry['start']),
                                            _entry['description']))
        
    def _populate(self):
        self._data_lb.Clear()
        if not self._type or not self._source:
            # nothing to import
            return
        wx.BeginBusyCursor()
        dlg=wx.ProgressDialog('Calendar Data Import',
                              'Importing data, please wait ...',
                              parent=self)
        self._type.read(self._source.get(), dlg)
        dlg.Destroy()
        self._populate_lb()
        wx.EndBusyCursor()

    def _OnFilter(self, _):
        cat_list=self._type.get_category_list()
        dlg=common_calendar.FilterDialog(self, -1, 'Filtering Parameters',
                                         cat_list)
        if dlg.ShowModal()==wx.ID_OK:
            self._type.set_filter(dlg.get())
            self._populate_lb()
        dlg.Destroy()

    def set(self, data):
        self._type=data.get('data_obj', None)
        self._source=data.get('source_obj', None)
        if not data.get('imported', False):
            self._populate()
    def get(self, data):
        data['imported']=True

#-------------------------------------------------------------------------------
class ImportOptionPage(setphone_wizard.MyPage):
    _choices=('Replace All', 'Add')
    def __init__(self, parent):
        super(ImportOptionPage, self).__init__(parent,
                                               'Import Options')
    def GetMyControls(self):
        vbs=wx.BoxSizer(wx.VERTICAL)
        self._option_rb=wx.RadioBox(self, -1, 'Import Options',
                                    choices=self._choices,
                                    style=wx.RA_SPECIFY_ROWS)
        vbs.Add(self._option_rb, 0, wx.EXPAND|wx.ALL, 5)
        return vbs

    def set(self, data):
        self._option_rb.SetSelection(data.get('option', 0))
    def get(self, data):
        data['option']=self._option_rb.GetSelection()

#-------------------------------------------------------------------------------
class ImportCalendarWizard(wiz.Wizard):
    ID_ADD=wx.NewId()
    def __init__(self, parent, id=-1, title='Calendar Import Wizard'):
        super(ImportCalendarWizard, self).__init__(parent, id, title,
                                                   style=wx.DEFAULT_DIALOG_STYLE|\
                                                   wx.RESIZE_BORDER)
        self._data={}
        _import_type_page=ImportTypePage(self)
        _import_source_page=ImportSourcePage(self)
        _import_data_all=ImportDataAll(self)
        _import_option=ImportOptionPage(self)

        wiz.WizardPageSimple_Chain(_import_type_page, _import_source_page)
        wiz.WizardPageSimple_Chain(_import_source_page, _import_data_all)
        wiz.WizardPageSimple_Chain(_import_data_all, _import_option)
        self.first_page=_import_type_page
        self.GetPageAreaSizer().Add(self.first_page, 1, wx.EXPAND|wx.ALL, 5)
        wiz.EVT_WIZARD_PAGE_CHANGING(self, self.GetId(), self.OnPageChanging)
        wiz.EVT_WIZARD_PAGE_CHANGED(self, self.GetId(), self.OnPageChanged)

    def RunWizard(self, firstPage=None):
        return super(ImportCalendarWizard, self).RunWizard(firstPage or self.first_page)

    def OnPageChanging(self, evt):
        pg=evt.GetPage()
        if not evt.GetDirection() or pg.ok():
            pg.get(self._data)
        else:
            evt.Veto()

    def OnPageChanged(self, evt):
        evt.GetPage().set(self._data)

    def get(self):
        if self._data.get('data_obj', None):
            return self._data['data_obj'].get()
        return {}

    def GetActiveDatabase(self):
        return self.GetParent().GetActiveDatabase()
    def get_categories(self):
        if self._data.get('data_obj', None):
            return self._data['data_obj'].get_category_list()
        return []

    def ShowModal(self):
        # run the wizard and return a code
        if self.RunWizard():
            if self._data.get('option', None)==IMP_OPTION_REPLACEALL:
                return wx.ID_OK
            return self.ID_ADD
        return wx.ID_CANCEL

#-------------------------------------------------------------------------------
# Testing
if __name__=="__main__":
    app=wx.PySimpleApp()
    f=wx.Frame(None, title='imp_cal_wizard')
    w=ImportCalendarWizard(f)
    print w.RunWizard()
    print w.get()
    w.Destroy()
