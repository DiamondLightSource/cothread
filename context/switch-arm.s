# This file is part of the Diamond cothread library.
#
# Copyright (C) 2010 Michael Abbott, Diamond Light Source Ltd.
#
# The Diamond cothread library is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License,
# or (at your option) any later version.
#
# The Diamond cothread library is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
# Contact:
#      Dr. Michael Abbott,
#      Diamond Light Source Ltd,
#      Diamond House,
#      Chilton,
#      Didcot,
#      Oxfordshire,
#      OX11 0DE
#      michael.abbott@diamond.ac.uk

# Coroutine frame switching for ARM

        .text
        .align  2

# void * switch_frame(frame_t *old_frame, frame_t new_frame, void *arg)
        .global switch_frame
        .type   switch_frame, %function

# Arugments on entry:
#   r0      address of frame to be saved
#   r1      frame to be loaded
#   r2      Context argument to pass through
switch_frame:
        stmfd   sp!, {r4, r5, r6, r7, r8, r9, sl, fp, lr}
        str     sp, [r0]
        mov     sp, r1
        mov     r0, r2
        ldmfd   sp!, {r4, r5, r6, r7, r8, r9, sl, fp, pc}
        .size   switch_frame, .-switch_frame


# frame_t get_frame(void)
        .globl  get_frame
        .type   get_frame, %function
get_frame:
        mov     r0, sp
        bx      r14
        .size   get_frame, .-get_frame


# frame_t create_frame(void *stack_base, frame_action_t action, void *context)
        .global create_frame
        .type   create_frame, %function

# Arguments on entry:
#   r0      initial base of stack
#   r1      action routine
#   r2      context argument to action
create_frame:
        stmfd   r0!, {r1, r2}           /* Save arguments for new coroutine */
        mov     ip, lr                  /* Save LR so can use same STM slot */
        ldr     lr, =action_entry
        stmfd   r0!, {r4, r5, r6, r7, r8, r9, sl, fp, lr}
        bx      ip

action_entry:
        # Receive control after first switch to new frame.  Top of stack has the
        # saved context and routine to call, switch argument is in r0.
        ldmfd   sp!, {r2, r3}   /* r2 <- action routine, r3 <- context */
        mov     r1, r3
        mov     r14, #0         /* Ensure no return from action */
        bx      r2
        .size   create_frame, .-create_frame
