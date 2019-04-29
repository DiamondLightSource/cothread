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

/* Python wrapper for greenlet like coroutines, but using proper stack switching
 * instead. */

#include <Python.h>
#include <stdbool.h>
#include <stdio.h>
#include <stddef.h>

#include "platform.h"
#include "cocore.h"


/* Special casting operation to bypass strict aliasing warnings. */
#define CAST(type, value) \
    ( { \
        union { __typeof__(value) a; type b; } __u; \
        __u.a = (value); \
        __u.b; \
    } )

#define CAPSULE_NAME    "cothread.coroutine"
#ifndef Py_CAPSULE_H
#define PyCapsule_GetPointer(object, name) \
    PyCObject_AsVoidPtr(object)
#define PyCapsule_New(object, name, delete) \
    PyCObject_FromVoidPtr(object, delete)
#endif

DECLARE_TLS(struct cocore *, base_coroutine);
static bool check_stack_enabled = false;
static int guard_pages = 4;


/* Helper function for use with "O&" format to extract the underlying cocore
 * object from the wrapping Python object. */
static int get_cocore(PyObject *object, void **result)
{
    *result = PyCapsule_GetPointer(object, CAPSULE_NAME);
    /* Check that we've chosen a valid target. */
    if (*result != NULL  &&  !check_cocore(*result))
    {
        PyErr_Format(PyExc_ValueError, "Invalid target coroutine");
        *result = NULL;
    }
    return *result != NULL;
}


static void *coroutine_wrapper(void *action_, void *arg_)
{
    PyThreadState *thread_state = PyThreadState_GET();

    /* New coroutine gets a brand new Python interpreter stack frame. */
    thread_state->frame = NULL;
    thread_state->recursion_depth = 0;

    /* Also reset the exception state in case it's non NULL at this point.  We
     * don't own these pointers at this point, coroutine_switch does. */
#if PY_VERSION_HEX >= 0x03070000
    /* In Python 3.7 the exec info moved. */
    thread_state->exc_state = (_PyErr_StackItem) { };
    thread_state->exc_info = &thread_state->exc_state;
#else
    thread_state->exc_type = NULL;
    thread_state->exc_value = NULL;
    thread_state->exc_traceback = NULL;
#endif

    /* Call the given action with the passed argument. */
    PyObject *action = *(PyObject **)action_;
    PyObject *arg = arg_;
    PyObject *result = PyObject_CallFunctionObjArgs(action, arg, NULL);
    Py_DECREF(action);
    Py_DECREF(arg);

    /* Some of the stuff we've initialised can leak through, so far I've only
     * seen exc_type still set at this point, but maybe other fields can also
     * leak.  Avoid a memory leak by making sure we're not holding onto these.
     *    All these pointers really are defunct, because as soon as we return
     * coroutine_switch will replace all these values. */
    Py_XDECREF(thread_state->frame);
#if PY_VERSION_HEX >= 0x03070000
    Py_XDECREF(thread_state->exc_state.exc_type);
    Py_XDECREF(thread_state->exc_state.exc_value);
    Py_XDECREF(thread_state->exc_state.exc_traceback);
#else
    Py_XDECREF(thread_state->exc_type);
    Py_XDECREF(thread_state->exc_value);
    Py_XDECREF(thread_state->exc_traceback);
#endif

    return result;
}


static PyObject *coroutine_create(PyObject *self, PyObject *args)
{
    struct cocore *parent;
    PyObject *action;
    int stack_size;
    if (PyArg_ParseTuple(args, "O&OI",
            get_cocore, &parent, &action, &stack_size))
    {
        Py_INCREF(action);
        struct cocore * coroutine = create_cocore(
            parent, coroutine_wrapper, &action, sizeof(action),
            stack_size == 0 ? GET_TLS(base_coroutine) : NULL,
            stack_size, check_stack_enabled, guard_pages);
        return PyCapsule_New(coroutine, CAPSULE_NAME, NULL);
    }
    else
        return NULL;
}


static PyObject *coroutine_switch(PyObject *Self, PyObject *args)
{
    struct cocore *target;
    PyObject *arg;
    if (PyArg_ParseTuple(args, "O&O", get_cocore, &target, &arg))
    {
        /* Need to switch the Python interpreter's record of recursion depth and
         * top frame around as we switch frames, otherwise the interpreter gets
         * confused and thinks we've recursed too deep.  In truth tracking this
         * stuff is the only reason this code is in a Python extension! */
        PyThreadState *thread_state = PyThreadState_GET();
        struct _frame *python_frame = thread_state->frame;
        int recursion_depth = thread_state->recursion_depth;

        /* We also need to switch the exception state around: if we don't do
         * this then we get confusion about the lifetime of exception state
         * between coroutines.  The most obvious problem is that the exception
         * isn't properly cleared on function return. */
#if PY_VERSION_HEX >= 0x03070000
        _PyErr_StackItem exc_state = thread_state->exc_state;
        _PyErr_StackItem *exc_info = thread_state->exc_info;
#else
        PyObject *exc_type = thread_state->exc_type;
        PyObject *exc_value = thread_state->exc_value;
        PyObject *exc_traceback = thread_state->exc_traceback;
#endif

        /* Switch to new coroutine.  For the duration arg needs an extra
         * reference count, it'll be accounted for either on the next returned
         * result or in the entry to a new coroutine. */
        Py_INCREF(arg);
        PyObject *result = switch_cocore(target, arg);

        /* Restore previously saved state.  I wonder if PyThreadState_GET()
         * really needs to be called again here... */
        thread_state = PyThreadState_GET();
        thread_state->frame = python_frame;
        thread_state->recursion_depth = recursion_depth;

        /* Restore the exception state. */
#if PY_VERSION_HEX >= 0x03070000
        thread_state->exc_state = exc_state;
        thread_state->exc_info = exc_info;
#else
        thread_state->exc_type = exc_type;
        thread_state->exc_value = exc_value;
        thread_state->exc_traceback = exc_traceback;
#endif
        return result;
    }
    else
        return NULL;
}


