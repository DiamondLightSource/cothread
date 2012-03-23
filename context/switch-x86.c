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

/* Coroutine frame switching for 32-bit x86.  This code is valid for Linux, OSX
 * and Windows (cdecl calling convention).
 *
 * Registers "owned" by caller:
 *  ebp, ebx, edi, esi, esp
 *
 * Registers and their roles:
 *
 *   esp     Stack pointer, switched by this function
 *   ebp     Frame pointer, safely restored on return
 *   eax     Return result register
 *   ebx     Must be preserved
 *   esi     Must be preserved
 *   edi     Must be preserved
 *   ecx     Scratch
 *   edx     Scratch
 *
 * The remaining registers, floating point stack, mm and xmm registers, are all
 * volatile and need not be preserved -- or to be precise, the only constraints
 * are standard conditions on function entry and exit, which are trivially
 * satisfied.
 *
 * Structure of a subroutine call after standard %ebp frame entry for function
 * call of form f(arg_1, ..., arg_n), all arguments are placed on the stack:
 *
 *   4n+4(%ebp)  Argument n
 *               ...
 *   8(%ebp)     Argument 1
 *   4(%ebp)     Return link (pushed by call instruction)
 *   0(%ebp)     Saved %ebp
 *   -4(%ebp)    ... local variables
 *
 * An integer result is returned in eax
 * The stack must be 16-byte aligned before the call occurs */


__asm__(
"       .text\n"

// void * switch_frame(frame_t *old_frame, frame_t new_frame, void *arg)
FNAME(switch_frame)

// On entry have following arguments on stack:
//   4(%esp)     address of frame to be written
//   8(%esp)     frame to be loaded
//   12(%esp)    argument to pass through switch
        // Pick up the arguments
"       movl    4(%esp), %ecx\n"       // %ecx = old_frame
"       movl    8(%esp), %edx\n"       // %edx = new_frame
"       movl    12(%esp), %eax\n"      // %eax = arg = result register

        // Save registers ABI requires to be preserved.
"       pushl   %ebp\n"
"       pushl   %ebx\n"
"       pushl   %edi\n"
"       pushl   %esi\n"

        // Save SIMD and floating point state just in case this coroutine has
        // made a change: we'll make such changes local to each coroutine.
"       sub     $4, %esp\n"
"       stmxcsr (%esp)\n"
"       sub     $4, %esp\n"
"       fstcw   (%esp)\n"

        // Switch stack frames.
"       movl    %esp, (%ecx)\n"
"       movl    %edx, %esp\n"

        // Restore saved floating point and SIMD state.
"       fnclex\n"
"       fldcw   (%esp)\n"
"       add     $4, %esp\n"
"       ldmxcsr (%esp)\n"
"       add     $4, %esp\n"

        // Restore previously saved registers and we're done, the result is
        // already in the right place.
"       popl    %esi\n"
"       popl    %edi\n"
"       popl    %ebx\n"
"       popl    %ebp\n"
"       ret\n"
FSIZE(switch_frame)


// frame_t create_frame(void *stack_base, frame_action_t action, void *context)
// On entry have following arguments on stack:
//   4(%esp)     base of stack to use
//   8(%esp)     action routine
//   12(%esp)    context to pass to action routine

FNAME(create_frame)
        // Save the context needed by the action routine and prepare the switch
        // context.  Start by picking up our arguments into registers.
"       movl    4(%esp), %eax\n"    // %eax = base of stack
"       movl    8(%esp), %edx\n"    // %edx = action routine to call
"       movl    12(%esp), %ecx\n"   // %ecx = context for action
"       movl    $0, -4(%eax)\n"     // Padding to ensure final base of stack on
"       movl    $0, -8(%eax)\n"     //   call to action is 16-byte aligned
"       movl    %ecx, -12(%eax)\n"
"       movl    %edx, -16(%eax)\n"
        // Push variables expected by switch_frame restore, but push 0 for %ebp
        // to mark base of stack frame list.  We use a position independent code
        // trick so this works on OSX as well.
"       call    here\n"
"here:  popl    %edx\n"
"       leal    action_entry-here(%edx), %edx\n"
"       movl    %edx, -20(%eax)\n" // Where switch_frame will switch to
"       movl    $0, -24(%eax)\n"
"       movl    %ebx, -28(%eax)\n"
"       movl    %edi, -32(%eax)\n"
"       movl    %esi, -36(%eax)\n"
"       stmxcsr -40(%eax)\n"
"       fstcw   -44(%eax)\n"

        // Save new stack frame and we're all done.
"       movl    4(%esp), %edx\n"    // Frame address
"       subl    $44, %eax\n"
"       ret\n"

"action_entry:\n"
        // We receive control here after the first switch to a newly created
        // frame.  The top of the stack is the function we're going to call, and
        // then the context it wants, our activation argument is in %eax.
"       popl    %ecx\n"             // Pick up action
"       pushl   %eax\n"             // Switch result is first argument
"       pushl   $0\n"               // Returning is not allowed!
"       jmp     *%ecx\n"
FSIZE(create_frame)
);
