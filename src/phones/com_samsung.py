### BITPIM
###
### Copyright (C) 2004 Joe Pham <djpham@netzero.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with a Samsung SCH-Axx phone using AT commands"""

import com_phone
from string import split,strip
import time
import re

class Phone(com_phone.Phone):

    "Talk to a Samsung phone using AT commands"

    desc="Samsung SCH-Axx phone"

    __AT_str="AT"
    __OK_str="\r\nOK\r\n"
    __Error_str="\r\nERROR\r\n"
    __read_timeout=0.1

    def __init__(self, logtarget, commport):

        com_phone.Phone.__init__(self, logtarget, commport)
	self.is_online()

    def _get_at_response(self):

        s=self.comm.read(1, False)
	if not len(s):
	    return ''

	# got at least one char, try to read the rest with short timeout

	i=self.comm.ser.getTimeout()
	self.comm.ser.setTimeout(self.__read_timeout)
	while True:
            s1=self.comm.read(1, False)
            if len(s1):
                s += s1
            else:
                break;

        self.comm.ser.setTimeout(i)
        return s

    def _send_at_cmd(self, cmd_str):

        self.comm.write(str(self.__AT_str+cmd_str+"\r"))

        return self._get_at_response()

    def is_online(self):
        try:
	    self.comm.sendatcommand("E0V1")
	    return True
        except ATError:
	    return False

    def pmode_on(self):
        try:
	    self.comm.sendatcommand("#PMODE=1")
	    return True
        except ATError:
	    return False

    def pmode_off(self):
        try:
	    self.comm.sendatcommand("#PMODE=0")
	    return Truth
        except ATError:
	    return False

    def get_esn(self):
        try:
	    s=self.comm.sendatcommand("+gsn")
	    if len(s):
	        return split(s[0], ": ")[1]
	except ATError:
            pass
        return ''

    def get_groups(self, groups_range):

        g=[]
	for i in groups_range:
            try:
                s=self.comm.sendatcommand("#PBGRR=%d" % i)
                if len(s):
                    g.append(strip(split(split(s[0],": ")[1],",")[1], '"'))
                else:
                    g.append('')
            except ATError:
                g.append('')
	return g

    def get_phone_entry(self, entry_index):
        try:
            s=self.comm.sendatcommand("#PBOKR=%d" % entry_index)
            if len(s):
                return split(split(s, ": ")[1], ",")
        except ATError:
            pass
        return []

    def del_phone_entry(self, entry_index):
        try:
            s=self.comm.sendatcommand("#PBOKW=%d" % entry_index)
            return Truth
        except ATError:
            return False

    def save_phone_entry(self, entry_str):
        try:
            s=self.comm.sendatcommand("#PBOKW="+entry_str)
            return Truth
        except ATError:
            return False

    def get_time_stamp(self):

        now = time.localtime(time.time())
        return "%04d%02d%02dT%02d%02d%02d" % now[0:6]

    def phonize(self, str):
        """Convert the phone number into something the phone understands
        All digits, P, T, * and # are kept, everything else is removed"""

        return re.sub("[^0-9PT#*]", "", str)



class Profile(com_phone.Profile):

    pass

