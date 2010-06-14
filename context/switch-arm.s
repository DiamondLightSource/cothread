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
