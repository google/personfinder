#!/bin/bash
# Modified from Google Person Finder:
# http://code.google.com/p/googlepersonfinder/

# Scripts in the tools/ directory should source this file with the line:
# pushd "$(dirname $0)" >/dev/null && source common.sh && popd >/dev/null

export TOOLS_DIR=$(pwd)
export PROJECT_DIR=$(dirname $TOOLS_DIR)
export APP_DIR=$PROJECT_DIR/app
export TESTS_DIR=$PROJECT_DIR/tests

for dir in \
    "$APPENGINE_DIR" \
    /usr/lib/google_appengine \
    /usr/local/lib/google_appengine \
    /usr/local/google_appengine \
    $HOME/google_appengine; do
    if [ -d "$dir" ]; then
        export APPENGINE_DIR="$dir"
        break
    fi
done

if [ -z "$APPENGINE_DIR" ]; then
    echo "Could not find google_appengine directory.  Please set APPENGINE_DIR."
    exit 1
fi

for python in \
    "$PYTHON" \
    $(which python) \
    /usr/local/bin/python \
    /usr/bin/python; do
    if [ -x "$python" ]; then
        export PYTHON="$python"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Could not find python executable.  Please set PYTHON."
    exit 1
fi

export PYTHONPATH=\
"$APP_DIR":\
"$TESTS_DIR":\
"$TOOLS_DIR":\
"$APPENGINE_DIR":\
"$APPENGINE_DIR/lib/fancy_urllib":\
"$APPENGINE_DIR/lib/webob":\
"$APPENGINE_DIR/lib/yaml/lib"
