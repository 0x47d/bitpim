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

features=('phonebook', 'calendar', 'ringtone', 'wallpaper', 'memo', 'todo',
          'sms')
req_attrs={ 'phonebook': { 'r': 'getphonebook', 'w': 'savephonebook' },
            'calendar': { 'r': 'getcalendar', 'w': 'savecalendar' },
            'ringtone': { 'r': 'getringtones', 'w': 'saveringtones' },
            'wallpaper': { 'r': 'getwallpapers', 'w': 'savewallpapers' },
            'memo': { 'r': 'getmemo', 'w': 'savememo' },
            'todo': { 'r': 'gettodo', 'w': 'savetodo' },
            'sms': { 'r': 'getsms', 'w': 'savesms' }
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
        r[model]=d
    return r

def html_results(r):
    print '<table cellpadding=5 cellspacing=5 border=1>'
    print '<tr><th>'
    for n in features:
        print '<th>%s'%n.upper()
    print '</tr>'
    keys=r.keys()
    keys.sort()
    yes_no={ True: 'X', False: ' ' }
    r_flg={ True: 'R', False: ' ' }
    w_flg={ True: 'W', False: ' ' }
    for k in keys:
        n=r[k]
        print '<tr><th>%s'%k
        for f in features:
            print '<td align=center>%s %s'%(r_flg[n[f]['r']], w_flg[n[f]['w']])
        print '</tr>'
    print '</table>'

if __name__ == '__main__':
    html_results(generate_phone_features())
