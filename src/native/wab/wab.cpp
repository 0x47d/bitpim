#include <windows.h>
#include <wab.h>
#include <stdio.h>


static HMODULE hModule;
static LPWABOPEN openfn;
static LPADRBOOK lpaddrbook;
static LPWABOBJECT lpwabobject;
static LPABCONT lpcontainer;
static LPMAPITABLE lptable;

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
    return false;

  openfn=(LPWABOPEN) GetProcAddress(hModule, "WABOpen");

  if (!openfn)
    return false;

  return true;
}

// see mapitypes.h for these names and ranges

static struct { ULONG id; const char* name; }  propnames[]={
#define PR(t) { PROP_ID(t), #t }
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


bool Load(const char *filename)
{
  WAB_PARAM wp={0};
  wp.cbSize=sizeof(WAB_PARAM);
  if (!filename) filename="";
  wp.szFileName=(CHAR*)filename;
  HRESULT hr=openfn(&lpaddrbook, &lpwabobject, &wp, 0);
  if (HR_FAILED(hr))
    return false;

  ULONG cbentryid;
  LPENTRYID entryid;
  hr=lpaddrbook->GetPAB(&cbentryid, &entryid);
  if (HR_FAILED(hr))
    return false;

  ULONG objtype;

  hr=lpaddrbook->OpenEntry(cbentryid, entryid, NULL, MAPI_BEST_ACCESS, &objtype, (LPUNKNOWN*)&lpcontainer);
  if (HR_FAILED(hr))
    return false;

  lpwabobject->FreeBuffer(entryid);

  hr=lpcontainer->GetContentsTable(0, &lptable);
  if (HR_FAILED(hr))
    return false;

  return true;
}

#define DO_PROPSIWANT
#include "_genprops.h"
#undef DO_PROPSIWANT

bool List(void)
{
  HRESULT hr=lptable->SeekRow(BOOKMARK_BEGINNING, 0, NULL);
  if (HR_FAILED(hr))
    return false;

  hr=lptable->SetColumns((SPropTagArray*)&propsiwant, 0);
  if (HR_FAILED(hr))
    return false;

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
  printf("Load(%s)=%d\n", fname?fname:"<NULL>", Load(fname));
 
  printf("List()=%d\n", List());
  return 0;
}
