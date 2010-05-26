/* Simple coroutine library. */

typedef struct coroutine *coroutine_t;
typedef void * (*coroutine_action_t)(void *context, void *argument);

coroutine_t get_current_coroutine(void);
coroutine_t create_coroutine(
    coroutine_t parent, coroutine_action_t action, size_t stack_size,
    void *context);
void * switch_coroutine(coroutine_t coroutine, void *parameter);
void enable_check_stack(bool enable_check);
