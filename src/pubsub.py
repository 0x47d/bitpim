### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$


"""The publish subscribe mechanism used to maintain lists of stuff.

This helps different pieces of code maintain lists of things (eg
wallpapers, categories) and other to express and interest and be
notified when it changes (eg field editors).  The wxPython pubsub
module is the base.  The enhancements are a list of standard topics in
this file.

This code also used to be larger as the wxPython pubsub didn't use
weak references.  It does now, so a whole bunch of code could be
deleted.
"""

from wx.lib.pubsub import Publisher


###
### A list of topics
###


# Maintain the list of categories
REQUEST_CATEGORIES=( 'request', 'categories' ) # no data
ALL_CATEGORIES=( 'response', 'categories') # data is list of strings
SET_CATEGORIES=( 'request', 'setcategories') # data is list of strings
ADD_CATEGORY=( 'request', 'addcategory') # data is list of strings
MERGE_CATEGORIES=( 'request', 'mergecategories') # data is list of strings
ALL_WALLPAPERS=( 'response', 'wallpapers') # data is list of strings
REQUEST_WALLPAPERS=( 'request', 'wallpapers') # no data
ALL_RINGTONES=( 'response', 'ringtones' ) # data is list of strings
REQUEST_RINGTONES=( 'request', 'ringtones') # no data
PHONE_MODEL_CHANGED=( 'notification', 'phonemodelchanged') # data is phone module

def subscribe(listener, topic):
    Publisher.subscribe(listener, topic)

def unsubscribe(listener):
    Publisher.unsubscribe(listener)

def publish(topic, data=None):
    Publisher.sendMessage(topic, data)


