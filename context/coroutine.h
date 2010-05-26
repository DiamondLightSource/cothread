/* Simple coroutine library. */

typedef struct coroutine *coroutine_t;
typedef void * (*coroutine_action)(void *context, void *argument);

coroutine_t get_current_coroutine(void);
coroutine_t create_coroutine(
    coroutine_t parent, coroutine_action action, size_t stack_size,
    void *context);
void delete_coroutine(coroutine_t coroutine);
void * switch_coroutine(coroutine_t coroutine, void *parameter);
