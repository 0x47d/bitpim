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
import copy
import time
import apsw

if __debug__:
    # Change this to True to see what is going on under the hood.  It
    # will produce a lot of output!
    TRACE=False
else:
    TRACE=False



class basedataobject(dict):
    """A base object derived from dict that is used for various
    records.  Existing code can just continue to treat it as a dict.
    New code can treat it as dict, as well as access via attribute
    names (ie object["foo"] or object.foo).  attribute name access
    will always give a result includes None if the name is not in
    the dict.

    As a bonus this class includes checking of attribute names and
    types in non-production runs.  That will help catch typos etc.
    For production runs we may be receiving data that was written out
    by a newer version of BitPim so we don't check or error."""
    # which properties we know about
    _knownproperties=[]
    # which ones we know about that should be a list of dicts
    _knownlistproperties={'serials': ['sourcetype', '*']}

    if __debug__:
        # in debug code we check key name and value types

        def __check_property(self,name,value=None):
            assert isinstance(name, (str, unicode)), "keys must be a string type"
            assert name in self._knownproperties or name in self._knownlistproperties, "unknown property name"
            if value is None: return
            if name in getattr(self, "_knownlistproperties"):
                assert isinstance(value, list), "list properties must be given a list as value"
                # each list member must be a dict
                for v in value:
                    self._check_property_dictvalue(name,v)
                return
            # the value must be a basetype supported by apsw/SQLite
            assert isinstance(value, (str, unicode, buffer, int, long, float)), "only serializable types supported for values"

        def __check_property_dictvalue(self, name, value):
            assert isinstance(value, dict), "items in "+name+" (a list) must be dicts"
            assert name in self._knownlistproperties
            for key in value:
                assert key in self._knownlistproperties[name] or '*' in self._knownlistproperties[name], "dict key "+key+" as member of item in list "+name+" is not known"
                v=value[key]
                assert isinstance(v, (str, unicode, buffer, int, long, float)), "only serializable types supported for values"
                
        def update(self, items):
            assert isinstance(items, dict), "update only supports dicts" # Feel free to fix this code ...
            for k in items:
                self.__check_property(self, k, items[k])
            super(basedataobject, self).update(items)

        def __getitem__(self, name):
            self.__check_property(name)
            v=super(basedataobject, self).__getitem__(name)
            if name in self._knownproperties: return v
            assert isinstance(v,list), name+" takes list of dicts as value"
            # check list item dict values are legit - sadly we only
            # check when they are retrieved, not set.  I did try
            # catching the append method, but the layers of nested
            # namespaces got too confused
            for value in v:
                self.__check_property_dictvalue(name, value)
            return v
            

        def __setitem__(self, name, value):
            self.__check_property(name, value)
            super(basedataobject,self).__setitem__(name, value)

        def __setattr__(self, name, value):
            # note that we map setattr to update the dict
            self.__check_property(name, value)
            self.__setitem__(name, value)

        def __getattr__(self, name):
            self.__check_property(name)
            if name in self.keys():
                return self[name]
            return None

        def __delattr__(self, name):
            self.__check_property(name)
            if name in self.keys():
                del self[name]

    else:
        # non-debug mode - we don't do any attribute name/value type
        # checking as the data may (legitimately) be from a newer
        # version of the program.
        def __setattr__(self, name, value):
            # note that we map setattr to update the dict
            super(basedataobject,self).__setitem__(name, value)

        def __getattr__(self, name):
            # and getattr checks the dict
            if name in self.keys():
                return self[name]
            return None

        def __delattr__(self, name):
            if name in self.keys():
                del self[name]

# an example of how to use (needs to be corrected for the list types to include fields in contained dicts)
#class calendarobject(basedataobject):
#    _knownproperties=['repeat', 'orange']
#    _knownlistproperties=['serials']
#
#class phonebookobject(basedataobject):
#    _knownproperties=basedataobject._knownproperties+["last modified"]
#    _knownlistproperties=basedataobject._knownlistproperties+["categories", "memos"]


class dataobjectfactory:
    "Called by the code to read in objects when it needs a new object container"
    def __init__(self, dataobjectclass=basedataobject):
        self.dataobjectclass=dataobjectclass

    if __debug__:
        def newdataobject(self, values={}):
            v=self.dataobjectclass()
            if len(values):
                v.update(values)
            return v
    else:
        def newdataobject(self, values={}):
            return self.dataobjectclass(values)

dictdataobjectfactory=dataobjectfactory(dict)


