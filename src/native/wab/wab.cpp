#include <windows.h>
#include <wab.h>
#include <stdio.h>
#include <stdarg.h>

static HMODULE hModule;
static LPWABOPEN openfn;
static LPADRBOOK lpaddrbook;
static LPWABOBJECT lpwabobject;
static LPABCONT lpcontainer;
static LPMAPITABLE lptable;

char *errorstring=NULL;

static void errorme(HRESULT hr, IMAPIProp *glefrom, const char *format, ...)
{
  va_list arglist;
  va_start(arglist, format);
  char *tmp=(char*)malloc(4096);
  vsnprintf(tmp, 4096, format, arglist);
  va_end(arglist);

  LPSTR sysmsg=NULL;

  FormatMessage(FORMAT_MESSAGE_ALLOCATE_BUFFER | 
		FORMAT_MESSAGE_FROM_SYSTEM | 
		FORMAT_MESSAGE_IGNORE_INSERTS,
		NULL,
		GetLastError(),
		MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
		(LPSTR)&sysmsg,
		0,
		NULL );

  if (!errorstring)
    errorstring=(char*)malloc(16384);

  snprintf(errorstring, 16384, "%s: HResult: %lu  System message %s", tmp, hr, sysmsg?sysmsg:"<NULL>");
  free(tmp);
  LocalFree(sysmsg);
  if (glefrom)
    {
      LPMAPIERROR me=NULL;
      hr=glefrom->GetLastError(hr, 0, &me);
      if (!HR_FAILED(hr) && me)
	printf("AddrBook: %s.%s\n", me->lpszComponent, me->lpszError);
    }
}


bool Initialize(void)
{
  HKEY keyresult;
  BYTE keyValue[MAX_PATH+1];
  DWORD dataout=MAX_PATH;

  RegOpenKeyEx(HKEY_LOCAL_MACHINE, "Software\\Microsoft\\WAB\\DLLPath", 0, KEY_ALL_ACCESS, &keyresult);
  RegQueryValueEx(keyresult, "", 0, 0, keyValue, &dataout);
  RegCloseKey(keyresult);

  hModule=LoadLibrary((char*)keyValue);

  if (!hModule)
    {
      errorme(GetLastError(), NULL, "Failed to load library %s", keyValue);
      return false;
    }

  openfn=(LPWABOPEN) GetProcAddress(hModule, "WABOpen");

  if (!openfn)
    {
      errorme(0, NULL, "Couldn't find WABOpen function in %s", keyValue);
      return false;
    }

  return true;
}

// see mapitypes.h for these names and ranges

static struct { ULONG id; const char* name; }  propnames[]={
#define PR(t) { PROP_ID(t), #t }
  // these are for debug purposes only
  PR(PR_DISPLAY_TYPE),
  PR(PR_ACCESS_LEVEL),
  PR(PR_RECORD_KEY),
  PR(PR_ROWID),
  PR(PR_CONTAINER_FLAGS),
  PR(PR_FOLDER_TYPE),
  PR(PR_SUBFOLDERS),
  PR(PR_CONTAINER_HIERARCHY),
  PR(PR_CONTAINER_CONTENTS),
  PR(PR_INSTANCE_KEY),
  PR(PR_AB_PROVIDER_ID),
  PR(PR_CONTAINER_CLASS),
#define DO_PRSTUFF
#include "_genprops.h"
#undef DO_PRSTUFF
#undef PR
  { 0, NULL } };

static char*propbuffy=NULL;

