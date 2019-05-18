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
"""Tests for the deletion tasks."""

import datetime
import logging
import sys

from google.appengine import runtime
from google.appengine.ext import db
from google.appengine.api import taskqueue
import mock
# We should be moving off mox and to mock. However, taskqueue doesn't play nice
# with mock, so dropping mox for these tests means moving to GAE's stuff for
# this. Since taskqueue has to get replaced by Cloud Tasks for Python 3 anyway,
# it's not worth rewriting these tests now just to avoid mox.
import mox

import model
import utils

import task_tests_base


class ProcessExpirationsTaskTests(task_tests_base.TaskTestsBase):
    """Tests the expirations processing task."""

    def init_testbed_stubs(self):
        self.testbed.init_user_stub()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()

    def setUp(self):
        super(ProcessExpirationsTaskTests, self).setUp()

        self.data_generator.repo(repo_id='haiti')
        logging.basicConfig(level=logging.INFO, stream=sys.stderr)
        self.mox = None

        utils.set_utcnow_for_test(datetime.datetime(2010, 1, 1))

        # TODO(nworden): factor out a general-purpose utility for creation of
        # test entities.
        self.photo = self.data_generator.photo()
        self.photo_key = self.photo.key()
        self.p1 = self.data_generator.person_a(photo=self.photo)
        self.p2 = self.data_generator.person_b()
        self.key_p1 = self.p1.key()
        self.key_p2 = self.p2.key()
        self.n1_1 = self.data_generator.note(person_id=self.p1.record_id)
        self.note_id = self.n1_1.note_record_id
        self.to_delete = [self.p1, self.p2, self.n1_1, self.photo]

    def test_task_scheduling(self):
        tq_mock = mox.Mox()
        tq_mock.StubOutWithMock(taskqueue, 'add')
        taskqueue.add(name=mox.IsA(unicode),
                      method='POST',
                      url='/haiti/tasks/process_expirations',
                      queue_name='expiry',
                      params={'cursor': ''})
        tq_mock.ReplayAll()
        self.run_task('/global/tasks/process_expirations')
        tq_mock.VerifyAll()
        tq_mock.UnsetStubs()

    def test_task_rescheduling(self):
        """Tests that task is rescheduled for continuation."""
        tq_mock = mox.Mox()
        tq_mock.StubOutWithMock(taskqueue, 'add')
        taskqueue.add(name=mox.IsA(unicode),
                      method='POST',
                      url='/haiti/tasks/process_expirations',
                      queue_name='expiry',
                      params={'cursor': ''})
        tq_mock.ReplayAll()
        # DeadlineExceededErrors can be raised at any time. A convenient way for
        # us to raise it during this test execution is with utils.get_utcnow.
        with mock.patch('utils.get_utcnow') as get_utcnow_mock:
            get_utcnow_mock.side_effect = runtime.DeadlineExceededError()
            self.run_task('/haiti/tasks/process_expirations', method='POST')
        tq_mock.VerifyAll()
        tq_mock.UnsetStubs()

    def test_task(self):
        # TODO(nworden): break this test up into smaller, more isolated tests.
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

        self.run_task('/haiti/tasks/process_expirations',
                      data={}, method='POST')

        # Confirm that DeleteExpired had no effect.
        assert model.Person.all().count() == 2
        assert_past_due_count(0)
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 1, 1)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 1, 1)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert model.Note.get('haiti', self.note_id)
        assert db.get(self.photo_key)

        # Advance to just after the expiry_date of self.p1.
        utils.set_utcnow_for_test(datetime.datetime(2010, 2, 2))

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
        self.mox.ReplayAll()
        self.run_task('/haiti/tasks/process_expirations',
                      data={}, method='POST')
        self.mox.VerifyAll()

        # Confirm that DeleteExpired set is_expired and updated the timestamps
        # on self.p1, but did not wipe its fields or delete the Note or Photo.
        assert model.Person.all().count() == 1
        assert_past_due_count(1)
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert db.get(self.key_p1).is_expired is True
        assert model.Note.get('haiti', self.note_id) is None  # Note is hidden
        assert db.get(self.n1_1.key())  # but the Note entity still exists
        assert db.get(self.photo_key)

        # Advance past the end of the expiration grace period of self.p1.
        utils.set_utcnow_for_test(datetime.datetime(2010, 2, 5))

        # Confirm that nothing has changed yet.
        assert model.Person.all().count() == 1
        assert_past_due_count(1)
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert db.get(self.key_p1).is_expired is True
        assert model.Note.get('haiti', self.note_id) is None  # Note is hidden
        assert db.get(self.n1_1.key())  # but the Note entity still exists
        assert db.get(self.photo_key)

        self.run_task('/haiti/tasks/process_expirations',
                      data={}, method='POST')

        # Confirm that the task wiped self.p1 without changing the timestamps,
        # and deleted the related Note and Photo.
        assert model.Person.all().count() == 1
        assert_past_due_count(1)
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert db.get(self.key_p1).is_expired is True
        assert db.get(self.key_p1).given_name is None
        assert model.Note.get('haiti', self.note_id) is None  # Note is hidden
        assert db.get(self.n1_1.key()) is None  # Note entity is actually gone
        assert db.get(self.photo_key) is None  # Photo entity is gone

        # Advance past the end of the expiration grace period for self.p2.
        utils.set_utcnow_for_test(datetime.datetime(2010, 3, 15))

        # Confirm that both records are now counted as past due.
        assert model.Person.all().count() == 1
        assert_past_due_count(2)
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert db.get(self.key_p2).source_date == datetime.datetime(2010, 1, 1)
        assert db.get(self.key_p2).entry_date == datetime.datetime(2010, 1, 1)
        assert db.get(self.key_p2).expiry_date == datetime.datetime(2010, 3, 1)

        self.run_task('/haiti/tasks/process_expirations',
                      data={}, method='POST')

        # Confirm that the task wiped self.p2 as well.
        assert model.Person.all().count() == 0
        assert_past_due_count(2)
        assert db.get(self.key_p1).is_expired is True
        assert db.get(self.key_p1).given_name is None
        assert db.get(self.key_p1).source_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).entry_date == datetime.datetime(2010, 2, 2)
        assert db.get(self.key_p1).expiry_date == datetime.datetime(2010, 2, 1)
        assert db.get(self.key_p2).is_expired is True
        assert db.get(self.key_p2).given_name is None
        assert db.get(self.key_p2).source_date == datetime.datetime(2010, 3, 15)
        assert db.get(self.key_p2).entry_date == datetime.datetime(2010, 3, 15)
        assert db.get(self.key_p2).expiry_date == datetime.datetime(2010, 3, 1)
        self.mox.UnsetStubs()


