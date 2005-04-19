### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@netzero.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

""" Generate Phone Features from source code """

import guiwidgets

def check_phone_info(module):
    # check if this phone module supports Phone Info feature
    return hasattr(module.Phone, 'getphoneinfo')

def check_auto_detect(module):
    # check of this phone module supports Auto Detect feature
    if hasattr(module.Profile, 'phone_model') and \
       hasattr(module.Profile, 'phone_manufacturer'):
        return True
    if hasattr(module.Phone, 'detectphone'):
        return True
    return False

features=('phonebook', 'calendar', 'ringtone', 'wallpaper', 'memo', 'todo',
          'sms', 'call_history')
misc_features=('Phone Info', 'Auto Detect')
req_attrs={ 'phonebook': { 'r': 'getphonebook', 'w': 'savephonebook' },
            'calendar': { 'r': 'getcalendar', 'w': 'savecalendar' },
            'ringtone': { 'r': 'getringtones', 'w': 'saveringtones' },
            'wallpaper': { 'r': 'getwallpapers', 'w': 'savewallpapers' },
            'memo': { 'r': 'getmemo', 'w': 'savememo' },
            'todo': { 'r': 'gettodo', 'w': 'savetodo' },
            'sms': { 'r': 'getsms', 'w': 'savesms' },
            'call_history': { 'r': 'getcallhistory', 'w': None },
            'Phone Info': check_phone_info,
            'Auto Detect': check_auto_detect
            }
def generate_phone_features():
    pm=guiwidgets.ConfigDialog.phonemodels
    models=pm.keys()
    models.sort()
    r={}
    for model in models:
        module=__import__(pm[model])
        # check for Profile._supportedsyncs
        support_sync=[(x[0], x[1]) for x in module.Profile._supportedsyncs]
        d={}
        for f in features:
            d[f]={ 'r': False, 'w': False }
            if (f, 'read') in support_sync:
                if hasattr(module.Phone, req_attrs[f]['r']) and\
                   getattr(module.Phone, req_attrs[f]['r']) is not NotImplemented\
                   and getattr(module.Phone, req_attrs[f]['r']) is not None:
                    d[f]['r']=True
            if (f, 'write') in support_sync:
                if hasattr(module.Phone, req_attrs[f]['w']) and\
                   getattr(module.Phone, req_attrs[f]['w']) is not NotImplemented\
                   and getattr(module.Phone, req_attrs[f]['w']) is not None:
                    d[f]['w']=True
        for f in misc_features:
            d[f]={ 'x': req_attrs[f](module) }
        r[model]=d
    return r

def html_results(r):
    print '<table cellpadding=5 cellspacing=5 border=1>'
    print '<tr><th>'
    for n in features+misc_features:
        print '<th>%s'%n.replace('_', ' ').upper()
    print '</tr>'
    keys=r.keys()
    keys.sort()
    r_flg={ True: 'R', False: '' }
    w_flg={ True: 'W', False: '' }
    x_flg={ True: 'X', False: '' }
    for k in keys:
        n=r[k]
        print '<tr><th>%s'%k
        for f in features+misc_features:
            if n[f].get('r', False) or n[f].get('w', False):
                print '<td align=center>%s %s'%(r_flg[n[f]['r']], w_flg[n[f]['w']])
            elif n[f].get('x', False):
                print '<td align=center>X'
            else:
                print '<td align=center>&nbsp;'
        print '</tr>'
    print '</table>'

if __name__ == '__main__':
    html_results(generate_phone_features())
