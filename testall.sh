#!/bin/sh
set -e -x

# Build and run unittests (currently only tests/cosocket.py)
# for several different interpreter versions
#
# First argument is the git revision to used, which is
# exported and built in a temp. directory.
# Remaining arguments are python interpreter executables
#
# $ ./testall.sh master python2.6 python2.7
# $ ./testall.sh python3 python3.2

BRANCH=${1:-HEAD}
shift

echo "Test $BRANCH"

for PY in "$@"
do
    echo "Test with $PY"
    BUILD="$(mktemp -d)"
    echo "temp dir $BUILD"

    trap "rm -rf $BUILD" INT HUP TERM EXIT QUIT

    git archive --prefix=src/ $BRANCH | tar -C $BUILD -xv

    # gcc 4.7 issues spurious warnings about valgrind.h macros
    #   warning: variable ‘_qzz_res’ set but not used [-Wunused-but-set-variable]
    sed -i -e '/Werror/d' $BUILD/src/setup.py

    install -d $BUILD/usr/lib/python

    export PYTHONPATH=$BUILD/usr/lib/python

    (cd $BUILD/src && $PY ./setup.py install --home $BUILD/usr)

    if $PY $BUILD/src/tests/cosocket.py
    then
        echo "Pass $PY"
    else
        echo "Fail $PY"
        exit 1
    fi

    rm -rf $BUILD
    trap "" INT HUP TERM QUIT

done

exit 0
