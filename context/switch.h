/* Interface for stack switching. */

/* A saved stack frame is completely defined by a pointer to the top of the
 * stack frame. */
typedef void *frame_t;

/* The action performed by in a new frame takes two arguments: the context
 * argument passed to create_frame() when this frame was first established and
 * the argument passed in the first activating switch_frame() call.
 *
 * This routine must never return. */
typedef __attribute__((noreturn))
    void (*frame_action_t)(void *arg, void *context);

/* Switch to new frame, previously established by create_frame() or an earlier
 * switch_frame().  The caller's stack frame is written to *old_frame. */
void * switch_frame(frame_t *old_frame, frame_t new_frame, void *arg);

/* Retrieves the current frame.  Note that the returned result will be invalid
 * as soon as control is returned, so this is only useful for retrieving an
 * indication of the current high water mark in the stack. */
frame_t get_frame(void);

/* Establish a new frame in the given stack.  action(arg, context) will be
 * called when the newly created frame is switched to, and it must never return.
 *
 * The initial frame can safely be relocated and started at a different
 * location.  FRAME_START(stack_base, *frame) points to the start of the created
 * frame and FRAME_LENGTH(stack_base, *frame) computes its length, which is
 * guaranteed to be no more than INITIAL_FRAME_SIZE. */
void create_frame(
    frame_t *frame, void *stack_base, frame_action_t action, void *context);

/* This is a safe upper bound on the storage required by create_frame(), a newly
 * created frame is guaranteed to fit into this many bytes. */
#define INITIAL_FRAME_SIZE      128


/* Abstractions of stack direction dependent constructions.
 *
 *  STACK_BASE(stack_start, length)
 *      Returns the base of an area of stack allocated with the given start
 *      address and length.  Conversely, STACK_BASE(stack_base, -length) returns
 *      the original allocation base.
 *
 *  FRAME_START(stack_base, frame_ptr)
 *      Returns lowest address of the complete frame bounded by stack_base and
 *      the saved frame pointer.
 *
 *  FRAME_LENGTH(stack_base, frame_ptr)
 *      Returns the length of the frame bounded by stack base and frame pointer.
 *
 *  STACK_INDEX(stack_base, index)
 *      Returns a char* pointer to the indexed character in the stack, with
 *      index 0 addressing the first pushed byte.
 */
#ifdef STACK_GROWS_DOWNWARD
#define STACK_BASE(stack_start, length)     ((stack_start) + (length))
#define FRAME_START(stack_base, frame)      (frame)
#define FRAME_LENGTH(stack_base, frame)     ((stack_base) - (frame))
#define STACK_INDEX(stack_base, index) \
    (&((unsigned char *)(stack_base))[-(index)-1])
#else
#define STACK_BASE(stack_start, length)     (stack_start)
#define FRAME_START(stack_base, frame)      (stack_base)
#define FRAME_LENGTH(stack_base, frame)     ((frame) - (stack_base))
#define STACK_INDEX(stack_base, index) \
    (&((unsigned char *)(stack_base))[(index)])
#endif
