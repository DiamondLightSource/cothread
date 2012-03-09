/* This file is part of the Diamond cothread library.
 *
 * Copyright (C) 2011-2012 Michael Abbott, Diamond Light Source Ltd.
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

#define DECLARE_TLS(type, var)  static pthread_key_t var##__key
#define INIT_TLS(var)           pthread_key_create(&var##__key, NULL)
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
    __mingw_aligned_malloc((size), alignment)
#define FREE_ALIGNED(mem)   __mingw_aligned_free(mem)

#elif defined(WIN64)
/* This is what we have to use on 64-bit Windows. */
#define MALLOC_ALIGNED(alignment, size) \
    _aligned_malloc((size), alignment)
#define FREE_ALIGNED(mem)   _aligned_free(mem)

#else
/* Proper posix system. */
#define MALLOC_ALIGNED(alignment, size) memalign(alignment, (size))
#define FREE_ALIGNED(mem)               free(mem)
#endif


/* Windows vs Posix issues.  Let's try and gather these differences in a single
 * place as they arise.  Some useful references:
 *
 *  http://msdn.microsoft.com/en-us/library/aa366898%28v=vs.85%29.aspx
 *      MSDN reference for VirtualProtect()
 *
 *  http://coding.derkeiler.com/Archive/Assembler/
 *  comp.lang.asm.x86/2005-05/msg00280.html
 *      An example of memory protection and exception handling.
 *
 *  http://www.genesys-e.org/jwalter/mix4win.htm
 *      References critical sections for mutual exclusion and system info
 *      interrogation functions. */

#if defined(WIN32)

#define getpagesize() \
    ( { \
        SYSTEM_INFO system_info; \
        GetSystemInfo(&system_info); \
        system_info.dwPageSize; \
    } )

#define mprotect(addr, size, prot) \
    ( { \
        DWORD old_protect; \
        VirtualProtect(addr, size, prot, &old_protect); \
    } )

#define PROT_NONE       PAGE_NOACCESS
#define PROT_READWRITE  PAGE_READWRITE

#else
/* Standard posix stuff.  Mostly we'll try and make Windows look like Posix, but
 * if we fail stuff needs to go here. */

#define PROT_READWRITE  (PROT_READ | PROT_WRITE)

#endif


/* For size_t print specifiers mostly we can use "z", but not on Windows. */
#if defined(WIN32)
#define PRIz        ""
#else
#define PRIz        "z"
#endif
