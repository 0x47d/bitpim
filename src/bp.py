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

if __name__ == '__main__':
    import sys  
    import gui

    if __debug__: # this will be optimised out of optimized builds
        if False:
            import hotshot, hotshot.stats, os
            file=os.path.abspath("bpprof")
            profile=hotshot.Profile(file)
            profile.run("gui.run(sys.argv)")
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

    gui.run(sys.argv)
