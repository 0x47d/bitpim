#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Main entry point to Bitpim

It invokes BitPim in gui or commandline mode as appropriate

@Note: Only gui mode is supported at the moment
"""

import sys

# only gui mode support at the moment

if __debug__:
    def profile(filename, command):
        import hotshot, hotshot.stats, os
        file=os.path.abspath(filename)
        profile=hotshot.Profile(file)
        profile.run(command)
        profile.close()
        del profile
        stats=hotshot.stats.load(file)
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        stats.print_stats(25)
        stats.sort_stats('cum', 'calls')
        stats.print_stats(25)
        stats.sort_stats('calls', 'time')
        stats.print_stats(25)
        sys.exit(0)
        

if __name__ == '__main__':
    import sys  
    import encodings.utf_8
    import encodings.ascii

    # in production builds we don't need the stupid warnings
    if not __debug__:
        import warnings
        def ignorer(*args, **kwargs): pass
        warnings.showwarning=ignorer

        # on windows we set stdout, stderr to do nothing objects otherwise there
        # is an error after 4kb of output
        class _donowt:
            def __getattr__(self, _):
                return self

            def __call__(self, *args, **kwargs):
                pass
            
        # heck, do it for all platforms
        sys.stdout=_donowt()
        sys.stderr=_donowt()
    
    if len(sys.argv)==2 and sys.argv[1]=="bitfling":
        import bitfling.bitfling
        #if True:
        #    profile("bitfling.prof", "bitfling.bitfling.run(sys.argv)")
        #else:
        bitfling.bitfling.run(sys.argv)
    else:
        import gui
        #if True:
        #    profile("bitpim.prof", "gui.run(sys.argv)")
        #else:
        gui.run(sys.argv)
