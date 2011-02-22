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

from datetime import timedelta
import time

from google.appengine.api import quota
from google.appengine.api import taskqueue
from google.appengine.ext import db

import delete
import model
import utils

FETCH_LIMIT = 100


class ClearTombstones(utils.Handler):
    """Scans the tombstone table, deleting each record and associated entities
    if their TTL has expired. The TTL is declared in app/delete.py as
    TOMBSTONE_TTL_DAYS."""
    subdomain_required = False # Run at the root domain, not a subdomain.

    def get(self):
        def get_notes_by_person_tombstone(tombstone, limit=200):
            return model.NoteTombstone.get_by_tombstone_record_id(
                tombstone.subdomain, tombstone.record_id, limit=limit)
        # Only delete tombstones more than 3 days old
        time_boundary = utils.get_utcnow() - \
            timedelta(days=delete.TOMBSTONE_TTL_DAYS)
        query = model.PersonTombstone.all().filter('timestamp <', time_boundary)
        for tombstone in query:
            notes = get_notes_by_person_tombstone(tombstone)
            while notes:
                db.delete(notes)
                notes = get_notes_by_person_tombstone(tombstone)
            if (hasattr(tombstone, 'photo_url') and
                tombstone.photo_url[:10] == '/photo?id='):
                photo = model.Photo.get_by_id(
                    int(tombstone.photo_url.split('=', 1)[1]))
                if photo:
                    db.delete(photo)
            db.delete(tombstone)


def run_count(make_query, update_counter, counter, cpu_megacycles):
    """Scans the entities matching a query for a limited amount of CPU time."""
    cpu_limit = quota.get_request_cpu_usage() + cpu_megacycles
    while quota.get_request_cpu_usage() < cpu_limit:
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
            run_count(self.make_query, self.update_counter, counter, 1000)
            counter.put()
            if counter.last_key:  # Continue counting in another task.
                self.add_task(self.subdomain)
        else:  # Launch counting tasks for all subdomains.
            for subdomain in model.Subdomain.list():
                self.add_task(subdomain)

    def add_task(self, subdomain):
        """Queues up a task for an individual subdomain."""  
        timestamp = utils.get_utcnow().strftime('%Y%m%d-%H%M%S')
        task_name = '%s-%s-%s' % (subdomain, self.SCAN_NAME, timestamp)
        taskqueue.add(name=task_name, method='GET', url=self.URL,
                      params={'subdomain': subdomain})

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
        counter.increment('source_name=' + (person.source_name or ''))
        counter.increment('sex=' + (person.sex or ''))
        counter.increment('home_country=' + (person.home_country or ''))
        counter.increment('photo=' + (person.photo_url and 'present' or ''))
        counter.increment('num_notes=%d' % len(person.get_notes()))
        counter.increment('status=' + (person.latest_status or ''))
        counter.increment('found=' + found)


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
        counter.increment('found=' + found)
        counter.increment(
            'location=' + (note.last_known_location and 'present' or ''))


if __name__ == '__main__':
    utils.run((CountPerson.URL, CountPerson),
              (CountNote.URL, CountNote),
              ('/tasks/clear_tombstones', ClearTombstones))
