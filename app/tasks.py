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

import datetime
import time

from google.appengine.api import quota
from google.appengine.api import taskqueue
from google.appengine.ext import db

import delete
import model
import utils

CPU_MEGACYCLES_PER_REQUEST = 1000
EXPIRED_TTL = datetime.timedelta(delete.EXPIRED_TTL_DAYS, 0, 0)
FETCH_LIMIT = 100



class ScanForExpired(utils.Handler):
    """Common logic for scanning the Person table looking for things to delete.

    The common logic handles iterating through the query, updating the expiry
    date and wiping/deleting as needed. The is_expired flag on all records whose
    expiry_date has passed.  Records that expired more than EXPIRED_TTL in the
    past will also have their data fields, notes, and photos permanently
    deleted.

    Subclasses set the query and task_name."""
    subdomain_required = False

    def task_name(self):
        """Subclasses should implement this."""
        pass

    def query(self):
        """Subclasses should implement this."""
        pass

    def schedule_next_task(self, query):
        """Schedule the next task for to carry on with this query.

        we pass the query as a parameter to make testing easier.
        """
        self.add_task_for_subdomain(
            self.subdomain, self.task_name(),
            self.URL, cursor=query.cursor(),
            queue_name='expiry')

    def get(self):
        if self.subdomain:
            query = self.query()
            if self.params.cursor:
                query.with_cursor(self.params.cursor)
            for person in query:
                if quota.get_request_cpu_usage() > CPU_MEGACYCLES_PER_REQUEST:
                    # Stop before running into the hard limit on CPU time per
                    # request, to avoid aborting in the middle of an operation.
                    # Add task back in, restart at current spot:
                    self.schedule_next_task(query)
                    break
                was_expired = person.is_expired
                person.put_expiry_flags()
                if (utils.get_utcnow() - person.get_effective_expiry_date() >
                    EXPIRED_TTL):
                    person.wipe_contents()
                else:
                    # treat this as a regular deletion.
                    if person.is_expired and not was_expired:
                        delete.delete_person(self, person)
        else:
            for subdomain in model.Subdomain.list():
                self.add_task_for_subdomain(subdomain, self.task_name(),
                                            self.URL)

class DeleteExpired(ScanForExpired):
    """Scan for person records with expiry date thats past."""
    URL = '/tasks/delete_expired'

    def task_name(self):
        return 'delete-expired'

    def query(self):
        return model.Person.past_due_records(self.subdomain)

class DeleteOld(ScanForExpired):
    """Scan for person records with old source dates for expiration."""
    URL = '/tasks/delete_old'

    def task_name(self):
        return 'delete-old'

    def query(self):
        return model.Person.potentially_expired_records(self.subdomain)

def run_count(make_query, update_counter, counter):
    """Scans the entities matching a query for a limited amount of CPU time."""
    while quota.get_request_cpu_usage() < CPU_MEGACYCLES_PER_REQUEST:
        # Get the next batch of entities.
        query = make_query()
        if counter.last_key:
            query = query.filter('__key__ >', db.Key(counter.last_key))
        entities = query.order('__key__').fetch(FETCH_LIMIT)
        if not entities:
            counter.last_key = ''
            break

        # Pass the entities to the counting function.
        for entity in entities:
            update_counter(counter, entity)

        # Remember where we left off.
        counter.last_key = str(entities[-1].key())


class CountBase(utils.Handler):
    """A base handler for counting tasks.  Making a request to this handler
    without a subdomain will start tasks for all subdomains in parallel.
    Each subclass of this class handles one scan through the datastore."""
    subdomain_required = False  # Run at the root domain, not a subdomain.

    SCAN_NAME = ''  # Each subclass should choose a unique scan_name.
    URL = ''  # Each subclass should set the URL path that it handles.

    def get(self):
        if self.subdomain:  # Do some counting.
            counter = model.Counter.get_unfinished_or_create(
                self.subdomain, self.SCAN_NAME)
            run_count(self.make_query, self.update_counter, counter)
            counter.put()
            if counter.last_key:  # Continue counting in another task.
                self.add_task_for_subdomain(
                    self.subdomain, self.SCAN_NAME, self.URL)
        else:  # Launch counting tasks for all subdomains.
            for subdomain in model.Subdomain.list():
                self.add_task_for_subdomain(subdomain, self.SCAN_NAME, self.URL)

    def make_query(self):
        """Subclasses should implement this.  This will be called to get the
        datastore query; it should always return the same query."""

    def update_counter(self, counter, entity):
        """Subclasses should implement this.  This will be called once for
        each entity that matches the query; it should call increment() on
        the counter object for whatever accumulators it wants to increment."""