/* This function has a very important side effect: on first call it initialises
 * the thread specific part of the coroutine library.  Fortunately the API
 * published by this module really requires that get_current() be called before
 * doing anything substantial. */
static PyObject *coroutine_getcurrent(PyObject *self, PyObject *args)
{
    if (unlikely(GET_TLS(base_coroutine) == NULL))
        /* First time through initialise the cocore library. */
        SET_TLS(base_coroutine, initialise_cocore_thread());
    return PyCapsule_New(get_current_cocore(), CAPSULE_NAME, NULL);
}


static PyObject *coroutine_is_equal(PyObject *self, PyObject *args)
{
    struct cocore *cocore1, *cocore2;
    if (PyArg_ParseTuple(args, "O&O&",
            get_cocore, &cocore1, get_cocore, &cocore2))
        return PyBool_FromLong(cocore1 == cocore2);
    else
        return NULL;
}


static PyObject *enable_check_stack(PyObject *self, PyObject *arg)
{
    int is_true = PyObject_IsTrue(arg);
    if (is_true == -1)
        return NULL;
    else
    {
        check_stack_enabled = is_true == 1;
        Py_RETURN_NONE;
    }
}


static PyObject *py_stack_use(PyObject *self, PyObject *args)
{
    struct cocore *target = NULL;
    if (PyArg_ParseTuple(args, "|O&", get_cocore, &target))
    {
        if (target == NULL)
            target = get_current_cocore();
        ssize_t current_use, max_use;
        size_t stack_size;
        stack_use(target, &current_use, &max_use, &stack_size);
        return Py_BuildValue("nnn", current_use, max_use, stack_size);
    }
    else
        return NULL;
}


static PyObject *readline_hook_callback;

static int readline_hook(void)
{
    PyGILState_STATE state = PyGILState_Ensure();
    PyObject *result =
        PyObject_CallFunctionObjArgs(readline_hook_callback, NULL);
    if (result == NULL)
    {
        fprintf(stderr, "Exception caught from readline hook\n");
        PyErr_PrintEx(0);
    }
    else
    {
        if (PyObject_IsTrue(result))
            fprintf(stderr, "Alas can't pass ctrl-C to readline\n");
//             PyErr_SetInterrupt();
        Py_DECREF(result);
    }
    PyGILState_Release(state);

    return 0;
}


static PyObject *install_readline_hook(PyObject *self, PyObject *arg)
{
    Py_XDECREF(readline_hook_callback);
    Py_INCREF(arg);
    readline_hook_callback = arg;
    if (arg == Py_None)
        PyOS_InputHook = NULL;
    else
        PyOS_InputHook = readline_hook;
    Py_RETURN_NONE;
}


static PyMethodDef module_methods[] = {
    { "get_current", coroutine_getcurrent, METH_NOARGS,
      "_coroutine.getcurrent()\nReturns the current coroutine." },
    { "is_equal", coroutine_is_equal, METH_VARARGS,
      "is_equal(coroutine1, coroutine2)\n\
Compares two coroutine objects for equality" },
    { "create", coroutine_create, METH_VARARGS,
      "create(parent, action, stack_size)\n\
Creates a new coroutine with the given action to invoke.  The parent\n\
will be switched to when the coroutine exits.  If no stack_size is\n\
specified the stack is shared with the main stack." },
    { "switch", coroutine_switch, METH_VARARGS,
      "result = switch(coroutine, arg)\n\
Switches control to this coroutine, passing arg to new coroutine.\n\
When switched back new argument will be returned as result" },
    { "enable_check_stack", enable_check_stack, METH_O,
      "enable_check_stack(enable)\n\
Enables verbose stack checking with results written to stderr when each\n\
coroutine terminates." },
    { "stack_use", py_stack_use, METH_VARARGS,
      "Returns current and maximum stack use." },
    { "install_readline_hook", install_readline_hook, METH_O,
      "install_readline_hook(hook)\n\
Installs hook to be called while the interpreter is waiting for input.\n\
If the hook function returns true an interrupt will be raised." },
    { NULL, NULL }
};


#define MODULE_DOC  "Core coroutine module for cothread"

#if PY_MAJOR_VERSION > 2
static PyModuleDef coroutine_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_coroutine",
    .m_doc = MODULE_DOC,
    .m_size = -1,
    .m_methods = module_methods
};
#endif


#if PY_MAJOR_VERSION == 2
extern void init_coroutine(void);
void init_coroutine(void)
#else
extern void PyInit__coroutine(void);
void PyInit__coroutine(void)
#endif
{
    INIT_TLS(base_coroutine);
    initialise_cocore();
#if PY_MAJOR_VERSION == 2
    Py_InitModule3("_coroutine", module_methods, MODULE_DOC);
#else
    PyModule_Create(&coroutine_module);
#endif
}
