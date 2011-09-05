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

/* Some cross-platform support for thread support.  If we can't use __thread
 * we'll use the posix pthread_{get,set}specific API instead. */

#if defined(__APPLE__)
/* No __thread support on this platform. */

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
