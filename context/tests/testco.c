/* This file is part of the Diamond cothread library.
 *
 * Copyright (C) 2010 Michael Abbott, Diamond Light Source Ltd.
 *
 * The Diamond cothread library is free software; you can redistribute it
 * and/or modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the License,
 * or (at your option) any later version.
 *
 * The Diamond cothread library is distributed in the hope that it will be
 * useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
 * Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc., 51
 * Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
 *
 * Contact:
 *      Dr. Michael Abbott,
 *      Diamond Light Source Ltd,
 *      Diamond House,
 *      Chilton,
 *      Didcot,
 *      Oxfordshire,
 *      OX11 0DE
 *      michael.abbott@diamond.ac.uk
 */

/* Simple coroutine test. */

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cocore.h"

#define STACK_SIZE      (1 << 16)

struct context { int x; };

struct cocore *c0, *c1, *c2;

#define N   2

void *coroutine_1(void *_context, void *arg)
{
    struct context *context = _context;
    printf("coroutine_1 started: %p (%d), %p\n", context, context->x, arg);
    for (int i = 0; i < N + 1; i++)
    {
        char x[4096];
        memset(x, 0x55, sizeof(x));
        printf("switching to coroutine_2: %d, %p\n", i, arg);
        arg = switch_cocore(c2, (void*)((long) arg + 1));
        printf("coroutine_1 in control: %d, %p\n", i, arg);
    }
    printf("coroutine_1 returning %p\n", arg);
    return arg;
}

void *coroutine_2(void *_context, void *arg)
{
    struct context *context = _context;
    printf("coroutine_2 started: %p (%d), %p\n", context, context->x, arg);
    for (int i = 0; i < N; i ++)
    {
        char x[4096];
        memset(x, 0, sizeof(x));
        printf("switching to master: %d, %p\n", i, arg);
        arg = switch_cocore(c0, (void*)((long) arg + 1));
        printf("coroutine_2 in control: %d, %p\n", i, arg);
    }
    printf("coroutine_2 returning %p\n", arg);
    return arg;
}

int main(int argc, char **argv)
{
    initialise_cocore();
    c0 = initialise_cocore_thread();
    c1 = create_cocore(c0, coroutine_1,
       &(struct context) { .x = 101 }, sizeof(struct context),
       NULL, STACK_SIZE, true, 4);
    c2 = create_cocore(c1, coroutine_2,
       &(struct context) { .x = 102 }, sizeof(struct context),
       c0, STACK_SIZE, true, 4);

    printf("About to start: %p, %p, %p\n", c0, c1, c2);
    void *arg = (void *) 1;
    for (int i = 0; i < N + 1; i ++)
    {
        printf("switching to coroutine_1: %d, %p\n", i, arg);
        arg = switch_cocore(c1, (void *) ((long) arg + 1));
        printf("master in control: %d, %p\n", i, arg);
    }
    printf("All done: %p\n", arg);
}
