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


/* Coroutine frame switching for ARMv8 64 bits, this code follows the
 * Procedure Call Standard for the Arm® 64-bit Architecture (AArch64)
 *
 * Registers and their roles:
 *
 *     SP      The Stack Pointer
 *     x30/LR  The Link Register
 *     X29/FP  The Frame Pointer
 *     x19-x28 Callee-saved registers
 *     x18     The Platform Register, if needed; otherwise a temporary register
 *     x17/IP1 The second intra-procedure-call temporary register(can be used
 *             by callveneers and PLT code); at other times may be used as a
 *             temporary register
 *     x16/IP0 The first intra-procedure-call scratch register (can be used by
 *             call veneers and PLT code); at other times may be used as a
 *             temporary register
 *     x9-x15  Temporary registers
 *     x8      Indirect result location register
 *     x0-x7   Parameter/result registers
 *
 * This means that the registers that the callee should save and restore are:
 *   x19-x28, FP, LR and SP
 * Additionally, ARMv8 64 bits ABI makes NEON mandatory and some extra
 * registers must be saved, in particular registers v8-v15 but only the bottom
 * 64 bits.
 *
 * For more information, see:
 * https://github.com/ARM-software/abi-aa/releases/download/2021Q1/aapcs64.pdf
 */


__asm__(
"       .text\n"

// void * switch_frame(frame_t *old_frame, frame_t new_frame, void *arg)
// Arguments on entry:
//   x0      address of frame to be saved
//   x1      frame to be loaded
//   x2      Context argument to pass through

FNAME(switch_frame)
"       stp x19, x20, [sp, #-16]!\n"
"       stp x21, x22, [sp, #-16]!\n"
"       stp x23, x24, [sp, #-16]!\n"
"       stp x25, x26, [sp, #-16]!\n"
"       stp x27, x28, [sp, #-16]!\n"
"       stp fp, lr, [sp, #-16]!\n"
"       stp d8, d9, [sp, #-16]!\n"
"       stp d10, d11, [sp, #-16]!\n"
"       stp d12, d13, [sp, #-16]!\n"
"       stp d14, d15, [sp, #-16]!\n"
"       mov ip0, sp\n"
"       str ip0, [x0]\n"
"       mov sp, x1\n"
"       mov x0, x2\n"
"       ldp d14, d15, [sp], #16\n"
"       ldp d12, d13, [sp], #16\n"
"       ldp d10, d11, [sp], #16\n"
"       ldp d8, d9, [sp], #16\n"
"       ldp fp, lr, [sp], #16\n"
"       ldp x27, x28, [sp], #16\n"
"       ldp x25, x26, [sp], #16\n"
"       ldp x23, x24, [sp], #16\n"
"       ldp x21, x22, [sp], #16\n"
"       ldp x19, x20, [sp], #16\n"
"       br  lr\n"
FSIZE(switch_frame)


// frame_t create_frame(void *stack_base, frame_action_t action, void *context)
// Arguments on entry:
//   x0      initial base of stack
//   x1      action routine
//   x2      context argument to action
FNAME(create_frame)
"       stp x1, x2, [x0, #-16]!\n"
"       mov ip0, lr\n"               // Save LR so can use same STP slot
"       ldr lr, =action_entry\n"
"       stp x19, x20, [x0, #-16]!\n"
"       stp x21, x22, [x0, #-16]!\n"
"       stp x23, x24, [x0, #-16]!\n"
"       stp x25, x26, [x0, #-16]!\n"
"       stp x27, x28, [x0, #-16]!\n"
"       stp fp, lr, [x0, #-16]!\n"
"       stp d8, d9, [x0, #-16]!\n"
"       stp d10, d11, [x0, #-16]!\n"
"       stp d12, d13, [x0, #-16]!\n"
"       stp d14, d15, [x0, #-16]!\n"
"       br  ip0\n"

"action_entry:\n"
        // Receive control after first switch to new frame.  Top of stack has
        // the saved context and routine to call, switch argument is in r0.
"       ldp x2, x3, [sp], #16\n"   // x2 <- action routine, x3 <- context
"       mov x1, x3\n"
"       mov lr, #0\n"              // Ensure no return from action
"       br  x2\n"
FSIZE(create_frame)
);
