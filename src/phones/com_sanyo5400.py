### BITPIM
###
### Copyright (C) 2003-2004 Stephen Wood <sawecw@users.sf.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Talk to the Sanyo SCP-5400 (RL2500) cell phone

Reported to work with 5500 bitpim code.
"""

# my modules
import common
import p_sanyo5400
import com_sanyo5500
import com_brew
import com_phone
import com_sanyo
import prototypes


class Phone(com_sanyo5500.Phone):
    "Talk to the Sanyo SCP-5400 cell phone"

    desc="SCP-5400"

    protocolclass=p_sanyo5400
    serialsname='scp5400'

    builtinringtones=( 'None', 'Vibrate', 'Ringer & Voice', '', '', '', '', '', '', 
                       'Tone 1', 'Tone 2', 'Tone 3', 'Tone 4', 'Tone 5',
                       'Tone 6', 'Tone 7', 'Tone 8', '', '', '', '', '',
                       '', '', '', '', '', '', '',
                       'Tschaik.Swanlake', 'Satie Gymnop.#1',
                       'Bach Air on the G', 'Beethoven Sym.5', 'Greensleeves',
                       'Johnny Comes..', 'Foster Ky. Home', 'Asian Jingle',
                       'Disco', 'Toy Box', 'Rodeo' )
                      
    calendar_defaultringtone=0

    def __init__(self, logtarget, commport):
        com_sanyo5500.Phone.__init__(self, logtarget, commport)
        self.mode=self.MODENONE

class Profile(com_sanyo5500.Profile):

    protocolclass=p_sanyo5400
    serialsname='scp5400'

    def __init__(self):
        com_sanyo5500.Profile.__init__(self)
