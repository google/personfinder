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

"""Deletion tasks."""

import datetime
import time

import django.http
from google.appengine import runtime
from google.appengine.api import datastore_errors
from google.appengine.ext import db
from google.appengine.api import taskqueue

import delete
import tasksmodule.base
import model
import utils


_EXPIRED_TTL = datetime.timedelta(delete.EXPIRED_TTL_DAYS, 0, 0)

_STRAY_CLEANUP_TTL = datetime.timedelta(30, 0, 0)


class ProcessExpirationsTask(tasksmodule.base.PerRepoTaskBaseView):
    """The handler for clearing expired records.

    This task goes over all Person records, and will:
    - If a record is expired and is a clone of a record from another source,
      deletes it immediately.
    - If a record is an original record from this site and expired recently
      (within the last three days), marks it expired, but leaves the data so it
      can be recovered for a short period.
    - Once an original record has been expired for three days, we clear it and
      delete associated content (leaving a tombstone record with metadata like
      record ID and expiration date, so that API users can see it's expired).
    """

    ACTION_ID = 'tasks/process_expirations'

    def setup(self, request, *args, **kwargs):
        super(ProcessExpirationsTask, self).setup(request, *args, **kwargs)
        self.params.read_values(post_params={'cursor': utils.strip})

    def schedule_task(self, repo, **kwargs):
        name = '%s-process_expirations-%s' % (repo, int(time.time()*1000))
        path = self.build_absolute_path('/%s/tasks/process_expirations' % repo)
        cursor = kwargs.get('cursor', '')
        taskqueue.add(name=name, method='POST', url=path, queue_name='expiry',
                      params={'cursor': cursor})

    def post(self, request, *args, **kwargs):
        del request, args, kwargs  # unused
        q = model.Person.all(filter_expired=False).filter(
            'repo =', self.env.repo)
        cursor = self.params.get('cursor', '')
        if cursor:
            q.with_cursor(cursor)
        try:
            now = utils.get_utcnow()
            for person in q:
                next_cursor = q.cursor()
                was_expired = person.is_expired
                person.put_expiry_flags()
                if (now - person.get_effective_expiry_date() > _EXPIRED_TTL):
                    # Only original records should get to this point, since
                    # other records should have been deleted altogether as soon
                    # as they expired. Just in case the deletion task has failed
                    # for three days though, check that it's an original record
                    # to ensure we don't change the contents of a non-original
                    # record.
                    if person.is_original():
                        person.wipe_contents()
                    else:
                        person.delete_related_entities(delete_self=True)
                elif person.is_expired and not was_expired:
                    # Since we're not sending notices, handler isn't really
                    # needed.
                    # TODO(nworden): check with Product about whether we want to
                    # send notices for expirations. The current language
                    # indicates it was designed for cases where someone manually
                    # requested deletion of the record.
                    delete.delete_person(None, person, send_notices=False)
                cursor = next_cursor
        except runtime.DeadlineExceededError:
            self.schedule_task(self.env.repo, cursor=cursor)
        except datastore_errors.Timeout:
            self.schedule_task(self.env.repo, cursor=cursor)
        return django.http.HttpResponse('')


class CleanupStrayItemsTaskView(tasksmodule.base.PerRepoTaskBaseView):
    """A base handler for cleaning up data unassociated with any person record.

    It's possible for data that's unassociated with a Person record we have to
    make their way into the database via the API. This is a base class for
    handlers that clean up those unassociated entities if a) they're over 30
    days old and b) they aren't associated with a Person record we have (if we
    haven't gotten the Person record by then, it seems reasonable to assume we
    never will).
    """

    def schedule_task(self, repo, **kwargs):
        """Schedules a new task.

        Should be implemented by subclasses.
        """
        del self, repo, kwargs  # unusued
        raise NotImplementedError()

    def get_query(self):
        """Gets the query for items to possibly delete.

        Should be implemented by subclasses.
        """
        del self  # unused
        raise NotImplementedError()

    def get_person_record_id(self, item):
        """Gets the ID of the Person record the item is associated with.

        Should be implemented by subclasses.
        """
        del item  # unused
        raise NotImplementedError()

    def get_base_timestamp(self, item):
        """Gets the timestamp to use as the start of the grace period.

        Should be implemented by subclasses.
        """
        del item  # unused
        raise NotImplementedError()

    def setup(self, request, *args, **kwargs):
        super(CleanupStrayItemsTaskView, self).setup(request, *args, **kwargs)
        self.params.read_values(post_params={'cursor': utils.strip})

    def post(self, request, *args, **kwargs):
        del request, args, kwargs  # unused
        q = self.get_query()
        cursor = self.params.get('cursor', '')
        if cursor:
            q.with_cursor(cursor)
        try:
            now = utils.get_utcnow()
            for item in q:
                next_cursor = q.cursor()
                associated_person = model.Person.get(
                    self.env.repo, self.get_person_record_id(item))
                if not associated_person:
                    if now - self.get_base_timestamp(item) > _STRAY_CLEANUP_TTL:
                        db.delete(item)
                cursor = next_cursor
        except runtime.DeadlineExceededError:
            self.schedule_task(self.env.repo, cursor=cursor)
        except datastore_errors.Timeout:
            self.schedule_task(self.env.repo, cursor=cursor)
        return django.http.HttpResponse('')


class CleanupStrayNotesTask(CleanupStrayItemsTaskView):
    """Cleanup task handler for unassociated notes."""

    ACTION_ID = 'tasks/cleanup_stray_notes'

    def schedule_task(self, repo, **kwargs):
        name = '%s-cleanup_stray_notes-%s' % (
            repo, int(time.time()*1000))
        path = self.build_absolute_path(
            '/%s/tasks/cleanup_stray_notes' % repo)
        cursor = kwargs.get('cursor', '')
        taskqueue.add(name=name, method='POST', url=path, queue_name='expiry',
                      params={'cursor': cursor})

    def get_query(self):
        return model.Note.all(filter_expired=False).filter(
            'repo =', self.env.repo)

    def get_person_record_id(self, note):
        return note.person_record_id

    def get_base_timestamp(self, note):
        return note.original_creation_date


class CleanupStraySubscriptionsTask(CleanupStrayItemsTaskView):
    """Cleanup task handler for unassociated subscriptions."""

    ACTION_ID = 'tasks/cleanup_stray_subscriptions'

    def schedule_task(self, repo, **kwargs):
        name = '%s-cleanup_stray_subscriptions-%s' % (
            repo, int(time.time()*1000))
        path = self.build_absolute_path(
            '/%s/tasks/cleanup_stray_subscriptions' % repo)
        cursor = kwargs.get('cursor', '')
        taskqueue.add(name=name, method='POST', url=path, queue_name='expiry',
                      params={'cursor': cursor})

    def get_query(self):
        return model.Subscription.all().filter('repo =', self.env.repo)

    def get_person_record_id(self, subscription):
        return subscription.person_record_id

    def get_base_timestamp(self, subscription):
        return subscription.timestamp
