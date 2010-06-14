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

#include "coroutine.h"

#define STACK_SIZE      (1 << 16)

coroutine_t c0, c1, c2;

void * coroutine_1(void *context, void *arg)
{
    printf("coroutine_1 started: %p, %p\n", context, arg);
    for (int i = 0; i < 5; i++)
    {
        printf("switching to coroutine_2: %d, %p\n", i, arg);
        arg = switch_coroutine(c2, (void*)((long) arg + 1));
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
        arg = switch_coroutine(c1, (void*)((long) arg + 1));
        printf("coroutine_2 in control: %d, %p\n", i, arg);
    }
    printf("coroutine_2 returning %p\n", arg);
    return arg;
}

int main(int argc, char **argv)
{
    c0 = get_current_coroutine();
    c1 = create_coroutine(c0, coroutine_1, (void*)101, NULL, STACK_SIZE, true);
    c2 = create_coroutine(c1, coroutine_2, (void*)102, NULL, STACK_SIZE, true);

    printf("About to start\n");
    void * n = switch_coroutine(c1, (void *)1);
    printf("All done: %p\n", n);
}
