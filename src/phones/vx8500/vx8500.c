//### BITPIM
//###
//### Copyright (C) 2007 Joe Pham <djpham@bitpim.org>
//###
//### This program is free software; you can redistribute it and/or modify
//### it under the terms of the BitPim license as detailed in the LICENSE file.
//###
//### $Id$

#include "Python.h"
#include <Windows.h>

#ifdef __cplusplus
extern "C" {
#endif
int calldll(unsigned long long_in, char *buf, char *dll_address);
#ifdef __cplusplus
}
#endif

static PyObject *
get_key(PyObject *self, PyObject *args)
{
	char *s, buf[4096], *p;
	unsigned long i, j;
	HINSTANCE hinstDll;
	int res_flg=0;

	if(!PyArg_ParseTuple(args, "is:get_key(int ,string", &i, &s))
		return NULL;
	// printf("i: 0x%08X, s: %s\n", i, s);
	hinstDll=LoadLibrary(s);
	if (hinstDll != NULL) {
		p=(char *)GetProcAddress(hinstDll, "TestSCRDownloadUSB_Interface");
		if (p != NULL) {
			j=calldll(i, buf, p);
			res_flg=1;
		}
		FreeLibrary(hinstDll);
	}
	if (res_flg) {
		// valid result
		return Py_BuildValue("i", j);
	} else {
		// Error happen
		Py_INCREF(Py_None);
		return Py_None;
	}
}

static PyMethodDef vx8500_methods[] = {
	{"get_key", get_key, METH_VARARGS, "Return a DM key"},
	{NULL, NULL, 0, NULL }        /* Sentinel */
};

PyMODINIT_FUNC
initpyvx8500(void)
{
	Py_InitModule("pyvx8500", vx8500_methods);
}
