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

# Coroutine frame switching for 32-bit x86
#
# Registers "owned" by caller:
#  ebp, ebx, edi, esi, esp
#
# Registers and their roles:
#
#   esp     Stack pointer, switched by this function
#   ebp     Frame pointer, safely restored on return
#   eax     Return result register
#   ebx     Must be preserved
#   esi     Must be preserved
#   edi     Must be preserved
#   ecx     Scratch
#   edx     Scratch
#
# Structure of a subroutine call after standard %ebp frame entry for function
# call of form f(arg_1, ..., arg_n)
#
#   4n+4(%ebp)  Argument n
#               ...
#   8(%ebp)     Argument 1
#   4(%ebp)     Return link (pushed by call instruction)
#   0(%ebp)     Saved %ebp
#   -4(%ebp)    ... local variables


# void * switch_frame(frame_t *old_frame, frame_t new_frame, void *arg)
.globl  switch_frame
        .type   switch_frame, @function

# On entry have following arguments on stack:
#   4(%esp)     address of frame to be written
#   8(%esp)     frame to be loaded
#   12(%esp)    argument to pass through switch
switch_frame:
        # Pick up the arguments
        movl    4(%esp), %ecx       # %ecx = old_frame
        movl    8(%esp), %edx       # %edx = new_frame
        movl    12(%esp), %eax      # %eax = arg = result register

        # Save registers ABI requires to be preserved.
        pushl   %ebp
        pushl   %ebx
        pushl   %edi
        pushl   %esi

        # Switch stack frames.
        movl    %esp, (%ecx)
        movl    %edx, %esp

        # Restore previously saved registers and we're done, the result is
        # already in the right place.
        popl    %esi
        popl    %edi
        popl    %ebx
        popl    %ebp
        ret
        .size   switch_frame, .-switch_frame


# frame_t get_frame(void)
.globl  get_frame
        .type   get_frame, @function
get_frame:
        movl    %esp, %eax
        ret
        .size   get_frame, .-get_frame


# frame_t create_frame(void *stack_base, frame_action_t action, void *context)
.globl  create_frame
        .type   create_frame, @function

# On entry have following arguments on stack:
#   4(%esp)     base of stack to use
#   8(%esp)     action routine
#   12(%esp)    context to pass to action routine
create_frame:
        # Save the context needed by the action routine and prepare the switch
        # context.  Start by picking up our arguments into registers.
        movl    4(%esp), %eax       # %eax = base of stack
        movl    8(%esp), %edx       # %edx = action routine to call
        movl    12(%esp), %ecx      # %ecx = context for action
        movl    %ecx, -4(%eax)
        movl    %edx, -8(%eax)
        # Push variables expected by switch_frame restore, but push 0 for %ebp
        # to mark base of stack frame list.
        movl    $action_entry, -12(%eax)  # Where switch_frame will switch to
        movl    $0, -16(%eax)
        movl    %ebx, -20(%eax)
        movl    %edi, -24(%eax)
        movl    %esi, -28(%eax)

        # Save new stack frame and we're all done.
        movl    4(%esp), %edx       # Frame address
        subl    $28, %eax
        ret

action_entry:
        # We receive control here after the first switch to a newly created
        # frame.  The top of the stack is the function we're going to call, and
        # then the context it wants, our activation argument is in %eax.
        popl    %ecx                # Pick up action
        pushl   %eax                # Switch result is first argument
        pushl   $0                  # Returning is not allowed!
        jmp     *%ecx

        .size   create_frame, .-create_frame
