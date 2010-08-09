#!/usr/bin/python2.5
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

import os
import sys
import unittest

# Make scripts/remote_api.py importable.
TESTS_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(PROJECT_DIR, 'scripts')
sys.path.append(SCRIPTS_DIR)

# Make imports work for the App Engine modules and modules in this app.
import remote_api
from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub

# Gather the tests from all the test modules.
loader = unittest.defaultTestLoader
suites = []
for filename in os.listdir(TESTS_DIR):
  if filename.startswith('test_') and filename.endswith('.py'):
    module = filename[:-3]
    suites.append(loader.loadTestsFromName(module))

# Create a new apiproxy and temp datastore to use for this test suite
apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
temp_db = datastore_file_stub.DatastoreFileStub(
    'PersonFinderUnittestDataStore', None, None, trusted=True)
apiproxy_stub_map.apiproxy.RegisterStub('datastore', temp_db)

# An application id is required to access the datastore, so let's create one
os.environ['APPLICATION_ID'] = 'personfinder-unittest'

# Run the tests.
result = unittest.TextTestRunner().run(unittest.TestSuite(suites))
sys.exit(not result.wasSuccessful())
