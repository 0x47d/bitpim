### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""
Code to handle setting colors for fields in various BitPim Editor Dialogs.
The idea is to show which fields are supported by the current phone model,
which fields are not, and which fields are unknown (default).

To use/enable this feature for your phone, define a dict value in your phone
profile that specifies the applicability of various fields.  It's probably best
if you copy the default_field_info dict to your phone profile and set
appropriate values.  The value of each key can be either None (don't know),
0 (not applicable), or >0 (number of entries this phone can have).
The name of this dict is 'field_color_data'.  An example is included in module
com_lgvx9800.

"""

import wx

applicable_color=wx.BLUE
notapplicable_color=wx.RED
dunno_color=wx.BLACK

default_field_info={
    'phonebook': {
        'name': {
            'first': None, 'middle': None, 'last': None, 'full': None,
            'nickname': None },
        'number': {
            'type': None, 'speeddial': None, 'number': None },
        'email': None,
        'address': {
            'type': None, 'company': None, 'street': None, 'street2': None,
            'city': None, 'state': None, 'postalcode': None, 'country': None },
        'url': None,
        'memo': None,
        'category': None,
        'wallpaper': None,
        'ringtone': None,
        'storage': None,
        },
    'calendar': {
        'general': {
            'summary': None, 'location': None, 'allday': None,
            'from': None, 'to': None, 'priority': None,
            'alarm': None, 'vibrate': None,
            },
        'repeat': None,
        'memo': None,
        'category': None,
        'wallpaper': None,
        'ringtone': None,
        'storage': None,
        },
    }

current_field_info=default_field_info


def build_field_info(widget, name=None):
    """Return the dict info for this widget
    """
    global current_field_info
    _parent=widget.GetParent()
    if name:
        _names=[name]
    else:
        _names=[]
    while _parent:
        if hasattr(_parent, 'color_field_name'):
            _names.append(_parent.color_field_name)
        _parent=_parent.GetParent()
    _names.reverse()
    _dict=current_field_info
    for n in _names:
        if not _dict.has_key(n):
            _dict[n]={}
        _dict=_dict[n]
    return _dict

def get_children_count(widget):
    """Return the number of sibblings to this widget
    """
    _parent=widget.GetParent()
    _cnt=0
    if _parent:
        for _w in _parent.GetChildren():
            if isinstance(_w, widget.__class__):
                _cnt+=1
    return _cnt

def get_color_info_from_profile(widget):
    """Walk up the widget chain to find the one that has the phone profile
    """
    global current_field_info
    current_field_info=default_field_info
    _w=widget.GetParent()
    while _w:
        if hasattr(_w, 'phoneprofile'):
            # found it
            current_field_info=_w.phoneprofile.field_color_data
            return
        _w=_w.GetParent()

def color(widget, name, tree=None):
    """Return the appropriate color for this field
    """
    if tree:
        _dict=tree
    else:
        # need to build the field info dict
        _dict=build_field_info(widget)
    _val=_dict.get(name, None)
    _cnt=get_children_count(widget)
    if _val is None:
        return dunno_color
    elif _cnt>_val:
        return notapplicable_color
    else:
        return applicable_color

def build_color_field(widget, klass, args, name, tree=None):
    """
    instantiate the widget, set the color, and return the widget
    """
    _w=klass(*args)
    if _w:
        _w.SetForegroundColour(color(widget, name, tree))
    return _w
