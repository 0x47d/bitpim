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
            # ::TODO:: deal with successful return v exception thrown
            # and commit/rollback as appropriate
            return method(*args, **kwargs)
        finally:
            if exlock._RLock__count==1:
                # cursor.execute("COMMIT TRANSACTION")
                # getattr(args[0], "connection").commit()
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

def idquote(s):
    """returns an sqlite quoted identified (eg for when a column name is also an SQL keyword

    The value returned is quoted in square brackets"""
    return '['+s+']'

class Database:

    def __init__(self, directory, filename):
        self.connection=sqlite.connect(os.path.join(directory, filename))
        self.cursor=self.connection.cursor()
        self.exlock=threading.RLock()

    def sql(self, statement, params=()):
        "Execute statement and return a generator of the results"
        print "SQL:",statement
        if len(params):
            print "Params:", params
        self.cursor.execute(statement,params)
        return self.cursor

    def sqlmany(self, statement, params):
        "Like cursor.executemany but it actually works"
        # get another cursor
        cursor=self.connection.cursor()
        for p in params:
            print "SQLM:",statement,p
            cursor.execute(statement, p)
            for res in cursor:
                yield res

    def doestableexist(self, tablename):
        return bool(self.sql("select count(*) from sqlite_master where type='table' and name=%s" % (sqlquote(tablename),)).next()[0])

    def getcolumns(self, tablename):
        l=[x for x in self.sql("pragma table_info("+idquote(tablename)+")")]
        for colnum,name,type, _, default, primarykey in l:
            if primarykey:
                type+=" primary key"
            yield colnum,name,type

    def savemajordict(self, tablename, dict):
        """This is the entrypoint for saving a first level dictionary
        such as the phonebook or calendar.

        @param tablename: name of the table to use
        @param dict: The dictionary of record.  The key must be the uniqueid for each record.
                   The @L{extractbpserials} function can do the conversion for you for
                   phonebook and similar formatted records.
        """

        # work on a copy of dict
        dict=dict.copy()
        
        # make sure the table exists first
        if not self.doestableexist(tablename):
            # create table and include meta-fields
            self.sql("create table %s (__rowid__ integer primary key, __timestamp__ TIMESTAMP, __deleted__ integer, __uid__ varchar)" % (idquote(tablename),))
        # examine the keys in dict
        dk=[]
        for k in dict.keys():
            for kk in dict[k]:
                if kk not in dk:
                    dk.append(kk)
        # verify that they don't start with __
        assert len([k for k in dk if k.startswith("__")])==0
        # get database keys
        dbkeys=[name for _, name, _ in self.getcolumns(tablename)]
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
                dbtkeys=[(name,type) for _, name, type, in self.getcolumns(tablename)]
                cmd=["create", "temporary", "table", idquote("backup_"+tablename), "("]
                for n,t in dbtkeys:
                    if cmd[-1]!="(":
                        cmd.append(",")
                    cmd.append(idquote(n))
                    cmd.append(t)
                cmd.append(")")
                self.sql(" ".join(cmd))
                # copy the values into the temporary table
                self.sql("insert into %s select * from %s" % (idquote("backup_"+tablename), idquote(tablename)))
                # drop the source table
                self.sql("drop table %s" % (idquote(tablename),))
                # recreate the source table with new columns
                del cmd[1] # remove temporary
                cmd[2]=idquote(tablename) # change tablename
                del cmd[-1] # remove trailing )
                for n,t in creates:
                    cmd.extend((',', idquote(n), t))
                cmd.append(')')
                self.sql(" ".join(cmd))
                # put values back in
                cmd=["insert into", idquote(tablename), '(']
                for n,_ in dbtkeys:
                    if cmd[-1]!="(":
                        cmd.append(",")
                    cmd.append(idquote(n))
                cmd.extend([")", "select * from", idquote("backup_"+tablename)])
                self.sql(" ".join(cmd))

        # get the latest values for each guid ...
        current=self.getmajordictvalues(tablename)
        # compare what we have, and update/mark deleted as appropriate ...
        deleted=[k for k in current if k not in dict]
        new=[k for k in dict if k not in current]
        modified=[k for k in dict if k in current] # only potentially modified ...

        # deal with modified first
        dl=[]
        for i,k in enumerate(modified):
            if dict[k]==current[k]:
                # unmodified!
                del dict[k]
                dl.append(i)
        dl.reverse()
        for i in dl:
            del modified[i]

        # add deleted entries back into dict
        for d in deleted:
            assert d not in deleted
            dict[d]=current[d]
            dict[d]["__deleted__"]=True
            
        # now we only have new, changed and deleted entries left in dict
        
        # write out indirect values
        dbtkeys=[(name,type) for _, name, type in self.getcolumns(tablename)]
        # for every indirect, we have to replace the value with a pointer
        for n,t in dbtkeys:
            if t=="indirect":
                indirects={}
                for r in dict.keys():
                    record=dict[r]
                    v=record.get(n,None)
                    if v is not None:
                        indirects[r]=v
                if len(indirects):
                    self.updateindirecttable("phonebook__"+n, indirects)
                    for r in indirects.keys():
                        dict[r][n]=indirects[r]

        # and now the main table
        for k in dict.keys():
            record=dict[k]
            record["__uid__"]=k
            rk=record.keys()
            rk.sort()
            cmd=["insert into", idquote(tablename), "("]
            cmd.append(",".join([idquote(r) for r in rk]))
            cmd.extend([")", "values", "("])
            cmd.append(",".join(["?" for r in rk]))
            cmd.append(")")
            self.sql(" ".join(cmd), [record[r] for r in rk])
        
        self.sql("COMMIT")


    def updateindirecttable(self, tablename, indirects):
        # this is mostly similar to savemajordict, except we only deal
        # with lists of dicts, and we find existing records with the
        # same value if possible

        # does the table even exist?
        if not self.doestableexist(tablename):
            # create table and include meta-fields
            self.sql("create table %s (__rowid__ integer primary key)" % (idquote(tablename),))
        # get the list of keys from indirects
        datakeys=[]
        for i in indirects.keys():
            assert isinstance(indirects[i], list)
            for v in indirects[i]:
                assert isinstance(v, dict)
                for k in v.keys():
                    if k not in datakeys:
                        assert not k.startswith("__")
                        datakeys.append(k)
        # get the keys from the table
        dbkeys=[name for _, name, _ in self.getcolumns(tablename)]
        # are any missing?
        missing=[k for k in datakeys if k not in dbkeys]
        if len(missing):
            dbtkeys=[(name,type) for _, name, type in self.getcolumns(tablename)]
            cmd=["create", "temporary", "table", idquote("backup_"+tablename), "("]
            for n,t in dbtkeys:
                if cmd[-1]!="(":
                    cmd.append(",")
                cmd.append(idquote(n))
                cmd.append(t)
            cmd.append(")")
            self.sql(" ".join(cmd))
            # copy the values into the temporary table
            self.sql("insert into %s select * from %s" % (idquote("backup_"+tablename), idquote(tablename)))
            # drop the source table
            self.sql("drop table %s" % (idquote(tablename),))
            # recreate the source table with new columns
            del cmd[1] # remove temporary
            cmd[2]=idquote(tablename) # change tablename
            del cmd[-1] # remove trailing )
            for m in missing:
                cmd.extend((',', idquote(m), "value"))
            cmd.append(')')
            self.sql(" ".join(cmd))
            # put values back in
            cmd=["insert into", idquote(tablename), '(']
            for n,_ in dbtkeys:
                if cmd[-1]!="(":
                    cmd.append(",")
                cmd.append(idquote(n))
            cmd.extend([")", "select * from", idquote("backup_"+tablename)])
            self.sql(" ".join(cmd))
        # for each row we now work out the indirect information
        for r in indirects:
            res=tablename+","
            for record in indirects[r]:
                cmd=["select __rowid__ from", idquote(tablename), "where"]
                params=[]
                for d in datakeys:
                    if cmd[-1]!="where":
                        cmd.append("and")
                    v=record.get(d,None)
                    if v is None:
                        cmd.extend([idquote(d), "isnull"])
                    else:
                        cmd.extend([idquote(d), "=", "?"])
                        params.append(v)
                found=None
                for found in self.sql(" ".join(cmd), params):
                    # get matching row
                    found=found[0]
                    break
                if found is None:
                    # add it
                    cmd=["insert into", idquote(tablename), "("]
                    params=[]
                    for k in record:
                        if cmd[-1]!="(":
                            cmd.append(",")
                        cmd.append(k)
                        params.append(record[k])
                    cmd.extend([")", "values", "("])
                    cmd.append(",".join(["?" for p in params]))
                    cmd.append(")")
                    self.sql(" ".join(cmd), params)
                    found=self.sql("select last_insert_rowid()").next()[0]
                res+=`found`+","
            indirects[r]=res
            print  "indirects[",r,"]=",res
                        

    def getmajordictvalues(self, tablename):
        if not self.doestableexist(tablename):
            return {}

        res={}
        uids=[u[0] for u in self.sql("select distinct __uid__ from %s" % (idquote(tablename),))]
        desc={}
        desc[tablename]=[d for d in self.getcolumns(tablename)]
        for colnum,name,type in desc[tablename]:
            if name=='__deleted__':
                deleted=colnum
            elif name=='__uid__':
                uid=colnum
        for row in self.sqlmany("select * from %s where __uid__=? order by __rowid__ desc limit 1" % (idquote(tablename),), [(u,) for u in uids]):
            if row[deleted]:
                continue
            record={}
            for colnum,name,type in desc[tablename]:
                if name.startswith("__") or type not in ("value", "indirect") or row[colnum] is None:
                    continue
                if type=="value":
                    record[name]=row[colnum]
                    continue
                assert type=="indirect"
                record[name]=self.getindirect(row[colnum], desc)
            res[row[uid]]=record
        return res

    def getindirect(self, what, schemas=None):
        """Gets a list of values (indirect) as described by what
        @param what: what to get - eg phonebook_serials,1,3,5,
                      (note there is always a trailing comma)
        @param schemas: a dict holding the schemas for various tables.  It is useful to provide
                     this if you repeatedly call this function
        """
        if schemas is None:
            schemas={}

        tablename,rows=schemas.split(',', 1)
        if tablename not in schemas:
            schemas[tablename]=[d for d in self.getcolumns(tablename)]

        res=[]
        for row in self.sqlmany("select * from %s where __rowid__=?" % (idquote(tablename),), [(int(r),) for r in rows.split(',') if len(r)]):
            record={}
            for colnum,name,type in schemas[tablename]:
                if name.startswith("__") or type not in ("value", "indirect") or row[colnum] is None:
                    continue
                if type=="value":
                    record[name]=row[colnum]
                    continue
                assert type=="indirect"
                assert False, "indirect in indirect no handled"
            assert len(record)
            res.append(record)
        assert len(res)
        return res
        
    # savemajordict=ExclusiveWrapper(savemajordict)

def extractbpserials(dict):
    """Changes dict keys to be the bitpim serial for each row"""
    res={}
    
    for r in dict.keys():
        found=False
        record=dict[r]
        for v in record["serials"]:
            if v["sourcetype"]=="bitpim":
                found=True
                res[v["id"]]=record
                break
        assert found
    return res


if __name__=='__main__':
    import common

    try:
        db=Database(".", "testdb")
        
        # use the phonebook out of the examples directory
        execfile("examples/phonebook-index.idx")

        db.savemajordict("phonebook", extractbpserials(phonebook))
    except:
        print common.formatexception()
        
