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
    import gui


    if len(sys.argv)==2 and sys.argv[1]=="bitfling":
        import bitfling.bitfling
        if True:
            profile("bitfling.prof", "bitfling.bitfling.run(sys.argv)")
        else:
            bitfling.bitfling.run(sys.argv)
    else:
        gui.run(sys.argv)
