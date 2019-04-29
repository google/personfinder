#!/usr/bin/python2.7
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

"""Runs the unit tests, with stubs for the datastore API.

Instead of running this script directly, use the 'unit_tests' shell script,
which sets up the PYTHONPATH and other necessary environment variables."""

import argparse
import os
import pytest
import six
import sys

# The test files that should be run by default when we're running Python 3.
PY3_TEST_FILES = [
    'test_jautils.py',
    'test_text_query.py',
]

# These dependencies don't support Python 3. Also, they're only used for tests
# involving App Engine APIs, which we won't be running with Python 3. So, only
# import them when we're running Python 2.
if six.PY2:
    from google.appengine.api import apiproxy_stub_map
    from google.appengine.api import datastore_file_stub

    # Create a new apiproxy and temp datastore to use for this test suite
    apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
    temp_db = datastore_file_stub.DatastoreFileStub(
        'x', None, None, trusted=True)
    apiproxy_stub_map.apiproxy.RegisterStub('datastore', temp_db)

# An application id is required to access the datastore, so let's create one
os.environ['APPLICATION_ID'] = 'personfinder-unittest'
# We set this to something beginning with "Development" to use development
# settings. Also, the requests library wants this to be set for some reason (it
# doesn't care what the value is, it just wants there to be one).
os.environ['SERVER_SOFTWARE'] = 'Development-testing'

# When the appserver is running, the APP_DIR should be the current directory...
os.chdir(os.environ['APP_DIR'])

if six.PY2:
    default_test_files = [os.environ['TESTS_DIR']]
else:
    default_test_files = [
        os.path.join(os.environ['TESTS_DIR'], test_file)
        for test_file in PY3_TEST_FILES
    ]

# ...but we want pytest to default to finding tests in TESTS_DIR, not the cwd.
# So, when no arguments are given, we use TESTS_DIR by default for the test
# files we pass to pytest.
parser = argparse.ArgumentParser()
parser.add_argument('--tb')
parser.add_argument('--pyargs', action='store_true')
parser.add_argument('-q', action='store_true')
parser.add_argument('-k', type=str,
                    help='Keyword expressions to pass to pytest.')
parser.add_argument('test_files', nargs='*', default=default_test_files)
args = parser.parse_args()
pytest_args = []
if args.tb:
  pytest_args += ['--tb', args.tb]
if args.pyargs:
  pytest_args.append('--pyargs')
if args.q:
  pytest_args.append('-q')
if args.k:
  pytest_args += ['-k', args.k]
pytest_args += args.test_files

# Run the tests, using sys.exit to set exit status (nonzero for failure).
sys.exit(pytest.main(pytest_args))