const char *property_name(unsigned id)
{
  const int buflen=256;

  unsigned i=0;
  do
    {
      if (propnames[i].id==id)
	return propnames[i].name;
      i++;
    } while (propnames[i].name);
  if(!propbuffy)
    propbuffy=(char*)malloc(buflen);

  // main categories
  if (id>=0x0001 && id<=0x0bff)
    snprintf(propbuffy, buflen, "MAPI_defined evelope property %04x", id);
  else if (id>=0x0c00 && id<=0x0dff)
    snprintf(propbuffy, buflen, "MAPI_defined per-recipient property %04x", id);
  else if (id>=0x0e00 && id<=0x0fff)
    snprintf(propbuffy, buflen, "MAPI_defined non-transmittable property %04x", id);
  else if (id>=0x1000 && id<=0x2fff)
    snprintf(propbuffy, buflen, "MAPI_defined message content property %04x", id);
  else if (id>=0x4000 && id<=0x57ff)
    snprintf(propbuffy, buflen, "Transport defined envelope property %04x", id);
  else if (id>=0x5800 && id<=0x5fff)
    snprintf(propbuffy, buflen, "Transport defined per-recipient property %04x", id);
  else if (id>=0x6000 && id<=0x65ff)
    snprintf(propbuffy, buflen, "User-defined non-transmittable property %04x", id);
  else if (id>=0x6600 && id<=0x67ff)
    snprintf(propbuffy, buflen, "Provider defined internal non-transmittable property %04x", id);
  else if (id>=0x6800 && id<=0x7bff)
    snprintf(propbuffy, buflen, "Message class-defined content property %04x", id);
  else if (id>=0x7c00 && id<=0x7fff)
    snprintf(propbuffy, buflen, "Messafe class-defined non-transmittable property %04x", id);
  else if (id>=0x8000 && id<=0xfffe)
    snprintf(propbuffy, buflen, "User defined Name-to-id property %04x", id);
  // mapi defined stuff
  else if (id>=0x3000 && id<=0x33ff)
    snprintf(propbuffy, buflen, "Common property %04x", id);
  else if (id>=0x3400 && id<=0x35ff)
    snprintf(propbuffy, buflen, "Message store object %04x", id);
  else if (id>=0x3600 && id<=0x36ff)
    snprintf(propbuffy, buflen, "Folder or AB container %04x", id);
  else if (id>=0x3700 && id<=0x38ff)
    snprintf(propbuffy, buflen, "Attachment %04x", id);
  else if (id>=0x3900 && id<=0x39ff)
    snprintf(propbuffy, buflen, "Address book %04x", id);
  else if (id>=0x3a00 && id<=0x3bff)
    snprintf(propbuffy, buflen, "Mail user %04x", id);
  else if (id>=0x3c00 && id<=0x3cff)
    snprintf(propbuffy, buflen, "Distribution list %04x", id);
  else if (id>=0x3d00 && id<=0x3dff)
    snprintf(propbuffy, buflen, "Profile section %04x", id);
  else if (id>=0x3e00 && id<=0x3fff)
    snprintf(propbuffy, buflen, "Status object %04x", id);
  else 
    snprintf(propbuffy, buflen, "NO IDEA WHAT THIS IS %04x", id);

  return propbuffy;
}

static char *valuebuffy=NULL;

const char *value(unsigned int type, const union _PV &value)
{
  const int buflen=4096;
  if (!valuebuffy)
    valuebuffy=(char*)malloc(buflen);

  if (type==PT_I2 || type==PT_SHORT)
    snprintf(valuebuffy, buflen, "<short>: %d", (int)value.i);
  else if (type==PT_I4 || type==PT_LONG)
    snprintf(valuebuffy, buflen, "<long>: %ld", value.l);
  else if (type==PT_BOOLEAN)
    snprintf(valuebuffy, buflen, "<boolean>: %d", (int)value.b);
  else if (type==PT_STRING8)
    snprintf(valuebuffy, buflen, "<string>: %s", value.lpszA);
#define tt(t) else if (type==t) snprintf(valuebuffy, buflen, "<%s>", #t)
  tt(PT_FLOAT);
  tt(PT_R4);
  tt(PT_R8);
  tt(PT_DOUBLE);
  tt(PT_CURRENCY);
  tt(PT_APPTIME);
  tt(PT_SYSTIME);
  tt(PT_BINARY);
  tt(PT_UNICODE);
  tt(PT_CLSID);
  tt(PT_I8);
  tt(PT_LONGLONG);
  tt(PT_MV_I2);
  tt(PT_MV_LONG);
  tt(PT_MV_R4);
  tt(PT_MV_DOUBLE);
  tt(PT_MV_CURRENCY);
  tt(PT_MV_APPTIME);
  tt(PT_MV_SYSTIME);
  tt(PT_MV_BINARY);
  tt(PT_MV_STRING8);
  tt(PT_MV_UNICODE);
  tt(PT_MV_CLSID);
  tt(PT_MV_I8);
  tt(PT_ERROR);
  tt(PT_NULL);
  tt(PT_OBJECT);
#undef tt
  else snprintf(valuebuffy, buflen, "<unknown type %ux>", type);

  return valuebuffy;

}


static void print_property(const SPropValue &prop)
{
  printf("            %s\n", property_name(PROP_ID(prop.ulPropTag)));
  printf("            %s\n", value(PROP_TYPE(prop.ulPropTag), prop.Value));
}

static void print_row(const SRow &row)
{
  printf("   %ld properties\n", row.cValues);

  for (unsigned i=0;i<row.cValues;i++)
    {
      if (PROP_TYPE(row.lpProps[i].ulPropTag)==PT_ERROR)
	continue;
      printf("        property %d\n", i);
      print_property(row.lpProps[i]);
    }
}

static SPropValue *get_property(const SRow &row, ULONG propdetails)
{
  for (unsigned i=0; i<row.cValues;i++)
    if (row.lpProps[i].ulPropTag==propdetails)
      return &row.lpProps[i];
  return NULL;
}

