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
import threading

import sqlite


def ExclusiveWrapper(method):
    """Wrap a method so that it has an exclusive lock on the database
    (noone else can read or write) until it has finished"""

    # pysqlite currently tries to issue its own BEGINs and ENDs which breaks things
    
    def _transactionwrapper(*args, **kwargs):
        exlock=getattr(args[0], "exlock")
        exlock.acquire()
        cursor=getattr(args[0], "cursor")
        # RLock doesn't expose the count nicely so we have to dig inside it
        if exlock._RLock__count==1:
            # cursor.execute("BEGIN EXCLUSIVE TRANSACTION")
            pass
        try:
            return method(*args, **kwargs)
        finally:
            if exlock._RLock__count==1:
                # cursor.execute("COMMIT TRANSACTION")
                pass
            exlock.release()

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


def sqlquote(s):
    "returns an sqlite quoted string (the return value will begin and end with single quotes)"
    return "'"+s.replace("'", "''")+"'"

class Database:

    def __init__(self, directory, filename):
        self.connection=sqlite.connect(os.path.join(directory, filename))
        self.cursor=self.connection.cursor()
        self.exlock=threading.RLock()

    def sql(self, statement, *params):
        "Execute statement and return a generator of the results"
        print "SQL:",statement
        self.cursor.execute(statement,params)
        return self.cursor

    def doestableexist(self, tablename):
        return bool(self.sql("select count(*) from sqlite_master where type='table' and name=%s" % (sqlquote(tablename),)).next()[0])

    def savemajordict(self, tablename, dict):
        """This is the entrypoint for saving a first level dictionary
        such as the phonebook or calendar.

        @param tablename: name of the table to use
        @param dict: The dictionary of values.  The key is ignored, and
                     the value of each key is treated as a record
        """
        
        # make sure the table exists first
        if not self.doestableexist(tablename):
            # create table and include meta-fields
            self.sql("create table %s (__rowid__ integer primary key, __timestamp__ TIMESTAMP, __deleted__ integer, __uid__ varchar)" % (sqlquote(tablename),))
        # examine the keys in dict
        dk=[]
        for k in dict.keys():
            for kk in dict[k]:
                if kk not in dk:
                    dk.append(kk)
        # verify that they don't start with __
        assert len([k for k in dk if k.startswith("__")])==0
        # get database keys
        dbkeys=[name for _, name, _, _, _, _ in self.sql("pragma table_info(%s)" % (sqlquote(tablename),))]
        # are any missing?
        missing=[k for k in dk if k not in dbkeys]
        if len(missing):
            creates=[]
            # for each missing key, we have to work out if the value
            # is a list type (which we indirect to another table)
            for m in missing:
                islist=None
                isnotlist=None
                for r in dict.keys():
                    record=dict[r]
                    v=record.get(m,None)
                    if v is None:
                        continue
                    if isinstance(v, list):
                        islist=record
                    else:
                        isnotlist=record
                if islist is None and isnotlist is None:
                    # they have the key but no record has any values, so we ignore it
                    del dk[dk.index(m)]
                    continue
                if islist is not None and isnotlist is not None:
                    # can't have it both ways
                    raise ValueError("key %s for table %s has some values as list as some as not. eg LIST: %s, NOTLIST: %s" % (m,tablename,`islist`,`isnotlist`))
                if isnotlist is not None:
                    creates.append( (m, "value") )
                    continue
                if islist is not None:
                    creates.append( (m, "indirect") )
                    continue
            if len(creates):
                # alter the table to add the new fields - sqlite doesn't support alter table so we do it manually
                dbtkeys=[(name,type) for _, name, type, _, _, _ in self.sql("pragma table_info(%s)" % (sqlquote(tablename),))]
                cmd=["create", "temporary", "table", sqlquote("backup_"+tablename), "("]
                for n,t in dbtkeys:
                    if cmd[-1]!="(":
                        cmd.append(",")
                    cmd.append(sqlquote(n))
                    cmd.append(t)
                cmd.append(")")
                self.sql(" ".join(cmd))
                # copy the values into the temporary table
                self.sql("insert into %s select * from %s" % (sqlquote("backup_"+tablename), sqlquote(tablename)))
                # drop the source table
                self.sql("drop table %s" % (sqlquote(tablename),))
                # recreate the source table with new columns
                del cmd[1] # remove temporary
                cmd[2]=sqlquote(tablename) # change tablename
                del cmd[-1] # remove trailing )
                for n,t in creates:
                    cmd.extend((',', sqlquote('n'), t))
                cmd.append(')')
                self.sql(" ".join(cmd))
                # put values back in
                cmd=["insert into", sqlquote(tablename), '(']
                for n,_ in dbtkeys:
                    if cmd[-1]!="(":
                        cmd.append(",")
                    cmd.append(sqlquote(n))
                cmd.extend([")", "select * from", sqlquote("backup_"+tablename)])
                self.sql(" ".join(cmd))
                self.connection.commit() # ::TODO:: remove this
                
    savemajordict=ExclusiveWrapper(savemajordict)


if __name__=='__main__':
    db=Database(".", "testdb")

    # use the phonebook out of the examples directory
    execfile("examples/phonebook-index.idx")

    db.savemajordict("phonebook", phonebook)
        