class CountPerson(CountBase):
    SCAN_NAME = 'person'
    URL = '/tasks/count/person'

    def make_query(self):
        return model.Person.all().filter('subdomain =', self.subdomain)

    def update_counter(self, counter, person):
        found = ''
        if person.latest_found is not None:
            found = person.latest_found and 'TRUE' or 'FALSE'

        counter.increment('all')
        counter.increment('original_domain=' + (person.original_domain or ''))
        counter.increment('sex=' + (person.sex or ''))
        counter.increment('home_country=' + (person.home_country or ''))
        counter.increment('photo=' + (person.photo_url and 'present' or ''))
        counter.increment('num_notes=%d' % len(person.get_notes()))
        counter.increment('status=' + (person.latest_status or ''))
        counter.increment('found=' + found)
        counter.increment(
            'linked_persons=%d' % len(person.get_linked_persons()))


class CountNote(CountBase):
    SCAN_NAME = 'note'
    URL = '/tasks/count/note'

    def make_query(self):
        return model.Note.all().filter('subdomain =', self.subdomain)

    def update_counter(self, counter, note):
        found = ''
        if note.found is not None:
            found = note.found and 'TRUE' or 'FALSE'

        counter.increment('all')
        counter.increment('status=' + (note.status or ''))
        counter.increment('original_domain=' + (note.original_domain or ''))
        counter.increment('found=' + found)
        if note.linked_person_record_id:
            counter.increment('linked_person')
        if note.last_known_location:
            counter.increment('last_known_location')


class AddReviewedProperty(CountBase):
    """Sets 'reviewed' to False on all notes that have no 'reviewed' property.
    This task is for migrating datastores that were created before the
    'reviewed' property existed; 'reviewed' has to be set to False so that
    the Notes will be indexed."""
    SCAN_NAME = 'unreview-note'
    URL = '/tasks/count/unreview_note'

    def make_query(self):
        return model.Note.all().filter('subdomain =', self.subdomain)

    def update_counter(self, counter, note):
        if not note.reviewed:
            note.reviewed = False
            note.put()


class UpdateStatus(CountBase):
    """This task looks for Person records with the status 'believed_dead',
    checks for the last non-hidden Note, and updates the status if necessary.
    This is designed specifically to address bogus 'believed_dead' notes that
    are flagged as spam.  (This is a cleanup task, not a counting task.)"""
    SCAN_NAME = 'update-status'
    URL = '/tasks/count/update_status'

    def make_query(self):
        return model.Person.all().filter('subdomain =', self.subdomain
                          ).filter('latest_status =', 'believed_dead')

    def update_counter(self, counter, person):
        status = None
        status_source_date = None
        for note in person.get_notes():
            if note.status and not note.hidden:
                status = note.status
                status_source_date = note.source_date
        if status != person.latest_status:
            person.latest_status = status
            person.latest_status_source_date = status_source_date
        person.put()


class Reindex(CountBase):
    """A handler for re-indexing Persons."""
    SCAN_NAME = 'reindex'
    URL = '/tasks/count/reindex'

    def make_query(self):
        return model.Person.all().filter('subdomain =', self.subdomain)

    def update_counter(self, counter, person):
        person.update_index(['old', 'new'])
        person.put()


if __name__ == '__main__':
    utils.run((CountPerson.URL, CountPerson),
              (CountNote.URL, CountNote),
              (DeleteExpired.URL, DeleteExpired),
              (DeleteOld.URL, DeleteOld),
              (UpdateStatus.URL, UpdateStatus),
              (Reindex.URL, Reindex))
