### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Interface to the database"""

import os

import sqlite


def ExclusiveWrapper(method):
    def _transactionwrapper(self, *args, **kwargs):
        self.cursor.execute("BEGIN EXCLUSIVE TRANSACTION")
        try:
            return method(self, *args, **kwargs)
        finally:
            self.cursor.execute("COMMIT TRANSACTION")

    return _transactionwrapper


_whitespace="\t \r\n"
_alnum="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890_"

def sqltokens(sql):
    "A generator that returns the tokens of an sql statement"
    pos=0

    while pos<len(sql):
        # skip leading whitespace
        c=sql[pos]
        pos+=1
        if c in _whitespace:
            continue
        if c in _alnum:
            # find end of alnum
            res=c
            while pos<len(sql):
                c=sql[pos]
                if c not in _alnum:
                    break
                res+=c
                pos+=1
            yield res
            continue
        if c!="'":
            yield c
            continue
        # find end of quote delimited string, taking into account embedded quotes
        res=None
        while pos<len(sql):
            c=sql[pos]
            if c=="'":
                # is it followed by another ' ?
                if pos+1<len(sql) and sql[pos+1]=="'":
                    if res is None:
                        res=""
                    res+="'"
                    pos+=2
                    continue
                pos+=1
                yield res
                res=None
                break
            if res is None:
                res=""
            res+=c
            pos+=1
        if res is not None:
            yield res


class Database:

    def __init__(self, directory, filename):
        self.connection=sqlite.connect(os.path.join(directory, filename))
        self.cursor=self.connection.cursor
