### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

%{

"""Various descriptions of data specific to GSM phones"""

from prototypes import *
from prototypeslg import *

# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

%}

PACKET echo_off:
    * STRING { 'terminator': None, 'default': 'E0V1' } +command

PACKET esnrequest:
    * STRING { 'terminator': None, 'default': '+GSN' } +command

PACKET esnresponse:
    * CSVSTRING {'quotechar': None, 'terminator': ord(' '), 'default': '+GSN'} command
    * CSVSTRING {'quotechar': None, 'terminator': None} esn

PACKET SIM_ID_Req:
    * STRING { 'terminator': None, 'default': '+CIMI' } +command

PACKET single_value_resp:
    * STRING { 'terminator': None } value

PACKET manufacturer_id_req:
    * STRING { 'terminator': None, 'default': '+GMI'} +command

PACKET model_id_req:
    * STRING { 'terminator': None, 'default': '+GMM' } +command

PACKET firmware_version_req:
    * STRING { 'terminator': None, 'default': '+GMR' } +command

