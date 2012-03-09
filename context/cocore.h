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

/* Core of coroutine switching implementation. */

struct cocore;

/* Initialises the cocore library, must be called exactly once before using this
 * library. */
void initialise_cocore(void);

/* The coroutine action is passed a pointer to itself together with the argument
 * passed to the first switch_cocore() routine used to activate it.  The
 * returned result will be passed through to the registered parent. */
typedef void *(*cocore_action_t)(void *context, void *argument);

/* Initialises the master coroutine for the calling thread.  Must be called (per
 * thread) before any other coroutine actions.  Returns the newly initialised
 * base coroutine. */
struct cocore *initialise_cocore_thread(void);

/* This will delete the base coroutine.  This must be the last cocore action on
 * this thread. */
void terminate_cocore_thread(void);

/* Returns the current coroutine. */
struct cocore *get_current_cocore(void);

/* Checks that the target coroutine can be switched to. */
bool check_cocore(struct cocore *coroutine);

/* Creates a new coroutine.  context_size bytes are saved from context[] and
 * passed as the context pointer to action() when it is started.  Control will
 * be returned to parent when (and if) the created coroutine exits, and parent
 * must be non NULL even if the coroutine will never exit.
 *
 * If shared_stack is NULL then stack_size bytes will be allocated for the new
 * coroutine, otherwise it will share its stack with the stack of shared_stack.
 * If check_stack is set (when shared_stack is NULL) the allocated stack will be
 * filled with marker characters, stack_use() can be used to interrogate stack
 * usage during the coroutine lifetime, and a summary of stack usage will be
 * printed to stderr on coroutine exit.
 *
 * Once the created coroutine has exited (by returning from action() and
 * transferring control to parent) its associated cocore structure will
 * automatically be deleted and so must not be referenced after this point. */
struct cocore *create_cocore(
    struct cocore *parent, cocore_action_t action,
    void *context, size_t context_size,
    struct cocore *shared_stack,
    size_t stack_size, bool check_stack, int guard_pages);

/* Idea: Could have an at-exit hook to be called just before a defuct coroutine
 * is destroyed, and a private data mechanism to help _coroutine manage the
 * coroutines. */

/* Switches control to the selected target coroutine with parameter
 * pass-through. */
void *switch_cocore(struct cocore *target, void *parameter);

/* Reports current and maximum stack use for the calling coroutine.  On the
 * base coroutine *current_use is relative to the base used for frame
 * switching, rather than the true stack base and neither max_use nor stack_size
 * are available.  max_use is only available if check_stack was set when the
 * coroutine was created. */
void stack_use(struct cocore *target,
     ssize_t *current_use, ssize_t *max_use, size_t *stack_size);

/* Macro derived from the kernel to tell the compiler that x is quite
 * unlikely to be true. */
#define unlikely(x)   __builtin_expect((x), 0)
