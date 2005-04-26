### BITPIM
###
### Copyright (C) 2004 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""
Auto detect of phones.
This module provides functionality to perform auto-detection of connected phone.
To implement auto-detection for your phone, perform the following:

1.  If your phone can be determined by examining the Phone Manufacturer and
Phone Model values returned by +GMI and +GMM commands, just set the following
attributes in your Profile class:

phone_manufacturer='string'
phone_model='string'

The phone_manufacturer attribute will be checked for substring ie, 'SAMSUNG' in
'SAMSUNG ELECTRONICS CO.,LTD.'; phone_model must match exactly.

2.  If your phone detection scheme is more complex, define a staticmethod
'detectphone' in your Phone class.  The declaration of the method is:

def detectphone(ports, likely_ports, detect_dict)

ports: list of available ports returned from comscan
likely_ports: list of likely ports as returned from comdiagnose.islikelyport,
            ie ['com1', 'com2'].
where detect_dict is a dict with the following key/value pairs:
'port': {
'mode_modem': True if the phone can be set to modem mode, False otherwise
'mode_brew': True if the phone can be set to DM mode, False otherwise.  This
             value is not currently set since I'm not sure all phones can
             transition out of DM mode.
'manufacturer': string value returned by +GMI
'model': string value returned by +GMM
'firmware_version': string value returned by +GMR
'esn': ESN value of this phone, will be used to associate a name with it.
'firmwareresponse': response data based on BREW firmwarerequest command.
                    Currently not implemented.
}

If a possitive identification is made, method detectphone should return the
port associated with that phone, otherwise just return None.

"""

# standard modules
try:
    import threading
    has_threading=True
except:
    has_threading=False

# wx modules

# BitPim modules
import comdiagnose
import common
import commport
import comscan
import guiwidgets

class DetectPhone(object):
    __default_timeout=1
    def __init__(self, log=None):
        # get standard commport parameters
        self.__log=log
        self.__data={}
        if has_threading:
            self.__data_lock=threading.Lock()

    def log(self, log_str):
        if self.__log is None:
            print log_str
        else:
            self.__log.log(log_str)

    def __get_mode_modem(self, comm):
        """ check if this port supports mode modem"""
        try:
            resp=comm.sendatcommand('E0V1')
            return True
        except:
            return False
    def __get_manufacturer(self, comm):
        try:
            resp=comm.sendatcommand('+GMI')
            return resp[0].split(': ')[1]
        except:
            return None
    def __get_model(self, comm):
        try:
            resp=comm.sendatcommand('+GMM')
            return resp[0].split(': ')[1]
        except:
            return None
    def __get_firmware_version(self, comm):
        try:
            resp=comm.sendatcommand('+GMR')
            return resp[0].split(': ')[1]
        except:
            return None
    def __get_esn(self, comm):
        try:
            resp=comm.sendatcommand('+GSN')
            return resp[0].split(': ')[1]
        except:
            return None
    def __get_mode_brew(self, comm):
        try:
            resp=comm.sendatcommand('$QCDMG')
            return True
        except:
            return False
    def __get_firmware_response(self, comm):
        pass
    def __get_data(self, port):
        r={ 'mode_modem': False, 'mode_brew': False,
            'manufacturer': None, 'model': None, 'firmware_version': None,
            'esn': None, 'firmwareresponse': None }
        try:
            c=commport.CommConnection(self.__log, port,
                                      timeout=self.__default_timeout)
        except:
            self.log('Failed to open port: '+port)
            return r
        r['mode_modem']=self.__get_mode_modem(c)
        if r['mode_modem'] is not None:
            # in modem mode, ok to try other info
            r['manufacturer']=self.__get_manufacturer(c)
            r['model']=self.__get_model(c)
            r['firmware_version']=self.__get_firmware_version(c)
            r['esn']=self.__get_esn(c)
        c.close()
        return r

    def __check_profile(self, profile):
        if not hasattr(profile, 'phone_manufacturer') or \
           not hasattr(profile, 'phone_model'):
            return None
        phone_model=profile.phone_model
        phone_manufacturer=profile.phone_manufacturer
        for k,e in self.__data.items():
            if e['manufacturer'] is None or\
               e['model'] is None:
                continue
            if phone_manufacturer in e['manufacturer'] and \
               phone_model==e['model'][:len(phone_model)]:
                return k

    def do_get_data(self, port):
        self.log('Gathering data on port: '+port)
        r=self.__get_data(port)
        if has_threading:
            self.__data_lock.acquire()
        self.__data[port]=r
        if has_threading:
            self.__data_lock.release()
        self.log('Done on port: '+port)

    def detect(self, using_port=None):
        # start the detection process
        # 1st, get the list of available ports
        coms=comscan.comscan()
        available_modem_coms=[x['name'] for x in coms if x['available'] \
                              and x['class']=='modem']
        if using_port is None:
            available_coms=[x['name'] for x in coms if x['available']]
        else:
            available_coms=[using_port]
            available_modem_coms=[x for x in available_coms if x in available_modem_coms]
        # loop through each port and gather data
        self.log('Available ports: '+str(available_coms))
        self.log('Available modem ports: '+str(available_modem_coms))
        # only try those AT commands on modem ports
        if has_threading:
            threads=[threading.Thread(target=self.do_get_data, args=(e,)) \
                     for e in available_modem_coms]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        else:
            for e in available_modem_coms:
                self.do_get_data(e)
        # go through each phone and ask it
        pm=guiwidgets.ConfigDialog.phonemodels
        models=pm.keys()
        models.sort()
        found_port=found_model=None
        for model in models:
            self.log('Checking for model: '+model)
            module=__import__(pm[model])
            # check for detectphone in module.Phone or
            # phone_model and phone_manufacturer in module.Profile
            if hasattr(module.Phone, 'detectphone'):
                likely_ports=[x['name'] for x in coms if \
                              x['available'] and \
                              comdiagnose.islikelyport(x, module)]
                found_port=getattr(module.Phone, 'detectphone')(coms,
                                                                likely_ports,
                                                                self.__data)
                if found_port is not None:
                    # found it
                    found_model=model
                    break
            found_port=self.__check_profile(module.Profile)
            if found_port is not None:
                found_model=model
                break
        if found_port is not None and found_model is not None:
            return { 'port': found_port, 'phone_name': found_model,
                     'phone_module': pm[found_model],
                     'phone_esn': self.__data[found_port]['esn'] }
    def get(self):
        return self.__data

