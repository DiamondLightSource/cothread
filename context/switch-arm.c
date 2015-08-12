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

// Coroutine frame switching for ARM

// If Vector Floating Point support is present then we need to preserve the VFP
// registers d8-d15.
#ifdef __VFP_FP__
#define IF_VFP_FP(code)    code
#else
#define IF_VFP_FP(code)
#endif

__asm__(
"       .text\n"
"       .align  2\n"

// void * switch_frame(frame_t *old_frame, frame_t new_frame, void *arg)
// Arugments on entry:
//   r0      address of frame to be saved
//   r1      frame to be loaded
//   r2      Context argument to pass through

FNAME(switch_frame)
"       stmfd   sp!, {r4, r5, r6, r7, r8, r9, sl, fp, lr}\n"
IF_VFP_FP(
"       fstmfdd sp!, {d8-d15}\n")
"       str     sp, [r0]\n"
"       mov     sp, r1\n"
"       mov     r0, r2\n"
IF_VFP_FP(
"       fldmfdd sp!, {d8-d15}\n")
"       ldmfd   sp!, {r4, r5, r6, r7, r8, r9, sl, fp, pc}\n"
FSIZE(switch_frame)


// frame_t create_frame(void *stack_base, frame_action_t action, void *context)
// Arguments on entry:
//   r0      initial base of stack
//   r1      action routine
//   r2      context argument to action
FNAME(create_frame)
"       stmfd   r0!, {r1, r2}\n"       // Save arguments for new coroutine
"       mov     ip, lr\n"              // Save LR so can use same STM slot
"       ldr     lr, =action_entry\n"
"       stmfd   r0!, {r4, r5, r6, r7, r8, r9, sl, fp, lr}\n"
IF_VFP_FP(
"       fstmfdd r0!, {d8-d15}\n")
"       bx      ip\n"

"action_entry:\n"
        // Receive control after first switch to new frame.  Top of stack has
        // the saved context and routine to call, switch argument is in r0.
"       ldmfd   sp!, {r2, r3}\n"       // r2 <- action routine, r3 <- context
"       mov     r1, r3\n"
"       mov     r14, #0\n"             // Ensure no return from action
"       bx      r2\n"
FSIZE(create_frame)
);
