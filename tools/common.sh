#!/bin/bash
# Copyright 2019 Google Inc.
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


# Scripts in the tools/ directory should source this file with the line:
# pushd "$(dirname $0)" >/dev/null && source common.sh && popd >/dev/null

export TOOLS_DIR=$(pwd)
export PROJECT_DIR=$(dirname $TOOLS_DIR)
export APP_DIR=$PROJECT_DIR/app
export TESTS_DIR=$PROJECT_DIR/tests

# Look for non-standalone SDK inside google-cloud-sdk.
# Then look for a standalone one (deprecated).
for dir in \
    "$APPENGINE_DIR" \
    $HOME/opt/google-cloud-sdk/platform/google_appengine \
    $HOME/google-cloud-sdk/platform/google_appengine; do
    if [ -d "$dir" ]; then
        export APPENGINE_DIR="$dir"
        break
    fi
done

if [ -z "$APPENGINE_DIR" ]; then
    echo "Could not find google_appengine directory.  Please set APPENGINE_DIR."
    echo "Standalone SDK is deprecated. Please update to Google Cloud SDK"
    exit 1
fi

for python in \
    "$PYTHON" \
    $(which python2.7) \
    /usr/local/bin/python2.7 \
    /usr/bin/python2.7 \
    /Library/Frameworks/Python.framework/Versions/2.7/bin/python; do
    if [ -x "$python" ]; then
        export PYTHON="$python"
        break
    fi
done

for python3 in \
    "$PYTHON3" \
    $(which python3.7) \
    /usr/local/bin/python3.7 \
    /usr/bin/python3.7 \
    /Library/Frameworks/Python.framework/Versions/3.7/bin/python; do
    if [ -x "$python3" ]; then
        export PYTHON3="$python3"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    DEFAULT_PYTHON=$(which python)
    if [[ "$($DEFAULT_PYTHON -V 2>&1)" =~ "Python 2.7" ]]; then
        export PYTHON="$DEFAULT_PYTHON"
    fi
fi

if [ -z "$PYTHON" ]; then
    echo "Could not find python2.7 executable.  Please set PYTHON."
    exit 1
fi

export PYTHONPATH=\
"$APP_DIR":\
"$APP_DIR/vendors":\
"$TESTS_DIR":\
"$TOOLS_DIR":\
"$APPENGINE_DIR":\
"$APPENGINE_DIR/lib/django-1.11":\
"$APPENGINE_DIR/lib/fancy_urllib":\
"$APPENGINE_DIR/lib/webapp2-2.5.2":\
"$APPENGINE_DIR/lib/webob-1.2.3":\
"$APPENGINE_DIR/lib/yaml-3.10"

export APPENGINE_RUNTIME=python27

if [ -z "$USER_EMAIL" ]; then
    export USER_EMAIL=$(whoami)@google.com
fi
