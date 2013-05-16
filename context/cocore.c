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

/* Coroutine implementation. */

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#if !defined(__APPLE__)
#include <malloc.h>
#endif
#include <assert.h>
#include <unistd.h>
#include <string.h>
#if defined(WIN32)
#include <windows.h>
#else
#include <sys/mman.h>
#endif

/* We include valgrind annotations so that valgrind can follow along without
 * complaints as we switch stack frames. */
#include "valgrind.h"
#include "memcheck.h"

#include "switch.h"
#include "platform.h"
#include "cocore.h"


/* The shared stack coroutine frame switcher runs in its own stack.  Only a tiny
 * stack is needed for this self contained routine. */
#define FRAME_SWITCHER_STACK    4096

/* Used to advise the compiler that we're doing horrible things behind the
 * scenes and NOT TO MOVE CODE AROUND! */
#define COMPILER_MEMORY_BARRIER()   __asm__ __volatile__("" ::: "memory")


/* A single stack frame can be shared among multiple coroutines, in the style of
 * "greenlets", so we manage the stack separately.  The stack frame records the
 * current coroutine and has to be reference counted (unless it's the master
 * stack, which never goes away).
 *
 * The base of the stack is where loaded frames start.  For dynamically created
 * stacks this is the base of the entire stack frame, for the master stack frame
 * we discover the stack base the first time we need to create a shared
 * coroutine.  We don't store the start of the allocated memory because this can
 * be recovered when necessary. */
struct stack {
    void *stack_base;           // Base of this stack, initial frame pointer
    size_t stack_size;          // Size of allocated stack.
    int guard_size;             // Length of the guard area for this stack
    bool check_stack;           // Whether to check consumption on exit
    struct cocore *current;     // Coroutine currently on the stack
    unsigned int ref_count;     // Number of sharing coroutines
    unsigned int valgrind_stack_id;
};

/* This represents the state of a single coroutine. */
struct cocore {
    frame_t frame;              // Coroutine frame: saves dynamic state
    struct stack *stack;        // Stack that this cocore belongs to
    cocore_action_t action;     // Action performed by coroutine
    struct cocore *parent;      // Receives control when coroutine exits
    struct cocore *defunct;     // Used to delete exited coroutine
    struct cocore_state *state; // Access to thread local state

    /* If the coroutine needs to share a stack frame then the following state
     * is used to save the frame while it is not in use. */
    void *saved_frame;          // Saved stack frame for shared stack
    size_t max_saved_length;    // Size of saved_frame area
    size_t saved_length;        // Bytes saved in saved_frame

    char context[];             // Context saved for coroutine startup
};

/* This is the global state of the coroutine for a single thread. */
struct cocore_state {
    struct cocore *base_coroutine;      // Master coroutine representing thread
    struct cocore *current_coroutine;   // Currently active coroutine
    frame_t switcher_coroutine; // Coroutine to switch a shared stack frame
};


static size_t page_size;        // System page size for guard page allocation
DECLARE_TLS(struct cocore_state *, cocore_state);


/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/*  Shared Stack Switching.                                                  */
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

/* This block of code is concerned with the rather delicate process of switching
 * between coroutine frames which share the same stack.  The rather horrible
 * idea of doing this is inspired by Python Greenlets, but the implementation is
 * not related. */


/* Saves the stack frame currently on the stack that target is currently using.
 * This is simply a matter of saving everything between stack_base of the stack
 * and the target's frame away in the target's saved_frame area. */
static void save_frame(struct cocore *target)
{
    struct stack *stack = target->stack;
    ssize_t frame_size = FRAME_LENGTH(stack->stack_base, target->frame);
    if (frame_size < 0)
        /* Can happen for frames on the main stack if the stack pointer falls
         * below the originally detected stack base. */
        frame_size = 0;
    else
    {
        if ((size_t) frame_size > target->max_saved_length)
        {
            /* Ensure we have enough room for the required save area. */
            free(target->saved_frame);
            target->saved_frame = malloc(frame_size);
            target->max_saved_length = frame_size;
        }
        memcpy(
            target->saved_frame, FRAME_START(stack->stack_base, target->frame),
            frame_size);
    }
    target->saved_length = frame_size;
}


/* Restores a previously saved frame onto the associated stack. */
static void restore_frame(struct cocore *target)
{
    struct stack *stack = target->stack;
    void *frame_start = FRAME_START(stack->stack_base, target->frame);
    VALGRIND_MAKE_MEM_UNDEFINED(frame_start, target->saved_length);
    memcpy(frame_start, target->saved_frame, target->saved_length);
    stack->current = target;
}



