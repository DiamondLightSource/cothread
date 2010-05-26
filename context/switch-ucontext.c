/* Implementation of switching for ucontext. */

#include <stddef.h>
#include <ucontext.h>

#include "switch.h"


void * switch_frame(frame_t *old_frame, frame_t *new_frame, void *arg)
{
    new_frame->result = arg;
    swapcontext(&old_frame->ucontext, &new_frame->ucontext);
    return old_frame->result;
}


static void coroutine_wrapper(
    frame_t *this, frame_action_t action, void *context)
{
    action(this->result, context);
    /* We won't get control back.  Hell, we'd better not, we're dead if we try
     * to return from this! */
}

void create_frame(
    frame_t *frame, void *stack, size_t stack_size,
    frame_action_t action, void *context)
{
    getcontext(&frame->ucontext);
    frame->ucontext.uc_stack.ss_sp = stack;
    frame->ucontext.uc_stack.ss_size = stack_size;
    frame->ucontext.uc_stack.ss_flags = 0;
    frame->ucontext.uc_link = NULL;
    makecontext(&frame->ucontext, (void (*)()) coroutine_wrapper,
        3, frame, action, context);
}

void current_frame(frame_t *frame)
{
    getcontext(&frame->ucontext);
}


void* get_frame(
    frame_t *frame, void *stack, size_t stack_size,
    frame_action_t action, void *context)
{
    return context;
}
