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


"""Tests for the datastore setup handler."""

import os
import unittest

import django
import django.test
from google.appengine.ext import testbed

import config


class MetaSetupDatastoreHandlerTests(unittest.TestCase):
    """Tests the datastore setup handler."""

    def setUp(self):
        super(MetaSetupDatastoreHandlerTests, self).setUp()
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.testbed.init_datastore_v3_stub()
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
        django.setup()
        django.test.utils.setup_test_environment()
        self.client = django.test.Client()

    def tearDown(self):
        self.testbed.deactivate()
        django.test.utils.teardown_test_environment()

    def test_setup(self):
        self.assertFalse(config.get('initialized'))
        resp = self.client.get('/setup_datastore/', secure=True)
        self.assertTrue(config.get('initialized'))
        self.assertIsInstance(resp, django.http.HttpResponseRedirect)
        self.assertEqual(resp.url, 'https://testserver/')

    def test_already_setup(self):
        config.set(initialized=True)
        resp = self.client.get('/setup_datastore', secure=True)
        self.assertEqual(resp.status_code, 400)