/* Arguments passed to frame_switcher. */
struct frame_action {
    void *arg;                  // Argument to pass through to target coroutine
    struct cocore *target;      // Coroutine to be switched to
};

/* Independent coroutine dedicated to switch stack frames when the current frame
 * overlaps with the new frame. */
static __attribute__((noreturn))
    void frame_switcher(void *action_, void *context)
{
    struct cocore_state *state = context;
    frame_t *switcher_coroutine = &state->switcher_coroutine;
    while (true)
    {
        /* Pull the target coroutine and switch argument from the callers stack
         * frame before we potentially destroy this information by relocating
         * the frame. */
        struct frame_action *action = action_;
        void *arg = action->arg;
        struct cocore *target = action->target;

        /* The frame switching code below is likely to destroy the action
         * structure above, so force the compiler not to reorder the code above
         * after the frame switching. */
        COMPILER_MEMORY_BARRIER();
        save_frame(target->stack->current);
        restore_frame(target);

        /* Complete activation of new coroutine and wait for next action. */
        action_ = switch_frame(switcher_coroutine, target->frame, arg);
    }
}


/* Called to switch control from current to target if target doesn't currently
 * own its stack. */
static void *switch_shared_frame(
    struct cocore *current, struct cocore *target, void *arg)
{
    if (current->stack == target->stack)
    {
        /* In this case the stack we want to switch to overlaps the stack we're
         * currently using.  We solve this problem by switching control away to
         * a dedicated switching coroutine while we swap the stacks out. */
        struct frame_action action = { .arg = arg, .target = target };
        return switch_frame(
            &current->frame, current->state->switcher_coroutine, &action);
    }
    else
    {
        /* The target frame doesn't overlap so we can do the switching right
         * here.  In this case it's possible that we're switching to a frame
         * that's already defunct, in which case we don't save it. */
        if (target->stack->current != NULL)
            save_frame(target->stack->current);
        restore_frame(target);
        return switch_frame(&current->frame, target->frame, arg);
    }
}



/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/*  Coroutine and Stack Creation and Deletion.                               */
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */


/* Prepares a brand new stack structure initially owned only by the given
 * coroutine. */
static struct stack *create_stack(
    struct cocore *coroutine, size_t stack_size, bool check_stack,
    int guard_pages)
{
    /* Align the stack either by its minimum alignment or to pages if guard
     * pages have been requested. */
    size_t guard_size = guard_pages * page_size;
    size_t alignment = guard_size == 0 ? STACK_ALIGNMENT : page_size;
    stack_size = (stack_size + alignment - 1) & -alignment;

    size_t alloc_size = stack_size + guard_size;
    void *alloc_base = MALLOC_ALIGNED(alignment, alloc_size);
    if (guard_size > 0)
        /* Disable access to the guard area. */
        mprotect(
            FRAME_START(alloc_base + stack_size, alloc_base),
            guard_size, PROT_NONE);

    struct stack *stack = malloc(sizeof(struct stack));
    stack->stack_base = STACK_BASE(alloc_base, stack_size + guard_size);
    stack->stack_size = stack_size;
    stack->guard_size = guard_size;
    stack->valgrind_stack_id =
        VALGRIND_STACK_REGISTER(alloc_base, alloc_base + alloc_size);

    stack->check_stack = check_stack;
    stack->current = coroutine;
    stack->ref_count = 1;
    if (check_stack)
        memset(FRAME_START(alloc_base, alloc_base + guard_size),
            0xC5, stack_size);
    return stack;
}


/* Creates the base stack for the current thread. */
static struct stack *create_base_stack(struct cocore *coroutine)
{
    struct stack *stack = calloc(1, sizeof(struct stack));
    stack->current = coroutine;
    stack->ref_count = 1;

    /* The allocation of the base of the master stack is straightforward but
     * slightly delicate.  It doesn't hugely matter where it is, so long as it's
     * within the active stack frame and properly aligned.
     *
     * As to *why* it doesn't matter, even when we share the stack frame: the
     * start of stack for all coroutines sharing this stack frame will be placed
     * at this base except for the master coroutine.  This means that memory
     * above this point is properly managed and shared, and memory below this
     * point is exclusive to the master coroutine. */
    stack->stack_base = (void *) ((intptr_t) &stack & -STACK_ALIGNMENT);
    return stack;
}


