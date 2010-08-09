#!/bin/bash
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

export SCRIPTS_DIR=$(pwd)
export PROJECT_DIR=$(dirname $SCRIPTS_DIR)
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
    fi
done

for python in \
    $(which python2.5) \
    /usr/local/bin/python2.5 \
    /usr/bin/python2.5 \
    /Library/Frameworks/Python.framework/Versions/2.5/bin/python; do
    if [ -x "$python" ]; then
        export PYTHON="$python"
    fi
done

if [ -z "$PYTHON" ]; then
    DEFAULT_PYTHON="$(which python)"
    if [[ "$($DEFAULT_PYTHON -V 2>&1)" =~ "Python 2.5" ]]; then
        export PYTHON="$DEFAULT_PYTHON"
    fi
fi

if [ -z "$PYTHON" ]; then
    echo "Could not find python2.5 executable.  Set PYTHON."
    exit 1
fi

export PYTHONPATH=\
"$APP_DIR":\
"$TESTS_DIR":\
"$SCRIPTS_DIR":\
"$SELENIUM_PYTHON_DIR":\
"$APPENGINE_DIR":\
"$APPENGINE_DIR/lib/django":\
"$APPENGINE_DIR/lib/webob":\
"$APPENGINE_DIR/lib/yaml/lib"

cd $(dirname $0)
$PYTHON unit_tests.py
$PYTHON server_tests.py
