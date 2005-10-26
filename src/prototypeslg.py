### BITPIM
###
### Copyright (C) 2003-2005 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

import calendar
import prototypes
import re
import time

class LGCALDATE(prototypes.UINTlsb):
    def __init__(self, *args, **kwargs):
        """A date/time as used in the LG calendar"""
        super(LGCALDATE,self).__init__(*args, **kwargs)
        self._valuedate=(0,0,0,0,0)  # year month day hour minute

        dict={'sizeinbytes': 4}
        dict.update(kwargs)

        if self._ismostderived(LGCALDATE):
            self._update(args,kwargs)

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

        super(LGCALDATE,self)._update(args, kwargs) # we want the args
        self._complainaboutunusedargs(LGCALDATE,kwargs)
        assert self._sizeinbytes==4

    def getvalue(self):
        """Unpack 32 bit value into date/time

        @rtype: tuple
        @return: (year, month, day, hour, minute)
        """
        val=super(LGCALDATE,self).getvalue()
        min=val&0x3f # 6 bits
        val>>=6
        hour=val&0x1f # 5 bits (uses 24 hour clock)
        val>>=5
        day=val&0x1f # 5 bits
        val>>=5
        month=val&0xf # 4 bits
        val>>=4
        year=val&0xfff # 12 bits
        return (year, month, day, hour, min)

    def _converttoint(self, date):
        assert len(date)==5
        year,month,day,hour,min=date
        if year>4095:
            year=4095
        val=year
        val<<=4
        val|=month
        val<<=5
        val|=day
        val<<=5
        val|=hour
        val<<=6
        val|=min
        return val

class LGCALREPEAT(prototypes.UINTlsb):
    def __init__(self, *args, **kwargs):
        """A 32-bit bitmapped value used to store repeat info for events in the LG calendar"""
        super(LGCALREPEAT,self).__init__(*args, **kwargs)
        
        # The meaning of the bits in this field
        # MSB                          LSB
        #  3         2         1         
        # 10987654321098765432109876543210
        #                              210  repeat_type
        #                            0      exceptions, set to 1 if there are exceptions
        #                     6543210       dow_weekly (weekly repeat type)
        #                         210       dow (monthly repeat type)
        #             543210                interval
        #               3210                month_index
        #  543210                           day_index    

        # repeat_type: 0=none, 1=daily, 2=weekly, 3=monthly, 4=yearly, 5=weekdays, 6=XthDayEachMonth(e.g. 3rd Friday each month)
        # dow_weekly: Weekly repeat type only. Identical to bpcalender dow bits, multiple selections allowed(Bit0=sun,Bit1=mon,Bit2=tue,Bit3=wed,Bit4=thur,Bit5=fri,Bit6=sat)  
        # dow_monthly: Monthly repeat type 6 only. (0=sun,1=mon,2=tue,3=wed,4=thur,5=fri,6=sat)
        # interval: repeat interval, eg. every 1 week, 2 weeks 4 weeks etc. Also be used for months, but bp does not support this.
        # month_index: For type 4 this is the month the event starts in
        # day_index: For type 6 this represents the number of the day that is the repeat, e.g. "2"nd tuesday
        #            For type 3&4 this is the day of the month that the repeat occurs, usually the same as the start date.
        #            bp does not support this not being the support date

        dict={'sizeinbytes': 4}
        dict.update(kwargs)

        if self._ismostderived(LGCALREPEAT):
            self._update(args,kwargs)

    def _update(self, args, kwargs):
        for k in 'constant', 'default', 'value':
            if kwargs.has_key(k):
                kwargs[k]=self._converttoint(kwargs[k])
        if len(args)==0:
            pass
        elif len(args)==1:
            args=(self._converttoint(args[0]),)
        else:
            raise TypeError("expected (type, dow, interval) as arg")

        super(LGCALREPEAT,self)._update(args, kwargs) # we want the args
        self._complainaboutunusedargs(LGCALDATE,kwargs)
        assert self._sizeinbytes==4

    def getvalue(self):
        val=super(LGCALREPEAT,self).getvalue()
        # get repeat type
        type=val&0x7 # 3 bits
        val>>=4
        exceptions=val&0x1
        val>>=1
        #get day of week, only valid for some repeat types
        #format of data is also different for different repeat types
        if type==6: # for monthly repeats
            dow=1<<(val&3) #day of month, valid for monthly repeat types, need to convert to bitpim format
        elif type==2: #weekly 
            dow=val&0x7f # 7 bits, already matched bpcalender format
        else:
            dow=0
        # get interval
        if type==6:
            val>>=20
            interval=val&0x1f # day_index
        else:
            val>>=9
            interval=val&0x3f
        return (type, dow, interval, exceptions)

    _caldomvalues={
        0x01: 0x0, #sun
        0x02: 0x1, #mon
        0x04: 0x2, #tue
        0x08: 0x3, #wed
        0x10: 0x4, #thur
        0x20: 0x5, #fri
        0x40: 0x6  #sat
        }
        
    def _converttoint(self, repeat):
        assert len(repeat)==4
        type,dow,interval,exceptions=repeat
        val=0
        # construct bitmapped value for repeat
        # look for weekday type
        val=interval
        if type==6 or type==3:
            val<<=11
            val|=1 # force monthly interval to 1
        if type==4: #yearly
            val<<=11
            val|=dow
        val<<=9
        if type==2:
            val|=dow
        elif type==6:
            val|=self._caldomvalues[dow]
        val<<=1
        val|=exceptions
        val<<=4
        val|=type
        return val

