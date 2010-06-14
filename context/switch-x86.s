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


# void create_frame(
#     frame_t *frame, void *stack, size_t stack_size,
#     frame_action_t action, void *context)
.globl  create_frame
        .type   create_frame, @function

# On entry have following arguments on stack:
#   4(%esp)     address of frame to be created
#   8(%esp)     base of stack to use
#   12(%esp)    length of stack to use
#   16(%esp)    action routine
#   20(%esp)    context to pass to action routine
create_frame:
        # Compute the new stack frame.  On this architecture the stack frame
        # grows downwards, so we add the stack length.
        movl    8(%esp), %ecx       # Base of stack
        addl    12(%esp), %ecx      # Compute active base of stack

        # Save the context needed by the action routine and prepare the switch
        # context.
        movl    20(%esp), %eax
        movl    %eax, -4(%ecx)      # Context for action
        movl    16(%esp), %eax
        movl    %eax, -8(%ecx)      # Action routine to call
        # Push variables expected by switch_frame restore, but push 0 for %ebp
        # to mark base of stack frame list.
        movl    $action_entry, -12(%ecx)  # Where switch_frame will switch to
        movl    $0, -16(%ecx)
        movl    %ebx, -20(%ecx)
        movl    %edi, -24(%ecx)
        movl    %esi, -28(%ecx)

        # Save new stack frame and we're all done.
        movl    4(%esp), %edx       # Frame address
        subl    $28, %ecx
        movl    %ecx, (%edx)
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
