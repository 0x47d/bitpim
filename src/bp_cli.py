#!/usr/bin/env python
### BITPIM
###
### Copyright (C) 2007 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Provide Command Line Interface (CLI) functionality
"""

# System modules
import os

# BitPim modules
import bp_config
import common
import commport
import phones

# Constants
InvalidCommand_Error=1

_commands=frozenset(('ls', 'll', 'cp', 'rm', 'mv'))

def valid_command(arg):
    """Check of this arg is a valid command or not
    @param arg: input arg, most likely passed from command line
    @returns: T if this is a valid command, F otherwise
    """
    global _commands
    return arg.split(' ')[0] in _commands


class PhoneModelError(Exception):
    pass

class CLI(object):
    """BitPim Command Line Interface implementation"""

    def __init__(self, arg, file_in, file_out, file_err,
                 config_filename=None, comm_port=None,
                 phone_model=None):
        """Constructor
        @param arg: command string including the command and its argument
        @param file_in: input stream file object
        @param file_out: output stream file object
        @param file_err: error strean file object
        @config_filename: use this config file instead of the default
        @comm_port: string name of the comm port to use (default to config file)
        @phone_model: string phone model to use (default to config file)
        """
        self.OK=False
        try:
            _cmd_line=arg.split(' ')
            self.cmd=_cmd_line[0]
            self.args=_cmd_line[1:]
            self.config=bp_config.Config(config_filename)
            _commport=comm_port if comm_port else self.config.Read("lgvx4400port", None)
            _phonemodel=phone_model if phone_model else self.config.Read("phonetype", None)
            if os.environ.get('PHONE_FS', None):
                # running in BREW FS debug/sim mode
                self.commport=None
            else:
                self.commport=commport.CommConnection(self, _commport)
            try:
                self.phonemodule=common.importas(phones.module(_phonemodel))
            except KeyError:
                raise PhoneModelError
            self.phone=self.phonemodule.Phone(self, self.commport)
            self._pwd=''
            self._in=file_in
            self._out=file_out
            self._err=file_err
        except common.CommsOpenFailure:
            file_err.write('Error: Failed to open comm port %s\n'%_commport)
        except PhoneModelError:
            file_err.write('Error: Phone Model %s not available\n'%_phonemodel)
        else:
            self.OK=True

    _phone_prefix='phone:'
    _phone_prefix_len=len(_phone_prefix)
    def _parse_args(self, args, force_phonefs=False):
        """Parse the args for a list of input and out args
        @param args: input agrs
        @returns: a dict that has 2 keys: 'source' and 'dest'.  'source' has a
        list of files and/or directories.  'dest' is either a file or dir.
        """
        _res=[]
        for _item in args:
            if _item.startswith(self._phone_prefix):
                _res.append({ 'name': '/'.join((self._pwd, _item[self._phone_prefix_len:])),
                              'phonefs': True })
            else:
                _res.append({ 'name': _item,
                              'phonefs': False or force_phonefs})
        for _item in _res:
            _paths=_item['name'].split('/')
            _item['path']=os.path.join(*_paths)
        return _res
        
    def run(self, cmdline=None):
        """Execute the specified command if specified, or the one
        currently stored
        @param cmdline: string command line
        @returns: (T, None) if the command completed successfully,
                  (F, error code) otherwise
        """
        if cmdline:
            _cmdline=cmdline.split(' ')
            self.cmd=_cmdline[0]
            self.args=_cmdline[1:]
        _func=getattr(self, self.cmd, None)
        if _func is None:
            return (False, InvalidCommand_Error)
        return _func(self.args)

    def log(self, logstr):
        pass

    def logdata(self, logstr, logdata, dataclass=None, datatype=None):
        pass

    def ls(self, args):
        """Do a directory listing
        @param args: string directory names
        @returns: (True, None) if successful, (False, error code) otherwise
        """
        _src=self._parse_args(args, force_phonefs=True)
        for _dir in _src:
            try:
                _dirlist=self.phone.getfilesystem(_dir['path'])
                self._out.write('%s:\n'%_dir['name'])
                for _,_file in _dirlist.items():
                    self._out.write('%s\n'%_file['name'])
            except (phones.com_brew.BrewNoSuchDirectoryException,
                    phones.com_brew.BrewBadPathnameException):
                self._out.write('ls: cannot access %s: no such file or directory\n'%_dir['name'])
            self._out.write('\n')
        return (True, None)

    def ll(self, args):
        """Do a long dir listing command
        @param args: string directory names
        @returns: (True, None) if successful, (False, error code) otherwise
        """
        _src=self._parse_args(args, force_phonefs=True)
        for _dir in _src:
            try:
                _dirlist=self.phone.getfilesystem(_dir['path'])
                self._out.write('%s:\n'%_dir['name'])
                _maxsize=0
                _maxdatelen=0
                for _,_file in _dirlist.items():
                    if _file.get('type', '')=='file':
                        _maxsize=max(_maxsize, _file.get('size', 0))
                    _maxdatelen=max(_maxdatelen, len(_file.get('date', (0, ''))[1]))
                _formatstr='%%(dir)1s %%(size)%(maxsizelen)is %%(date)%(maxdatelen)is %%(name)s\n'%\
                            { 'maxdatelen': _maxdatelen,
                              'maxsizelen': len(str(_maxsize)) }
                for _,_file in _dirlist.items():
                    _strdict={ 'name': _file['name'] }
                    if _file['type']=='file':
                        _strdict['dir']=''
                        _strdict['size']=str(_file['size'])
                    else:
                        _strdict['dir']='d'
                        _strdict['size']=''
                    _strdict['date']=_file.get('date', (0, ''))[1]
                    self._out.write(_formatstr%_strdict)
            except (phones.com_brew.BrewNoSuchDirectoryException,
                    phones.com_brew.BrewBadPathnameException):
                self._out.write('ls: cannot access %s: no such file or directory\n'%_dir['name'])
            self._out.write('\n')
        return (True, None)
