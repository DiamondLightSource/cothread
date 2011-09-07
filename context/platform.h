/* This file is part of the Diamond cothread library.
 *
 * Copyright (C) 2011 Michael Abbott, Diamond Light Source Ltd.
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

/* Attempting to gather all the peculiar cross-platform dependencies into one
 * place. */


/* Some cross-platform support for thread support.  If we can't use __thread
 * we'll use the posix pthread_{get,set}specific API instead. */

#if defined(__APPLE__)
/* No __thread support on this platform, instead we use Posix pthread keys. */

#include <pthread.h>

#define DECLARE_TLS(type, var) \
    static pthread_key_t var##__key; \
    static pthread_once_t var##__once = PTHREAD_ONCE_INIT; \
    static void var##__init(void) { pthread_key_create(&var##__key, NULL); }
#define INIT_TLS(var)           pthread_once(&var##__once, var##__init)
#define GET_TLS(var)            pthread_getspecific(var##__key)
#define SET_TLS(var, value)     pthread_setspecific(var##__key, value)

#else
/* Assume __thread support.  Makes life a *lot* simpler. */

#define DECLARE_TLS(type, var)  static __thread type var##__thread
#define INIT_TLS(var)           do {} while(0)
#define GET_TLS(var)            var##__thread
#define SET_TLS(var, value)     var##__thread = (value)

#endif


/* Allocating stack aligned memory.  Again this is very platform dependent. */

#if defined(__APPLE__)
/* On OSX there is no memalign, and valloc is mostly what we want anyway. */
#define MALLOC_ALIGNED(alignment, size) valloc(size)
#define FREE_ALIGNED(mem)               free(mem)

#elif defined(WIN32)
/* This is what we have to use on 32-bit Windows. */
#define MALLOC_ALIGNED(alignment, size) \
    __mingw_aligned_malloc((size), STACK_ALIGNMENT)
#define FREE_ALIGNED(mem)   __mingw_aligned_free(mem)

#elif defined(WIN64)
/* This is what we have to use on 64-bit Windows. */
#define MALLOC_ALIGNED(alignment, size) \
    _aligned_malloc((size), STACK_ALIGNMENT)
#define FREE_ALIGNED(mem)   _aligned_free(mem)

#else
/* Proper posix system. */
#define MALLOC_ALIGNED(alignment, size) memalign(alignment, (size))
#define FREE_ALIGNED(mem)               free(mem)
#endif


/* For size_t print specifiers mostly we can use "z", but not on Windows. */
#if defined(WIN32)
#define PRIz        ""
#else
#define PRIz        "z"
#endif