def ExclusiveWrapper(method):
    """Wrap a method so that it has an exclusive lock on the database
    (noone else can read or write) until it has finished"""

    # note that the existing threading safety checks in apsw will
    # catch any thread abuse issues.

    
    def _transactionwrapper(*args, **kwargs):

        cursor=getattr(args[0], "cursor")
        excounter=getattr(args[0], "excounter")
        excounter+=1
        setattr(args[0], "excounter", excounter)
        setattr(args[0], "transactionwrite", False)
        if excounter==1:
            cursor.execute("BEGIN EXCLUSIVE TRANSACTION")
        try:
            try:
                success=True
                return method(*args, **kwargs)
            except:
                success=False
                raise
        finally:
            excounter=getattr(args[0], "excounter")
            excounter-=1
            setattr(args[0], "excounter", excounter)
            if excounter==0:
                w=getattr(args[0], "transactionwrite")
                if success:
                    if w:
                        cursor.execute("COMMIT TRANSACTION")
                    else:
                        cursor.execute("END TRANSACTION")
                else:
                    if w:
                        cursor.execute("ROLLBACK TRANSACTION")
                    else:
                        cursor.execute("END TRANSACTION")

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
        self.connection=apsw.Connection(os.path.join(directory, filename))
        self.cursor=self.connection.cursor()
        # exclusive lock counter
        self.excounter=0
        # this should be set to true by any code that writes - it is
        # used by the exclusivewrapper to tell if it should do a
        # commit/rollback or just a plain end
        self.transactionwrite=False
        # a cache of the table schemas
        self._schemacache={}
        self.sql=self.cursor.execute
        self.sqlmany=self.cursor.executemany
        if TRACE:
            self.cursor.setexectrace(self._sqltrace)
            self.cursor.setrowtrace(self._rowtrace)

    def _sqltrace(self, cmd, bindings):
        print "SQL:",cmd
        if bindings:
            print " bindings:",bindings
        return True

    def _rowtrace(self, *row):
        print "ROW:",row
        return row

    def sql(self, statement, params=()):
        "Executes statement and return a generator of the results"
        # this is replaced in init
        assert False

    def sqlmany(self, statement, params):
        "execute statements repeatedly with params"
        # this is replaced in init
        assert False
            
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
            self.transactionwrite=True
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
                    creates.append( (m, "valueBLOB") )
                    continue
                if islist is not None:
                    creates.append( (m, "indirectBLOB") )
                    continue
            if len(creates):
                self._altertable(tablename, creates, createindex=1)

        # write out indirect values
        dbtkeys=self.getcolumns(tablename)
        # for every indirect, we have to replace the value with a pointer
        for _,n,t in dbtkeys:
            if t=="indirectBLOB":
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
            self.sql(" ".join(cmd), [timestamp]+[record[r] for r in rk])
            self.transactionwrite=True
        
    def updateindirecttable(self, tablename, indirects):
        # this is mostly similar to savemajordict, except we only deal
        # with lists of dicts, and we find existing records with the
        # same value if possible

        # does the table even exist?
        if not self.doestableexist(tablename):
            # create table and include meta-fields
            self.sql("create table %s (__rowid__ integer primary key)" % (idquote(tablename),))
            self.transactionwrite=True
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
            self._altertable(tablename, [(m,"valueBLOB") for m in missing], createindex=2)
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
                        params.append(v)
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
                        params.append(record[k])
                    cmd.extend([")", "values", "("])
                    cmd.append(",".join(["?" for p in params]))
                    cmd.append("); select last_insert_rowid()")
                    found=self.sql(" ".join(cmd), params).next()[0]
                    self.transactionwrite=True
                res+=`found`+","
            indirects[r]=res
                        

    def getmajordictvalues(self, tablename, factory=dictdataobjectfactory):
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
            record=factory.newdataobject()
            for colnum,name,type in schema:
                if name.startswith("__") or type not in ("valueBLOB", "indirectBLOB") or row[colnum] is None:
                    continue
                if type=="value":
                    record[name]=row[colnum]
                    continue
                assert type=="indirectBLOB"
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
                if name.startswith("__") or type not in ("valueBLOB", "indirectBLOB") or row[colnum] is None:
                    continue
                if type=="valueBLOB":
                    record[name]=row[colnum]
                    continue
                assert type=="indirectBLOB"
                assert False, "indirect in indirect not handled"
            assert len(record)
            res.append(record)
        assert len(res)
        return res
        
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
        self.transactionwrite=True
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

    # various operations need exclusive access to the database
    savemajordict=ExclusiveWrapper(savemajordict)
    getmajordictvalues=ExclusiveWrapper(getmajordictvalues)
    deleteold=ExclusiveWrapper(deleteold)

                    
            
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

        # note that iterations increases the size of the
        # database/journal and will make each one take longer and
        # longer as the db/journal gets bigger
        if len(sys.argv)>=2:
            iterations=int(sys.argv[1])
        else:
            iterations=1
        if iterations >1:
            TRACE=False

        db=Database(".", "testdb")


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
        

