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

/* Coroutine frame switching for 32-bit Power PC on OSX
 *
 * See ABI documentation at
 *  http://developer.apple.com/library/mac/documentation/DeveloperTools/
 *  Conceptual/LowLevelABI/100-32-bit_PowerPC_Function_Calling_Conventions/
 *  32bitPowerPC.html
 *
 * and "System V Application Binary Interface, PowerPC Processor Supplement",
 *  Steve Zucker (SunSoft), Kari Karhi (IBM), Sep 1995.  802-3334-10,
 *  http://refspecs.freestandards.org/elf/elfspec_ppc.pdf
 *
 * Registers and their roles:
 *  r0      Scratch
 *  r1      Stack pointer
 *  r2      System reserved register on AIX, volatile on Darwin
 *  r3,r4   Parameter passing and return result
 *  r5-r10  Parameter passing
 *  r11,r12 Scratch (r11 is parent frame for nested functions)
 *  r13     Small data area pointer
 *  r14-r30 Local variables
 *  r31     ? local variable or environment pointer ?
 *  f0      Scratch
 *  f1      Argument and return result
 *  f2-f8   Argument passing
 *  f9-f13  Scratch
 *  f14-f31 Local variables
 * Plus: cr0 to cr7, lr, ctr, xer, fpscr.
 *
 * Note: The Apple documentation also mentions vector registers v20-v31 which
 * also apparently need to be saved.  Not done in this code.
 *
 * The stack (r1) is always 16-byte aligned.
 *
 * Unfortunately the state that needs to be preserved is rather large:
 *  r13-r31, f14-f31, cr2-cr4
 *
 * Arguments are passed in r3 to r10, in ascending sequence
 * An integer result is returned in r3
 *
 * The functions saveFP and restFP are also part of the OSX Darwin API.  The
 * best documentation for these functions seems to be here:
 *  http://gcc.gnu.org/ml/gcc/2004-03/msg01219.html
 *  http://gcc.gnu.org/ml/gcc/2004-03/msg01219/darwin-fpsave.asm
 *
 * saveFP
 *  Saves r0 to 8(r1) and saves f14-f31 to -144(r1), returns with blr
 * restFP
 *  Restores f14-f31 from -144(r1) and returns to address saved at 8(r1)
 *
 * Other useful references:
 *  http://pds.twi.tudelft.nl/vakken/in1200/labcourse/instruction-set/
 *      Lists the core PowerPC instructions
 *  http://class.ee.iastate.edu/cpre211/labs/quickrefPPC.html
 *      Quick reference list of instructions
 */

__asm__(
"       .text\n"
"       .align  2\n"

// void * switch_frame(frame_t *old_frame, frame_t new_frame, void *arg)
// Arguments on entry:
//   r3      address of frame to be saved
//   r4      frame to be loaded
//   r5      Context argument to pass through
FNAME(switch_frame)
        /* The Power PC stack usage convention is a little odd.  On entry
         * locations 4(r1) and 8(r1) are available for saving cr and lr
         * respectively, and we have a 224 byte "red zone" below r1 reserved for
         * other register saves. */
"       mr      r11,r1\n"
"       mflr    r0\n"
"       bl      saveRegs\n"

        /* The coroutine library doesn't know about the red zone and makes
         * assumptions about stack frame storage, so we need to do some
         * compensating here. */
"       subi    r11,r11,220\n"
"       stw     r11,0(r3)\n"
"       addi    r1,r4,220\n"

"       mr      r3,r5\n"
"       b       restRegs\n"
FSIZE(switch_frame)


// frame_t create_frame(void *stack_base, frame_action_t action, void *context)
// Arguments on entry:
//   r3      initial base of stack
//   r4      action routine
//   r5      context argument to action
FNAME(create_frame)
        /* Compute initial stack frame by allocating 32 bytes and using the red
         * zone for register saves. */
"       subi    r11,r3,32\n"        /* 32 bytes for stack frame. */
"       stw     r4,24(r11)\n"       /* Place action_entry args. */
"       stw     r5,28(r11)\n"

        /* All this dance is required to load action_entry into a register using
         * position independent code: only branches can generate PC relative
         * addresses! */
"       mflr    r4\n"
"       bl      here\n"
"here:  mflr    r2\n"
"       addi    r2,r2,lo16(action_entry-here)\n"
"       addis   r0,r2,ha16(action_entry-here)\n"    // am sure don't need this

"       bl      saveRegs\n"
"       subi    r3,r11,220\n"       /* Allow for red zone in new frame. */
"       mtlr    r4\n"
"       blr\n"

"action_entry:\n"
        /* Enter here with action routine at 24(r1), context argument at 28(r1),
         * and the transfer value in r3.  Can recycle the stack we have. */
"       lwz     r0,24(r1)\n"
"       lwz     r4,28(r1)\n"
"       sub     r2,r2,r2\n"
"       mtlr    r2\n"               /* Ensure callee cannot return. */
"       mtctr   r0\n"               /* Fake bl to r0. */
"       bctr\n"
FSIZE(create_frame)


/* Saves all registers in their standard locations taking advantage of the 220
 * byte reserved "red zone" above the calling stack.   Call with r11 pointing at
 * the desired stack frame (so can be reused in _create_frame) and with the
 * caller's lr (to be saved) in r0. */
"saveRegs:\n"
"       mfcr    r2\n"
"       stmw    r13,-220(r11)\n"
"       stfd    f14,-144(r11)\n"
"       stfd    f15,-136(r11)\n"
"       stfd    f16,-128(r11)\n"
"       stfd    f17,-120(r11)\n"
"       stfd    f18,-112(r11)\n"
"       stfd    f19,-104(r11)\n"
"       stfd    f20,-96(r11)\n"
"       stfd    f21,-88(r11)\n"
"       stfd    f22,-80(r11)\n"
"       stfd    f23,-72(r11)\n"
"       stfd    f24,-64(r11)\n"
"       stfd    f25,-56(r11)\n"
"       stfd    f26,-48(r11)\n"
"       stfd    f27,-40(r11)\n"
"       stfd    f28,-32(r11)\n"
"       stfd    f29,-24(r11)\n"
"       stfd    f30,-16(r11)\n"
"       stfd    f31,-8(r11)\n"
"       stw     r2,4(r11)\n"
"       stw     r0,8(r11)\n"
"       blr\n"

"restRegs:\n"
"       lwz     r2,4(r1)\n"
"       lwz     r0,8(r1)\n"
"       lmw     r13,-220(r1)\n"
"       lfd     f14,-144(r1)\n"
"       lfd     f15,-136(r1)\n"
"       lfd     f16,-128(r1)\n"
"       lfd     f17,-120(r1)\n"
"       lfd     f18,-112(r1)\n"
"       lfd     f19,-104(r1)\n"
"       lfd     f20,-96(r1)\n"
"       lfd     f21,-88(r1)\n"
"       lfd     f22,-80(r1)\n"
"       lfd     f23,-72(r1)\n"
"       lfd     f24,-64(r1)\n"
"       lfd     f25,-56(r1)\n"
"       lfd     f26,-48(r1)\n"
"       lfd     f27,-40(r1)\n"
"       lfd     f28,-32(r1)\n"
"       lfd     f29,-24(r1)\n"
"       lfd     f30,-16(r1)\n"
"       lfd     f31,-8(r1)\n"
"       mtcr    r2\n"
"       mtlr    r0\n"
"       blr\n"
);
