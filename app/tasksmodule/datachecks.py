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

"""Tasks to check data.

These tasks don't modify data, they just double-check things that are already
expected to be true.
"""

import datetime
import time

import django.http
from google.appengine import runtime
from google.appengine.api import datastore_errors
from google.appengine.api import taskqueue

import tasksmodule.base
import model
import utils


class DatacheckException(Exception):
    """An exception raised when a datacheck tasks finds a problem."""
    pass


class DatachecksBaseTask(tasksmodule.base.PerRepoTaskBaseView):

    def setup(self, request, *args, **kwargs):
        super(DatachecksBaseTask, self).setup(request, *args, **kwargs)
        self.params.read_values(post_params={'cursor': utils.strip})

    def schedule_task(self, repo, **kwargs):
        name = '%s-%s-%s' % (repo, self.BASE_NAME, int(time.time()*1000))
        path = self.build_absolute_path('/%s/tasks/%s' % (repo, self.TASK_PATH))
        cursor = kwargs.get('cursor', '')
        # TODO(nworden): figure out why setting task_retry_limit isn't working
        retry_options = taskqueue.taskqueue.TaskRetryOptions(task_retry_limit=1)
        taskqueue.add(name=name, method='POST', url=path,
                      queue_name='datachecks', retry_options=retry_options,
                      params={'cursor': cursor})

    def alert(self, msg):
        """Alerts developers of an error.

        For now, we just raise an exception. It will show up in Stackdriver.
        """
        raise DatacheckException(msg)


class PersonDataValidityCheckTask(DatachecksBaseTask):
    """Checks that person records have valid data."""

    BASE_NAME = 'person_data_validity_check'
    TASK_PATH = 'check_person_data_validity'

    def _check_person(self, person):
        if not person.entry_date:
            self.alert(
                'A person record is missing an entry_date value (%s).'
                % person.record_id)
        if not person.original_creation_date:
            self.alert(
                'A person record is missing an original_creation_date value'
                '(%s).' % person.record_id)
        if (person.author_email and
                not utils.validate_email(person.author_email)):
            self.alert(
                'A person record has an invalid author_email value (%s).'
                % person.record_id)

    def post(self, request, *args, **kwargs):
        del request, args, kwargs  # unused
        query = model.Person.all(filter_expired=False).filter(
            'repo =', self.env.repo)
        cursor = self.params.cursor
        if cursor:
            query.with_cursor(cursor)
        try:
            for person in query:
                next_cursor = query.cursor()
                self._check_person(person)
                cursor = next_cursor
        except runtime.DeadlineExceededError:
            self.schedule_task(self.env.repo, cursor=cursor)
        except datastore_errors.Timeout:
            self.schedule_task(self.env.repo, cursor=cursor)
        return django.http.HttpResponse('')


class NoteDataValidityCheckTask(DatachecksBaseTask):
    """Checks that notes have valid data."""

    BASE_NAME = 'note_data_validity_check'
    TASK_PATH = 'check_note_data_validity'

    def _check_note(self, note):
        if not note.entry_date:
            self.alert(
                'A note record is missing an entry_date value (%s).' %
                note.record_id)
        if not note.original_creation_date:
            self.alert(
                'A note record is missing an original_creation_date value (%s).'
                % note.record_id)
        if not note.person_record_id:
            self.alert(
                'A note record is missing a person_record_id value (%s).' %
                note.record_id)
        if (note.author_email and not utils.validate_email(note.author_email)):
            self.alert(
                'A note record has an invalid author_email value (%s).' %
                note.record_id)
        if (note.email_of_found_person and
                not utils.validate_email(note.email_of_found_person)):
            self.alert(
                'A note record has an invalid email_of_found_person value (%s).'
                % note.record_id)
        if not model.Person.get(self.env.repo, note.person_record_id):
            self.alert(
                'A note record\'s associated person record is missing (%s).' %
                note.record_id)

    def post(self, request, *args, **kwargs):
        del request, args, kwargs  # unused
        query = model.Note.all(filter_expired=False).filter(
            'repo =', self.env.repo)
        cursor = self.params.cursor
        if cursor:
            query.with_cursor(cursor)
        try:
            for note in query:
                next_cursor = query.cursor()
                self._check_note(note)
                cursor = next_cursor
        except runtime.DeadlineExceededError:
            self.schedule_task(self.env.repo, cursor=cursor)
        except datastore_errors.Timeout:
            self.schedule_task(self.env.repo, cursor=cursor)
        return django.http.HttpResponse('')


class ExpiredPersonRecordCheckTask(DatachecksBaseTask):
    """Checks that expired person records have been cleared."""

    BASE_NAME = 'expired_person_record_check'
    TASK_PATH = 'check_expired_person_records'

    def _check_person(self, person):
        # Check things that were expired yesterday, just in case this job is
        # ahead of the deletion job.
        yesterday = utils.get_utcnow() - datetime.timedelta(days=1)
        if not (person.expiry_date and person.expiry_date < yesterday):
            return
        for name, prop in person.properties().items():
            if name not in ['repo', 'is_expired', 'original_creation_date',
                            'source_date', 'entry_date', 'expiry_date',
                            'last_modified']:
                if getattr(person, name) != prop.default:
                    self.alert(
                        'An expired person record still has data (%s, %s).' %
                        (person.record_id, name))

    def post(self, request, *args, **kwargs):
        query = model.Person.all(filter_expired=False).filter(
            'repo =', self.env.repo)
        cursor = self.params.cursor
        if cursor:
            query.with_cursor(cursor)
        try:
            for person in query:
                next_cursor = query.cursor()
                self._check_person(person)
                cursor = next_cursor
        except runtime.DeadlineExceededError:
            self.schedule_task(self.env.repo, cursor=cursor)
        except datastore_errors.Timeout:
            self.schedule_task(self.env.repo, cursor=cursor)
        return django.http.HttpResponse('')