class GPSDATE(prototypes.UINTlsb):
    _time_t_ofs=calendar.timegm((1980, 1, 6, 0, 0, 0))
    def __init__(self, *args, **kwargs):
        """A date/time as used in the LG call history files,
        """
        super(GPSDATE, self).__init__(*args, **kwargs)

        dict={'sizeinbytes': 4}
        dict.update(kwargs)

        if self._ismostderived(GPSDATE):
            self._update(args,kwargs)

    def _update(self, args, kwargs):
        for k in 'constant', 'default', 'value':
            if kwargs.has_key(k):
                kwargs[k]=self._converttoint(kwargs[k])
        if len(args)==0:
            pass
        elif len(args)==1:
            args=(self._converttoint(args[0]),)
        else:
            raise TypeError("expected (year,month,day,hour,minute,sec) as arg")

        super(GPSDATE, self)._update(args, kwargs) # we want the args
        self._complainaboutunusedargs(GPSDATE,kwargs)
        assert self._sizeinbytes==4

    def getvalue(self):
        """Convert 32 bit value into date/time

        @rtype: tuple
        @return: (year, month, day, hour, minute, sec)
        """
        return time.gmtime(self._time_t_ofs+super(GPSDATE, self).getvalue())[:6]

    def _converttoint(self, date):
        assert len(date)==6
        return calendar.timegm(date)-self._time_t_ofs

class GSMCALDATE(prototypes.CSVSTRING):
    """ Represent date string with format "YYMMDD*"
    This format is being used in LG GSM Calendar Evetns
    """
    def __init__(self, *args, **kwargs):
        super(GSMCALDATE, self).__init__(*args, **kwargs)
        self._data=None
        self._readmode=True
        if self._ismostderived(GSMCALDATE):
            self._update(args, kwargs)

    def _set_data(self, v=None):
        if v:
            self._data=v[:3]
        else:
            self._data=(2000+int(self._value[:2]), int(self._value[2:4]),
                        int(self._value[4:6]))
    def _set_value(self):
        self._value='%02d%02d%02d'%(self._data[0]-2000, self._data[1],
                                    self._data[2])

    def _update(self, args, kwargs):
        self._consumekw(kwargs, ('readmode',))
        if len(args)==1:
            if isinstance(args[0], (list, tuple)):
                super(GSMCALDATE, self)._update((), kwargs)
                self._set_data(args[0])
                self._set_value()
            elif isinstance(args[0], (str, unicode)):
                super(GSMCALDATE, self)._update(args, kwargs)
                self._set_data()
            else:
                raise TypeError
        elif len(args)==0:
            super(GSMCALDATE, self)._update(args, kwargs)
        else:
            raise TypeError
        self._complainaboutunusedargs(GSMCALDATE, kwargs)

    def readfrombuffer(self, buf):
        super(GSMCALDATE, self).readfrombuffer(buf)
        if self._value:
            self._set_data()
        else:
            self._data=None

    def getvalue(self):
        """Returns the tuple of (year, month, day)"""
        if self._data is None:
            if self._value is None:
                raise prototypes.ValueNotSetException()
            self._set_data()
        if self._readmode:
            return self._data
        else:
            if self._quotechar:
                _quote=chr(self._quotechar)
            else:
                _quote=''
            return _quote+self._value+_quote

class GSMCALTIME(GSMCALDATE):
    """ Represent date time with format "hhm"
    This format is being used in LG GSM Calendar Evetns
    """

    def __init__(self, *args, **kwargs):
        super(GSMCALTIME, self).__init__(*args, **kwargs)
        if self._ismostderived(GSMCALTIME):
            self._update(args, kwargs)

    def _set_data(self, v=None):
        if v:
            self._data=v[:2]
        else:
            self._data=(int(self._value[:2]), int(self._value[2:4]))

    def _set_value(self):
        self._value='%02d%02d'%self._data

class SMSDATETIME(prototypes.CSVSTRING):
    """ Represent date time with the format 'yy/MM/dd,hh:mm:ss+-zz' used
    by GSM SMS messages.
    Currently works only 1 way: SMS Date Time -> ISO String
    """
    _re_pattern='^\d\d/\d\d/\d\d,\d\d:\d\d:\d\d[+\-]\d\d$'
    _re_compiled_pattern=None
    def __init__(self, *args, **kwargs):
        if SMSDATETIME._re_compiled_pattern is None:
            SMSDATETIME._re_compiled_pattern=re.compile(SMSDATETIME._re_pattern)
        super(SMSDATETIME, self).__init__(*args, **kwargs)
        if self._ismostderived(SMSDATETIME):
            self._update(args, kwargs)

    def _update(self, args, kwargs):
        super(SMSDATETIME, self)._update(args, kwargs)
        if self._value and \
           not re.match(SMSDATETIME._re_compiled_pattern, self._value):
            raise ValueError('COrrect Format: yy/MM/dd,hh:mm:ss+-zz')

    def getvalue(self):
        """Returns the ISO Format 'YYYMMDDTHHMMSS+-mmss'"""
        if self._value:
            _s=self._value.split(',')
            return '20%sT%s00'%(_s[0].replace('/', ''),
                                _s[1].replace(':', ''))
