### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Deals with iCalendar calendar import stuff"

# system modules
import datetime

# site modules

# local modules
import bpcalendar
import bptime
import common_calendar
import vcal_calendar as vcal

module_debug=False

#-------------------------------------------------------------------------------
class ImportDataSource(common_calendar.ImportDataSource):
    # how to define, and retrieve calendar import data source
    message_str="Pick an iCal Calendar File"
    wildcard='*.ics'

#-------------------------------------------------------------------------------
class Duration(object):
    def __init__(self, data):
        # Got a dict, compute the time duration in seconds
        self._duration=0
        self._neg=False
        self._extract_data(data)
    _funcs={
        'W': lambda x: x*604800,    # 7*24*60*60
        'H': lambda x: x*3600,      # 60*60
        'M': lambda x: x*60,
        'S': lambda x: x,
        'D': lambda x: x*86400,     # 24*60*60
        'T': lambda x: 0,
        'P': lambda x: 0,
        }
    def _extract_data(self, data):
        _i=0
        for _ch in data.get('value', ''):
            if _ch=='+':
                self._neg=False
            elif _ch=='-':
                self._neg=True
            elif _ch.isdigit():
                _i=_i*10+int(_ch)
            else:
                self._duration+=self._funcs.get(_ch, lambda _: 0)(_i)
                _i=0
    def get(self):
        if self._neg:
            return -self._duration
        return self._duration

#-------------------------------------------------------------------------------
parentclass=vcal.VCalendarImportData
class iCalendarImportData(parentclass):

    def __init__(self, file_name=None):
        super(iCalendarImportData, self).__init__(file_name)

    def _conv_alarm(self, v, dd):
        # return True if there's valid alarm and set dd['alarm_value']
        # False otherwise
        # Only supports negative alarm duration value.
        try:
            _params=v.get('params', {})
            if _params.get('RELATED', None)=='END':
                return False
            if _params.get('VALUE', 'DURATION')!='DURATION':
                return False
            _d=Duration(v)
            if _d.get()>0:
                return False
            dd['alarm_value']=abs(_d.get()/60)
            return True
        except:
            if __debug__:
                raise
            return False

    def _conv_duration(self, v, dd):
        # compute the 'end' date based on the duration
        return (datetime.datetime(*dd['start'])+\
                datetime.timedelta(seconds=Duration(v).get())).timetuple()[:5]

    def _conv_date(self, v, dd):
        if v.get('params', {}).get('VALUE', None)=='DATE':
            # allday event
            dd['allday']=True
        return bptime.BPTime(v['value']).get()

    # building repeat data
    def _build_value_dict(self, data):
        _value={}
        for _item in data.get('value', '').split(';'):
            _l=_item.split('=')
            if len(_l)>1:
                _value[_l[0]]=_l[1].split(',')
            else:
                _value[_l[0]]=[]
        return _value

    _sorted_weekdays=['FR', 'MO', 'TH', 'TU', 'WE']
    _dow_bitmap={
        'SU': 1,
        'MO': 2,
        'TU': 4,
        'WE': 8,
        'TH': 0x10,
        'FR': 0x20,
        'SA': 0x40
        }

    def _build_daily(self, value, dd):
        # build a daily repeat event
        dd['repeat_type']='daily'
        # only support either every nth day or every weekday
        # is this every weekday?
        _days=value.get('BYDAY', [])
        _days.sort()
        if _days==self._sorted_weekdays:
            _interval=0
        else:
            try:
                _interval=int(value.get('INTERVAL', [1])[0])
            except ValueError:
                _interval=1
        dd['repeat_interval']=_interval
        return True

    def _build_weekly(self, value, dd):
        # build a weekly repeat event
        dd['repeat_type']='weekly'
        try:
            _interval=int(value.get('INTERVAL', [1])[0])
        except ValueError:
            _interval=1
        dd['repeat_interval']=_interval
        _dow=0
        for _day in value.get('BYDAY', []):
            _dow|=self._dow_bitmap.get(_day, 0)
        dd['repeat_dow']=_dow
        return True

    def _build_monthly(self, value, dd):
        dd['repeat_type']='monthly'
        try:
            _interval2=int(value.get('INTERVAL', [1])[0])
        except ValueError:
            _interval2=1
        dd['repeat_interval2']=_interval2
        # nth day of the month by default
        _nth=0
        _dow=0
        _daystr=value.get('BYDAY', [None])[0]
        if _daystr:
            # every nth day-of-week ie 1st Monday
            _dow=self._dow_bitmap.get(_daystr[-2:], 0)
            _nth=1
            try:
                if len(_daystr)>2:
                    _nth=int(_daystr[:-2])
                elif value.get('BYSETPOS', [None])[0]:
                    _nth=int(value['BYSETPOS'][0])
            except ValueError:
                pass
            if _nth==-1:
                _nth=5
            if _nth<1 or _nth>5:
                _nth=1
        dd['repeat_dow']=_dow
        dd['repeat_interval']=_nth
        return True

    def _build_yearly(self, value, dd):
        dd['repeat_type']='yearly'
        return True

    _funcs={
        'DAILY': _build_daily,
        'WEEKLY': _build_weekly,
        'MONTHLY': _build_monthly,
        'YEARLY': _build_yearly,
        }
    def _conv_repeat(self, v, dd):
        _params=v.get('params', {})
        _value=self._build_value_dict(v)
        _rep=self._funcs.get(
            _value.get('FREQ', [None])[0], lambda *_: False)(self, _value, dd)
        if _rep:
            if _value.get('COUNT', [None])[0]:
                dd['repeat_num']=int(_value['COUNT'][0])
            elif _value.get('UNTIL', [None])[0]:
                dd['repeat_end']=bptime.BPTime(_value['UNTIL'][0]).get()
        return _rep

    def _conv_exceptions(self, v, _):
        try:
            l=v['value'].split(',')
            r=[]
            for n in l:
                r.append(bptime.BPTime(n).get())
            return r
        except:
            if __debug__:
                raise
            return []

    def _conv_start_date(self, v, dd):
        _dt=bptime.BPTime(v['value']).get(default=(0,0,0, None, None))
        if _dt[-1] is None:
            # all day event
            dd['allday']=True
            _dt=_dt[:3]+(0,0)
        return _dt

    def _conv_end_date(self, v, _):
        return bptime.BPTime(v['value']).get(default=(0,0,0, 23,59))

    _calendar_keys=[
        ('CATEGORIES', 'categories', parentclass._conv_cat),
        ('DESCRIPTION', 'notes', parentclass._conv_str),
        ('DTSTART', 'start', _conv_start_date),
        ('DTEND', 'end', _conv_end_date),
        ('DURATION', 'end', _conv_duration),
        ('LOCATION', 'location', parentclass._conv_str),
        ('PRIORITY', 'priority', parentclass._conv_priority),
        ('SUMMARY', 'description', parentclass._conv_str),
        ('TRIGGER', 'alarm', _conv_alarm),
        ('RRULE', 'repeat', _conv_repeat),
        ('EXDATE', 'exceptions', _conv_exceptions),
        ]

#-------------------------------------------------------------------------------
class iCalImportCalDialog(vcal.VcalImportCalDialog):
    _filetype_label='iCalendar File:'
    _data_type='iCalendar'
    _import_data_class=iCalendarImportData
