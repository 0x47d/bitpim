/*
 * $Id$
 *
 * This file is parsed by both Swig and C++
 *
 */

#ifdef SWIG
%immutable;  // nothing is modifiable
%include "cstring.i"
#endif


class entryid
{
  void *data;
  size_t len;
  entryid(entryid &); // copying and assignment not allowed
  void operator=(entryid &);
 public:
  entryid(): data(0), len(0) { }
  entryid(void *, size_t);
  ~entryid();
#ifndef SWIG
  LPENTRYID getdata() const { return (LPENTRYID)data; }
  size_t getlen() const { return len; }
#endif

};



#ifndef SWIG
class refcounter
{
  int count;
 public:
  refcounter() : count(0) {}
  void AddRef() { count++; }
  bool Release() { count--; return count==0; }
};
#endif

/* One of these is created by the Initialize function */
class wabmodule
{
  HMODULE hModule;
  LPWABOPEN openfn;
  LPADRBOOK addrbook;
  LPWABOBJECT wabobject;
  refcounter *refcount;
  // private constructor
  wabmodule(HMODULE &hm, LPWABOPEN &op, LPADRBOOK &bk, LPWABOBJECT &wo) : hModule(hm), 
    openfn(op), addrbook(bk), wabobject(wo), refcount(new refcounter())
    {
      refcount->AddRef();
    }
  friend wabmodule* Initialize(bool, const char *);

 public:
#ifndef SWIG
  wabmodule(const wabmodule&);
  void FreeObject(LPSRowSet rows);
  void FreeObject(LPSPropTagArray ta);
#endif
  ~wabmodule();
#ifdef SWIG
%newobject getpab;
%newobject openobject;
#endif
  entryid *getpab(void);
  class wabobject *openobject(const entryid&);
};

class wabobject
{
  LPUNKNOWN iface;
  ULONG type;
  class wabmodule module;

  wabobject(wabobject&); //copying and assignment not allowed
  void operator=(wabobject&);
  // private contstructor
  wabobject(const wabmodule& mod, ULONG t, LPUNKNOWN iface);
  friend class wabmodule;
 public:
  ~wabobject();
   unsigned long gettype() const { return type; }

#ifdef SWIG
  %newobject getcontentstable;
#endif
  class wabtable* getcontentstable(unsigned long flags); 
};

class wabtable
{
  LPMAPITABLE table;
  class wabmodule module;
  wabtable(wabtable&);       //copying and assignment not allowed
  void operator=(wabtable&);
  // private constructor
  wabtable(const wabmodule &mod, LPMAPITABLE t) : table(t), module(mod) {}
  friend class wabobject;
 public:
#ifdef SWIG
%newobject makeentryid;
%cstring_output_allocate_size(char **TheData, size_t *TheLength,);
#endif
  entryid* makeentryid(unsigned long pointer, unsigned long len);
  void makebinarystring(char **TheData, size_t *TheLength, unsigned long pointer, unsigned long len);

  ~wabtable();
  int getrowcount();
  bool enableallcolumns();
#ifdef SWIG
%newobject getnextrow;
#endif
  class wabrow* getnextrow();
};

class wabrow
{
  LPSRowSet rowset;     
  class wabmodule module;
  wabrow(wabrow&);        //copying and assignment not allowed
  void operator=(wabrow&);
  // private constructor
  wabrow(const wabmodule &mod, LPSRowSet r) : rowset(r), module(mod) {}
  friend class wabtable;
 public:
  ~wabrow();
  unsigned numproperties();
  const char *getpropertyname(unsigned which);
  const char *getpropertyvalue(unsigned which);
  bool IsEmpty();
};

#ifdef SWIG
// this is here to convince swig to make a class named constants with the various
// members.  we do some sed magic on the swig generated code to get the correct
// values
class constants
{
  constants();
  ~constants();
 public:
  
  // PR_CONTAINER_FLAGS
  static enum {AB_FIND_ON_OPEN, AB_MODIFIABLE, AB_RECIPIENTS, AB_SUBCONTAINERS, AB_UNMODIFIABLE} ;
  // IABContainer::GetContentsTable 
  static enum {WAB_LOCAL_CONTAINERS, WAB_PROFILE_CONTENTS} ;
  // PR_OBJECT_TYPE
  static enum {MAPI_STORE, MAPI_ADDRBOOK, MAPI_FOLDER, MAPI_ABCONT, MAPI_MESSAGE, 
	       MAPI_MAILUSER, MAPI_ATTACH, MAPI_DISTLIST, MAPI_PROFSECT, MAPI_STATUS, 
	       MAPI_SESSION, MAPI_FORMINFO };
  // PR_DISPLAY_TYPE
  static enum {DT_AGENT, DT_DISTLIST, DT_FOLDER, DT_FOLDER_LINK, DT_FORUM,
	       DT_GLOBAL, DT_LOCAL, DT_MAILUSER, DT_MODIFIABLE, DT_NOT_SPECIFIC, DT_ORGANIZATION,
	       DT_PRIVATE_DISTLIST, DT_REMOTE_MAILUSER, DT_WAN};

};
#endif

#ifdef SWIG
%newobject Initialize;
#endif
wabmodule* Initialize(bool enableprofiles=true, const char *INPUT=NULL);


extern char *errorstring;

