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
"""Tests for the datacheck tasks."""

import datetime
import os

from google.appengine import runtime
from google.appengine.api import taskqueue
import mock
import mox

import tasksmodule
import utils

import task_tests_base


def deadline_exceeded_side_effect(*args, **kwargs):
    del args, kwargs  # Unused.
    raise runtime.DeadlineExceededError()


def _test_deadline_exceeded(run_task_func, task_url):
    mox_obj = mox.Mox()
    mox_obj.StubOutWithMock(taskqueue, 'add')
    taskqueue.add(
        method='POST',
        url=task_url,
        params={'cursor': None},
        queue_name='datachecks',
        retry_options=mox.IsA(taskqueue.taskqueue.TaskRetryOptions),
        name=mox.IsA(unicode))
    mox_obj.ReplayAll()
    with mock.patch('utils.validate_email') as mock_validate_email:
        mock_validate_email.side_effect = deadline_exceeded_side_effect
        run_task_func()
    mox_obj.VerifyAll()
    mox_obj.UnsetStubs()


class PersonDataValidityCheckTaskTests(task_tests_base.TaskTestsBase):
    """Tests the person record validity datacheck task.

    We don't have a unit test for the missing entry date case, because
    entry_date is required by the model (i.e., we cannot test it because we
    cannot create a Person entity without it to test with).
    """

    def init_testbed_stubs(self):
        self.testbed.init_user_stub()
        self.testbed.init_datastore_v3_stub()
        path_to_app = os.path.join(os.path.dirname(__file__), '../../app')
        self.testbed.init_taskqueue_stub(root_path=path_to_app)

    def setUp(self):
        super(PersonDataValidityCheckTaskTests, self).setUp()
        self.data_generator.repo(repo_id='haiti')

    def test_good_data(self):
        self.data_generator.person()
        self.run_task('/haiti/tasks/check_person_data_validity', method='POST')

    def test_missing_original_creation_date(self):
        self.data_generator.person(original_creation_date=None)
        self.assertRaises(
            tasksmodule.datachecks.DatacheckException,
            self.run_task,
            '/haiti/tasks/check_person_data_validity', method='POST')

    def test_invalid_author_email(self):
        self.data_generator.person(author_email='not-a-valid-email-address')
        self.assertRaises(
            tasksmodule.datachecks.DatacheckException,
            self.run_task,
            '/haiti/tasks/check_person_data_validity', method='POST')

    def test_deadline_exceeded(self):
        self.data_generator.person(author_email='abc@example.com')

        def run_task_func():
            self.run_task(
                '/haiti/tasks/check_person_data_validity', method='POST')
        _test_deadline_exceeded(
             run_task_func, '/haiti/tasks/check_person_data_validity')


class NoteDataValidityCheckTaskTests(task_tests_base.TaskTestsBase):
    """Tests the note validity datacheck task.

    Doesn't test the missing entry date or missing Person record ID case,
    because those fields are required by the model class.
    """

    def init_testbed_stubs(self):
        self.testbed.init_user_stub()
        self.testbed.init_datastore_v3_stub()
        path_to_app = os.path.join(os.path.dirname(__file__), '../../app')
        self.testbed.init_taskqueue_stub(root_path=path_to_app)

    def setUp(self):
        super(NoteDataValidityCheckTaskTests, self).setUp()
        self.data_generator.repo(repo_id='haiti')
        self.person = self.data_generator.person()

    def test_good_data(self):
        self.data_generator.note(person_id=self.person.record_id)
        self.run_task('/haiti/tasks/check_note_data_validity', method='POST')

    def test_missing_original_creation_date(self):
        self.data_generator.note(
            person_id=self.person.record_id, original_creation_date=None)
        self.assertRaises(
            tasksmodule.datachecks.DatacheckException,
            self.run_task,
            '/haiti/tasks/check_note_data_validity', method='POST')

    def test_invalid_author_email(self):
        self.data_generator.note(
            person_id=self.person.record_id,
            author_email='not-a-valid-email-address')
        self.assertRaises(
            tasksmodule.datachecks.DatacheckException,
            self.run_task,
            '/haiti/tasks/check_note_data_validity', method='POST')

    def test_invalid_email_of_found_person(self):
        self.data_generator.note(
            person_id=self.person.record_id,
            email_of_found_person='not-a-valid-email-address')
        self.assertRaises(
            tasksmodule.datachecks.DatacheckException,
            self.run_task,
            '/haiti/tasks/check_note_data_validity', method='POST')

    def test_missing_person_record(self):
        self.data_generator.note(person_id='not-an-existing-person-record')
        self.assertRaises(
            tasksmodule.datachecks.DatacheckException,
            self.run_task,
            '/haiti/tasks/check_note_data_validity', method='POST')

    def test_deadline_exceeded(self):
        person = self.data_generator.person()
        self.data_generator.note(
            person_id=person.record_id,
            author_email='xyz@example.com')

        def run_task_func():
            self.run_task(
                '/haiti/tasks/check_person_data_validity', method='POST')
        _test_deadline_exceeded(
             run_task_func, '/haiti/tasks/check_person_data_validity')


class ExpiredPersonRecordCheckTaskTest(task_tests_base.TaskTestsBase):

    _NOW = datetime.datetime(2010, 2, 1)
    _YESTERDAY = _NOW - datetime.timedelta(days=1, hours=1)

    def init_testbed_stubs(self):
        self.testbed.init_user_stub()
        self.testbed.init_datastore_v3_stub()
        path_to_app = os.path.join(os.path.dirname(__file__), '../../app')
        self.testbed.init_taskqueue_stub(root_path=path_to_app)

    def setUp(self):
        super(ExpiredPersonRecordCheckTaskTest, self).setUp()
        utils.set_utcnow_for_test(ExpiredPersonRecordCheckTaskTest._NOW)
        self.data_generator.repo(repo_id='haiti')

    def test_good_expired_record(self):
        self.data_generator.person(
            expiry_date=ExpiredPersonRecordCheckTaskTest._YESTERDAY,
            given_name=None,
            family_name=None,
            home_city='',
            home_state='',
            home_postal_code='',
            home_neighborhood='',
            author_name='',
            author_phone='',
            author_email='',
            source_name='',
            source_url='')
        self.run_task(
            '/haiti/tasks/check_expired_person_records', method='POST')

    def test_unexpired_record(self):
        expiry_date = (
            ExpiredPersonRecordCheckTaskTest._NOW +
            datetime.timedelta(days=1, hours=1))
        self.data_generator.person(expiry_date=expiry_date)
        self.run_task(
            '/haiti/tasks/check_expired_person_records', method='POST')

    def test_expired_record_with_data(self):
        self.data_generator.person(
            expiry_date=ExpiredPersonRecordCheckTaskTest._YESTERDAY)
        self.assertRaises(
            tasksmodule.datachecks.DatacheckException,
            self.run_task,
            '/haiti/tasks/check_expired_person_records', method='POST')
