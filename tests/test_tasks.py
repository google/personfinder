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
import sys
import unittest
import webob

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp

import model
import tasks
from utils import get_utcnow, set_utcnow_for_test

class TasksTests(unittest.TestCase):
    def tearDown(self):
        db.delete(model.PersonTombstone.all())

    def simulate_request(self, path, handler=tasks.ClearTombstones()):
        request = webapp.Request(webob.Request.blank(path).environ)
        response = webapp.Response()
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

    def test_delete_expired(self):
        """Make sure we delete expired persons, and only expired persons."""

        def expect_remaining(num_remaining):
            handler = self.simulate_request('/tasks/delete_expired', 
                                            tasks.DeleteExpired())
            handler.get()
            self.assertEquals(num_remaining, 
                              len([p for p in model.Person.all()]))

        # setup cheerfully stolen from test_model.
        set_utcnow_for_test(datetime.datetime(2010,1,1))
        self.p1 = model.Person.create_original(
            'haiti',
            first_name='John',
            last_name='Smith',
            home_street='Washington St.',
            home_city='Los Angeles',
            home_state='California',
            home_postal_code='11111',
            home_neighborhood='Good Neighborhood',
            author_name='Alice Smith',
            author_phone='111-111-1111',
            author_email='alice.smith@gmail.com',
            source_url='https://www.source.com',
            source_date=datetime.datetime(2010, 1, 1),
            source_name='Source Name',
            entry_date=datetime.datetime(2010, 1, 1),
            expiry_date=datetime.datetime(2010, 2, 1),
            other='')
        self.p2 = model.Person.create_original(
            'haiti',
            first_name='Tzvika',
            last_name='Hartman',
            home_street='Herzl St.',
            home_city='Tel Aviv',
            home_state='Israel',
            entry_date=datetime.datetime(2010, 1, 1),
            expiry_date=datetime.datetime(2010, 3, 1),
            other='')
        self.key_p1 = db.put(self.p1)
        self.key_p2 = db.put(self.p2)
        self.n1_1 = model.Note.create_original(
            'haiti',
            person_record_id=self.p1.record_id,
            linked_person_record_id=self.p2.record_id,
            status=u'believed_missing',
            found=False,
            entry_date=get_utcnow(),
            source_date=datetime.datetime(2000, 1, 1))
        note_id = self.n1_1.note_record_id
        db.put(self.n1_1)
        expect_remaining(2)
        assert model.Note.get('haiti', note_id)
        set_utcnow_for_test(datetime.datetime(2010,2,15))
        expect_remaining(1)
        # note 1 should be gone with p1.
        assert not model.Note.get('haiti', note_id)
        set_utcnow_for_test(datetime.datetime(2010,3,15))
        expect_remaining(0)
