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

/* Coroutine implementation for testing. */

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>

#include "switch.h"
#include "cocore.h"
#include "coroutine.h"


struct coroutine {
    struct cocore cocore;
    void *context;
    coroutine_action_t action;
};


/* Extracts associated coroutine from cocore pointer. */
#define get_coroutine(cocore_)   container_of(cocore_, struct coroutine, cocore)


static __thread coroutine_t base_coroutine = NULL;

void * action_wrapper(struct cocore *cocore, void *argument)
{
    coroutine_t coroutine = get_coroutine(cocore);
    return coroutine->action(coroutine->context, argument);
}


/* Creates a new coroutine with the given parent, action and context.  If
 * shared_stack is NULL a fresh stack of stack_size is created, otherwise the
 * stack is shared with the shared_stack coroutine. */
coroutine_t create_coroutine(
    coroutine_t parent, coroutine_action_t action, void *context,
    coroutine_t shared_stack, size_t stack_size, bool check_stack)
{
    coroutine_t coroutine = malloc(sizeof(struct coroutine));
    coroutine->context = context;
    coroutine->action = action;
    struct cocore *shared =
        shared_stack == NULL ? NULL : &shared_stack->cocore;
    create_cocore(
        &coroutine->cocore, &parent->cocore, action_wrapper,
        shared, stack_size, check_stack);
    return coroutine;
}


/* Returns the current coroutine.  On first call a wrapper to represent the main
 * stack is created at the same time. */
coroutine_t get_current_coroutine(void)
{
    if (unlikely(base_coroutine == NULL))
    {
        base_coroutine = malloc(sizeof(struct coroutine));
        initialise_cocore(&base_coroutine->cocore);
    }
    return get_coroutine(get_current_cocore());
}


/* Switches control to target coroutine passing the given parameter.  Depending
 * on stack frame sharing the switching process may be more or less involved. */
void * switch_coroutine(coroutine_t target, void *parameter)
{
    struct cocore *defunct;
    void *result = switch_cocore(&target->cocore, parameter, &defunct);
    if (defunct != NULL)
        free(get_coroutine(defunct));
    return result;
}
