/* Coroutine implementation. */

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "coroutine.h"

#include "switch.h"


/* If multiple threads are in play then each thread needs its own coroutine. */
static __thread coroutine_t current_coroutine = NULL;
static bool check_stack_enabled = false;

struct coroutine {
    frame_t frame;              // Coroutine frame
    void *stack;
    size_t stack_size;
    coroutine_action_t action;  // Action performed by coroutine
    coroutine_t parent;         // Receives control when coroutine exits
    coroutine_t defunct;        // Used to delete exited coroutine
};


void enable_check_stack(bool enable_check)
{
    check_stack_enabled = enable_check;
}

coroutine_t get_current_coroutine(void)
{
    if (current_coroutine == NULL)
    {
        current_coroutine = malloc(sizeof(struct coroutine));
        current_frame(&current_coroutine->frame);
        current_coroutine->defunct = NULL;
    }
    return current_coroutine;
}

static void action_wrapper(void *switch_arg, void *context)
{
    coroutine_t this = current_coroutine;
    void *result = this->action(context, switch_arg);

    /* We're nearly done.  As soon as control is switched away from this
     * coroutine it can be recycled: the receiver of our switch will do the
     * recycling, which we trigger by setting its .defunct field. */
    coroutine_t parent = this->parent;
    parent->defunct = this;
    // Pass control to the parent.  We'd better never get control back again!
    switch_coroutine(parent, result);
}

coroutine_t create_coroutine(
    coroutine_t parent, coroutine_action_t action, size_t stack_size,
    void *context)
{
    coroutine_t coroutine = malloc(sizeof(struct coroutine));
    coroutine->stack = malloc(stack_size);
    coroutine->stack_size = stack_size;
    coroutine->action = action;
    coroutine->parent = parent;
    coroutine->defunct = NULL;
    if (check_stack_enabled)
        memset(coroutine->stack, 0xC5, stack_size);
    create_frame(&coroutine->frame, coroutine->stack, stack_size,
        action_wrapper, context);
    return coroutine;
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

void * switch_coroutine(coroutine_t coroutine, void *parameter)
{
    coroutine_t this = get_current_coroutine();
    current_coroutine = coroutine;
    void *result = switch_frame(&this->frame, &coroutine->frame, parameter);

    coroutine_t defunct = current_coroutine->defunct;
    if (defunct)
    {
        if (check_stack_enabled)
            check_stack(defunct->stack, defunct->stack_size);
        free(defunct->stack);
        free(defunct);
        current_coroutine->defunct = NULL;
    }

    return result;
}
