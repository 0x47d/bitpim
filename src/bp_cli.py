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
from __future__ import with_statement

# System modules
import os

# BitPim modules
import bp_config
import common
import commport
import phones

# Constants
InvalidCommand_Error=1
NotImplemented_Error=2
InvalidDir_Error=3
DirExists_Error=4

_commands=frozenset(('ls', 'll', 'cp', 'mkdir', 'cli'))

def valid_command(arg):
    """Check of this arg is a valid command or not
    @param arg: input arg, most likely passed from command line
    @returns: T if this is a valid command, F otherwise
    """
    global _commands
    return arg.split(None)[0] in _commands


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
        @param config_filename: use this config file instead of the default
        @param comm_port: string name of the comm port to use (default to config file)
        @param phone_model: string phone model to use (default to config file)
        """
        self.OK=False
        self._inCLI=False
        try:
            _cmd_line=arg.split(None)
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
            if not _item['phonefs']:
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
            _cmdline=cmdline.split(None)
            self.cmd=_cmdline[0]
            self.args=_cmdline[1:]
        _func=getattr(self, self.cmd, None)
        if _func is None:
            self._err.write('Error: invalid command: %s\n'%self.cmd)
            return (False, InvalidCommand_Error)
        return _func(self.args)

    def log(self, logstr):
        pass

    def logdata(self, logstr, logdata, dataclass=None, datatype=None):
        pass

    def progress(self, pos, maxcnt, desc):
        "Update the progress meter"
        pass

    def ls(self, args):
        """Do a directory listing
        @param args: string directory names
        @returns: (True, None) if successful, (False, error code) otherwise
        """
        _src=self._parse_args(args, force_phonefs=True)
        for _dir in _src:
            try:
                _dirlist=self.phone.getfilesystem(_dir['name'])
                self._out.write('%s:\n'%_dir['name'])
                for _,_file in _dirlist.items():
                    self._out.write('%s\n'%_file['name'])
            except (phones.com_brew.BrewNoSuchDirectoryException,
                    phones.com_brew.BrewBadPathnameException):
                self._out.write('Error: cannot access %s: no such file or directory\n'%_dir['name'])
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
                _dirlist=self.phone.getfilesystem(_dir['name'])
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
                self._out.write('Error: cannot access %s: no such file or directory\n'%_dir['name'])
            self._out.write('\n')
        return (True, None)

    def _cpfilefromphone(self, filename, destdir):
        # copy a single file from the phone to the dest dir
        with open(os.path.join(destdir, self.phone.basename(filename)),
                  'wb') as f:
            f.write(self.phone.getfilecontents(filename))
            self._out.write('Copied file %(srcname)s to %(dirname)s\n'% { 'srcname': filename,
                                                                          'dirname': destdir})
    def _cpdirfromphone(self, dirname, destdir):
        # copy all files under a phone dir to the dest dir
        for _, _item in self.phone.listfiles(dirname).items():
            self._cpfilefromphone(_item['name'], destdir)

    def _cpfromphone(self, args):
        # copy files from the phone
        _destdir=args[-1]['path']
        if not os.path.isdir(_destdir):
            self._out.write('Error: %(dirname)s is not a valid local directory.\n'% {'dirname': _destdir })
            return (False, InvalidDir_Error)
        for _item in args[:-1]:
            _name=_item['name']
            if self.phone.exists(_name):
                # this is a dir, cp all files under it
                self._cpdirfromphone(_name, _destdir)
            elif self.phone.statfile(_name):
                # this is a file, just copy it
                self._cpfilefromphone(_name, _destdir)
            else:
                # not sure what it is
                self._out.write('Error: %(name)s does not exist\n'%{'name': _name})
        return (True, None)

    def _cpfiletophone(self, name, destdir, phonefs=False, force=False):
        # copy a file to the phone
        _filename=self.phone.join(destdir,
                                  self.phone.basename(name) if phonefs else \
                                  os.path.basename(name))
        if not force:
            # check if file already exists
            if self.phone.statfile(_filename):
                # file exists, warn
                self._out.write('Phone file %(name)s exists, overwrite (y/n): '%\
                                { 'name': _filename })
                if self._in.readline()[0].upper()!='Y':
                    return
        if phonefs:
            # cp from phone FS to phone FS
            self.phone.writefile(_filename,
                                 self.phone.getfilecontents(name))
        else:
            # local to phone FS
            with open(name, 'rb') as f:
                self.phone.writefile(_filename,
                                     f.read())
        self._out.write('Copied %(filename)s to %(dirname)s.\n'%\
                        { 'filename': name,
                          'dirname': destdir })

    def _cpdirtophone(self, dirname, destdir, phonefs=False):
        # cp a dir to the phone
        if phonefs:
            # phone FS dir
            for _, _item in self.phone.listfiles(dirname).items():
                self._cpfiletophone(_item['name'], destdir, phonefs=True)
        else:
            # local dir
            for _item in os.listdir(dirname):
                if os.path.isfile(_item):
                    self._cpfiletophone(_item, destdir, phonefs=False)

    def _cptophone(self, args):
        # copy files to the phone
        _destdir=args[-1]['name']
        if not self.phone.exists(_destdir):
            self._out.write('Error: phone directory %(dirname)s is not exist.\n'%\
                            { 'dirname': _destdir })
            return (False, InvalidDir_Error)
        for _item in args[:-1]:
            if _item['phonefs']:
                # this one on the phone
                _name=_item['name']
                if self.phone.exists(_name):
                    self._cpdirtophone(_name, _destdir, phonefs=True)
                elif self.phone.statfile(_name):
                    self._cpfiletophone(_name, _destdir, phonefs=True)
                else:
                    self._out.write('Error: %(name)s does not exist.\n'%\
                                    { 'name': _name })
            else:
                # this one on the PC
                _name=_item['path']
                if os.path.isdir(_name):
                    self._cpdirtophone(_name, _destdir, phonefs=False)
                elif os.path.isfile(_name):
                    self._cpfiletophone(_name, _destdir, phonefs=False)
                else:
                    self._out.write('Error: %(name) does not exist.\n'%\
                                    { 'name': _name })
        return (True, None)
            
    def cp(self, args):
        """Transfer files between the phone filesystem and local filesystem
        @param args: string dir names
        @returns: (True, None) if successful, (False, error code) otherwise
        """
        _args=self._parse_args(args, force_phonefs=False)
        # The syntax of the last argument indicates the direction of the transfer
        # If the last arg is a phone FS: copy to the phone
        # If the last arg is not a phone FS: copy from the phone.
        if _args[-1]['phonefs']:
            # copy to the phone
            return self._cptophone(_args)
        else:
            # copy from the phone
            return self._cpfromphone(_args)

    def mkdir(self, args):
        """Create one or more dirs on the phone FS.
        @param args: string dir names
        @returns: (True, None) if successful, (False, error code) otherwise
        """
        _src=self._parse_args(args, force_phonefs=True)
        for _dir in _src:
            try:
                self.phone.mkdir(_dir['name'])
            except phones.com_brew.BrewDirectoryExistsException:
                self._out.write('Error: dir %(name)s exists.\n'% \
                                { 'name': _dir['name'] })
            except phones.com_brew.BrewNoSuchDirectoryException:
                self._out.write('Error: Failed to create dir %(name)s.\n'%\
                                { 'name': _dir['name'] })
        return (True, None)

    def cli(self, _):
        """Run a primitive interactive CLI sesssion.
        @params _: don't care
        @returns: always (True, None)
        """
        if self._inCLI:
            # we're in our shell, bail
            return (True, None)
        self._inCLI=True
        try:
            while True:
                self._out.write('BitPim>')
                _cmdline=self._in.readline()
                if _cmdline.startswith('exit'):
                    break
                self.run(_cmdline)
        finally:
            self._inCLI=False
            return (True, None)