class CleanupStrayNotesTaskTests(task_tests_base.TaskTestsBase):
    """Tests the stray notes cleanup task."""

    def setUp(self):
        super(CleanupStrayNotesTaskTests, self).setUp()
        self.person = self.data_generator.person(
            expiry_date=datetime.datetime(2010, 5, 1))
        self.note1 = self.data_generator.note(
            person_id=self.person.record_id,
            original_creation_date=datetime.datetime(2010, 1, 2))
        self.note2 = self.data_generator.note(
            person_id='notanexistingrecord',
            original_creation_date=datetime.datetime(2010, 3, 15))
        self.note3 = self.data_generator.note(
            person_id='notanexistingrecord',
            original_creation_date=datetime.datetime(2010, 1, 2))

    def test_task(self):
        utils.set_utcnow_for_test(datetime.datetime(2010, 4, 2))
        self.run_task('/haiti/tasks/cleanup_stray_notes',
                      data={}, method='POST')
        notes_q = model.Note.all()
        # Note #1 should be kept because it's associated with an existing Person
        # record, and note #2 should be kept because it's within the grace
        # period.
        self.assertEqual(2, notes_q.count())
        notes = notes_q[:2]
        self.assertEqual(sorted([n.key() for n in notes]),
                         sorted([self.note1.key(), self.note2.key()]))


class CleanupStraySubscriptionsTaskTests(task_tests_base.TaskTestsBase):
    """Tests the stray subscriptions cleanup task."""

    def setUp(self):
        super(CleanupStraySubscriptionsTaskTests, self).setUp()
        self.person = self.data_generator.person(
            expiry_date=datetime.datetime(2010, 5, 1))
        self.subscription1 = self.data_generator.subscription(
            person_id=self.person.record_id,
            timestamp=datetime.datetime(2010, 1, 2))
        self.subscription2 = self.data_generator.subscription(
            person_id='notanexistingrecordid',
            timestamp=datetime.datetime(2010, 3, 15))
        self.subscription3 = self.data_generator.subscription(
            person_id='notanexistingrecordid',
            timestamp=datetime.datetime(2010, 1, 2))

    def test_task(self):
        utils.set_utcnow_for_test(datetime.datetime(2010, 4, 2))
        self.run_task('/haiti/tasks/cleanup_stray_subscriptions',
                      data={}, method='POST')
        subs_q = model.Subscription.all()
        # Subscription #1 should be kept because it's associated with an
        # existing Person record, and subscription #2 should be kept because
        # it's within the grace period.
        self.assertEqual(2, subs_q.count())
        subs = subs_q[:2]
        self.assertEqual(sorted([s.key() for s in subs]),
                         sorted([self.subscription1.key(),
                                 self.subscription2.key()]))
