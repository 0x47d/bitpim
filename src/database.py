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
import copy
import time
import sqlite

if __debug__:
    TRACE=True
else:
    TRACE=False

# pysqlite 2 is currently broken for manifest typing (it likes to
# convert strings of digits into integers and screw them up).  We use
# these as a workaround

def _addsentinel(val):
    if isinstance(val, (str, unicode)) and val.isdigit(): # this checks all chars
        return "#@$%>"+val
    return val

def _stripsentinel(val):
    if isinstance(val, (str, unicode)) and val.startswith("#@$%>"):
        return val[5:]
    return val

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


def sqlquote(s):
    "returns an sqlite quoted string (the return value will begin and end with single quotes)"
    return "'"+s.replace("'", "''")+"'"

def idquote(s):
    """returns an sqlite quoted identifier (eg for when a column name is also an SQL keyword

    The value returned is quoted in square brackets"""
    return '['+s+']'

class Database:

    def __init__(self, directory, filename):
        self.connection=sqlite.connect(os.path.join(directory, filename))
        self.cursor=self.connection.cursor()
        self.exlock=threading.RLock()
        self._schemacache={}

    def sql(self, statement, params=()):
        "Execute statement and return a generator of the results"
        if TRACE:
            print "SQL:",statement
            if len(params):
                print "Params:", params
        self.cursor.execute(statement,params)
        return self.cursor

    def sqlmany(self, statement, params):
        "Like cursor.executemany but it actually works"
        # non-new cursor implementation
        res=[]
        for p in params:
            res.extend([row for row in self.sql(statement, p)])
        return res
            
    def doestableexist(self, tablename):
        if tablename in self._schemacache:
            return True
        return bool(self.sql("select count(*) from sqlite_master where type='table' and name=%s" % (sqlquote(tablename),)).next()[0])

    def getcolumns(self, tablename, onlynames=False):
        res=self._schemacache.get(tablename,None)
        if res is None:
            res=[]
            for colnum,name,type, _, default, primarykey in self.sql("pragma table_info("+idquote(tablename)+")"):
                if primarykey:
                    type+=" primary key"
                res.append([colnum,name,type])
            self._schemacache[tablename]=res
        if onlynames:
            return [name for colnum,name,type in res]
        return res


    def savemajordict(self, tablename, dict, timestamp=None):
        """This is the entrypoint for saving a first level dictionary
        such as the phonebook or calendar.

        @param tablename: name of the table to use
        @param dict: The dictionary of record.  The key must be the uniqueid for each record.
                   The @L{extractbpserials} function can do the conversion for you for
                   phonebook and similar formatted records.
        @param timestamp: the UTC time in seconds since the epoch.  This is 
        """

        if timestamp is None:
            timestamp=time.time()

        # work on a shallow copy of dict
        dict=dict.copy()
        
        # make sure the table exists first
        if not self.doestableexist(tablename):
            # create table and include meta-fields
            self.sql("create table %s (__rowid__ integer primary key, __timestamp__, __deleted__ integer, __uid__ varchar)" % (idquote(tablename),))

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
            assert d not in dict
            dict[d]=current[d]
            dict[d]["__deleted__"]=1
            
        # now we only have new, changed and deleted entries left in dict

        # examine the keys in dict
        dk=[]
        for k in dict.keys():
            # make a copy since we modify values, but it doesn't matter about deleted since we own those
            if k not in deleted:
                dict[k]=dict[k].copy()
            for kk in dict[k]:
                if kk not in dk:
                    dk.append(kk)
        # verify that they don't start with __
        assert len([k for k in dk if k.startswith("__") and not k=="__deleted__"])==0
        # get database keys
        dbkeys=self.getcolumns(tablename, onlynames=True)
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
                    # in devel code, we check every single value
                    # in production, we just use the first we find
                    if not __debug__:
                        break
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
                self._altertable(tablename, creates, createindex=1)

        # write out indirect values
        dbtkeys=self.getcolumns(tablename)
        # for every indirect, we have to replace the value with a pointer
        for _,n,t in dbtkeys:
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
            cmd=["insert into", idquote(tablename), "( [__timestamp__],"]
            cmd.append(",".join([idquote(r) for r in rk]))
            cmd.extend([")", "values", "(?,"])
            cmd.append(",".join(["?" for r in rk]))
            cmd.append(")")
            self.sql(" ".join(cmd), [timestamp]+[_addsentinel(record[r]) for r in rk])
        
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
        dbkeys=self.getcolumns(tablename, onlynames=True)
        # are any missing?
        missing=[k for k in datakeys if k not in dbkeys]
        if len(missing):
            self._altertable(tablename, [(m,"value") for m in missing], createindex=2)
        # for each row we now work out the indirect information
        for r in indirects:
            res=tablename+","
            for record in indirects[r]:
                cmd=["select __rowid__ from", idquote(tablename), "where"]
                params=[]
                coals=[]
                for d in datakeys:
                    v=record.get(d,None)
                    if v is None:
                        coals.append(idquote(d))
                    else:
                        if cmd[-1]!="where":
                            cmd.append("and")
                        cmd.extend([idquote(d), "= ?"])
                        params.append(_addsentinel(v))
                assert cmd[-1]!="where" # there must be at least one non-none column!
                if len(coals)==1:
                    cmd.extend(["and",coals[0],"isnull"])
                elif len(coals)>1:
                    cmd.extend(["and coalesce(",",".join(coals),") isnull"])

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
                        params.append(_addsentinel(record[k]))
                    cmd.extend([")", "values", "("])
                    cmd.append(",".join(["?" for p in params]))
                    cmd.append(")")
                    self.sql(" ".join(cmd), params)
                    found=self.sql("select last_insert_rowid()").next()[0]
                res+=`found`+","
            indirects[r]=res
                        

    def getmajordictvalues(self, tablename):
        if not self.doestableexist(tablename):
            return {}

        res={}
        uids=[u[0] for u in self.sql("select distinct __uid__ from %s" % (idquote(tablename),))]
        schema=self.getcolumns(tablename)
        for colnum,name,type in schema:
            if name=='__deleted__':
                deleted=colnum
            elif name=='__uid__':
                uid=colnum
        # get all relevant rows
        indirects=[]
        for row in self.sqlmany("select * from %s where __uid__=? order by __rowid__ desc limit 1" % (idquote(tablename),), [(u,) for u in uids]):
            if row[deleted]:
                continue
            record={}
            for colnum,name,type in schema:
                if name.startswith("__") or type not in ("value", "indirect") or row[colnum] is None:
                    continue
                if type=="value":
                    record[name]=_stripsentinel(row[colnum])
                    continue
                assert type=="indirect"
                record[name]=row[colnum]
                if name not in indirects:
                    indirects.append(name)
            res[row[uid]]=record
        # now get the indirects
        for name in indirects:
            for r in res:
                v=res[r].get(name,None)
                if v is not None:
                    res[r][name]=self._getindirect(v)
        return res

    def _getindirect(self, what):
        """Gets a list of values (indirect) as described by what
        @param what: what to get - eg phonebook_serials,1,3,5,
                      (note there is always a trailing comma)
        """

        tablename,rows=what.split(',', 1)
        schema=self.getcolumns(tablename)
        
        res=[]
        for row in self.sqlmany("select * from %s where __rowid__=?" % (idquote(tablename),), [(int(r),) for r in rows.split(',') if len(r)]):
            record={}
            for colnum,name,type in schema:
                if name.startswith("__") or type not in ("value", "indirect") or row[colnum] is None:
                    continue
                if type=="value":
                    record[name]=_stripsentinel(row[colnum])
                    continue
                assert type=="indirect"
                assert False, "indirect in indirect not handled"
            assert len(record)
            res.append(record)
        assert len(res)
        return res
        
    # savemajordict=ExclusiveWrapper(savemajordict)

    def _altertable(self, tablename, columnstoadd, createindex=0):
        """Alters the named table by adding the listed columns

        @param tablename: name of the table to alter
        @param columnstoadd: a list of (name,type) of the columns to add
        @param createindex: what sort of index to create.  0 means none, 1 means on just __uid__ and 2 is on all data columns
        """
        # indexes are automatically dropped when table is dropped so we don't need to
        dbtkeys=self.getcolumns(tablename)
        # clean out cache entry since we are about to invalidate it
        del self._schemacache[tablename]

        cmd=["create", "temporary", "table", idquote("backup_"+tablename), "("]
        for _,n,t in dbtkeys:
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
        for n,t in columnstoadd:
            cmd.extend((',', idquote(n), t))
        cmd.append(')')
        self.sql(" ".join(cmd))
        # create index if needed
        if createindex:
            if createindex==1:
                cmd=["create index", idquote("__index__"+tablename), "on", idquote(tablename), "(__uid__)"]
            elif createindex==2:
                cmd=["create index", idquote("__index__"+tablename), "on", idquote(tablename), "("]
                cols=[]
                for _,n,t in dbtkeys:
                    if not n.startswith("__"):
                        cols.append(idquote(n))
                for n,t in columnstoadd:
                    cols.append(idquote(n))
                cmd.extend([",".join(cols), ")"])
            else:
                raise ValueError("bad createindex "+`createindex`)
            self.sql(" ".join(cmd))
        # put values back in
        cmd=["insert into", idquote(tablename), '(']
        for _,n,_ in dbtkeys:
            if cmd[-1]!="(":
                cmd.append(",")
            cmd.append(idquote(n))
        cmd.extend([")", "select * from", idquote("backup_"+tablename)])
        self.sql(" ".join(cmd))

    def deleteold(self, tablename, uids=None, minvalues=3, maxvalues=5, keepoldest=93):
        """Deletes old entries from the database.  The deletion is based
        on either criterion of maximum values or age of values matching.

        @param uids: You can limit the items deleted to this list of uids,
             or None for all entries.
        @param minvalues: always keep at least this number of values
        @param maxvalues: maximum values to keep for any entry (you
             can supply None in which case no old entries will be removed
             based on how many there are).
        @param keepoldest: values older than this number of days before
             now are removed.  You can also supply None in which case no
             entries will be removed based on age.
        @returns: number of rows removed,number of rows remaining
             """
        if not self.doestableexist(tablename):
            return (0,0)
        
        timecutoff=0
        if keepoldest is not None:
            timecutoff=time.time()-(keepoldest*24*60*60)
        if maxvalues is None:
            maxvalues=sys.maxint-1

        if uids is None:
            uids=[u[0] for u in self.sql("select distinct __uid__ from %s" % (idquote(tablename),))]

        deleterows=[]

        for uid in uids:
            deleting=False
            for count, (rowid, deleted, timestamp) in enumerate(
                self.sql("select __rowid__,__deleted__, __timestamp__ from %s where __uid__=? order by __rowid__ desc" % (idquote(tablename),), [uid])):
                if count<minvalues:
                    continue
                if deleting:
                    deleterows.append(rowid)
                    continue
                if count>=maxvalues or timestamp<timecutoff:
                    deleting=True
                    if deleted:
                        # we are ok, this is an old value now deleted, so we can remove it
                        deleterows.append(rowid)
                        continue
                    # we don't want to delete current data (which may
                    # be very old and never updated)
                    if count>0:
                        deleterows.append(rowid)
                    continue

        self.sqlmany("delete from %s where __rowid__=?" % (idquote(tablename),), [(r,) for r in deleterows])

        return len(deleterows), self.sql("select count(*) from "+idquote(tablename)).next()[0]
                    
            
