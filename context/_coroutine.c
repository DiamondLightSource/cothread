/* This file is part of the Diamond cothread library.
 *
 * Copyright (C) 2010 Michael Abbott, Diamond Light Source Ltd.
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

#include "cocore.h"


/* Special casting operation to bypass strict aliasing warnings. */
#define CAST(type, value) \
    ( { \
        union { __typeof__(value) a; type b; } __u; \
        __u.a = (value); \
        __u.b; \
    } )


static __thread struct cocore *base_coroutine = NULL;
static bool check_stack_enabled = false;


/* Helper function for use with "O&" format to extract the underlying cocore
 * object from the wrapping Python object. */
static int get_cocore(PyObject *object, void **result)
{
    *result = PyCObject_AsVoidPtr(object);
    /* Check that we've chosen a valid target. */
    if (*result != NULL  &&  !check_cocore(*result))
    {
        printf("Validity check failed on %p\n", *result);
        PyErr_Format(PyExc_ValueError, "Invalid target coroutine");
        *result = NULL;
    }
    return *result != NULL;
}


static void * coroutine_wrapper(void *action_, void *arg_)
{
    PyThreadState *thread_state = PyThreadState_GET();
    /* New coroutine gets a brand new Python interpreter stack frame. */
    thread_state->frame = NULL;
    thread_state->recursion_depth = 0;

    /* Call the given action with the passed argument. */
    PyObject *action = *(PyObject **)action_;
    PyObject *arg = arg_;
    PyObject *result = PyObject_CallFunction(action, "O", arg);
    Py_DECREF(action);
    Py_DECREF(arg);
    return result;
}


static PyObject * coroutine_create(PyObject *self, PyObject *args)
{
    struct cocore *parent;
    PyObject *action;
    size_t stack_size;
    if (PyArg_ParseTuple(args, "O&OI",
            get_cocore, &parent, &action, &stack_size))
    {
        Py_INCREF(action);
        struct cocore * coroutine = create_cocore(
            parent, coroutine_wrapper, &action, sizeof(action),
            stack_size == 0 ? base_coroutine : NULL,
            stack_size, check_stack_enabled);
        return PyCObject_FromVoidPtr(coroutine, NULL);
    }
    else
        return NULL;
}


static PyObject * coroutine_switch(PyObject *Self, PyObject *args)
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
        return result;
    }
    else
        return NULL;
}


static PyObject* coroutine_getcurrent(PyObject *self, PyObject *args)
{
    if (unlikely(base_coroutine == NULL))
        /* First time through initialise the cocore library. */
        base_coroutine = initialise_cocore();
    return PyCObject_FromVoidPtr(get_current_cocore(), NULL);
}


static PyObject* enable_check_stack(PyObject *self, PyObject *arg)
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


static PyObject* py_stack_use(PyObject *self, PyObject *args)
{
    struct cocore *target = NULL;
    if (PyArg_ParseTuple(args, "|O&", get_cocore, &target))
    {
        if (target == NULL)
            target = get_current_cocore();
        ssize_t current_use, max_use;
        stack_use(target, &current_use, &max_use);
        return Py_BuildValue("nn", current_use, max_use);
    }
    else
        return NULL;
}


static PyMethodDef module_methods[] = {
    { "get_current", coroutine_getcurrent, METH_NOARGS,
      "_coroutine.getcurrent()\nReturns the current coroutine." },
    { "create", coroutine_create, METH_VARARGS,
      "create(parent, action, stack_size)\n\
Creates a new coroutine with the given action to invoke.  The parent will\n\
be switched to when the coroutine exits.  If no stack_size is specified\n\
the stack is shared with the main stack." },
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
    { NULL, NULL }
};


/* Ugh: the compiler gets all excited about "strict-aliasing rules", broken by
 * the definition of Py_True.  Make it happy. */
#undef Py_True
#define Py_True CAST(PyObject *, &_Py_TrueStruct)

void init_coroutine(void)
{
    PyObject * module = Py_InitModule("_coroutine", module_methods);
    Py_INCREF(Py_True);
    PyModule_AddObject(module, "separate_stacks", Py_True);
}
