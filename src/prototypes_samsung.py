### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id: $

"""The various types used in protocol descriptions specific to Samsung phones"""

import datetime
import time

import prototypes

class DateTime(prototypes.UINTlsb):
    def __init__(self, *args, **kwargs):
        super(DateTime, self).__init__(*args, **kwargs)
        kwargs.update({ 'sizeinbytes': 4 })
        if self._ismostderived(DateTime):
            self._update(args, kwargs)

    def _update(self, args, kwargs):
        for k in 'constant', 'default', 'value':
            if kwargs.has_key(k):
                kwargs[k]=self._converttoint(kwargs[k])
        if len(args)==0:
            pass
        elif len(args)==1:
            args=(self._converttoint(args[0]),)
        else:
            raise TypeError("expected (year,month,day,hour,minute) as arg")

        super(DateTime, self)._update(args, kwargs)
        self._complainaboutunusedargs(DateTime, kwargs)
        assert self._sizeinbytes==4

    _time_delta=315529200.0
    def _converttoint(self, date):
        assert len(date)==5
        year,month,day,hour,min=date
        _dt=datetime.datetime(*date)
        return int(time.mktime(_dt.timetuple())-self._time_delta)

    def getvalue(self):
        """Unpack 32 bit value into date/time
        @rtype: tuple
        @return: (year, month, day, hour, minute)
        """
        val=super(DateTime, self).getvalue()
        return time.localtime(val+self._time_delta)[:5]

class DateTime1(DateTime):
    # similar to DateTime, except getvalue includes seconds
    def __init__(self, *args, **kwargs):
        super(DateTime1, self).__init__(*args, **kwargs)
        kwargs.update({ 'sizeinbytes': 4 })
        if self._ismostderived(DateTime1):
            self._update(args, kwargs)

    def getvalue(self):
        """Unpack 32 bit value into date/time
        @rtype: tuple
        @return: (year, month, day, hour, minute, second)
        """
        val=prototypes.UINTlsb.getvalue(self)
        if time.daylight:
            # account for daylight, which gmtime always ignores
            val+=3600
        return time.gmtime(val+self._time_delta)[:6]

class ExpiringTime(prototypes.UINTlsb):
    # Implement a weird expiring time used by Samsung calendar events
    def __init__(self, *args, **kwargs):
        super(ExpiringTime, self).__init__(*args, **kwargs)
        dict={ 'sizeinbytes': 4 }
        dict.update(kwargs)
        if self._ismostderived(ExpiringTime):
            self._update(args, dict)

    def _update(self, args, kwargs):
        for k in 'constant', 'default', 'value':
            if kwargs.has_key(k):
                kwargs[k]=self._converttoint(kwargs[k])
        if len(args)==0:
            pass
        elif len(args)==1:
            args=(self._converttoint(args[0]),)
        else:
            raise TypeError("expected (hour, minute, duration) as arg")

        super(ExpiringTime, self)._update(args, kwargs)
        self._complainaboutunusedargs(ExpiringTime, kwargs)
        assert self._sizeinbytes==4

    _delta=3786843600L
    def _converttoint(self, v):
        assert len(v)==2
        hour, min=v
        return hour*3600+min*60+self._delta
