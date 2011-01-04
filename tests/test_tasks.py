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

"""Unittest for tasks.py module."""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import datetime
import webob
import unittest

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp

import model
import tasks


class TasksTests(unittest.TestCase):
    def tearDown(self):
        db.delete(model.PersonTombstone.all())

    def simulate_request(self, path):
        request = webapp.Request(webob.Request.blank(path).environ)
        response = webapp.Response()
        handler = tasks.ClearTombstones()
        handler.initialize(request, response)
        return handler

    def test_clear_tombstones(self):
        """Tests the clear tombstones cron job."""
        pt_new = model.PersonTombstone(
            subdomain='haiti', record_id='example.org/person.123')
        pt_old = model.PersonTombstone(
            subdomain='haiti', record_id='example.org/person.456')
        pt_old.timestamp -= datetime.timedelta(days=4)
        db.put([pt_new, pt_old])

        handler = self.simulate_request('/tasks/clear_tombstones')
        handler.get()

        assert db.get(pt_new.key())
        assert not db.get(pt_old.key())
