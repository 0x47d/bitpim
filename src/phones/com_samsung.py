### BITPIM
###
### Copyright (C) 2004 Joe Pham <djpham@netzero.com>
### Copyright (C) 2004 Stephen Wood <saw@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Communicate with a Samsung SCH-Axx phone using AT commands"""

import p_brew
import com_brew
import com_phone
import common
import commport
from string import split,strip,atoi
import time
import re
from DSV import DSV

class Phone(com_phone.Phone,com_brew.BrewProtocol):
    "Talk to a Samsung phone using AT commands"

    desc="Samsung SCH-Axx phone"

    __AT_str="AT"
    __OK_str="\r\nOK\r\n"
    __Error_str="\r\nERROR\r\n"
    __read_timeout=0.1

    def __init__(self, logtarget, commport):
        "Call all the contructors and sets initial modes"
        com_phone.Phone.__init__(self, logtarget, commport)
        com_brew.BrewProtocol.__init__(self)
        self.mode=self.MODENONE
	#self.is_online()

    def _setmodephonebook(self):
        # Do just AT commands.  Reboot if necessary
        # 
        for baud in (0, 115200, 19200, 230400):
            if baud:
                if not self.comm.setbaudrate(baud):
                    continue

            print "Baud=",baud
            try:
                response=self.comm.sendatcommand("+GMM")
            except:
                self.mode=self.MODENONE
                return False
                #raise
            
            try:
                s=self.comm.readline()
                self.log(s)
                break
            except modignoreerrortypes:
                self.log("No response to AT+GMM")
                self.mode=self.MODENONE
                return False

        response=self.comm.sendatcommand("#PMODE=1")
        print "Now in Phonebook mode"
        return True
        
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
                break

        self.comm.ser.setTimeout(i)
        return s

    def _send_at_cmd(self, cmd_str):

        self.comm.write(str(self.__AT_str+cmd_str+"\r"))

        return self._get_at_response()

    def is_online(self):
        try:
	    self.comm.sendatcommand("E0V1")
	    return True
        except commport.ATError:
	    return False

    def pmode_on(self):
        try:
	    self.comm.sendatcommand("#PMODE=1")
	    return True
        except commport.ATError:
	    return False

    def pmode_off(self):
        try:
	    self.comm.sendatcommand("#PMODE=0")
	    return True
        except commport.ATError:
	    return False

    def get_esn(self):
        try:
	    s=self.comm.sendatcommand("+gsn")
	    if len(s):
	        return split(s[0], ": ")[1]
	except commport.ATError:
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
            except commport.ATError:
                g.append('')
	return g

    def get_phone_entry(self, entry_index):
        try:
            s=self.comm.sendatcommand("#PBOKR=%d" % entry_index)
            if len(s):
                return DSV.importDSV([split(s[0], ": ")[1]])[0]
        except commport.ATError:
            pass
        return []

    def del_phone_entry(self, entry_index):
        try:
            s=self.comm.sendatcommand("#PBOKW=%d" % entry_index)
            return True
        except commport.ATError:
            return False

    def save_phone_entry(self, entry_str):
        try:
            s=self.comm.sendatcommand("#PBOKW="+entry_str)
            return True
        except commport.ATError:
            return False

    def get_time_stamp(self):

        now = time.localtime(time.time())
        return "%04d%02d%02dT%02d%02d%02d" % now[0:6]

    def phonize(self, str):
        """Convert the phone number into something the phone understands
        All digits, P, T, * and # are kept, everything else is removed"""

        return re.sub("[^0-9PT#*]", "", str)

    def get_calendar_entry(self, entry_index):
        s=self._send_at_cmd('#PISHR=%d' % entry_index)
        if s==self.__OK_str or s==self.__Error_str:
            return []
        return split(split(split(s, ": ")[1], "\r\n")[0], ",")

    def save_calendar_entry(self, entry_str):
        return self._send_at_cmd('#PISHW='+entry_str)==self.__OK_str

    def extract_timedate(self, td):
        # extract samsung timedate 'YYYYMMDDTHHMMSS' to (y, m, d, h, m)
        return (atoi(td[:4]), atoi(td[4:6]), atoi(td[6:8]), atoi(td[9:11]), atoi(td[11:13]))

    def encode_timedate(self, td):
        # reverse if extract_timedate
        return "%04d%02d%02dT%02d%02d00" % (td[0], td[1], td[2], td[3], td[4])

    def csvsplit(self, line):
        """Parse a Samsung comma separated list."""
        e=line.split(",")
        i=0
        print len(e)
        result=[]
        while i<len(e):
            # Recombine when ;'s in quotes
            if len(e[i]) and e[i][0]=='"' and e[i][-1]!='"':
                while i+1<len(e) and (len(e[i+1])==0 or e[i+1][-1]!='"'):
                    e[i] = e[i]+","+e[i+1]
                    del e[i+1]
                else:
                    if i+1<len(e):
                        e[i] = e[i]+","+e[i+1]
                        del e[i+1]
        

            # Identify type of each item
            # Strip quotes on strings
            # Un escape escaped characters
            item=e[i]
            if len(item)==0:
                t=0
            elif item[0]=='"' or item[-1]=='"':
                mo=re.match('^"?(.*?)"?$',item)
                item=mo.group(1)
                item=item.replace("}\002",'"')
                item=item.replace("}]","}")
                t='string'
            elif re.match('^\d+T\d+$',item):
                t='timestamp'
            elif re.match('^[\dPT]+$',item):
                # Number or phone number
                t='number'
            elif re.match('^\(\d+-\d+\)',item):
                t='range'
            elif re.match('^\d\d?/\d\d?/\d\d(\d\d)?$',item):
                t='date'
            else:
                t='other'
                
            if t:
                result.append({'type':t, 'value':item})
            else:
                result.append(0)
                
            i+=1

        return result
        
        #PBOKR: 2,5,2,20,"Jones, Mike",4,0,1111111111,0,2222222222,0,3333333333,0,4444444444,0,5555555555,0,6666666666,0,,,"bitpim@a.com","bitpim.sf.net",11/08/1956,20,20041021T205421


class Profile(com_phone.Profile):

    serialsname='samsung'

    usbids=( ( 0x04e8, 0x6601, 1),  # Samsung internal USB interface
        )

    # which device classes we are.
    deviceclasses=("modem",)

    _supportedsyncs=()

    def __init__(self):
        com_phone.Profile.__init__(self)

