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

import delete
import hashlib
import logging
import time
import urllib
from utils import *
from model import *
from google.appengine.api import taskqueue
from google.appengine.api import quota
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

COUNT_FETCH_LIMIT = 100
REINDEX_FETCH_LIMIT = 10
MAX_PUT_RETRIES = 3


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
        entities = query.order('__key__').fetch(COUNT_FETCH_LIMIT)
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

    SCAN_NAME = ''  # Each subclass should choose a unique scan_name.
    URL = ''  # Each subclass should set the URL path that it handles. 

    def get(self):
        if self.subdomain:  # Do some counting.
            counter = Counter.get_unfinished_or_create(
                self.subdomain, self.SCAN_NAME)
            run_count(self.make_query, self.update_counter, counter, 1000)
            counter.put()
            if counter.last_key:  # Continue counting in another task.
                self.add_task(self.subdomain)
        else:  # Launch counting tasks for all subdomains.
            for subdomain in Subdomain.list():
                self.add_task(subdomain)

    def add_task(self, subdomain):
        """Queues up a task for an individual subdomain."""  
        task_name = '%s-%s-%s' % (
            subdomain, self.SCAN_NAME, int(time.time()*1000))
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
    SCAN_NAME = 'note'
    URL = '/tasks/count/note'

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


