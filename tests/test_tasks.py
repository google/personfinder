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
import mox
import sys
import unittest
import webob

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import taskqueue
from google.appengine.ext import webapp

import model
import tasks
from utils import get_utcnow, set_utcnow_for_test
from nose.tools import eq_ as eq

class TasksTests(unittest.TestCase):
    # TODO(kpy@): tests for Count* methods.

    def initialize_handler(self, handler):
        model.Subdomain(key_name='haiti').put()
        request = webapp.Request(
            webob.Request.blank(handler.URL + '?subdomain=haiti').environ)
        response = webapp.Response()
        handler.initialize(request, response)
        return handler

    def test_delete_expired(self):
        """Test the flagging and deletion of expired records."""

        def run_delete_expired_task():
            """Runs the DeleteExpired task."""
            self.initialize_handler(tasks.DeleteExpired()).get()

        def assert_past_due_count(expected):
            actual = len(list(model.Person.past_due_records(subdomain='haiti')))
            assert actual == expected

        # This test sets up two Person entities, self.p1 and self.p2.
        # self.p1 is deleted in two stages (running DeleteExpired once during
        # the grace period, then again after the grace period); self.p2 is
        # deleted in one stage (running DeleteExpired after the grace period).

        # Setup cheerfully stolen from test_model.
        set_utcnow_for_test(datetime.datetime(2010, 1, 1))
        photo = model.Photo(bin_data='0x1111')
        photo.put() 
        photo_id = photo.key().id()
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
            photo_url='',
            photo=photo,
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
            source_date=datetime.datetime(2010, 1, 1),
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
            source_date=datetime.datetime(2010, 1, 2))
        note_id = self.n1_1.note_record_id
        db.put(self.n1_1)


        # Initial state: two Persons and one Note, nothing expired yet.
        eq(model.Person.all().count(), 2)
        assert_past_due_count(0)
        assert model.Note.get('haiti', note_id)
        assert model.Photo.get_by_id(photo_id)

        # verify schedule_next_task does the right thing.
        query = model.Person.all()
        query.get()
        cursor = query.cursor()
        self.mox = mox.Mox()
        self.mox.StubOutWithMock(taskqueue, 'add')
        taskqueue.add(method='GET',
                      url='/tasks/delete_expired',
                      params= { 'cursor' :cursor,
                                'queue_name': 'expiry', 
                                'subdomain' : u'haiti'},
                      name=mox.IsA(unicode))
        self.mox.ReplayAll()
        delexp = self.initialize_handler(tasks.DeleteExpired())
        delexp.schedule_next_task(query)
        self.mox.VerifyAll()


        run_delete_expired_task()

        # Confirm that DeleteExpired had no effect.
        eq(model.Person.all().count(), 2)
        assert_past_due_count(0)
        eq(db.get(self.key_p1).source_date, datetime.datetime(2010, 1, 1))
        eq(db.get(self.key_p1).entry_date, datetime.datetime(2010, 1, 1))
        eq(db.get(self.key_p1).expiry_date, datetime.datetime(2010, 2, 1))
        assert model.Note.get('haiti', note_id)
        assert model.Photo.get_by_id(photo_id)

        # Advance to just after the expiry_date of self.p1.
        set_utcnow_for_test(datetime.datetime(2010, 2, 2))

        # self.p1 should now be past due.
        eq(model.Person.all().count(), 2)
        assert_past_due_count(1)
        eq(db.get(self.key_p1).source_date, datetime.datetime(2010, 1, 1))
        eq(db.get(self.key_p1).entry_date, datetime.datetime(2010, 1, 1))
        eq(db.get(self.key_p1).expiry_date, datetime.datetime(2010, 2, 1))
        assert model.Note.get('haiti', note_id)
        assert model.Photo.get_by_id(photo_id)

        self.mox = mox.Mox()
        self.mox.StubOutWithMock(taskqueue, 'add')
        taskqueue.add(queue_name='send-mail', 
                      url='/admin/send_mail',
                      params=mox.IsA(dict))
        self.mox.ReplayAll()
        run_delete_expired_task()
        self.mox.VerifyAll()

        # Confirm that DeleteExpired set is_expired and updated the timestamps
        # on self.p1, but did not wipe its fields or delete the Note or Photo.
        eq(model.Person.all().count(), 1)
        assert_past_due_count(1)
        eq(db.get(self.key_p1).source_date, datetime.datetime(2010, 2, 2))
        eq(db.get(self.key_p1).entry_date, datetime.datetime(2010, 2, 2))
        eq(db.get(self.key_p1).expiry_date, datetime.datetime(2010, 2, 1))
        eq(db.get(self.key_p1).is_expired, True)
        assert not model.Note.get('haiti', note_id)  # Note is hidden
        assert db.get(self.n1_1.key())  # but the Note entity still exists
        assert model.Photo.get_by_id(photo_id)

        # Advance past the end of the expiration grace period of self.p1.
        set_utcnow_for_test(datetime.datetime(2010, 2, 5))

        # Confirm that nothing has changed yet.
        eq(model.Person.all().count(), 1)
        assert_past_due_count(1)
        eq(db.get(self.key_p1).source_date, datetime.datetime(2010, 2, 2))
        eq(db.get(self.key_p1).entry_date, datetime.datetime(2010, 2, 2))
        eq(db.get(self.key_p1).expiry_date, datetime.datetime(2010, 2, 1))
        eq(db.get(self.key_p1).is_expired, True)
        eq(model.Note.get('haiti', note_id), None)  # Note is hidden
        assert db.get(self.n1_1.key())  # but the Note entity still exists
        assert model.Photo.get_by_id(photo_id)

        run_delete_expired_task()

        # Confirm that the task wiped self.p1 without changing the timestamps,
        # and deleted the related Note and Photo.
        eq(model.Person.all().count(), 1)
        assert_past_due_count(1)
        eq(db.get(self.key_p1).source_date, datetime.datetime(2010, 2, 2))
        eq(db.get(self.key_p1).entry_date, datetime.datetime(2010, 2, 2))
        eq(db.get(self.key_p1).expiry_date, datetime.datetime(2010, 2, 1))
        eq(db.get(self.key_p1).is_expired, True)
        eq(db.get(self.key_p1).first_name, None)
        eq(model.Note.get('haiti', note_id), None)  # Note is hidden
        eq(db.get(self.n1_1.key()), None)  # Note entity is actually gone
        eq(model.Photo.get_by_id(photo_id), None)  # Photo entity is gone

        # Advance past the end of the expiration grace period for self.p2.
        set_utcnow_for_test(datetime.datetime(2010, 3, 15))

        # Confirm that both records are now counted as past due.
        eq(model.Person.all().count(), 1)
        assert_past_due_count(2)
        eq(db.get(self.key_p1).source_date, datetime.datetime(2010, 2, 2))
        eq(db.get(self.key_p1).entry_date, datetime.datetime(2010, 2, 2))
        eq(db.get(self.key_p1).expiry_date, datetime.datetime(2010, 2, 1))
        eq(db.get(self.key_p2).source_date, datetime.datetime(2010, 1, 1))
        eq(db.get(self.key_p2).entry_date, datetime.datetime(2010, 1, 1))
        eq(db.get(self.key_p2).expiry_date, datetime.datetime(2010, 3, 1))

        run_delete_expired_task()

        # Confirm that the task wiped self.p2 as well.
        eq(model.Person.all().count(), 0)
        assert_past_due_count(2)
        eq(db.get(self.key_p1).is_expired, True)
        eq(db.get(self.key_p1).first_name, None)
        eq(db.get(self.key_p1).source_date, datetime.datetime(2010, 2, 2))
        eq(db.get(self.key_p1).entry_date, datetime.datetime(2010, 2, 2))
        eq(db.get(self.key_p1).expiry_date, datetime.datetime(2010, 2, 1))
        eq(db.get(self.key_p2).is_expired, True)
        eq(db.get(self.key_p2).first_name, None)
        eq(db.get(self.key_p2).source_date, datetime.datetime(2010, 3, 15))
        eq(db.get(self.key_p2).entry_date, datetime.datetime(2010, 3, 15))
        eq(db.get(self.key_p2).expiry_date, datetime.datetime(2010, 3, 1))