def extractbpserials(dict):
    """Returns a new dict with keys being the bitpim serial for each row"""
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
    import sys
    import time
    import os
    
    # use the phonebook out of the examples directory
    execfile(os.getenv("DBTESTFILE", "examples/phonebook-index.idx"))

    phonebookmaster=phonebook

    def testfunc():
        global phonebook, TRACE, db

        db=Database(".", "testdb")

        # note that iterations increases the size of the
        # database/journal and will make each one take longer and
        # longer as the db/journal gets bigger
        if len(sys.argv)>=2:
            iterations=int(sys.argv[1])
        else:
            iterations=1
        if iterations >1:
            TRACE=False
        b4=time.time()
        

        for i in xrange(iterations):
            phonebook=phonebookmaster.copy()
            
            # write it out
            db.savemajordict("phonebook", extractbpserials(phonebook))

            # check what we get back is identical
            v=db.getmajordictvalues("phonebook")
            assert v==extractbpserials(phonebook)

            # do a deletion
            del phonebook[17] # james bond @ microsoft
            db.savemajordict("phonebook", extractbpserials(phonebook))
            # and verify
            v=db.getmajordictvalues("phonebook")
            assert v==extractbpserials(phonebook)

            # modify a value
            phonebook[15]['addresses'][0]['city']="Bananarama"
            db.savemajordict("phonebook", extractbpserials(phonebook))
            # and verify
            v=db.getmajordictvalues("phonebook")
            assert v==extractbpserials(phonebook)

        after=time.time()

        print "time per iteration is",(after-b4)/iterations,"seconds"
        print "total time was",after-b4,"seconds for",iterations,"iterations"

        if iterations>1:
            print "testing repeated reads"
            b4=time.time()
            for i in xrange(iterations*10):
                db.getmajordictvalues("phonebook")
            after=time.time()
            print "\ttime per iteration is",(after-b4)/(iterations*10),"seconds"
            print "\ttotal time was",after-b4,"seconds for",iterations*10,"iterations"
            print
            print "testing repeated writes"
            x=extractbpserials(phonebook)
            k=x.keys()
            b4=time.time()
            for i in xrange(iterations*10):
                # we remove 1/3rd of the entries on each iteration
                xcopy=x.copy()
                for l in range(i,i+len(k)/3):
                    del xcopy[k[l%len(x)]]
                db.savemajordict("phonebook",xcopy)
            after=time.time()
            print "\ttime per iteration is",(after-b4)/(iterations*10),"seconds"
            print "\ttotal time was",after-b4,"seconds for",iterations*10,"iterations"

        db.cursor.execute("COMMIT")

    sys.excepthook=common.formatexceptioneh

    if len(sys.argv)==3:
        # also run under hotspot then
        def profile(filename, command):
            import hotshot, hotshot.stats, os
            file=os.path.abspath(filename)
            profile=hotshot.Profile(file)
            profile.run(command)
            profile.close()
            del profile
            howmany=100
            stats=hotshot.stats.load(file)
            stats.strip_dirs()
            stats.sort_stats('time', 'calls')
            stats.print_stats(100)
            stats.sort_stats('cum', 'calls')
            stats.print_stats(100)
            stats.sort_stats('calls', 'time')
            stats.print_stats(100)
            sys.exit(0)

        profile("dbprof", "testfunc()")

    else:
        testfunc()
        

