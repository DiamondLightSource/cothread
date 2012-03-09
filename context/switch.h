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

/* Interface for stack switching.
 *
 * This file defines a complete but minimal interface for implementing stack
 * frame switching.  All of the routines in this file can only be implemented in
 * assembler, and the descriptions below define the required implementation.
 *
 * This interface assumes a classical C stack occupying a contiguous block of
 * memory.  The assumption is made that stack frame switching can be achieved by
 * simply relocating the stack pointer and related registers.
 *
 * A saved "frame" as defined by this API is the position of the stack pointer
 * where all registers required to be saved by the ABI are saved.  Multiple
 * frames can be saved, each in its own dedicated stack, and switch_frame() is
 * used to transfer control between frames.
 *
 * The API defined here consists of the following routines:
 *
 *  create_frame()
 *      Creates a new saved frame on a previously unused stack.  When the frame
 *      is resumed control will be passed to the given action routine.
 *
 *  switch_frame()
 *      Switches control from the currently active stack to a saved frame.  The
 *      active stack becomes a saved frame and the switched to frame becomes the
 *      active stack.
 *
 * Some macros are also defined to help cope with the fact that, at least in
 * principle, the stack can grown up or down.  In practice only downward stacks
 * have ever been tested with this code. */

/* A saved stack frame is completely defined by a pointer to the top of the
 * stack frame. */
typedef void *frame_t;

/* The action performed for a new frame takes two arguments: the context
 * argument passed to create_frame() when this frame was first established and
 * the argument passed to the first activating switch_frame() call.
 *
 * This routine must never return. */
typedef __attribute__((noreturn))
    void (*frame_action_t)(void *arg, void *context);

/* Switch to new_frame, previously established by create_frame() or an earlier
 * switch_frame().  The caller's stack frame is written to *old_frame. */
void * switch_frame(frame_t *old_frame, frame_t new_frame, void *arg);

/* Establish a new frame in the given stack.  action(arg, context) will be
 * called when the newly created frame is switched to, and it must never return.
 *
 * The initial frame can safely be relocated and started at a different
 * location.  FRAME_START(stack_base, *frame) points to the start of the created
 * frame and FRAME_LENGTH(stack_base, *frame) computes its length, which is
 * guaranteed to be no more than INITIAL_FRAME_SIZE. */
frame_t create_frame(void *stack_base, frame_action_t action, void *context);


/* Architecture dependent definitions.  If necessary, use choices following the
 * same pattern as in switch.c to make system dependent choices.  For the time
 * being it seems that all our architectures share the key properties. */

/* This is a safe upper bound on the storage required by create_frame(), a newly
 * created frame is guaranteed to fit into this many bytes. */
#define INITIAL_FRAME_SIZE      512
/* For the moment we put all our stacks on a 16 byte alignment. */
#define STACK_ALIGNMENT     16
/* Don't actually know an architecture with an upward stack.  If one appears,
 * used preprocessor symbols here to detect it and ensure STACK_GROWS_DOWNWARD
 * is not defined.  Also in this case check *all* uses of the symbols below, as
 * they've never been tested. */
#define STACK_GROWS_DOWNWARD

/* Abstractions of stack direction dependent constructions.
 *
 *  STACK_BASE(stack_start, length)
 *      Returns the base of an area of stack allocated with the given start
 *      address and length.  Conversely, STACK_BASE(stack_base, -length) returns
 *      the original allocation base.
 *
 *  FRAME_START(stack_base, frame_ptr)
 *      Returns lowest address of the complete frame bounded by stack_base and
 *      the saved frame pointer.
 *
 *  FRAME_LENGTH(stack_base, frame_ptr)
 *      Returns the length of the frame bounded by stack base and frame pointer.
 *
 *  STACK_CHAR(stack_base, index)
 *      Returns the indexed character in the stack, with index 0 addressing the
 *      first pushed byte.
 */


#ifdef STACK_GROWS_DOWNWARD
#define STACK_BASE(stack_start, length)     ((stack_start) + (length))
#define FRAME_START(stack_base, frame)      (frame)
#define FRAME_LENGTH(stack_base, frame)     ((stack_base) - (frame))
#define STACK_CHAR(stack_base, index) \
    (((unsigned char *)(stack_base))[-(index)-1])
#else
#define STACK_BASE(stack_start, length)     (stack_start)
#define FRAME_START(stack_base, frame)      (stack_base)
#define FRAME_LENGTH(stack_base, frame)     ((frame) - (stack_base))
#define STACK_CHAR(stack_base, index) \
    (((unsigned char *)(stack_base))[(index)])
#endif
