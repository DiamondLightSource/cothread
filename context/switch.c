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

#if defined(__APPLE__)  ||  defined(WIN32)  ||  defined(WIN64)
    #define FNAME(name) \
        ".globl _" #name "\n_" #name ":\n"
    #define FSIZE(name)
#else
    #define FNAME(name) \
        ".globl " #name "\n" \
        ".type " #name ", STT_FUNC\n" \
        #name ":\n"
    #define FSIZE(name) \
        ".size " #name ", .-" #name "\n"
#endif

#if defined(__i386__)
    #include "switch-x86.c"
#elif defined(__x86_64__)
    #include "switch-x86_64.c"
#elif defined(__aarch64__)  &&  defined(__unix__)
    #include "switch-arm64.c"
#elif defined(__arm__)  &&  defined(__unix__)
    #include "switch-arm.c"
#elif defined(__ppc__)  &&  defined(__APPLE__)
    #include "switch-ppc_osx.c"
#else
    #error "Don't know how to support this platform"
#endif