class UpdateStatus(CountBase):
    """This task looks for Person records with the status 'believed_dead',
    checks for the last non-hidden Note, and updates the status if necessary.
    This is designed specifically to address bogus 'believed_dead' notes that
    are flagged as spam.  (This is a cleanup task, not a counting task.)"""
    SCAN_NAME = 'update-status'
    URL = '/tasks/count/update_status'

    def make_query(self):
        return Person.all().filter('subdomain =', self.subdomain
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


def run_reindexing(subdomain, cursor, cpu_megacycles):
    """Reindex entries for a limited amount of CPU time."""
    processed = 0
    cpu_limit = quota.get_request_cpu_usage() + cpu_megacycles
    while quota.get_request_cpu_usage() < cpu_limit:
        query = Person.all().filter('subdomain =', subdomain)
        query = query.order('__key__')
        if cursor:
            query = query.with_cursor(cursor)
        persons = query.fetch(REINDEX_FETCH_LIMIT)
        cursor = query.cursor()
        if len(persons) == 0:
            # Finished.
            break
        for person in persons:
            if quota.get_request_cpu_usage() > cpu_limit:
                break
            person.update_index(['old', 'new'])
            success = False
            # Try putting to datastore up to MAX_PUT_RETRIES times.
            for i in range(MAX_PUT_RETRIES):
                try:
                    db.put(person)
                    success = True
                    break
                except:
                    # Failed, retry.
                    pass
            if not success:
                # All attempts failed. Do not continue.
                break
            processed += 1
    return (cursor, processed)


class Reindex(Handler):
    """A handler for re-indexing."""
    subdomain_required = False  # Run at the root domain, not a subdomain.

    def get(self):
        if self.subdomain:  # Do re-indexing.
            cursor = self.request.get('cursor', '')
            offset = int(self.request.get('offset', '0'))
            logging.info('Reindexing %s from offset %d...' %
                         (self.subdomain, offset))
            (cursor, processed) = run_reindexing(self.subdomain, cursor, 1000)
            if processed > 0:  # Continue re-indexing in another task.
                logging.info('Processed entry %d..%d in %s.' %
                             (offset, offset+processed-1, self.subdomain))
                self.add_task(self.subdomain, cursor, offset + processed)
            else:
                logging.info('Finished all %d entries in %s.' %
                             (offset, self.subdomain))
        else:  # Launch counting tasks for all subdomains.
            for subdomain in Subdomain.list():
                self.add_task(subdomain, '', 0)

    def add_task(self, subdomain, cursor, offset):
        """Queues up a task for an individual subdomain."""
        task_name = ('%s-reindexer-offset%d-%d' %
                     (subdomain, offset, time.time()))
        taskqueue.add(name=task_name, method='GET', url='/tasks/reindex',
                      params={'subdomain': subdomain,
                              'cursor': cursor,
                              'offset': str(offset)})


# Form and task to fill in Person#alternate_first_names and
# Person#alternate_last_names using tab-separated text file.
# TODO(ryok): move non-task code to a separate file.

class UploadAlternateFormHandler(Handler):
    subdomain_required = False
    def get(self):
        upload_url = blobstore.create_upload_url('/tasks/upload_alternate')
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write('<html><body>')
        self.response.out.write(
            '<form action="%s" method="POST" enctype="multipart/form-data">'
            % upload_url)
        self.response.out.write(
            """Upload File: <input type="file" name="file"><br>
            <input type="submit" name="submit" value="Submit">
            </form></body></html>""")


class UploadAlternateHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        upload_files = self.get_uploads('file')
        # I couldn't find a way to pass this from somewhere. Other values in the
        # form at /tasks/upload_alternate_form is not inherited.
        # Hard-coded to 'japan' for now.
        subdomain = 'japan'
        blob_info = upload_files[0]
        logging.info('subdomain=%s, blob_key=%s' % (subdomain, blob_info.key()))
        self.redirect('/tasks/start_fill_alternate?subdomain=%s&blob_key=%s' %
            (urllib.quote(subdomain),
             urllib.quote(str(blob_info.key()))))


class StartFillAlternateHandler(Handler):
    def get(self):
        blob_key = self.request.get('blob_key')
        add_fill_alternate_task(self.subdomain, blob_key, 0)
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write('Task started. See AppEngine log for progress.')


def run_fill_alternate(subdomain, blob_key, offset, cpu_megacycles):
    """Fill alternates for a limited amount of CPU time."""
    processed = 0
    cpu_limit = quota.get_request_cpu_usage() + cpu_megacycles
    reader = blobstore.BlobReader(blob_key)
    reader.seek(offset)
    while quota.get_request_cpu_usage() < cpu_limit:
        # Use this for testing with dev_appserver.py.
        # dev_appserver doesn't support quota.get_request_cpu_usage().
        if reader.tell() >= offset + 1024 * 1024 * 10: break
        line = reader.readline()
        if not line: break
        line = line.rstrip("\n")
        if not line: break
        row = line.split("\t")
        person = Person.get(subdomain, row[4])
        if not person:
            logging.info("%s not found" % row[4])
            continue
        if not person.alternate_first_names:
            person.alternate_first_names = unicode(row[0], 'utf-8')
        if not person.alternate_last_names:
            person.alternate_last_names = unicode(row[1], 'utf-8')
        person.put()
    return reader.tell() - offset


def add_fill_alternate_task(subdomain, blob_key, offset):
    """Queues up a task"""
    task_name = ('%s-%s-alternate-filler-offset%d-%d' %
                 (subdomain, hashlib.sha224(blob_key).hexdigest(),
                  offset, time.time()))
    taskqueue.add(name=task_name,
                  method='GET',
                  url='/tasks/fill_alternate',
                  params={'subdomain': subdomain,
                          'blob_key': blob_key,
                          'offset': str(offset)})


class FillAlternate(Handler):
    def get(self):
        blob_key = self.request.get('blob_key')
        offset = int(self.request.get('offset', '0'))
        logging.info('FillAlternate from %s %s offset %d...' %
                     (self.subdomain, blob_key, offset))
        processed = run_fill_alternate(self.subdomain, blob_key, offset, 1000)
        if processed > 0:  # Continue re-indexing in another task.
            logging.info('Processed bytes %d..%d in %s %s.' %
                         (offset,
                          offset + processed - 1,
                          self.subdomain, blob_key))
            add_fill_alternate_task(
                self.subdomain, blob_key, offset + processed)
        else:
            logging.info('Finished all %d bytes in %s %s.' %
                         (offset, self.subdomain, blob_key))


if __name__ == '__main__':
    run((CountPerson.URL, CountPerson),
        (CountNote.URL, CountNote),
        (UpdateStatus.URL, UpdateStatus),
        ('/tasks/clear_tombstones', ClearTombstones),
        ('/tasks/upload_alternate_form', UploadAlternateFormHandler),
        ('/tasks/upload_alternate', UploadAlternateHandler),
        ('/tasks/start_fill_alternate', StartFillAlternateHandler),
        ('/tasks/fill_alternate', FillAlternate),
        ('/tasks/reindex', Reindex))
