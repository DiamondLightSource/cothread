# Coroutine frame switching for ARM

        .text
        .align  2

# void * switch_frame(frame_t *old_frame, frame_t *new_frame, void *arg)
        .global switch_frame
        .type   switch_frame, %function

# Arugments on entry:
#   r0      address of frame to be saved
#   r1      address of frame to be loaded
#   r2      Context argument to pass through
switch_frame:
        stmfd   sp!, {r4, r5, r6, r7, r8, r9, sl, fp, lr}
        str     sp, [r0]
        ldr     sp, [r1]
        mov     r0, r2
        ldmfd   sp!, {r4, r5, r6, r7, r8, r9, sl, fp, pc}
        .size   switch_frame, .-switch_frame


# void create_frame(
#     frame_t *frame, void *stack, size_t stack_size,
#     frame_action_t action, void *context)
        .global create_frame
        .type   create_frame, %function

# Arguments on entry:
#   r0      address of frame to be written
#   r1      initial base of stack
#   r2      length of stack (needs to be added to stack)
#   r3      action routine
#   [sp]    context argument to action
create_frame:
        add     r1, r1, r2      /* Compute base of downward growing stack */

        ldr     r2, [sp]        /* Save arguments needed for action routine */
        stmfd   r1!, {r2, r3}   /* Want action routine in later register */
        mov     ip, lr          /* Save LR so can use same STM slot */
        ldr     lr, _action_entry
        stmfd   r1!, {r4, r5, r6, r7, r8, r9, sl, fp, lr}
        str     r1, [r0]

        bx      ip

_action_entry:
        .word   action_entry
action_entry:
        # Receive control after first switch to new frame.  Top of stack has the
        # saved context and routine to call, switch argument is in r0.
        ldmfd   sp!, {r1, r2}   /* r1 <- context, r2 <- action routine */
        bx      r2
