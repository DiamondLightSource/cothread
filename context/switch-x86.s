# Coroutine frame switching for 32-bit x86
#
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


# void * switch_frame(frame_t *old_frame, frame_t *new_frame, void *arg)
.globl  switch_frame
        .type   switch_frame, @function
switch_frame:
        # Standard frame entry.  Don't need any extra registers for this one.
        pushl   %ebp
        movl    %esp, %ebp
        # Pick up the arguments
        movl    12(%ebp), %eax      # new_frame
        movl    8(%ebp), %ecx       # %ecx = old_frame
        movl    (%eax), %edx        # %edx = *new_frame
        movl    16(%ebp), %eax      # %eax = arg = result register

        # Save registers ABI requires to be preserved.
        pushl   %ebx
        pushl   %edi
        pushl   %esi

        # Switch stack frames.
        movl    %esp, (%ecx)
        movl    %edx, %esp

        # Restore previously saved registers.
        popl    %esi
        popl    %edi
        popl    %ebx

        # Done
        popl    %ebp
        ret
        .size   switch_frame, .-switch_frame


# void create_frame(
#     frame_t *frame, void *stack, size_t stack_size,
#     frame_action_t action, void *context)
.globl  create_frame
        .type   create_frame, @function

# After standard entry have following arguments on frame:
#   8(%ebp)     address of frame to be created
#   12(%ebp)    base of stack to use
#   16(%ebp)    length of stack to use
#   20(%ebp)    action routine
#   24(%ebp)    context to pass to action routine
create_frame:
        # Standard entry with some extra register saves.  We need all the
        # arguments in registers because we're going to switch stack frames
        # while we prepare the new frame.
        pushl   %ebp
        movl    %esp, %ebp

        # Compute the new stack frame.  On this architecture the stack frame
        # grows downwards, so we add the stack length.
        movl    12(%ebp), %ecx      # Base of stack
        movl    8(%ebp), %edx       # Pick up frame address in background
        addl    16(%ebp), %ecx      # Compute active base of stack
        # Switch to new frame, saving original frame in %eax
        movl    %esp, %eax
        movl    %ecx, %esp

        # Save the context needed by the action routine and prepare the switch
        # context.
        pushl   24(%ebp)            # Context for action
        pushl   20(%ebp)            # Action routine to call
        # Push variables expected by switch_frame restore, but push 0 for %ebp
        # to mark base of stack frame list.
        pushl   $action_entry       # Where switch_frame will switch to
        pushl   $0
        pushl   %ebx
        pushl   %edi
        pushl   %esi

        # Save new stack frame, switch back to original, then we're all done.
        movl    %esp, (%edx)
        movl    %eax, %esp
        popl    %ebp
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

.globl  current_frame
        .type   current_frame, @function
        # Nothing needs to be done for current
current_frame:
        ret
        .size   current_frame, .-current_frame
