/* Simple coroutine test. */

#include <stdbool.h>
#include <stdio.h>

#include "coroutine.h"

#define STACK_SIZE      (1 << 16)

coroutine_t c0, c1, c2;

void * coroutine_1(void *context, void *arg)
{
    printf("coroutine_1 started: %p, %p\n", context, arg);
    for (int i = 0; i < 5; i++)
    {
        printf("switching to coroutine_2: %d, %p\n", i, arg);
        arg = switch_coroutine(c2, (void*)((int) arg + 1));
        printf("coroutine_1 in control: %d, %p\n", i, arg);
    }
    printf("coroutine_1 returning %p\n", arg);
    return arg;
}

void * coroutine_2(void *context, void *arg)
{
    printf("coroutine_2 started: %p, %p\n", context, arg);
    for (int i = 0; i < 4; i ++)
    {
        printf("switching to coroutine_1: %d, %p\n", i, arg);
        arg = switch_coroutine(c1, (void*)((int) arg + 1));
        printf("coroutine_2 in control: %d, %p\n", i, arg);
    }
    printf("coroutine_2 returning %p\n", arg);
    return arg;
}

int main(int argc, char **argv)
{
    enable_check_stack(true);
    c0 = get_current_coroutine();
    c1 = create_coroutine(c0, coroutine_1, STACK_SIZE, (void*)101);
    c2 = create_coroutine(c1, coroutine_2, STACK_SIZE, (void*)102);

    printf("About to start\n");
    void * n = switch_coroutine(c1, (void *)1);
    printf("All done: %p\n", n);
}
