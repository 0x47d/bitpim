/*
 * $Id$
 *
 * This file is parsed by both Swig and C++
 *
 */

#ifdef SWIG
%immutable;
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
#endif
  ~wabmodule();
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
  typedef enum { STORE=MAPI_STORE, ADDRBOOK=MAPI_ADDRBOOK, FOLDER=MAPI_FOLDER,
		 ABCONT=MAPI_ABCONT, MESSAGE=MAPI_MESSAGE, MAILUSER=MAPI_MAILUSER,
		 ATTACH=MAPI_ATTACH, DISTLIST=MAPI_DISTLIST, PROFSECT=MAPI_PROFSECT,
		 STATUS=MAPI_STATUS, SESSION=MAPI_SESSION, 
		 FORMINFO=MAPI_FORMINFO }  thetype;
  thetype gettype(void) const { return (thetype)type; }
#ifdef SWIG
  static // we need enum as class member in swig, not instance member
#endif
  enum {FLAG_WAB_LOCAL_CONTAINERS=WAB_LOCAL_CONTAINERS, FLAG_WAB_PROFILE_CONTENTS=WAB_PROFILE_CONTENTS} ;
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
  entryid* makeentryid(unsigned long pointer, unsigned long len);
  ~wabtable();
  int getrowcount();
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

wabmodule* Initialize(bool enableprofiles=true, const char *INPUT=NULL);


extern char *errorstring;

