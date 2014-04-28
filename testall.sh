#!/bin/bash
set -e

HERE="$(cd "$(dirname "$0")"; pwd)"

# Build and run unittests (currently only tests/cosocket.py)
# for several different interpreter versions
#
# First argument is the git revision to used, which is
# exported and built in a temp. directory.
# Remaining arguments are python interpreter executables
#
# $ ./testall.sh master python2.6 python2.7
# $ ./testall.sh python3 python3.2

# Default revision to HEAD
if [[ $# > 0 ]]; then
    BRANCH="$1"
    shift
else
    BRANCH=HEAD
fi

# If no interpreter names given use python by default
if [[ $# > 0 ]]; then
    PYTHONS=("$@")
else
    PYTHONS=(python)
fi


TESTS=(cosocket)


echo "Testing $BRANCH"

for PYTHON in "${PYTHONS[@]}"; do
    echo "Testing with $PYTHON"
    BUILD="$(mktemp -d)"
    echo "temp dir $BUILD"

    trap "rm -rf $BUILD" EXIT

    cd "$HERE"
    git archive --prefix=src/ $BRANCH | tar -C $BUILD -x

    install -d $BUILD/usr/lib/python
    export PYTHONPATH=$BUILD/usr/lib/python

    cd $BUILD/src
    $PYTHON ./setup.py install --home $BUILD/usr

    for test in "${TESTS[@]}"; do
        if $PYTHON $BUILD/src/tests/$test.py; then
            echo "Pass $PYTHON $test"
        else
            echo "Fail $PYTHON $test"
            exit 1
        fi
    done

    rm -rf $BUILD
    trap '' EXIT
done

exit 0
