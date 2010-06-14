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

/* Coroutine implementation. */

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "coroutine.h"

#include "switch.h"

/* Macro for number formatting.  Bit tricky this, as the type of size_t depends
 * on the compiler, and inttypes.h doesn't appear to provide anything suitable.
 * Thus we have to roll our own. */
#if __WORDSIZE == 32
#define PRI_size_t  "%u"
#elif __WORDSIZE == 64
#define PRI_size_t  "%lu"
#endif


/* The shared stack coroutine frame switcher runs in its own stack.  Only a tiny
 * stack is needed for this self contained routine. */
#define FRAME_SWITCHER_STACK    (4 * 4096)

/* Used to advise the compiler that we're doing horrible things behind the
 * scenes and NOT TO MOVE CODE AROUND! */
#define COMPILER_MEMORY_BARRIER()   __asm__ __volatile__("" ::: "memory")


/* Saved frame allocation size calculation.  We round the saved length up to a
 * multiple of some largeish number to try and avoid lots of tiny reallocations
 * as the frame grows. */
#define SAVE_FRAME_INCREMENT    (1 << 12)
#define SAVE_FRAME_SIZE(size) \
    (((size) + SAVE_FRAME_INCREMENT - 1) & (SAVE_FRAME_INCREMENT - 1))


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
    void *stack_base;           // Base of this stack.
    size_t stack_size;          // Size of allocated stack.
    bool check_stack;           // Whether to check consumption on exit
    struct coroutine *current;  // Coroutine currently on the stack
    unsigned int ref_count;     // Number of sharing coroutines
};

struct coroutine {
    frame_t frame;              // Coroutine frame: saves dynamic state
    struct stack *stack;        // Stack that this coroutine belongs to
    coroutine_action_t action;  // Action performed by coroutine
    coroutine_t parent;         // Receives control when coroutine exits
    coroutine_t defunct;        // Used to delete exited coroutine
    /* If the coroutine needs to share a stack frame then the following state
     * is used to save the frame while it is not in use. */
    void *saved_frame;          // Saved stack frame for shared stack
    size_t saved_length;        // Bytes saved in saved_frame
    size_t max_saved_length;    // Length of allocated saved_frame
};


/* If multiple threads are in play then each thread needs its own coroutine. */
static __thread coroutine_t current_coroutine = NULL;
static __thread frame_t switcher_coroutine = NULL;



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
static void save_frame(struct coroutine *target)
{
    struct stack *stack = target->stack;
    ssize_t frame_size = FRAME_LENGTH(stack->stack_base, target->frame);
    if (frame_size < 0)
        /* Can happen for frames on the main stack if the high water mark falls
         * below the originally detected stack base. */
        frame_size = 0;
    else if (frame_size > (ssize_t) target->max_saved_length)
    {
        /* Rather than realloc, save the hassle of copying data around that we'd
         * immediately discard, just free and allocate at a larger size. */
        free(target->saved_frame);
        target->max_saved_length = SAVE_FRAME_SIZE(frame_size);
        target->saved_frame = malloc(target->max_saved_length);
    }
    memcpy(
        target->saved_frame, FRAME_START(stack->stack_base, target->frame),
        frame_size);
    target->saved_length = frame_size;
}


/* Restores a previously saved frame onto the associated stack. */
static void restore_frame(struct coroutine *target)
{
    struct stack *stack = target->stack;
    memcpy(
        FRAME_START(stack->stack_base, target->frame),
        target->saved_frame, target->saved_length);
    stack->current = target;
}


/* Arguments passed to frame_switcher. */
struct frame_action {
    void *arg;                  // Argument to pass through to target coroutine
    struct coroutine *target;   // Coroutine to be switched to
};

/* Independent coroutine dedicated to switch stack frames when the current frame
 * overlaps with the new frame. */
