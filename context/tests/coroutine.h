/* Simple coroutine library. */

typedef struct coroutine *coroutine_t;
typedef void * (*coroutine_action_t)(void *context, void *argument);

coroutine_t get_current_coroutine(void);
coroutine_t create_coroutine(
    coroutine_t parent, coroutine_action_t action, void *context,
    coroutine_t shared_stack, size_t stack_size, bool check_stack);
void * switch_coroutine(coroutine_t coroutine, void *parameter);
