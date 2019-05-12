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


import os
import unittest

import django
import django.test
from google.appengine.ext import testbed

from testutils import data_generator


class ServerTestsBase(unittest.TestCase):

    def init_testbed_stubs(self):
        """Initializes the App Engine testbed stubs.

        Subclasses can override this, but should include the user stub even if
        they don't need it directly (it seems to be required).
        """
        self.testbed.init_user_stub()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def setUp(self):
        self.data_generator = data_generator.TestDataGenerator()
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.init_testbed_stubs()
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
        django.setup()
        django.test.utils.setup_test_environment()
        self.client = django.test.Client()

    def tearDown(self):
        self.testbed.deactivate()
        django.test.utils.teardown_test_environment()
