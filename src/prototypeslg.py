### BITPIM
###
### Copyright (C) 2003-2005 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$


class LGCALDATE(UINTlsb):
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

class LGCALREPEAT(UINTlsb):
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
