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

/* Coroutine frame switching for 64-bit x86 on both Unix (Linux and OSX) and
 * Windows.  Unfortunately the ABIs for Unix and for Windows are rather
 * different in a number of key registers.
 *
 * References:
 *      System V Application Binary Interface, AMD64 Architecture Processor
 *      Supplement, Draft Version 0.99.5, September 3, 2010
 *
 *      http://msdn.microsoft.com/en-US/library/ms235286(v=VS.80).aspx
 *
 * The AMD64 architecture provides 16 general 64-bit registers together with 16
 * 128-bit SSE registers, overlapping with 8 legacy 80-bit x87 floating point
 * registers.
 *
 *              Both                Unix only           Windows only
 *              ----                ---------           ------------
 *  rax         Result register
 *  rbx         Must be preserved
 *  rcx                             Fourth argument     First argument
 *  rdx                             Third argument      Second argument
 *  rsp         Stack pointer, must be preserved
 *  rbp         Frame pointer, must be preserved
 *  rsi                             Second argument     Must be preserved
 *  rdi                             First argument      Must be preserved
 *  r8                              Fifth argument      Third argument
 *  r9                              Sixth argument      Fourth argument
 *  r10-r11     Volatile
 *  r12-r15     Must be preserved
 *  xmm0-5      Volatile
 *  xmm6-15                         Volatile            Must be preserved
 *  fpcsr       Non volatile
 *  mxcsr       Non volatile
 *
 * Thus for the two architectures we get slightly different lists of registers
 * to preserve.
 *
 * Registers "owned" by caller:
 *  Unix:       rbx, rsp, rbp, r12-r15, mxcsr (control bits), x87 CW
 *  Windows:    rbx, rsp, rbp, rsi, rdi, r12-r15, xmm6-15
 *
 * The status of mxcsr and fpcsr is a little more delicate, but it's safest to
 * save and restore them as well here.  To be precise, the Unix ABI specifies
 * that the control bits of mxcsr and fpcsr must be preserved by the caller,
 * whereas the Windows ABI presents a more involved story.  In practice it is
 * safest to save and restore them across coroutine switches. */


/* Define the three platform dependent parameter registers. */
#ifdef WIN64
#define P1      "%rcx"
#define P2      "%rdx"
#define P3      "%r8"
#else
#define P1      "%rdi"
#define P2      "%rsi"
#define P3      "%rdx"
#endif


