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
import delete
import sys
from utils import *
from model import *
from google.appengine.api import quota
from google.appengine.api import taskqueue

FETCH_LIMIT = 100

class DeleteExpired(Handler):
    """Scan the Person table looking for expired records to delete.

    Records whose expiration date has passed more than the 
    grace period will be permanently deleted.
    """
    subdomain_required = False
    
    # 3 days grace from expiration to deletion.
    expiration_grace = datetime.timedelta(3,0,0) 

    def get(self):
        query = Person.get_past_due()
        for person in query:
            if get_utcnow() - person.expiry_date > self.expiration_grace: 
                db.delete(person.get_notes())
                photo = person.get_photo()
                if photo:
                    db.delete(photo)
                db.delete(person)
            elif not person.is_expired:
                person.mark_for_delete()

class ClearTombstones(Handler):
    """Scans the tombstone table, deleting each record and associated entities
    if their TTL has expired. The TTL is declared in app/delete.py as
    TOMBSTONE_TTL_DAYS."""
    subdomain_required = False # Run at the root domain, not a subdomain.

    def get(self):
        def get_notes_by_person_tombstone(tombstone, limit=200):
            return NoteTombstone.get_by_tombstone_record_id(
                tombstone.subdomain, tombstone.record_id, limit=limit)
        # Only delete tombstones more than 3 days old
        time_boundary = datetime.datetime.now() - \
            timedelta(days=delete.TOMBSTONE_TTL_DAYS)
        query = PersonTombstone.all().filter('timestamp <', time_boundary)
        for tombstone in query:
            notes = get_notes_by_person_tombstone(tombstone)
            while notes:
                db.delete(notes)
                notes = get_notes_by_person_tombstone(tombstone)
            if (hasattr(tombstone, 'photo_url') and
                tombstone.photo_url[:10] == '/photo?id='):
                photo = Photo.get_by_id(
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


class CountBase(Handler):
    """A base handler for counting tasks.  Making a request to this handler
    without a subdomain will start tasks for all subdomains in parallel.
    Each subclass of this class handles one scan through the datastore."""
    subdomain_required = False  # Run at the root domain, not a subdomain.
    scan_name = ''  # Each subclass should choose a unique scan_name.

    def get(self):
        if self.subdomain:  # Do some counting.
            counter = Counter.get_unfinished_or_create(
                self.subdomain, self.scan_name)
            run_count(self.make_query, self.update_counter, counter, 1000)
            counter.put()
        else:  # Launch counting tasks for all subdomains.
            for subdomain in Subdomain.all():
                sd_name = subdomain.key().name()
                taskqueue.add(name=self.scan_name + '-' + sd_name,
                              method='GET', url=self.url,
                              params={'subdomain': sd_name})

    def make_query(self):
        """Subclasses should implement this.  This will be called to get the
        datastore query; it should always return the same query."""

    def update_counter(self, counter, entity):
        """Subclasses should implement this.  This will be called once for
        each entity that matches the query; it should call increment() on
        the counter object for whatever accumulators it wants to increment."""


class CountPerson(CountBase):
    scan_name = 'person'
    url = '/tasks/count/person'
    def make_query(self):
        return Person.all().filter('subdomain =', self.subdomain)

    def update_counter(self, counter, person):
        found = ''
        if person.latest_found is not None:
            found = person.latest_found and 'TRUE' or 'FALSE'

        counter.increment('all')
        counter.increment('status=' + (person.latest_status or ''))
        counter.increment('found=' + found)
        counter.increment('sex=' + (person.sex or ''))
        counter.increment('original_domain=' + (person.original_domain or ''))
        counter.increment('source_name=' + (person.source_name or ''))
        counter.increment('photo=' + (person.photo_url and 'present' or ''))


class CountNote(CountBase):
    scan_name = 'note'
    url = '/tasks/count/note'

    def make_query(self):
        return Note.all().filter('subdomain =', self.subdomain)

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
    run((CountPerson.url, CountPerson),
        (CountNote.url, CountNote),
        ('/tasks/clear_tombstones', ClearTombstones),
        ('/tasks/delete_expired', DeleteExpired))