/* For a stack frame originally initialised with C5 in each byte checks for the
 * high water mark and logs the frame usage to stderr. */
static size_t check_stack_use(struct stack *stack)
{
    ssize_t i;
    for (i = stack->stack_size - 1; i >= 0; i--)
        if (STACK_CHAR(stack->stack_base, i) != 0xC5)
            break;
    return i + 1;
}


/* Called when the last coroutine using this stack has been deleted. */
static void delete_stack(struct cocore_state *state, struct stack *stack)
{
    if (stack->check_stack)
        fprintf(stderr,
            "Stack frame: %"PRIz"u of %"PRIz"u bytes used\n",
            check_stack_use(stack), stack->stack_size);
    /* Recover allocated base from working stack base and original allocation
     * size. */
    void *alloc_base = STACK_BASE(
        stack->stack_base, - stack->stack_size - stack->guard_size);
    if (stack->guard_size > 0)
        /* Restore the original protection on the memory region before freeing
         * it back to the memory pool.  Actually we have a snag here: don't know
         * in general whether PROT_EXEC was enabled, maybe need some system
         * option to discover this.  Chances are it wasn't, and if it was that'd
         * be only because it can't be disabled anyway. */
        mprotect(
            FRAME_START(alloc_base + stack->stack_size, alloc_base),
            stack->guard_size, PROT_READWRITE);
    FREE_ALIGNED(alloc_base);
    VALGRIND_STACK_DEREGISTER(stack->valgrind_stack_id);
    free(stack);
}


/* This is the core implementation of a new coroutine.  All we need to do is run
 * our action until it completes and finally return control to our parent having
 * marked ourself as defunct. */
static __attribute__((noreturn))
    void action_wrapper(void *switch_arg, void *context)
{
    struct cocore *this = context;
    this->state->current_coroutine = this;
    void *result = this->action(this->context, switch_arg);

    /* We're nearly done.  As soon as control is switched away from this
     * coroutine it can be recycled: the receiver of our switch will do the
     * recycling, which we trigger by setting its .defunct field. */
    struct cocore *parent = this->parent;
    parent->defunct = this;
    /* Pass control to the parent.  We'll never get control back again! */
    switch_cocore(parent, result);
    abort();    // (Only needed to persuade compiler.)
}


/* Initialises an initial coroutine frame in a saved state. */
static void create_shared_frame(struct cocore *coroutine)
{
    /* Create a temporary frame right here on the stack. */
    char initial_frame[INITIAL_FRAME_SIZE];
    void *initial_base = STACK_BASE(initial_frame, INITIAL_FRAME_SIZE);
    frame_t frame = create_frame(initial_base, action_wrapper, coroutine);

    /* Relocate the new frame into a saved frame area for this coroutine. */
    size_t frame_length = FRAME_LENGTH(initial_base, frame);
    coroutine->saved_frame = malloc(frame_length);
    coroutine->max_saved_length = frame_length;
    coroutine->saved_length = frame_length;
    memcpy(coroutine->saved_frame,
        FRAME_START(initial_base, frame), frame_length);

    /* Compute the true initial frame pointer by relocating frame to the target
     * stack base. */
    coroutine->frame = coroutine->stack->stack_base + (frame - initial_base);
}



/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/*  Published API                                                            */
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */


void initialise_cocore(void)
{
    INIT_TLS(cocore_state);
    page_size = getpagesize();
}


/* Creates master coroutine for this thread.  Must be called once per thread
 * before any other coroutine actions occur.
 *
 * Note that the coroutine structure is leaked when the thread exits unless
 * terminate_cocore_thread() is called on completion of the thread. */
struct cocore *initialise_cocore_thread(void)
{
    assert(GET_TLS(cocore_state) == NULL);
    struct cocore_state *state = calloc(1, sizeof(struct cocore_state));
    SET_TLS(cocore_state, state);

    /* The base coroutine is rather special: it represents the first coroutine
     * running on the main stack, and so everything is initialised slightly
     * differently. */
    struct cocore *coroutine = calloc(1, sizeof(struct cocore));
    coroutine->state = state;
    coroutine->stack = create_base_stack(coroutine);
    state->base_coroutine = coroutine;
    state->current_coroutine = coroutine;

