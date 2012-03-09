/* This file is part of the Diamond cothread library.
 *
 * Copyright (C) 2010-2012 Michael Abbott, Diamond Light Source Ltd.
 *
 * The Diamond cothread library is free software; you can redistribute it
 * and/or modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the License,
 * or (at your option) any later version.
 *
 * The Diamond cothread library is distributed in the hope that it will be
 * useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
 * Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc., 51
 * Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
 *
 * Contact:
 *      Dr. Michael Abbott,
 *      Diamond Light Source Ltd,
 *      Diamond House,
 *      Chilton,
 *      Didcot,
 *      Oxfordshire,
 *      OX11 0DE
 *      michael.abbott@diamond.ac.uk
 */

/* Python wrapper for minimal windows dependencies. */

#include <Python.h>
#include <stdbool.h>
#include <stdio.h>
#include <windows.h>


/* Wraps Windows WaitForMultipleObjects().  Takes three arguments:
 *  objects     List of waitable object handles to wait for
 *  wait_all    Whether to wait for any one or all objects
 *  timeout     Wait timeout in milliseconds
 * On success returns the index of the first ready item in the list. */
static PyObject *winlib_waitformultiple(PyObject *self, PyObject *args)
{
    PyObject *objects;
    int wait_all, timeout;
    if (PyArg_ParseTuple(args, "OII", &objects, &wait_all, &timeout))
    {
        ssize_t size = PyList_Size(objects);
        if (size == 0)
            PyErr_Format(PyExc_ValueError, "Zero length list not allowed");
        else if (size > 0)
        {
            HANDLE handles[size];
            bool ok = true;
            for (int i = 0; ok  &&  i < size; i ++)
            {
                PyObject *object = PyList_GetItem(objects, i);
                ok = object != NULL;
                if (ok)
                {
                    long handle = PyInt_AsLong(object);
                    ok = ! (handle == -1  &&  PyErr_Occurred());
                    handles[i] = (void *) handle;
                }
            }
            if (ok)
            {
                DWORD result = WaitForMultipleObjects(
                    size, handles, wait_all, timeout);
                if (result == WAIT_FAILED)
                    PyErr_Format(PyExc_OSError, "WaitForMultipleObjects");
                else
                    return PyInt_FromLong(result);
            }
        }
    }
    return NULL;
}

static PyMethodDef module_methods[] = {
    { "WaitForMultipleObjects", winlib_waitformultiple, METH_VARARGS, "" },
    { NULL, NULL }
};


#define MODULE_DOC  "Windows interface library for cothread"

#if PY_MAJOR_VERSION > 2
static PyModuleDef winlib_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_winlib",
    .m_doc = MODULE_DOC,
    .m_size = -1,
    .m_methods = module_methods
};
#endif

#if PY_MAJOR_VERSION == 2
extern void init_winlib(void);
void init_winlib(void)
#else
extern void PyInit__winlib(void);
void PyInit__winlib(void)
#endif
{
#if PY_MAJOR_VERSION == 2
    PyObject *module = Py_InitModule3("_winlib", module_methods, MODULE_DOC);
#else
    PyObject *module = PyModule_Create(&winlib_module);
#endif
    PyModule_AddObject(module, "INFINITE", PyInt_FromLong(INFINITE));
}
