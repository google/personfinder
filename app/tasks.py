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

from utils import *
from model import *
from google.appengine.api import quota
from google.appengine.api.labs import taskqueue

FETCH_LIMIT = 100


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
            for subdomain in Subdomain.list():
                taskqueue.add(name=scan_name + '-' + subdomain,
                              method='GET', url=self.request.url,
                              params={'subdomain': subdomain})

    def make_query(self):
        """Subclasses should implement this.  This will be called to get the
        datastore query; it should always return the same query."""

    def update_counter(self, counter, entity):
        """Subclasses should implement this.  This will be called once for
        each entity that matches the query; it should call increment() on
        the counter object for whatever accumulators it wants to increment."""


class CountPerson(CountBase):
    scan_name = 'person'

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
    run(('/tasks/count/person', CountPerson),
        ('/tasks/count/note', CountNote))
