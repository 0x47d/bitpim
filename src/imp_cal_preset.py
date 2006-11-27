#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

""" Handle Import Calendar Preset feature
"""

# System
import random
import sha

# wx
import wx
import wx.wizard as wiz

# BitPim
import common_calendar
import database
import imp_cal_wizard
import importexport
import setphone_wizard

# modules constants
IMP_OPTION_REPLACEALL=0
IMP_OPTION_ADD=1
IMP_OPTION_PREVIEW=2

#-------------------------------------------------------------------------------
class ImportCalendarDataObject(common_calendar.FilterDataObject):
    _knownproperties=common_calendar.FilterDataObject._knownproperties+\
                      ['name', 'type', 'source_id', 'option' ]

importcalendarobjectfactory=database.dataobjectfactory(ImportCalendarDataObject)

#-------------------------------------------------------------------------------
class ImportCalendarEntry(dict):
    # a dict class that automatically generates an ID for use with
    # BitPim database.

    _persistrandom=random.Random()
    def _create_id(self):
        "Create a BitPim serial for this entry"
        rand2=random.Random() # this random is seeded when this function is called
        num=sha.new()
        num.update(`self._persistrandom.random()`)
        num.update(`rand2.random()`)
        return num.hexdigest()
    def _get_id(self):
        s=self.get('serials', [])
        _id=None
        for n in s:
            if n.get('sourcetype', None)=='bitpim':
                _id=n.get('id', None)
                break
        if not _id:
            _id=self._create_id()
            self._set_id(_id)
        return _id
    def _set_id(self, id):
        s=self.get('serials', [])
        for n in s:
            if n.get('sourcetype', None)=='bitpim':
                n['id']=id
                return
        self.setdefault('serials', []).append({'sourcetype': 'bitpim', 'id': id } )
    id=property(fget=_get_id, fset=_set_id)

#-------------------------------------------------------------------------------
class FilterDialog(common_calendar.FilterDialog):
    def __init__(self, parent, id, caption, data):
        super(FilterDialog, self).__init__(parent, id, caption, [])
        self.set(data)

    def _get_from_fs(self):
        pass
    def _save_to_fs(self, data):
        pass

#-------------------------------------------------------------------------------
class PresetNamePage(setphone_wizard.MyPage):
    def __init__(self, parent):
        super(PresetNamePage, self).__init__(parent,
                                             'Calendar Import Preset Name')

    def GetMyControls(self):
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(wx.StaticText(self, -1, 'Preset Name:'), 0,
                wx.ALL|wx.EXPAND, 5)
        self._name=wx.TextCtrl(self, -1, '')
        vbs.Add(self._name, 0, wx.ALL|wx.EXPAND, 5)
        return vbs

    def ok(self):
        return bool(self._name.GetValue())
    def get(self, data):
        data['name']=self._name.GetValue()
    def set(self, data):
        self._name.SetValue(data.get('name', ''))

