/* Python wrapper for greenlet like coroutines, but using proper stack switching
 * instead. */

#include <stdbool.h>
#include <stdio.h>
#include <Python.h>

#include "coroutine.h"

/* Special casting operation to avoid strict aliasing warnings. */
#define CAST(type, value) \
    ( { \
        union { __typeof__(value) a; type b; } __u; \
        __u.a = (value); \
        __u.b; \
    } )


struct py_coroutine {
    coroutine_t coroutine;
    /* For the moment we hang onto the parent here for orderly shutdown.  Really
     * we need to rearrange the logic here and merge with the core library.
     * Similarly, we repeat the "defunct" logic here. */
    coroutine_t parent;
    bool defunct;
};

static __thread struct py_coroutine *current_coroutine = NULL;


PyObject * coroutine_action(PyObject *action, PyObject *arg)
{
    PyObject *result = PyObject_CallFunction(action, "O", arg);
    Py_DECREF(action);
    Py_DECREF(arg);
    Py_XINCREF(result);     // If NULL we're in trouble!
    return result;
}

PyObject * coroutine_create(PyObject *self, PyObject *args)
{
    PyObject *action;
    unsigned int parent_;
    size_t stack_size;
    if (PyArg_ParseTuple(args, "OII", &action, &parent_, &stack_size))
    {
        struct py_coroutine *parent = (struct py_coroutine *) parent_;
        struct py_coroutine *coroutine = malloc(sizeof(struct py_coroutine));
        Py_INCREF(action);
        coroutine->coroutine = create_coroutine(
            parent->coroutine, (coroutine_action_t) coroutine_action,
            stack_size, action);
        coroutine->parent = parent;
        coroutine->defunct = false;
        return PyInt_FromLong((int)coroutine);
    }
    else
        return NULL;
}

PyObject * coroutine_switch(PyObject *Self, PyObject *args)
{
    unsigned int coroutine_;
    PyObject *arg;
    if (PyArg_ParseTuple(args, "IO", &coroutine_, &arg))
    {
        struct py_coroutine *coroutine = (struct py_coroutine *) coroutine_;
        struct py_coroutine *this = current_coroutine;
        current_coroutine = coroutine;
        Py_INCREF(arg);
        PyObject * result =
            (PyObject *) switch_coroutine(coroutine->coroutine, arg);
        if (this->defunct)
        {
            free(this);
        }
    }
    else
        return NULL;
}

static PyObject* coroutine_getcurrent(PyObject *self, PyObject *args)
{
    if (current_coroutine == NULL)
    {
        /* In this special case the current coroutine must be the main thread,
         * so we create a dummy coroutine to represent it. */
        current_coroutine = malloc(sizeof(struct py_coroutine));
        current_coroutine->coroutine = get_current_coroutine();
        current_coroutine->parent = NULL;
        current_coroutine->defunct = false;
    }

    return PyInt_FromLong((int)current_coroutine);
}

static PyMethodDef module_methods[] = {
    { "getcurrent", coroutine_getcurrent, METH_NOARGS,
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
    { NULL, NULL }
};

void init_coroutine(void)
{
    Py_InitModule("_coroutine", module_methods);
}
