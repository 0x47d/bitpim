#include <windows.h>
#include <stdio.h>

static HMODULE hModule;

bool Load(void)
{
  HKEY keyresult;
  BYTE keyValue[MAX_PATH+1];
  DWORD dataout=MAX_PATH;

  RegOpenKeyEx(HKEY_LOCAL_MACHINE, "Software\\Microsoft\\WAB\\DLLPath", 0, KEY_ALL_ACCESS, &keyresult);
  long result = RegQueryValueEx(keyresult, "", 0, 0, keyValue, &dataout);
  RegCloseKey(keyresult);

  hModule=LoadLibrary((char*)keyValue);

  return true;
}

int main(void)
{
  printf("result=%d\n", Load());
}
