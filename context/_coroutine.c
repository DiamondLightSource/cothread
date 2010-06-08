/* Python wrapper for greenlet like coroutines, but using proper stack switching
 * instead. */

#include <Python.h>
#include <stdbool.h>
#include <stdio.h>

#include "switch.h"


/* Default suggested stack size.  Later on we might keep a pool of stack frames
 * of this size. */
#define DEFAULT_STACK_SIZE      (1 << 16)


struct py_coroutine {
    frame_t frame;
    void *stack;
    size_t stack_size;
    struct py_coroutine *parent;
    struct py_coroutine *defunct;
    /* Python stack tracking.  Need to switch recursion depth and top frame
     * around as we switch frames, otherwise the interpreter gets confused and
     * thinks we've recursed too deep.  In truth tracking this stuff is the
     * only reason this code is in a Python extension! */
    struct _frame *python_frame;
    int recursion_depth;
};

static __thread struct py_coroutine *current_coroutine = NULL;
static bool check_stack_enabled = false;


struct py_coroutine * get_current_coroutine(void)
{
    if (current_coroutine == NULL)
    {
        /* In this special case the current coroutine must be the main thread,
         * so we create a dummy coroutine to represent it. */
        current_coroutine = malloc(sizeof(struct py_coroutine));
        current_coroutine->stack = NULL;
        current_coroutine->stack_size = 0;
        current_coroutine->parent = NULL;
        current_coroutine->defunct = NULL;
        current_coroutine->python_frame = NULL;
        current_coroutine->recursion_depth = 0;
#ifdef USE_UCONTEXT
        current_frame(&current_coroutine->frame);
#endif
    }
    return current_coroutine;
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

    current_coroutine = target;
    PyObject *result = (PyObject *) switch_frame(
        &this->frame, &target->frame, arg);

    thread_state = PyThreadState_GET();
    thread_state->frame = this->python_frame;
    thread_state->recursion_depth = this->recursion_depth;
    return result;
}


static void coroutine_wrapper(void *arg, void *action)
{
    struct py_coroutine *this = current_coroutine;
    PyThreadState *thread_state = PyThreadState_GET();
    /* New coroutine gets a brand new stack frame. */
    thread_state->frame = NULL;
    thread_state->recursion_depth = 0;

    /* Call the given action with the passed argument. */
    PyObject *result = PyObject_CallFunction(
        (PyObject *) action, "O", (PyObject *) arg);
    Py_DECREF((PyObject *) action);
    Py_DECREF((PyObject *) arg);

    /* Switch control to parent.  We had better not get control back! */
    this->parent->defunct = this;
    (void) do_switch(this->parent, result);
}


PyObject * coroutine_create(PyObject *self, PyObject *args)
{
    PyObject *parent_, *action;
    size_t stack_size;
    if (PyArg_ParseTuple(args, "OOI", &parent_, &action, &stack_size))
    {
        struct py_coroutine *parent = 
            (struct py_coroutine *) PyCObject_AsVoidPtr(parent_);
        if (parent == NULL)
            return NULL;
        struct py_coroutine *coroutine = malloc(sizeof(struct py_coroutine));
        /* If a malloc this small fails we're dead anyway, not going to bother
         * to handle this one! */

        Py_INCREF(action);

        coroutine->stack = malloc(stack_size);  /* Ditto, but less force. */
        coroutine->stack_size = stack_size;
        if (check_stack_enabled)
            memset(coroutine->stack, 0xC5, stack_size);
        coroutine->parent = parent;
        coroutine->defunct = NULL;
        coroutine->python_frame = NULL;
        coroutine->recursion_depth = 0;
        create_frame(
            &coroutine->frame, coroutine->stack, stack_size,
            coroutine_wrapper, action);
        return PyCObject_FromVoidPtr(coroutine, NULL);
    }
    else
        return NULL;
}


void check_stack(unsigned char *stack, size_t stack_size)
{
    /* Hard wired assumption that stack grows down.  Ho hum. */
    size_t i;
    for (i = 0; i < stack_size; i ++)
        if (stack[i] != 0xC5)
            break;
    fprintf(stderr, "Stack frame: %d of %d bytes used\n",
        stack_size - i, stack_size);
}


PyObject * coroutine_switch(PyObject *Self, PyObject *args)
{
    PyObject *coroutine_, *arg;
    if (PyArg_ParseTuple(args, "OO", &coroutine_, &arg))
    {
        struct py_coroutine *target =
            (struct py_coroutine *) PyCObject_AsVoidPtr(coroutine_);
        if (target == NULL)
            return NULL;

        /* Switch to new coroutine.  For the duration arg needs an extra
         * reference count, it'll be accounted for either on the next returned
         * result or in the entry to a new coroutine. */
        Py_INCREF(arg);
        PyObject *result = do_switch(target, arg);

        /* If the coroutine switching to us has just terminated it will have
         * left us a defunct pointer, which can be cleaned up now. */
        struct py_coroutine *this = current_coroutine;
        struct py_coroutine *defunct = this->defunct;
        if (defunct)
        {
            if (check_stack_enabled)
                check_stack(defunct->stack, defunct->stack_size);
            free(defunct->stack);
            free(defunct);
            this->defunct = NULL;
        }

        return result;
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
