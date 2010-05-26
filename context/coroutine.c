/* Coroutine implementation. 
 *
 * This implementation uses swapcontext, see ucontext.h.  This is a somewhat
 * unoptimal implementation, as alas each context switch involves a system call
 * to set the signal mask! */

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <ucontext.h>

#include "coroutine.h"


/* If multiple threads are in play then each thread needs its own coroutine. */
static __thread coroutine_t current_coroutine = NULL;

struct coroutine {
    struct ucontext context;
    coroutine_t parent;
    void *parameter;
};


coroutine_t get_current_coroutine(void)
{
    if (current_coroutine == NULL)
    {
        current_coroutine = malloc(sizeof(struct coroutine));
        getcontext(&current_coroutine->context);
    }
    return current_coroutine;
}

static void coroutine_wrapper(coroutine_action action, void *context)
{
    coroutine_t this = current_coroutine;
    coroutine_t parent = this->parent;
    void *result = action(context, this->parameter);

    /* Once the action has completed we can completely destroy the coroutine.
     * Doing this here means fewer worries about lifetime management: the user
     * of the library has nothing to do with it! */
//     free(this->context.uc_stack.ss_sp);
//     free(this);

    parent->parameter = result;
    current_coroutine = parent;
    // Pass control to the parent.  We never get control back again!
    setcontext(&parent->context);
}

coroutine_t create_coroutine(
    coroutine_t parent, coroutine_action action, size_t stack_size,
    void *context)
{
    coroutine_t coroutine = malloc(sizeof(struct coroutine));
    getcontext(&coroutine->context);    // Initialise uc_sigmask
    coroutine->context.uc_link = &parent->context;
    coroutine->context.uc_stack.ss_sp = malloc(stack_size);
    coroutine->context.uc_stack.ss_size = stack_size;
    coroutine->context.uc_stack.ss_flags = 0;
    coroutine->parent = parent;
    makecontext(&coroutine->context,
        (void (*)())coroutine_wrapper, 2, action, context);
    return coroutine;
}

void delete_coroutine(coroutine_t coroutine)
{
    free(coroutine->context.uc_stack.ss_sp);
    free(coroutine);
}

void * switch_coroutine(coroutine_t coroutine, void *parameter)
{
    coroutine_t this = get_current_coroutine();
    coroutine->parameter = parameter;
    current_coroutine = coroutine;
    swapcontext(&this->context, &coroutine->context);
    return this->parameter;
}
