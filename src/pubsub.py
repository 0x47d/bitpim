### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

from wxPython.lib.pubsub import Publisher
import weakref


"""The publish subscribe mechanism used to maintain lists of stuff.

This helps different pieces of code maintain lists of things (eg wallpapers, categories)
and other to express and interest and be notified when it changes (eg field editors).
The wxPython pubsub module is the base.  The enhancements are a list of standard
topics in this file, and the automatic use of weakrefs to allow the right garbage
collection to happen at the right moment, and most importantly is that callers
don't need to implement a __del__ method to unsubscribe.
"""

###
### A list of topics
###


# Maintain the list of categories
REQUEST_CATEGORIES=( 'request', 'categories' ) # i wanna know ...
ALL_CATEGORIES=( 'response', 'categories') # data is list of strings
SET_CATEGORIES=( 'request', 'setcategories') # data is list of strings
ADD_CATEGORY=( 'request', 'addcategory') # data is list of strings
MERGE_CATEGORIES=( 'request', 'mergecategories') # data is list of strings

###
### Actual code using pubsub library
###

class _weaklistener:

    def __init__(self, obj, methodname):
        try:
            getattr(obj, methodname)
        except AttributeError:
            raise "Can't find "+methodname+" when adding listener"
        
        self.obj=weakref.ref(obj)
        self.methodname=methodname

    def __call__(self, *args, **kwargs):
        obj=self.obj()
        if obj is None:
            print "someone was gc'ed"
            try:
                unsubscribe(self.call)
            except:
                # we don't care if unsubscribe fails
                pass
        else:
            return getattr(obj, self.methodname)(*args, **kwargs)

    # The pubsub module does this stupid 'enhancement' where it tries to figure
    # out if we want arguments or not.  Consequently the method below has
    # to be supplied
    def call(self, argument):
        return self.__call__(argument)

def subscribe(topic, object, methodname):
    # by default we use weakrefs, so the subscribers don't
    # have to remember to unsubscribe
    obj=_weaklistener(object, methodname)
    Publisher.subscribe(topic, obj.call)

def subscribepersistent(topic, listener):
    Publisher.subscribe(topic, listener)

def unsubscribe(listener):
    Publisher.unsubscribe(listener)

def publish(topic, data=None):
    Publisher.sendMessage(topic, data)


