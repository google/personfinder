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

"""Unittest for tasks.py module."""

__author__ = 'pfritzsche@google.com (Phil Fritzsche)'

import calendar
import datetime
import logging
import mox
import os
import sys
import unittest
import urllib
import webob

from google.appengine import runtime
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import quota
from google.appengine.api import taskqueue
from google.appengine.ext import testbed
from google.appengine.ext import webapp

import config
import const
import delete
import model
import tasks
import test_handler
from utils import get_utcnow, set_utcnow_for_test



class TasksTests(unittest.TestCase):
    # TODO(kpy@): tests for Count* methods.

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        model.Repo(key_name='haiti').put()

        logging.basicConfig(level=logging.INFO, stream=sys.stderr)
        self.mox = None

        # Setup cheerfully stolen from test_model.
        set_utcnow_for_test(datetime.datetime(2010, 1, 1))
        self.photo = model.Photo.create('haiti', image_data='xyz')
        self.photo.put()
        self.photo_key = self.photo.key()
        self.p1 = model.Person.create_original(
            'haiti',
            given_name='John',
            family_name='Smith',
            home_street='Washington St.',
            home_city='Los Angeles',
            home_state='California',
            home_postal_code='11111',
            home_neighborhood='Good Neighborhood',
            author_name='Alice Smith',
            author_phone='111-111-1111',
            author_email='alice.smith@gmail.com',
            photo_url='',
            photo=self.photo,
            source_url='https://www.source.com',
            source_date=datetime.datetime(2010, 1, 1),
            source_name='Source Name',
            entry_date=datetime.datetime(2010, 1, 1),
            expiry_date=datetime.datetime(2010, 2, 1),
            other='')
        self.p2 = model.Person.create_original(
            'haiti',
            given_name='Tzvika',
            family_name='Hartman',
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
            author_made_contact=False,
            entry_date=get_utcnow(),
            source_date=datetime.datetime(2010, 1, 2))
        self.note_id = self.n1_1.note_record_id
        db.put(self.n1_1)
        self.to_delete = [self.p1, self.p2, self.n1_1, self.photo]

    def tearDown(self):
        self.testbed.deactivate()
        db.delete(self.to_delete)
        if self.mox:
            self.mox.UnsetStubs()

    def test_delete_expired(self):
        """Test the flagging and deletion of expired records."""

        def run_delete_expired_task():
            """Runs the DeleteExpired task."""
            test_handler.initialize_handler(tasks.DeleteExpired,
                                            tasks.DeleteExpired.ACTION).get()

        def assert_past_due_count(expected):
            actual = len(list(model.Person.past_due_records(repo='haiti')))
            assert actual == expected

        # This test sets up two Person entities, self.p1 and self.p2.
        # self.p1 is deleted in two stages (running DeleteExpired once during
        # the grace period, then again after the grace period); self.p2 is
        # deleted in one stage (running DeleteExpired after the grace period).

        # Initial state: two Persons and one Note, nothing expired yet.
        assert model.Person.all().count() == 2
        assert_past_due_count(0)
        assert model.Note.get('haiti', self.note_id)
        assert db.get(self.photo_key)

        # verify schedule_next_task does the right thing.
        query = model.Person.all()
        query.get()
        cursor = query.cursor()
        self.mox = mox.Mox()
        self.mox.StubOutWithMock(taskqueue, 'add')
        taskqueue.add(method='GET',
                      url='/haiti/tasks/delete_expired',
                      params={'cursor': cursor, 'queue_name': 'expiry'},
                      name=mox.IsA(str))
        self.mox.ReplayAll()
        delexp = test_handler.initialize_handler(tasks.DeleteExpired,
                                                 tasks.DeleteExpired.ACTION)
        delexp.schedule_next_task(query.cursor())
        self.mox.VerifyAll()


        run_delete_expired_task()

        # Confirm that DeleteExpired had no effect.
        assert model.Person.all().count() == 2
        assert_past_due_count(0)
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 1, 1)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 1, 1)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert model.Note.get('haiti', self.note_id)
        assert db.get(self.photo_key)

        # Advance to just after the expiry_date of self.p1.
        set_utcnow_for_test(datetime.datetime(2010, 2, 2))

        # self.p1 should now be past due.
        assert model.Person.all().count() == 2
        assert_past_due_count(1)
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 1, 1)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 1, 1)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert model.Note.get('haiti', self.note_id)
        assert db.get(self.photo_key)

        self.mox = mox.Mox()
        self.mox.StubOutWithMock(taskqueue, 'add')
        taskqueue.add(queue_name='send-mail',
                      url='/global/admin/send_mail',
                      params=mox.IsA(dict))
        self.mox.ReplayAll()
        run_delete_expired_task()
        self.mox.VerifyAll()

        # Confirm that DeleteExpired set is_expired and updated the timestamps
        # on self.p1, but did not wipe its fields or delete the Note or Photo.
        assert model.Person.all().count() == 1
        assert_past_due_count(1)
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert db.get(self.key_p1).is_expired == True
        assert model.Note.get('haiti', self.note_id) is None  # Note is hidden
        assert db.get(self.n1_1.key())  # but the Note entity still exists
        assert db.get(self.photo_key)

        # Advance past the end of the expiration grace period of self.p1.
        set_utcnow_for_test(datetime.datetime(2010, 2, 5))

        # Confirm that nothing has changed yet.
        assert model.Person.all().count() == 1
        assert_past_due_count(1)
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert db.get(self.key_p1).is_expired == True
        assert model.Note.get('haiti', self.note_id) is None  # Note is hidden
        assert db.get(self.n1_1.key())  # but the Note entity still exists
        assert db.get(self.photo_key)

        run_delete_expired_task()

        # Confirm that the task wiped self.p1 without changing the timestamps,
        # and deleted the related Note and Photo.
        assert model.Person.all().count() == 1
        assert_past_due_count(1)
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert db.get(self.key_p1).is_expired == True
        assert db.get(self.key_p1).given_name is None
        assert model.Note.get('haiti', self.note_id) is None  # Note is hidden
        assert db.get(self.n1_1.key()) is None  # Note entity is actually gone
        assert db.get(self.photo_key) is None  # Photo entity is gone

        # Advance past the end of the expiration grace period for self.p2.
        set_utcnow_for_test(datetime.datetime(2010, 3, 15))

        # Confirm that both records are now counted as past due.
        assert model.Person.all().count() == 1
        assert_past_due_count(2)
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert db.get(self.key_p2).source_date == datetime.datetime(2010, 1, 1)
        assert db.get(self.key_p2).entry_date == datetime.datetime(2010, 1, 1)
        assert db.get(self.key_p2).expiry_date == datetime.datetime(2010, 3, 1)

        run_delete_expired_task()

        # Confirm that the task wiped self.p2 as well.
        assert model.Person.all().count() == 0
        assert_past_due_count(2)
        assert db.get(self.key_p1).is_expired == True
        assert db.get(self.key_p1).given_name is None
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert db.get(self.key_p2).is_expired == True
        assert db.get(self.key_p2).given_name is None
        assert db.get(self.key_p2).source_date == datetime.datetime(2010, 3, 15)
        assert db.get(self.key_p2).entry_date == datetime.datetime(2010, 3, 15)
        assert db.get(self.key_p2).expiry_date == datetime.datetime(2010, 3, 1)

    def test_clean_up_in_test_mode(self):
        """Test the clean up in test mode."""

        def run_clean_up_in_test_mode_task():
            """Runs the CleanUpInTestMode task."""
            test_handler.initialize_handler(tasks.CleanUpInTestMode,
                                            tasks.CleanUpInTestMode.ACTION
                                            ).get()

        tasks.CleanUpInTestMode.DELETION_AGE_SECONDS = 2 * 3600  # 2 hours

        # entry_date of p3 is 4 hours after p1 and p2.
        self.p3 = model.Person.create_original(
            'haiti',
            first_name='Taro',
            last_name='Google',
            home_street='Roppongi',
            home_city='Minato',
            home_state='Tokyo',
            source_date=datetime.datetime(2010, 1, 1),
            entry_date=datetime.datetime(2010, 1, 1, 4, 0, 0),
            expiry_date=datetime.datetime(2010, 3, 1),
            other='')
        self.key_p3 = db.put(self.p3)
        self.to_delete.append(self.p3)

        # Initial state: three Persons and one Note.
        assert model.Person.all().count() == 3
        assert model.Note.get('haiti', self.note_id)
        assert db.get(self.photo_key)
        assert db.get(self.key_p1).is_expired == False  # still exists
        assert db.get(self.key_p2).is_expired == False
        assert db.get(self.key_p3).is_expired == False

        # verify schedule_next_task does the right thing.
        utcnow = datetime.datetime(2010, 1, 1)
        config.set(test_mode=True, repo='haiti')
        query = model.Person.all()
        query.get()
        self.mox = mox.Mox()
        self.mox.StubOutWithMock(taskqueue, 'add')
        taskqueue.add(method='GET',
                      url='/haiti/tasks/clean_up_in_test_mode',
                      params={
                          'cursor': query.cursor(),
                          'utcnow': str(calendar.timegm(utcnow.utctimetuple())),
                          'queue_name': 'clean_up_in_test_mode',
                      },
                      name=mox.IsA(str))
        self.mox.ReplayAll()
        cleanup = \
            test_handler.initialize_handler(tasks.CleanUpInTestMode,
                                            tasks.CleanUpInTestMode.ACTION)
        cleanup.schedule_next_task(query.cursor(), utcnow)
        self.mox.UnsetStubs()
        self.mox.VerifyAll()

        # Nothing happens if test_mode is False.
        config.set(test_mode=False, repo='haiti')
        set_utcnow_for_test(datetime.datetime(2010, 6, 1))
        run_clean_up_in_test_mode_task()
        assert db.get(self.key_p1).is_expired == False  # still exists
        assert db.get(self.key_p2).is_expired == False
        assert db.get(self.key_p3).is_expired == False

        # Records with entry_date before 2010-01-01 3:00 are deleted.
        config.set(test_mode=True, repo='haiti')
        set_utcnow_for_test(datetime.datetime(2010, 1, 1, 5, 0, 0))
        run_clean_up_in_test_mode_task()
        assert db.get(self.key_p1) is None
        assert db.get(self.key_p2) is None
        assert db.get(self.key_p3).is_expired == False  # still exists

        # All records are deleted.
        config.set(test_mode=True, repo='haiti')
        set_utcnow_for_test(datetime.datetime(2010, 1, 1, 7, 0, 0))
        run_clean_up_in_test_mode_task()
        assert db.get(self.key_p1) is None
        assert db.get(self.key_p2) is None
        assert db.get(self.key_p3) is None

    def test_clean_up_in_test_mode_multi_tasks(self):
        """Test the clean up in test mode when it is broken into multiple
        tasks."""

        class Listener(object):
            def before_deletion(self, person):
                # This will be implemented later using mock.
                assert False

        tasks.CleanUpInTestMode.DELETION_AGE_SECONDS = 2 * 3600  # 2 hours
        utcnow = datetime.datetime(2010, 1, 1, 7, 0, 0)
        set_utcnow_for_test(utcnow)
        self.mox = mox.Mox()
        cleanup = \
            test_handler.initialize_handler(tasks.CleanUpInTestMode,
                                            tasks.CleanUpInTestMode.ACTION)
        listener = Listener()
        cleanup.set_listener(listener)

        # Simulates add_task_for_repo() because it doesn't work in unit tests.
        def add_task_for_repo(repo, task_name, action, **kwargs):
            cleanup = test_handler.initialize_handler(
                tasks.CleanUpInTestMode, action, repo=repo, params=kwargs)
            cleanup.set_listener(listener)
            cleanup.get()

        self.mox.StubOutWithMock(cleanup, 'add_task_for_repo')
        (cleanup.add_task_for_repo(
                'haiti',
                mox.IsA(str),
                mox.IsA(str),
                utcnow=str(calendar.timegm(utcnow.utctimetuple())),
                cursor=mox.IsA(str),
                queue_name=mox.IsA(str)).
            WithSideEffects(add_task_for_repo).MultipleTimes())

        def raise_deadline_exceeded_error(_):
            raise runtime.DeadlineExceededError()

        self.mox.StubOutWithMock(listener, 'before_deletion')
        listener.before_deletion(self.key_p1)
        listener.before_deletion(self.key_p2).WithSideEffects(
            raise_deadline_exceeded_error)
        listener.before_deletion(self.key_p2)

        self.mox.ReplayAll()

        config.set(test_mode=True, repo='haiti')
        # This should run multiple tasks and finally deletes all records.
        cleanup.get()
        assert db.get(self.key_p1) is None
        assert db.get(self.key_p2) is None

        self.mox.UnsetStubs()
        self.mox.VerifyAll()

    def ignore_call_to_send_delete_notice(self):
        """Replaces delete.send_delete_notice() with empty implementation."""
        self.mox.StubOutWithMock(delete, 'send_delete_notice')
        (delete.send_delete_notice(
                mox.IsA(tasks.CleanUpInTestMode), mox.IsA(model.Person)).
            MultipleTimes())


