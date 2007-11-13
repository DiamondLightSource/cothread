#include "Python.h"
#include <setjmp.h>
#include <signal.h>
#include <errno.h>
#include <sys/time.h>

int PyOS_Readline_Interrupted = 0;

#if defined(HAVE_SETLOCALE)
/* GNU readline() mistakenly sets the LC_CTYPE locale.
 * This is evil.  Only the user or the app's main() should do this!
 * We must save and restore the locale around the rl_initialize() call.
 */
#define SAVE_LOCALE
#include <locale.h>
#endif

/* GNU readline definitions */
#undef HAVE_CONFIG_H /* Else readline/chardefs.h includes strings.h */
#include <readline/readline.h>
#include <readline/history.h>

#ifdef HAVE_RL_COMPLETION_MATCHES
#define completion_matches(x, y) \
    rl_completion_matches((x), ((rl_compentry_func_t *)(y)))
#endif



#if defined(HAVE_RL_CALLBACK) && defined(HAVE_SELECT)

static  char *completed_input_string;
static void rlhandler(char *text)
{
    completed_input_string = text;
    rl_callback_handler_remove();
}

extern PyThreadState* _PyOS_ReadlineTState;

static char * readline_until_enter_or_signal(char *prompt, int *signal)
{
    char * not_done_reading = "";
    fd_set selectset;

    *signal = 0;
#ifdef HAVE_RL_CATCH_SIGNAL
    rl_catch_signals = 0;
#endif

    rl_callback_handler_install (prompt, rlhandler);
    FD_ZERO(&selectset);
    
    completed_input_string = not_done_reading;

    while (completed_input_string == not_done_reading) {
        int has_input = 0;
        PyOS_Readline_Interrupted = 0;

        while (!has_input)
        {   
            struct timeval timeout = {0, 100000}; /* 0.1 seconds */
            FD_SET(fileno(rl_instream), &selectset);
            /* select resets selectset if no input was available */
            has_input = select(fileno(rl_instream) + 1, &selectset,
                       NULL, NULL, &timeout);
            if(PyOS_InputHook) PyOS_InputHook();
            if(PyOS_Readline_Interrupted) {
                has_input = -1;
                PyErr_SetInterrupt();
                break;
            }
        }

        if(has_input > 0) {
            rl_callback_read_char();
        }
        else if (errno == EINTR || PyOS_Readline_Interrupted) {
            int s;
#ifdef WITH_THREAD
            PyEval_RestoreThread(_PyOS_ReadlineTState);
#endif
            s = PyErr_CheckSignals();
#ifdef WITH_THREAD
            PyEval_SaveThread();    
#endif
            if (s < 0) {
                rl_free_line_state();
                rl_cleanup_after_signal();
                rl_callback_handler_remove();
                *signal = 1;
                completed_input_string = NULL;
            }
        }
    }

    return completed_input_string;
}


#else
#error "Oops.  This case isn't supported (no hook available)."
#endif /*defined(HAVE_RL_CALLBACK) && defined(HAVE_SELECT) */


static char * call_readline(FILE *sys_stdin, FILE *sys_stdout, char *prompt)
{
    size_t n;
    char *p, *q;
    int signal;

#ifdef SAVE_LOCALE
    char *saved_locale = strdup(setlocale(LC_CTYPE, NULL));
    if (!saved_locale)
        Py_FatalError("not enough memory to save locale");
    setlocale(LC_CTYPE, "");
#endif

    if (sys_stdin != rl_instream || sys_stdout != rl_outstream) {
        rl_instream = sys_stdin;
        rl_outstream = sys_stdout;
#ifdef HAVE_RL_COMPLETION_APPEND_CHARACTER
        rl_prep_terminal (1);
#endif
    }

    p = readline_until_enter_or_signal(prompt, &signal);
    
    /* we got an interrupt signal */
    if(signal) {
        return NULL;
    }

    /* We got an EOF, return a empty string. */
    if (p == NULL) {
        p = PyMem_Malloc(1);
        if (p != NULL)
            *p = '\0';
        return p;
    }

    /* we have a valid line */
    n = strlen(p);
    if (n > 0) {
        char *line;
        HISTORY_STATE *state = history_get_history_state();
        if (state->length > 0)
            line = history_get(state->length)->line;
        else
            line = "";
        if (strcmp(p, line))
            add_history(p);
        /* the history docs don't say so, but the address of state
           changes each time history_get_history_state is called
           which makes me think it's freshly malloc'd memory...
           on the other hand, the address of the last line stays the
           same as long as history isn't extended, so it appears to
           be malloc'd but managed by the history package... */
        free(state);
    }
    /* Copy the malloc'ed buffer into a PyMem_Malloc'ed one and
       release the original. */
    q = p;
    p = PyMem_Malloc(n+2);
    if (p != NULL) {
        strncpy(p, q, n);
        p[n] = '\n';
        p[n+1] = '\0';
    }
    free(q);
#ifdef SAVE_LOCALE
    setlocale(LC_CTYPE, saved_locale); /* Restore locale */
    free(saved_locale);
#endif
    return p;
}



PyDoc_STRVAR(doc_module,
    "This module patches the behaviour of the readline PyOS_InputHook \n"
    "function so that hooked functions can properly handle interrupts.");

PyMODINIT_FUNC initcall_readline(void)
{
    Py_InitModule4("call_readline",
        NULL, doc_module, NULL, PYTHON_API_VERSION);
    
    PyOS_ReadlineFunctionPointer = call_readline;
}
