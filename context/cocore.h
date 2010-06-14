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
typedef void * (*cocore_action_t)(struct cocore *coroutine, void *argument);

/* Initialises the master coroutine for the calling thread.  Must be called (per
 * thread) before any other coroutine actions. */
void initialise_cocore(struct cocore *coroutine);

/* Creates a new coroutine. */
void create_cocore(
    struct cocore *coroutine,
    struct cocore *parent, cocore_action_t action,
    struct cocore *shared_stack, size_t stack_size, bool check_stack);

/* Switches control to the selected target coroutine with parameter
 * pass-through.  If control is retunred here from a defunct coroutine it is
 * assigned to *defunct: at this point the original cocore structure has already
 * been released and invalidated, the caller can do any extra cleanup work. */
void * switch_cocore(
    struct cocore *current, struct cocore *target,
    void *parameter, struct cocore **defunct);


/* Casts a member of a structure out to the containing structure. */
#define container_of(ptr, type, member) \
    ( { \
        const typeof(((type *)0)->member) *__mptr = (ptr); \
        (type *)((char *)__mptr - offsetof(type, member)); \
    } )

/* Macro derived from the kernel to tell the compiler that x is quite
 *  * unlikely to be true. */
#define unlikely(x)   __builtin_expect((x), 0)


/******************************************************************************/
/* Private Interface Below.                                                   */

/* The structure below is published here only so that it can be contained in a
 * cocore implementation structure and accessed through the containerof()
 * macro. */


struct cocore {
    frame_t frame;              // Coroutine frame: saves dynamic state
    struct stack *stack;        // Stack that this cocore belongs to
    cocore_action_t action;     // Action performed by coroutine
    struct cocore *parent;      // Receives control when coroutine exits
    struct cocore *defunct;     // Used to delete exited coroutine
    /* If the coroutine needs to share a stack frame then the following state
     * is used to save the frame while it is not in use. */
    void *saved_frame;          // Saved stack frame for shared stack
    size_t saved_length;        // Bytes saved in saved_frame
    size_t max_saved_length;    // Length of allocated saved_frame
};