#-------------------------------------------------------------------------------
class PresetFilterPage(setphone_wizard.MyPage):
    def __init__(self, parent):
        self._data={}
        super(PresetFilterPage, self).__init__(parent,
                                               'Calendar Preset Filter')
    _col_names=({ 'label': 'Start Date:', 'attr': '_start' },
                { 'label': 'End Date:', 'attr': '_end' },
                { 'label': 'Preset Duration:', 'attr': '_preset' },
                { 'label': 'Repeat Events:', 'attr': '_repeat' },
                { 'label': 'Alarm Setting:', 'attr': '_alarm' },
                { 'label': 'Alarm Vibrate:', 'attr': '_vibrate' },
                { 'label': 'Alarm Ringtone:', 'attr': '_ringtone' },
                { 'label': 'Alarm Value:', 'attr': '_alarm_value' },
                )
    def GetMyControls(self):
        gs=wx.GridBagSizer(5, 10)
        gs.AddGrowableCol(1)
        for _row, _col in enumerate(PresetFilterPage._col_names):
            gs.Add(wx.StaticText(self, -1, _col['label']),
                   pos=(_row, 0), flag=wx.ALIGN_CENTER_VERTICAL)
            _w=wx.StaticText(self, -1, _col['attr'])
            setattr(self, _col['attr'], _w)
            gs.Add(_w, pos=(_row, 1), flag=wx.ALIGN_CENTER_VERTICAL)
        _btn=wx.Button(self, -1, 'Modify')
        wx.EVT_BUTTON(self, _btn.GetId(), self._OnFilter)
        gs.Add(_btn, pos=(_row+1, 0))
        return gs

    def _OnFilter(self, _):
        dlg=FilterDialog(self, -1, 'Filtering Parameters', self._data)
        if dlg.ShowModal()==wx.ID_OK:
            self._data.update(dlg.get())
            self._populate()
        dlg.Destroy()

    def _display(self, key, attr, fmt):
        # display the value field of this key
        _v=self._data.get(key, None)
        getattr(self, attr).SetLabel(_v is not None and eval(fmt) or '')
    def _populate(self):
        # populate the display with the filter parameters
        self._display('start', '_start', "'%04d/%02d/%02d'%(_v[0], _v[1], _v[2])")
        self._display('end', '_end', "'%04d/%02d/%02d'%(_v[0], _v[1], _v[2])")
        self._display('preset_date', '_preset',
                      "['This Week', 'This Month', 'This Year'][_v]")
        self._display('rpt_events', '_repeat',
                      "{ True: 'Import as mutil-single events', False: ''}[_v]")
        if self._data.get('no_alarm', None):
            _s='Disable All Alarms'
        elif self._data.get('alarm_override', None):
            _s='Set Alarm on All Events'
        else:
            _s='Use Alarm Settings from Import Source'
        self._alarm.SetLabel(_s)
        self._display('vibrate', '_vibrate',
                      "{ True: 'Enable Vibrate for Alarms', False: ''}[_v]")
        self._display('ringtone', '_ringtone', "'%s'%((_v != 'Select:') and _v or '',)")
        self._display('alarm_value', '_alarm_value', "'%d'%_v")
    def get(self, data):
        data.update(self._data)
    def set(self, data):
        self._data=data
        self._populate()

#-------------------------------------------------------------------------------
class ImportOptionPage(imp_cal_wizard.ImportOptionPage):
    _choices=('Replace All', 'Add', 'Preview')

#-------------------------------------------------------------------------------
class ImportCalendarPresetWizard(wiz.Wizard):
    ID_ADD=wx.NewId()
    def __init__(self, parent, entry,
                 id=-1, title='Calendar Import Preset Wizard'):
        super(ImportCalendarPresetWizard, self).__init__(parent, id, title)
        self._data=entry
        _import_name_page=PresetNamePage(self)
        _import_type_page=imp_cal_wizard.ImportTypePage(self)
        _import_source_page=imp_cal_wizard.ImportSourcePage(self)
        _import_filter_page=PresetFilterPage(self)
        _import_option=ImportOptionPage(self)

        wiz.WizardPageSimple_Chain(_import_name_page, _import_type_page)
        wiz.WizardPageSimple_Chain(_import_type_page, _import_source_page)
        wiz.WizardPageSimple_Chain(_import_source_page, _import_filter_page)
        wiz.WizardPageSimple_Chain(_import_filter_page, _import_option)
        self.first_page=_import_name_page
        self.GetPageAreaSizer().Add(self.first_page, 1, wx.EXPAND|wx.ALL, 5)
        wiz.EVT_WIZARD_PAGE_CHANGING(self, self.GetId(), self.OnPageChanging)
        wiz.EVT_WIZARD_PAGE_CHANGED(self, self.GetId(), self.OnPageChanged)

    def RunWizard(self, firstPage=None):
        return super(ImportCalendarPresetWizard, self).RunWizard(firstPage or self.first_page)

    def OnPageChanging(self, evt):
        pg=evt.GetPage()
        if not evt.GetDirection() or pg.ok():
            pg.get(self._data)
        else:
            evt.Veto()

    def OnPageChanged(self, evt):
        evt.GetPage().set(self._data)

    def get(self):
        return self._data

    def GetActiveDatabase(self):
        return self.GetParent().GetActiveDatabase()
    def get_categories(self):
        if self._data.get('data_obj', None):
            return self._data['data_obj'].get_category_list()
        return []

#-------------------------------------------------------------------------------
# Testing
if __name__=="__main__":
    app=wx.PySimpleApp()
    f=wx.Frame(None, title='imp_cal_preset')
    _data=ImportCalendarEntry()
    _data.id
    w=ImportCalendarPresetWizard(f, _data)
    print w.RunWizard()
    _data=w.get()
    _data['source_id']=_data['source_obj'].id
    print _data
    w.Destroy()
