### BITPIM
###
### Copyright (C) 2003-2004 Joe Pham <djpham@netzero.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

""" Module to handle BITPIM date & time """

import datetime

class BPTime:
    def __init__(self, v=None):
        self.__date=self.__time=None
        # I guess this is how python handles overloading ctors
        if isinstance(v, str):
            self.set_iso_str(v)
        elif isinstance(v, (tuple, list)):
            self.set(v)
        elif isinstance(v, datetime.date):
            self.__date=v

    def __get_date(self):
        return self.__date
    date=property(fget=__get_date)

    def __eq__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date==rhs.date
        return False
    def __ne__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date!=rhs.date
        return False
    def __lt__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date<rhs.date
        return False
    def __le__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date<=rhs.date
        return False
    def __gt__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date>rhs.date
        return False
    def __ge__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date>=rhs.date
        return False

    def set_iso_str(self, v):
        # set the date/time according to the ISO string
        if len(v)==8:
            self.__date=datetime.date(int(v[:4]), int(v[4:6]), int(v[6:8]))
            self.__time=None
        else:
            self.__date=datetime.date(int(v[:4]), int(v[4:6]), int(v[6:8]))
            self.__time=datetime.time(hour=int(v[9:11]), minute=int(v[11:13]))

    def iso_str(self, no_time=False):
        # return an ISO string representation
        s=''
        if self.__date is not None:
            s='%04d%02d%02d'%(self.__date.year, self.__date.month,
                                   self.__date.day)
        if self.__time is not None and not no_time:
            s+='T%02d%02d'%(self.__time.hour, self.__time.minute)
        return s

    def date_str(self):
        s=''
        if self.__date is None:
            s=''
        else:
            s='%04d-%02d-%02d'%(self.__date.year, self.__date.month,
                                self.__date.day)
        return s

    def get(self):
        if self.__date is None:
            t=(0, 0, 0)
        else:
            t=(self.__date.year, self.__date.month, self.__date.day)
        if self.__time is None:
            t+=(0, 0)
        else:
            t+=(self.__time.hour, self.__time.minute)
        return t

    def set(self, v):
        self.__date=self.__time=None
        if len(v)>2:
            self.__date=datetime.date(*v[:3])
        if len(v)==5:
            self.__time=datetime.time(*v[3:])
