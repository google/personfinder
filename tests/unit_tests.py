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

import os
import pytest
import sys

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub

# Create a new apiproxy and temp datastore to use for this test suite
apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
temp_db = datastore_file_stub.DatastoreFileStub('x', None, None, trusted=True)
apiproxy_stub_map.apiproxy.RegisterStub('datastore', temp_db)

# An application id is required to access the datastore, so let's create one
os.environ['APPLICATION_ID'] = 'personfinder-unittest'

# When the appserver is running, the APP_DIR should be the current directory...
os.chdir(os.environ['APP_DIR'])

# ...but we want pytest to default to finding tests in TESTS_DIR, not the cwd.
# So, when no arguments are given, we make the option parser return TESTS_DIR.
import _pytest.config
original_parse_setoption = _pytest.config.Parser.parse_setoption
_pytest.config.Parser.parse_setoption = \
    lambda *args: original_parse_setoption(*args) or [os.environ['TESTS_DIR']]

# Run the tests, using sys.exit to set exit status (nonzero for failure).
sys.exit(pytest.main())
