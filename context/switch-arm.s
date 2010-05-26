# Coroutine frame switching for ARM

# void * switch_frame(frame_t *old_frame, frame_t *new_frame, void *arg)
.globl  switch_frame
        .type   switch_frame, @function
switch_frame:
        stmfd   sp!, {r4, r5, r6, r7, r8, r9, sl, fp, lr}
        str     sp, [r0]
        mov     sp, r1
        mov     r0, r3
        ldmfd   sp!, {r4, r5, r6, r7, r8, r9, sl, fp, pc}
        .size   switch_frame, .-switch_frame

# void create_frame(
#     frame_t *frame, void *stack, size_t stack_size,
#     frame_action_t action, void *context)
.globl  create_frame
        .type   create_frame, @function
create_frame:

