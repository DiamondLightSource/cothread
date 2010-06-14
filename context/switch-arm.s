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


# void create_frame(
#     frame_t *frame, void *stack_base, frame_action_t action, void *context)
        .global create_frame
        .type   create_frame, %function

# Arguments on entry:
#   r0      address of frame to be written
#   r1      initial base of stack
#   r2      action routine
#   r3      context argument to action
create_frame:
        stmfd   r1!, {r2, r3}           /* Save arguments for new coroutine */
        mov     ip, lr                  /* Save LR so can use same STM slot */
        ldr     lr, =action_entry
        stmfd   r1!, {r4, r5, r6, r7, r8, r9, sl, fp, lr}
        str     r1, [r0]
        bx      ip

action_entry:
        # Receive control after first switch to new frame.  Top of stack has the
        # saved context and routine to call, switch argument is in r0.
        ldmfd   sp!, {r2, r3}   /* r2 <- action routine, r3 <- context */
        mov     r1, r3
        bx      r2
        .size   create_frame, .-create_frame
