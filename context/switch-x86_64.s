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

# Coroutine frame switching for 64-bit x86
#
# The AMD64 architecture provides 16 general 64-bit registers together with 16
# 128-bit SSE registers and 8 80-bit x87 floating point registers.
#
# Registers "owned" by caller:
#   rbx, rsp, rbp, r12-r15, mxcsr (control bits), x87 CW
# The callee must preserve the mxcsr control bits and the x87 control word.
# All other registers are volatile and do not need to be preserved.
#
# General registers and their roles:
#
#   rax     Result register
#   rbx     Must be preserved
#   rcx     Fourth argument
#   rdx     Third argument
#   rsp     Stack pointer, must be preserved
#   rbp     Frame pointer, must be preserved
#   rsi     Second argument
#   rdi     First argument
#   r8      Fifth argument
#   r9      Sixth argument
#   r10-r11 Scratch
#   r12-r15 Must be preserved


# void * switch_frame(frame_t *old_frame, frame_t new_frame, void *arg)
.globl  switch_frame
        .type   switch_frame, @function

# Arguments:
#   rdi     Address to store saved stack after switch
#   rsi     New stack pointer
#   rdx     Argument to pass through to switched frame
switch_frame:
        # Push all the registers we need to save
        pushq   %rbp
        pushq   %r15
        pushq   %r14
        pushq   %r13
        pushq   %r12
        pushq   %rbx

        # Save floating point and MMX status.
        subq    $8, %rsp            # 2 bytes for x86 CW, 4 for mxcsr
        wait                        # Ensure no lingering FP exceptions
        fnstcw  4(%rsp)             # Save x86 control word
        stmxcsr (%rsp)              # Save MMX control word

        # Switch frame and save current frame
        movq    %rsp, (%rdi)
        movq    %rsi, %rsp

        # Restore FP and MMX
        ldmxcsr (%rsp)
        fldcw   4(%rsp)
        addq    $8, %rsp

        # Return to caller with argument in hand
        movq    %rdx, %rax
        popq    %rbx
        popq    %r12
        popq    %r13
        popq    %r14
        popq    %r15
        popq    %rbp
        ret
        .size   switch_frame, .-switch_frame


# frame_t get_frame(void)
.globl  get_frame
        .type   get_frame, @function
get_frame:
        movq    %rsp, %rax
        ret
        .size   get_frame, .-get_frame


# frame_t create_frame(void *stack_base, frame_action_t action, void *context)
.globl  create_frame
        .type   create_frame, @function

# Arguments:
#   rdi     base of stack to use
#   rsi     action routine
#   rdx     context to pass to action routine
create_frame:
        # Save the extra arguments needed by the new frame
        movq    %rdx, -8(%rdi)      # Context for action routine
        movq    %rsi, -16(%rdi)     # Action routine to call
        # Push the frame expected by switch_frame, but store 0 for %rbp.  Set
        # things up to start control at action_entry
        movq    $action_entry, -24(%rdi)
        movq    $0, -32(%rdi)
        movq    %r15, -40(%rdi)
        movq    %r14, -48(%rdi)
        movq    %r13, -56(%rdi)
        movq    %r12, -64(%rdi)
        movq    %rbx, -72(%rdi)
        # Save floating point and MMX status.
        wait
        fnstcw  -74(%rdi)
        stmxcsr -80(%rdi)
        # Save the new frame pointer and we're done
        subq    $80, %rdi
        movq    %rdi, %rax
        ret

action_entry:
        # We receive control here after the first switch to a newly created
        # frame.  The top of the stack is the function we're going to call, and
        # then the context it wants, our activation argument is in %rax.
        #
        # We will call the action routine with the argument in rdi and the saved
        # context in rsi.
        popq    %rdx                # Action routine
        popq    %rsi                # Context argument
        movq    %rax, %rdi
        pushq   $0                  # Returning not allowed!
        jmp     *%rdx

        .size   create_frame, .-create_frame