class NotifyManyUnreviewedNotesTests(unittest.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_mail_stub()
        # root_path must be set the the location of queue.yaml.
        # Otherwise, only the 'default' queue will be available.
        path_to_app = os.path.join(os.path.dirname(__file__), '../app')
        self.testbed.init_taskqueue_stub(root_path=path_to_app)
        model.Repo(key_name='haiti').put()
        self.handler = test_handler.initialize_handler(
            handler_class=tasks.NotifyManyUnreviewedNotes,
            action=tasks.NotifyManyUnreviewedNotes.ACTION,
            repo='haiti', environ=None, params=None)

    def tearDown(self):
        self.testbed.deactivate()

    def test_should_notify(self):
        # If email is empty, always False is returned.
        config.set(notification_email='',
                   unreviewed_notes_threshold=9)
        self.assert_(not self.handler._should_notify(10))

        config.set(notification_email='inna-testing@gmail.com',
                   unreviewed_notes_threshold=100)
        # The number of unreviewed_notes larger than threshold: True
        self.assert_(self.handler._should_notify(101))
        # The number of unreviewed_notes is equal to threshold: False
        self.assert_(not self.handler._should_notify(100))
        # The number of unreviewed_notes is smaller than threshold: False
        self.assert_(not self.handler._should_notify(99))