    /* Now is also a good time to prepare the switcher coroutine in case we need
     * it. */
    void *stack = malloc(FRAME_SWITCHER_STACK);
    state->switcher_coroutine = create_frame(
        STACK_BASE(stack, FRAME_SWITCHER_STACK), frame_switcher, state);
    VALGRIND_STACK_REGISTER(stack, stack + FRAME_SWITCHER_STACK);

    return coroutine;
}


/* Ensures no dangling resources.  Only safe to call as the last action before
 * exiting the thread, and only safe to call from the main coroutine. */
void terminate_cocore_thread(void)
{
    struct cocore_state *state = GET_TLS(cocore_state);
    assert(state->base_coroutine == state->current_coroutine);

    // ...
    // Probably ought to do some further stuff
    free(state->base_coroutine);
    free(state);
    SET_TLS(cocore_state, NULL);
}


/* Returns current coroutine. */
struct cocore *get_current_cocore(void)
{
    struct cocore_state *state = GET_TLS(cocore_state);
    return state->current_coroutine;
}


/* Checks that the given coroutine exists and is in the same thread. */
bool check_cocore(struct cocore *coroutine)
{
    return coroutine->state == GET_TLS(cocore_state);
}


/* Creates a new coroutine with the given parent, action and context.  If
 * shared_stack is NULL a fresh stack of stack_size is created, otherwise the
 * stack is shared with the shared_stack coroutine. */
struct cocore *create_cocore(
    struct cocore *parent, cocore_action_t action,
    void *context, size_t context_size,
    struct cocore *shared_stack,
    size_t stack_size, bool check_stack, int guard_pages)
{
    /* To simplify default state, start with everything zero!  We add on enough
     * space to save the requested context area. */
    struct cocore *coroutine = calloc(1, sizeof(struct cocore) + context_size);
    coroutine->state = parent->state;
    coroutine->action = action;
    coroutine->parent = parent;
    memcpy(coroutine->context, context, context_size);

    if (shared_stack)
    {
        /* Coroutine is sharing space with other coroutines.  Makes initial
         * frame creation a bit more involved. */
        coroutine->stack = shared_stack->stack;
        coroutine->stack->ref_count += 1;
        create_shared_frame(coroutine);
    }
    else
    {
        /* Coroutine is created in its own stack frame.  This is the easiest
         * case, the frame can be created in place. */
        coroutine->stack = create_stack(
            coroutine, stack_size, check_stack, guard_pages);
        coroutine->frame = create_frame(
            coroutine->stack->stack_base, action_wrapper, coroutine);
    }
    return coroutine;
}


/* Deletes a defunct coroutine and releases use of its stack. */
static void delete_cocore(struct cocore *coroutine)
{
    struct stack *stack = coroutine->stack;
    stack->ref_count -= 1;
    if (stack->ref_count == 0)
        delete_stack(coroutine->state, stack);
    else if (stack->current == coroutine)
        /* Whoops: we're still marked as using the the stack.  This won't do. */
        stack->current = NULL;
    free(coroutine->saved_frame);
    free(coroutine);
}


/* Switches control to target coroutine passing the given parameter.  Depending
 * on stack frame sharing the switching process may be more or less involved. */
void *switch_cocore(struct cocore *target, void *parameter)
{
    assert(target->state == GET_TLS(cocore_state));
    struct cocore *this = target->state->current_coroutine;
    void *result;
    if (target->stack->current == target)
        /* No stack retargeting required, simply switch to already available
         * stack frame. */
        result = switch_frame(&this->frame, target->frame, parameter);
    else
        /* Need to switch a shared frame at the same time. */
        result = switch_shared_frame(this, target, parameter);
    this->state->current_coroutine = this;

    /* If the coroutine which just gave us control is defunct delete it now. */
    if (this->defunct)
        delete_cocore(this->defunct);
    this->defunct = NULL;
    return result;
}


/* Stack checking. */
void stack_use(struct cocore *coroutine,
    ssize_t *current_use, ssize_t *max_use, size_t *stack_size)
{
    struct stack *stack = coroutine->stack;
    /* For the active current coroutine use (a proxy for) the current stack
     * pointer, for a saved coroutine use its saved frame. */
    frame_t current_frame = coroutine == coroutine->state->current_coroutine ?
        (frame_t) &stack : coroutine->frame;
    *current_use = FRAME_LENGTH(stack->stack_base, current_frame);
    if (stack->check_stack)
        *max_use = check_stack_use(stack);
    else
        *max_use = -1;      // Error return, cannot compute this value
    *stack_size = stack->stack_size;
}