__asm__(
"      .text\n"

// void * switch_frame(frame_t *old_frame, frame_t new_frame, void *arg)
FNAME(switch_frame)

// Arguments:
//   P1      Address to store saved stack after switch
//   P2      New stack pointer
//   P3      Argument to pass through to switched frame
        // Push all the registers we need to save
"       pushq   %rbp\n"
"       pushq   %r15\n"
"       pushq   %r14\n"
"       pushq   %r13\n"
"       pushq   %r12\n"
"       pushq   %rbx\n"

        // Save floating point and MMX status.
"       subq    $8, %rsp\n"             // 2 bytes for x86 CW, 4 for mxcsr
"       wait\n"                         // Ensure no lingering FP exceptions
"       fnstcw  4(%rsp)\n"              // Save x86 control word
"       stmxcsr (%rsp)\n"               // Save MMX control word

#ifdef WIN64
"       pushq   %rsi\n"
"       pushq   %rdi\n"

        // Save MMX registers
"       subq    $128, %rsp\n"
"       movaps  %xmm6, 112(%rsp)\n"
"       movaps  %xmm7, 96(%rsp)\n"
"       movaps  %xmm8, 80(%rsp)\n"
"       movaps  %xmm9, 64(%rsp)\n"
"       movaps  %xmm10, 48(%rsp)\n"
"       movaps  %xmm11, 32(%rsp)\n"
"       movaps  %xmm12, 16(%rsp)\n"
"       movaps  %xmm13, (%rsp)\n"
"       subq    $32, %rsp\n"
"       movaps  %xmm14, 16(%rsp)\n"
"       movaps  %xmm15, (%rsp)\n"
#endif

        // Switch frame and save current frame
"       movq    %rsp, ("P1")\n"
"       movq    "P2", %rsp\n"

#ifdef WIN64
        // Restore MMX regs
"       movaps  (%rsp), %xmm15\n"
"       movaps  16(%rsp), %xmm14\n"
"       addq    $32, %rsp\n"
"       movaps  (%rsp), %xmm13\n"
"       movaps  16(%rsp), %xmm12\n"
"       movaps  32(%rsp), %xmm11\n"
"       movaps  48(%rsp), %xmm10\n"
"       movaps  64(%rsp), %xmm9\n"
"       movaps  80(%rsp), %xmm8\n"
"       movaps  96(%rsp), %xmm7\n"
"       movaps  112(%rsp), %xmm6\n"
"       addq    $128, %rsp\n"

"       popq    %rdi\n"
"       popq    %rsi\n"
#endif

        // Restore FP and MMX
"       ldmxcsr (%rsp)\n"
"       fldcw   4(%rsp)\n"
"       addq    $8, %rsp\n"

"       popq    %rbx\n"
"       popq    %r12\n"
"       popq    %r13\n"
"       popq    %r14\n"
"       popq    %r15\n"
"       popq    %rbp\n"

        // Return to caller with argument in hand
"       movq    "P3", %rax\n"
"       ret\n"
FSIZE(switch_frame)


// frame_t create_frame(void *stack_base, frame_action_t action, void *context)
// Arguments:
//   P1      base of stack to use
//   P2      action routine
//   P3      context to pass to action routine
//
// The initial frame is a saved context which will switch via action_entry to
// the given action routine.  The following fields are present in both ABIs:
//
//  -8(P1)      Second argument for action routine
//  -16         Action routine saved
//  -24         action_entry, start of saved coroutine stack frame
//  -32         ebp, saved as 0 to ensure backtraces work properly
//  -40..-72    r15..r12,rbx -- common saved registers
//  -80         mxcsr, fpcsr
//
// The following extra fields are only present on Windows:
//
//  -88..-96    rsi, rdi
//  -256..-112  xmm15..xmm6

FNAME(create_frame)
        // Save the extra arguments needed by the new frame
"       movq    "P3", -8("P1")\n"       // Context for action routine
"       movq    "P2", -16("P1")\n"      // Action routine to call
        // Push the frame expected by switch_frame, but store 0 for %rbp.  Set
        // things up to start control at action_entry
"       leaq    action_entry(%rip), %rax\n"
"       movq    %rax, -24("P1")\n"
"       movq    $0, -32("P1")\n"
"       movq    %r15, -40("P1")\n"
"       movq    %r14, -48("P1")\n"
"       movq    %r13, -56("P1")\n"
"       movq    %r12, -64("P1")\n"
"       movq    %rbx, -72("P1")\n"
        // Save floating point and MMX control registers.  For this we'd better
        // save something real, because we're saving control settings.
"       wait\n"
"       fnstcw  -76("P1")\n"
"       stmxcsr -80("P1")\n"

#ifdef WIN64
"       movq    %rsi, -88("P1")\n"
"       movq    %rdi, -96("P1")\n"
"       movaps  %xmm6, -112("P1")\n"
"       movaps  %xmm7, -128("P1")\n"
"       subq    $128, "P1"\n"
"       movaps  %xmm8, -16("P1")\n"
"       movaps  %xmm9, -32("P1")\n"
"       movaps  %xmm10, -48("P1")\n"
"       movaps  %xmm11, -64("P1")\n"
"       movaps  %xmm12, -80("P1")\n"
"       movaps  %xmm13, -96("P1")\n"
"       movaps  %xmm14, -112("P1")\n"
"       movaps  %xmm15, -128("P1")\n"
"       subq    $128, "P1"\n"
#else
"       subq    $80, "P1"\n"
#endif

        // Return the new frame pointer and we're done
"       movq    "P1", %rax\n"
"       ret\n"

"action_entry:\n"
        // We receive control here after the first switch to a newly created
        // frame.  The top of the stack is the function we're going to call, and
        // then the context it wants, our activation argument is in %rax.
        //
        // We will call the action routine with the argument in P1 and the
        // saved context in P2.
"       popq    %r8\n"                  // Action routine
"       popq    "P2"\n"                 // Context argument
"       movq    %rax, "P1"\n"
"       pushq   $0\n"                   // Returning not allowed!
"       jmp     *%r8\n"
FSIZE(create_frame)
);