static __attribute__((noreturn))
    void frame_switcher(void *action_, void *context)
{
    while (true)
    {
        /* Pull the target coroutine and switch argument from the callers stack
         * frame before we potentially destroy this information by relocating
         * the frame. */
        struct frame_action *action = (struct frame_action *) action_;
        void *arg = action->arg;
        struct coroutine *target = action->target;

        /* The frame switching code below is likely to destroy the action
         * structure above, so force the compiler not to reorder the code above
         * after the frame switching. */
        COMPILER_MEMORY_BARRIER();
        save_frame(target->stack->current);
        restore_frame(target);

        /* Complete activation of new coroutine and wait for next action. */
        action_ = switch_frame(&switcher_coroutine, target->frame, arg);
    }
}


/* Called to switch control from current to target if target doesn't currently
 * own its stack. */
static void *switch_shared_frame(
    struct coroutine *current, struct coroutine *target, void *arg)
{
    if (current->stack == target->stack)
    {
        /* In this case the stack we want to switch to overlaps the stack we're
         * currently using.  We solve this problem by switching control away to
         * a dedicated switching coroutine while we swap the stacks out. */
        if (switcher_coroutine == NULL)
        {
            /* If the switcher coroutine isn't running yet start it now.  In the
             * presence of multiple threads each thread will get its own frame
             * switcher coroutine. */
            void *stack = STACK_BASE(
                malloc(FRAME_SWITCHER_STACK), FRAME_SWITCHER_STACK);
            switcher_coroutine = create_frame(stack, frame_switcher, NULL);
        }

        struct frame_action action = { .arg = arg, .target = target };
        return switch_frame(&current->frame, switcher_coroutine, &action);
    }
    else
    {
        /* The target frame doesn't overlap so we can do the switching right
         * here. */
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
static struct stack * create_stack(
    coroutine_t coroutine, size_t stack_size, bool check_stack)
{
    struct stack *stack = malloc(sizeof(struct stack));
    void *alloc_base = malloc(stack_size);
    stack->stack_base = STACK_BASE(alloc_base, stack_size);
    stack->stack_size = stack_size;
    stack->check_stack = check_stack;
    stack->current = coroutine;
    stack->ref_count = 1;
    if (check_stack)
        memset(alloc_base, 0xC5, stack_size);
    return stack;
}


/* Creates the base stack for the current coroutine. */
static struct stack * create_base_stack(coroutine_t coroutine)
{
    struct stack *stack = calloc(1, sizeof(struct stack));
    stack->current = coroutine;
    stack->ref_count = 1;
    /* We need to initialise stack_base to something sensible.  It doesn't
     * hugely matter where it is, but placing it at the current high water mark
     * seems a good idea. */
    stack->stack_base = get_frame();
    return stack;
}


/* For a stack frame originally initialised with C5 in each byte checks for the
 * high water mark and logs the frame usage to stderr. */
static void check_stack(void *stack_base, size_t stack_size)
{
    ssize_t i;
    for (i = stack_size-1; i >= 0; i--)
        if (*STACK_INDEX(stack_base, i) != 0xC5)
            break;
    fprintf(stderr,
        "Stack frame: " PRI_size_t " of " PRI_size_t " bytes used\n",
        i + 1, stack_size);
}


/* Called when the last coroutine using this stack has been deleted. */
static void delete_stack(struct stack *stack)
{
    if (stack->check_stack)
        check_stack(stack->stack_base, stack->stack_size);
    /* Recover allocated base from working stack base and original allocation
     * size. */
    free(STACK_BASE(stack->stack_base, - stack->stack_size));
    free(stack);
}


/* This is the core implementation of a new coroutine.  All we need to do is run
 * our action until it completes and finally return control to our parent having
 * marked ourself as defunct. */
static __attribute__((noreturn))
    void action_wrapper(void *switch_arg, void *context)
{
    coroutine_t this = current_coroutine;
    void *result = this->action(context, switch_arg);

    /* We're nearly done.  As soon as control is switched away from this
     * coroutine it can be recycled: the receiver of our switch will do the
     * recycling, which we trigger by setting its .defunct field. */
    coroutine_t parent = this->parent;
    parent->defunct = this;
    /* Pass control to the parent.  We'll never get control back again! */
    switch_coroutine(parent, result);
    abort();    // (Only needed to persuade compiler.)
}


/* Initialises an initial coroutine frame in a saved state. */
static void create_shared_frame(coroutine_t coroutine, void *context)
{
    /* Create a temporary frame right here on the stack. */
    char initial_frame[INITIAL_FRAME_SIZE];
    void *initial_base = STACK_BASE(initial_frame, INITIAL_FRAME_SIZE);
    frame_t frame = create_frame(initial_base, action_wrapper, context);

    /* Relocate the new frame into a saved frame area for this coroutine. */
    size_t frame_length = FRAME_LENGTH(initial_base, frame);
    coroutine->max_saved_length = SAVE_FRAME_SIZE(frame_length);
    coroutine->saved_frame = malloc(frame_length);
    coroutine->saved_length = frame_length;
    memcpy(coroutine->saved_frame,
        FRAME_START(initial_base, frame), frame_length);

    /* Compute the true initial frame pointer by relocating frame to the target
     * stack base. */
    coroutine->frame = coroutine->stack->stack_base + (frame - initial_base);
}


/* The base coroutine is rather special: it represents the first coroutine
 * running on the main stack, and so everything is initialised slightly
 * differently. */
static coroutine_t create_base_coroutine(void)
{
    coroutine_t coroutine = calloc(1, sizeof(struct coroutine));
    coroutine->stack = create_base_stack(coroutine);
    return coroutine;
}


/* Deletes a defunct coroutine and releases use of its stack. */
static void delete_coroutine(struct coroutine *coroutine)
{
    struct stack *stack = coroutine->stack;
    stack->ref_count -= 1;
    if (stack->ref_count == 0)
        delete_stack(stack);
    free(coroutine->saved_frame);
    free(coroutine);
}



/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/*  Published API                                                            */
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */


/* Creates a new coroutine with the given parent, action and context.  If
 * shared_stack is NULL a fresh stack of stack_size is created, otherwise the
 * stack is shared with the shared_stack coroutine. */
coroutine_t create_coroutine(
    coroutine_t parent, coroutine_action_t action, void *context,
    coroutine_t shared_stack, size_t stack_size, bool check_stack)
{
    coroutine_t coroutine = calloc(1, sizeof(struct coroutine));
    coroutine->action = action;
    coroutine->parent = parent;

    if (shared_stack)
    {
        /* Coroutine is sharing space with other coroutines.  Makes initial
         * frame creation a bit more involved. */
        coroutine->stack = shared_stack->stack;
        coroutine->stack->ref_count += 1;
        create_shared_frame(coroutine, context);
    }
    else
    {
        /* Coroutine is created in its own stack frame.  This is the easiest
         * case, the frame can be created in place. */
        coroutine->stack = create_stack(coroutine, stack_size, check_stack);
        coroutine->frame = create_frame(
            coroutine->stack->stack_base, action_wrapper, context);
    }
    return coroutine;
}


/* Returns the current coroutine.  On first call a wrapper to represent the main
 * stack is created at the same time. */
coroutine_t get_current_coroutine(void)
{
    if (current_coroutine == NULL)
        current_coroutine = create_base_coroutine();
    return current_coroutine;
}


/* Switches control to target coroutine passing the given parameter.  Depending
 * on stack frame sharing the switching process may be more or less involved. */
void * switch_coroutine(coroutine_t target, void *parameter)
{
    coroutine_t this = get_current_coroutine();
    current_coroutine = target;

    void *result;
    if (target->stack->current == target)
        /* No stack retargeting required, simply switch to already available
         * stack frame. */
        result = switch_frame(&this->frame, target->frame, parameter);
    else
        /* Need to switch a shared frame at the same time. */
        result = switch_shared_frame(this, target, parameter);

    /* Trigger defunct coroutine processing. */
    coroutine_t defunct = current_coroutine->defunct;
    if (defunct)
    {
        delete_coroutine(defunct);
        current_coroutine->defunct = NULL;
    }

    return result;
}
