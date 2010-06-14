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

#include "switch.h"
#include "cocore.h"


/* Macro for number formatting.  Bit tricky this, as the type of size_t depends
 * on the compiler, and inttypes.h doesn't appear to provide anything suitable.
 * Thus we have to roll our own. */
#if __WORDSIZE == 32
#define PRI_size_t  "%u"
#elif __WORDSIZE == 64
#define PRI_size_t  "%lu"
#endif


/* Default suggested stack size.  Later on we might keep a pool of stack frames
 * of this size. */
#define DEFAULT_STACK_SIZE      (1 << 16)


struct py_coroutine {
    struct cocore cocore;
    PyObject *action;

    /* Python stack tracking.  Need to switch recursion depth and top frame
     * around as we switch frames, otherwise the interpreter gets confused and
     * thinks we've recursed too deep.  In truth tracking this stuff is the
     * only reason this code is in a Python extension! */
    struct _frame *python_frame;
    int recursion_depth;
};

static __thread struct py_coroutine *current_coroutine = NULL;
static __thread struct py_coroutine *base_coroutine = NULL;
static bool check_stack_enabled = false;


static struct py_coroutine * get_current_coroutine(void)
{
    if (unlikely(base_coroutine == NULL))
    {
        /* First time through: initialise the base coroutine and make it
         * current. */
        base_coroutine = malloc(sizeof(struct py_coroutine));
        initialise_cocore(&base_coroutine->cocore);
        current_coroutine = base_coroutine;
    }

    return current_coroutine;
}


static void * coroutine_wrapper(struct cocore *cocore, void *arg_)
{
    PyThreadState *thread_state = PyThreadState_GET();
    /* New coroutine gets a brand new Python interpreter stack frame. */
    thread_state->frame = NULL;
    thread_state->recursion_depth = 0;
    /* Call the given action with the passed argument. */
    struct py_coroutine *this =
        container_of(cocore, struct py_coroutine, cocore);
    current_coroutine = this;

    PyObject *arg = arg_;
    PyObject *result = PyObject_CallFunction(this->action, "O", arg);
    Py_DECREF(this->action);
    Py_DECREF(arg);
    return result;
}


static PyObject * coroutine_create(PyObject *self, PyObject *args)
{
    PyObject *parent_, *action;
    size_t stack_size;
    if (PyArg_ParseTuple(args, "OOI", &parent_, &action, &stack_size))
    {
        struct py_coroutine *parent = PyCObject_AsVoidPtr(parent_);
        if (parent == NULL)
            return NULL;
        struct py_coroutine *coroutine = malloc(sizeof(struct py_coroutine));

        Py_INCREF(action);
        coroutine->action = action;
        create_cocore(
            &coroutine->cocore, &parent->cocore, coroutine_wrapper,
            NULL, stack_size, check_stack_enabled);
        coroutine->python_frame = NULL;
        coroutine->recursion_depth = 0;
        return PyCObject_FromVoidPtr(coroutine, NULL);
    }
    else
        return NULL;
}


/* This does the core work of stack switching including the maintenance of all
 * associated Python state.  The given arg must already have the appropriate
 * extra reference count. */
static PyObject *do_switch(struct py_coroutine *target, PyObject *arg)
{
    struct py_coroutine *this = current_coroutine;
    PyThreadState *thread_state = PyThreadState_GET();
    this->python_frame = thread_state->frame;
    this->recursion_depth = thread_state->recursion_depth;

    struct cocore *defunct_core;
    PyObject *result = switch_cocore(
        &this->cocore, &target->cocore, arg, &defunct_core);
    if (defunct_core != NULL)
        free(container_of(defunct_core, struct py_coroutine, cocore));

    current_coroutine = this;

    thread_state = PyThreadState_GET();
    thread_state->frame = this->python_frame;
    thread_state->recursion_depth = this->recursion_depth;
    return result;
}


static PyObject * coroutine_switch(PyObject *Self, PyObject *args)
{
    PyObject *coroutine_, *arg;
    if (PyArg_ParseTuple(args, "OO", &coroutine_, &arg))
    {
        struct py_coroutine *target = PyCObject_AsVoidPtr(coroutine_);
        if (target == NULL)
            return NULL;

        /* Switch to new coroutine.  For the duration arg needs an extra
         * reference count, it'll be accounted for either on the next returned
         * result or in the entry to a new coroutine. */
        Py_INCREF(arg);
        return do_switch(target, arg);
    }
    else
        return NULL;
}


static PyObject* coroutine_getcurrent(PyObject *self, PyObject *args)
{
    return PyCObject_FromVoidPtr(get_current_coroutine(), NULL);
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


static PyMethodDef module_methods[] = {
    { "get_current", coroutine_getcurrent, METH_NOARGS,
      "_coroutine.getcurrent()\nReturns the current coroutine." },
    { "create", coroutine_create, METH_VARARGS,
      "create(action, parent, stack_size)\n\
Creates a new coroutine with the given action to invoke.  If no parent is\n\
specified the caller will become the parent, which will be switched to\n\
when the coroutine exits.  If no stack_size is specified a default small\n\
stack is allocated." },
    { "switch", coroutine_switch, METH_VARARGS,
      "result = switch(coroutine, arg)\n\
Switches control to this coroutine, passing arg to new coroutine.\n\
When switched back new argument will be returned as result" },
    { "enable_check_stack", enable_check_stack, METH_O,
      "enable_check_stack(enable)\n\
Enables verbose stack checking with results written to stderr when each\n\
coroutine terminates." },
    { NULL, NULL }
};


void init_coroutine(void)
{
    PyObject * module = Py_InitModule("_coroutine", module_methods);
    PyModule_AddObject(module,
        "DEFAULT_STACK_SIZE", PyInt_FromLong(DEFAULT_STACK_SIZE));
}
