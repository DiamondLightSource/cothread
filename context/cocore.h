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

/* Core of coroutine switching implementation. */

struct cocore;

/* The coroutine action is passed a pointer to itself together with the argument
 * passed to the first switch_cocore() routine used to activate it.  The
 * returned result will be passed through to the registered parent. */
typedef void * (*cocore_action_t)(void *context, void *argument);

/* Initialises the master coroutine for the calling thread.  Must be called (per
 * thread) before any other coroutine actions.  Returns the newly initialised
 * base coroutine. */
struct cocore * initialise_cocore(void);

/* Returns the current coroutine. */
struct cocore * get_current_cocore(void);

/* Creates a new coroutine.  context_size bytes are saved from context[] and
 * passed as the context pointer to action() when it is started. */
struct cocore * create_cocore(
    struct cocore *parent, cocore_action_t action,
    void *context, size_t context_size,
    struct cocore *shared_stack, size_t stack_size, bool check_stack);

/* Switches control to the selected target coroutine with parameter
 * pass-through. */
void * switch_cocore(struct cocore *target, void *parameter);

/* Reports current and maximum stack use for the calling coroutine.  On the
 * base coroutine *current_use is relative to the base used for frame
 * switching, rather than the true stack base. */
void stack_use(struct cocore *target, ssize_t *current_use, ssize_t *max_use);

/* Macro derived from the kernel to tell the compiler that x is quite
 * unlikely to be true. */
#define unlikely(x)   __builtin_expect((x), 0)
