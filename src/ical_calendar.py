### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@netzero.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id:  $

"Deals with iCalendar calendar import stuff"

# system modules

# site modules

# local modules
import bpcalendar
import bptime
import common_calendar
import helpids
import vcal_calendar as vcal
import vcard

module_debug=False

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
class RRule(object):
    # convert a iCal recurrence rule into a RepeatEntry object
    def __init__(self, data):
        self._rep=None
        self._count=None
        self._until=None
        self._extract_data(data)

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
    def _build_daily(self, value):
        # build a daily repeat event
        _rep=bpcalendar.RepeatEntry(bpcalendar.RepeatEntry.daily)
        # only support either every nth day or every weekday
        # is this every weekday?
        _days=value.get('BYDAY', [])
        _days.sort()
        if _days==self._sorted_weekdays:
            _rep.interval=0
        else:
            _rep.interval=_value.get('INTERVAL', [1])[0]
        return _rep

    def _build_weekly(self, value):
        # build a weekly repeat event
        _rep=bpcalendar.RepeatEntry(bpcalendar.RepeatEntry.weekly)
        _rep.interval=_value.get('INTERVAL', [1])[0]
        _dow=0
        for _day in _value.get('BYDAY', []):
            _dow|=self._dow_bitmap.get(_day, 0)
        _rep.dow=_dow
        return _rep

    def _build_monthly(self, value):
        return
    def _build_yearly(self, value):
        return
        
    _funcs={
        'DAILY': _build_daily,
        'WEEKLY': _build_weekly,
        'MONTHLY': _build_monthly,
        'YEARLY': _build_yearly,
        }
    def _extract_data(self, data):
        _params=data.get('params', {})
        _value=self._build_value_dict(data)
        self._rep=self._funcs.get(
            _value.get('FREQ', [None])[0], lambda _: None)(_value)
        if self._rep:
            self._count=_value.get('COUNT', [None])[0]
            self._until=_value.get('UNTIL', [None])[0]

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
            dd['alarm_value']=-_d.get()/60
            return True
        except:
            if __debug__:
                raise
            return False

    def _conv_duration(self, v, dd):
        # compute the 'end' date based on the duration
        return (datetime.datetime(*dd['start'])+\
                datetime.timedelta(seconds=Duration(v).get())).timetuple()[:5]

    _calendar_keys=[
        ('CATEGORIES', 'categories', parentclass._conv_cat),
        ('DESCRIPTION', 'notes', None),
        ('DTEND', 'end', parentclass._conv_date),
        ('DURATION', 'end', _conv_duration),
        ('LOCATION', 'location', None),
        ('PRIORITY', 'priority', parentclass._conv_priority),
        ('DTSTART', 'start', parentclass._conv_date),
        ('SUMMARY', 'description', None),
        ('TRIGGER', 'alarm', _conv_alarm),
        ('RRULE', 'repeat', parentclass._conv_repeat),
        ('EXDATE', 'exceptions', parentclass._conv_exceptions),
        ]