static bool has_property_value(const SRow &row, ULONG propdetails, long value)
{
  SPropValue *prop=get_property(row, propdetails);
  if (!prop)
    return false;
  switch(PROP_TYPE(prop->ulPropTag))
    {
      // case PT_I2:
    case PT_SHORT: return value==prop->Value.i;
      // case PT_I4:
    case PT_LONG: return value==prop->Value.l;
    case PT_BOOLEAN: return value==prop->Value.b;
    }
}

bool Load(const char *filename)
{
  WAB_PARAM wp={0};
  wp.cbSize=sizeof(WAB_PARAM);
  if (!filename) filename="";
  wp.szFileName=(CHAR*)filename;
  wp.ulFlags=WAB_ENABLE_PROFILES;

  printf("filename is '%s'\n", filename);
  HRESULT hr=openfn(&lpaddrbook, &lpwabobject, &wp, 0);
  if (HR_FAILED(hr))
    {
      errorme(hr, NULL, "Failed to open address book %s", strlen(filename)?filename:"<default>");
      return false;
    }

#if 0
  ULONG cbentryid;
  LPENTRYID entryid;
  hr=lpaddrbook->GetPAB(&cbentryid, &entryid);
  if (HR_FAILED(hr))
    return false;
#endif

  ULONG objtype;

  // hr=lpaddrbook->OpenEntry(cbentryid, entryid, NULL, MAPI_BEST_ACCESS, &objtype, (LPUNKNOWN*)&lpcontainer);
  hr=lpaddrbook->OpenEntry(0, NULL, NULL, MAPI_BEST_ACCESS, &objtype, (LPUNKNOWN*)&lpcontainer);
  if (HR_FAILED(hr))
    return false;

  //  lpwabobject->FreeBuffer(entryid);

  hr=lpcontainer->GetContentsTable(WAB_LOCAL_CONTAINERS|WAB_PROFILE_CONTENTS, &lptable);
  if (HR_FAILED(hr))
    return false;

  return true;
}

bool TopLevel(void)
{
  LPSRowSet lprowset=NULL;
  HRESULT hr=lpaddrbook->GetSearchPath(0, &lprowset);
  if (HR_FAILED(hr))
    {
      errorme(hr, lpaddrbook, "TopLevel:GetSearchPath failed");
      return false;
    }
  

  for (unsigned i=0;i<lprowset->cRows;i++)
    print_row(lprowset->aRow[i]);


  return true;
#if 0
  LPMAPITABLE table=NULL;
  HRESULT hr=lpcontainer->GetHierarchyTable(CONVENIENT_DEPTH, &table);
  if (HR_FAILED(hr))
    {
      errorme(hr, lpcontainer, "TopLevel:GetHierarchyTable1 failed");
      return false;
    }

  LPSRowSet lprowset=NULL;

  do {
    hr=table->QueryRows(1,0,&lprowset);
    if (HR_FAILED(hr))
      {
	errorme(hr, NULL, "TopLevel:QueryRows2 failed");
	return false;
      }
    if (lprowset->cRows==0)
      {
	lprowset=NULL;
	break; //end of table
      }

    print_row(lprowset->aRow[0]);

  } while(true);


  
  return true;
#endif
}

#define DO_PROPSIWANT
#include "_genprops.h"
#undef DO_PROPSIWANT

bool List(void)
{
  HRESULT hr;
#if 0
  HRESULT hr=lptable->SeekRow(BOOKMARK_BEGINNING, 0, NULL);
  if (HR_FAILED(hr))
    return false;

  hr=lptable->SetColumns((SPropTagArray*)&propsiwant, 0);
  if (HR_FAILED(hr))
    return false;
#endif

  LPSRowSet lprowset;
  do {
    hr=lptable->QueryRows(1,0,&lprowset);
    if (HR_FAILED(hr))
      return false;
    if (lprowset->cRows==0)
      break; //end of table

    print_row(lprowset->aRow[0]);

  } while(true);

  return true;
}


int main(int argc, char **argv)
{
  printf("Initialize=%d\n", Initialize());
  const char *fname=NULL;
  if (argc==2)
    fname=argv[1];

  bool res=Load(fname);
  printf("Load(%s)=%d\n", fname?fname:"<NULL>", res);
  if (!res)
    printf("Error: %s\n", errorstring);

  res=TopLevel();
  printf("TopLevel()=%d\n", res);
  if (!res)
    printf("Error: %s\n", errorstring);

  res=List();
  printf("List()=%d\n", res);
  if (!res)
    printf("Error: %s\n", errorstring);

  return 0;
}
