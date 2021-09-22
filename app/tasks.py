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

import calendar
import copy
import datetime
import logging
import time
import StringIO

from google.appengine import runtime
from google.appengine.api import datastore_errors
from google.appengine.api import quota
from google.appengine.api import taskqueue
from google.appengine.ext import db

import cloud_storage
import config
import const
import model
import photo
import pfif
import record_writer
import utils


CPU_MEGACYCLES_PER_REQUEST = 1000
FETCH_LIMIT = 100
PFIF = pfif.PFIF_VERSIONS[pfif.PFIF_DEFAULT_VERSION]


class CleanUpInTestMode(utils.BaseHandler):
    """If the repository is in "test mode", this task deletes all entries older
    than DELETION_AGE_SECONDS (defined below), regardless of their actual
    expiration specification.

    We delete entries quickly so that most of the test data does not persist in
    real mode, and to reduce the effect of spam.
    """
    repo_required = False
    ACTION = 'tasks/clean_up_in_test_mode'

    # App Engine issues HTTP requests to tasks.
    https_required = False

    # Entries older than this age in seconds are deleted in test mode.
    #
    # If you are maintaining a single repository and switching it between test
    # mode (for drills) and real mode (for real crises), you should be sure to
    # switch to real mode within DELETION_AGE_SECONDS after a real crisis
    # occurs, because:
    # - When the crisis happens, the users may be confused and enter real
    #   information on the repository, even though it's still in test mode.
    #   (All pages show "test mode" message, but some users may be still
    #   confused.)
    # - If we fail to make the switch in DELETION_AGE_SECONDS, such real
    #   entries are deleted.
    # - If we make the switch in DELETION_AGE_SECONDS, such entries are not
    #   deleted, and handled as a part of real mode data.
    DELETION_AGE_SECONDS = 24 * 3600

    def __init__(self, request, response, env):
        utils.BaseHandler.__init__(self, request, response, env)
        self.__listener = None

    def task_name(self):
        return 'clean-up-in-test-mode'

    def schedule_next_task(self, cursor, utcnow):
        """Schedule the next task for to carry on with this query.
        """
        self.add_task_for_repo(
                self.repo,
                self.task_name(),
                self.ACTION,
                utcnow=str(calendar.timegm(utcnow.utctimetuple())),
                cursor=cursor,
                queue_name='clean_up_in_test_mode')

    def in_test_mode(self, repo):
        """Returns True if the repository is in test mode."""
        return config.get('test_mode', repo=repo)

    def get(self):
        if self.repo:
            # To reuse the cursor from the previous task, we need to apply
            # exactly the same filter. So we use utcnow previously used
            # instead of the current time.
            utcnow = self.params.utcnow or utils.get_utcnow()
            max_entry_date = (
                    utcnow -
                    datetime.timedelta(
                            seconds=CleanUpInTestMode.DELETION_AGE_SECONDS))
            query = model.Person.all_in_repo(self.repo)
            query.filter('entry_date <=', max_entry_date)
            if self.params.cursor:
                query.with_cursor(self.params.cursor)
            cursor = self.params.cursor
            # Uses query.get() instead of "for person in query".
            # If we use for-loop, query.cursor() points to an unexpected
            # position.
            person = query.get()
            # When the repository is no longer in test mode, aborts the
            # deletion.
            try:
                while person and self.in_test_mode(self.repo):
                    if self.__listener:
                        self.__listener.before_deletion(person.key())
                    person.delete_related_entities(delete_self=True)
                    cursor = query.cursor()
                    person = query.get()
            except runtime.DeadlineExceededError:
                self.schedule_next_task(cursor, utcnow)
            except datastore_errors.Timeout:
                # This exception is sometimes raised, maybe when the query
                # object live too long?
                self.schedule_next_task(cursor, utcnow)
                
        else:
            for repo in model.Repo.list():
                if self.in_test_mode(repo):
                    self.add_task_for_repo(repo, self.task_name(), self.ACTION)

    def set_listener(self, listener):
        self.__listener = listener


def run_count(make_query, update_counter, counter):
    """Scans the entities matching a query up to FETCH_LIMIT.
    
    Returns False if we finished counting all entries."""
    # Get the next batch of entities.
    query = make_query()
    if counter.last_key:
        query = query.filter('__key__ >', db.Key(counter.last_key))
    entities = query.order('__key__').fetch(FETCH_LIMIT)
    if not entities:
        counter.last_key = ''
        return False

    # Pass the entities to the counting function.
    for entity in entities:
        update_counter(counter, entity)

    # Remember where we left off.
    counter.last_key = str(entities[-1].key())
    return True


class CountBase(utils.BaseHandler):
    """A base handler for counting tasks.  Making a request to this handler
    without a specified repo will start tasks for all repositories in parallel.
    Each subclass of this class handles one scan through the datastore."""
    repo_required = False  # can run without a repo

    SCAN_NAME = ''  # Each subclass should choose a unique scan_name.
    ACTION = ''  # Each subclass should set the action path that it handles.

    # App Engine issues HTTP requests to tasks.
    https_required = False

    def get(self):
        if self.repo:  # Do some counting.
            try:
                counter = model.Counter.get_unfinished_or_create(
                    self.repo, self.SCAN_NAME)
                entities_remaining = True
                batches_done = 0
                while entities_remaining and batches_done < 20:
                    # Batch the db updates.
                    for _ in xrange(100):
                        entities_remaining = run_count(
                            self.make_query, self.update_counter, counter)
                        if not entities_remaining:
                            break
                    # And put the updates at once.
                    counter.put()
                    batches_done += 1
                self.add_task_for_repo(self.repo, self.SCAN_NAME, self.ACTION)
                return
            except runtime.DeadlineExceededError:
                # Continue counting in another task.
                self.add_task_for_repo(self.repo, self.SCAN_NAME, self.ACTION)
        else:  # Launch counting tasks for all repositories.
            for repo in model.Repo.list():
                self.add_task_for_repo(repo, self.SCAN_NAME, self.ACTION)

    def make_query(self):
        """Subclasses should implement this.  This will be called to get the
        datastore query; it should always return the same query."""

    def update_counter(self, counter, entity):
        """Subclasses should implement this.  This will be called once for
        each entity that matches the query; it should call increment() on
        the counter object for whatever accumulators it wants to increment."""


class CountPerson(CountBase):
    SCAN_NAME = 'person'
    ACTION = 'tasks/count/person'

    def make_query(self):
        return model.Person.all().filter('repo =', self.repo)

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
        if person.author_email:  # author e-mail address present?
            counter.increment('author_email')
        if person.author_phone:  # author phone number present?
            counter.increment('author_phone')
        counter.increment(
            'linked_persons=%d' % len(person.get_linked_persons()))


class CountNote(CountBase):
    SCAN_NAME = 'note'
    ACTION = 'tasks/count/note'

    def make_query(self):
        return model.Note.all().filter('repo =', self.repo)

    def update_counter(self, counter, note):
        author_made_contact = ''
        if note.author_made_contact is not None:
            author_made_contact = note.author_made_contact and 'TRUE' or 'FALSE'

        counter.increment('all')
        counter.increment('status=' + (note.status or ''))
        counter.increment('original_domain=' + (note.original_domain or ''))
        counter.increment('author_made_contact=' + author_made_contact)
        if note.last_known_location:  # last known location specified?
            counter.increment('last_known_location')
        if note.author_email:  # author e-mail address present?
            counter.increment('author_email')
        if note.author_phone:  # author phone number present?
            counter.increment('author_phone')
        if note.linked_person_record_id:  # linked to another person?
            counter.increment('linked_person')


class AddReviewedProperty(CountBase):
    """Sets 'reviewed' to False on all notes that have no 'reviewed' property.
    This task is for migrating datastores that were created before the
    'reviewed' property existed; 'reviewed' has to be set to False so that
    the Notes will be indexed."""
    SCAN_NAME = 'unreview-note'
    ACTION = 'tasks/count/unreview_note'

    def make_query(self):
        return model.Note.all().filter('repo =', self.repo)

    def update_counter(self, counter, note):
        if not note.reviewed:
            note.reviewed = False
            note.put()


class UpdateDeadStatus(CountBase):
    """This task looks for Person records with the status 'believed_dead',
    checks for the last non-hidden Note, and updates the status if necessary.
    This is designed specifically to address bogus 'believed_dead' notes that
    are flagged as spam.  (This is a cleanup task, not a counting task.)"""
    SCAN_NAME = 'update-dead-status'
    ACTION = 'tasks/count/update_dead_status'

    def make_query(self):
        return model.Person.all().filter('repo =', self.repo
                          ).filter('latest_status =', 'believed_dead')

    def update_counter(self, counter, person):
        person.update_latest_status()


class UpdateStatus(CountBase):
    """This task scans Person records, looks for the last non-hidden Note, and
    updates latest_status.  (This is a cleanup task, not a counting task.)"""
    SCAN_NAME = 'update-status'
    ACTION = 'tasks/count/update_status'

    def make_query(self):
        return model.Person.all().filter('repo =', self.repo)

    def update_counter(self, counter, person):
        person.update_latest_status()


class Reindex(CountBase):
    """A handler for re-indexing Persons."""
    SCAN_NAME = 'reindex'
    ACTION = 'tasks/count/reindex'

    def make_query(self):
        return model.Person.all().filter('repo =', self.repo)

    def update_counter(self, counter, person):
        person.update_index(['old', 'new'])
        person.put()


class NotifyManyUnreviewedNotes(utils.BaseHandler):
    """This task sends email notification when the number of unreviewed notes
    exceeds threshold.
    """
    repo_required = False  # can run without a repo
    ACTION = 'tasks/notify_many_unreviewed_notes'

    # App Engine issues HTTP requests to tasks.
    https_required = False

    def task_name(self):
        return 'notify-bad-review-status'

    def get(self):
        if self.repo:
            try:
                count_of_unreviewed_notes = (
                    model.Note.get_unreviewed_notes_count(self.repo))
                self._maybe_notify(count_of_unreviewed_notes)
            except runtime.DeadlineExceededError:
                logging.info("DeadlineExceededError occurs")
                self.add_task_for_repo(
                    self.repo, self.task_name(), self.ACTION)
            except datastore_errors.Timeout:
                logging.info("Timeout occurs in datastore")
                self.add_task_for_repo(
                    self.repo, self.task_name(), self.ACTION)
        else:
            for repo in model.Repo.list():
                self.add_task_for_repo(
                    repo, self.task_name(), self.ACTION)

    def _subject(self):
        return "Please review your notes in %(repo_name)s" % {
            "repo_name": self.env.repo,
        }

    def _body(self, count_of_unreviewed_notes):
        return "%(repo_name)s has %(num_unreviewed)s unreviewed notes." % {
            "repo_name": self.env.repo,
            "num_unreviewed": count_of_unreviewed_notes,
        }

    def _maybe_notify(self, count_of_unreviewed_notes):
        # TODO(yaboo@): Response should be modified
        if self._should_notify(count_of_unreviewed_notes):
            self.send_mail(self.config.get('notification_email'),
                           subject=self._subject(),
                           body=self._body(count_of_unreviewed_notes))

    def _should_notify(self, count_of_unreviewed_notes):
        if not self.config.get('notification_email'):
            return False

        return  count_of_unreviewed_notes > self.config.get(
                'unreviewed_notes_threshold')


class ThumbnailPreparer(utils.BaseHandler):
    """A class to run the thumbnail preparation job (for uploaded photos)."""

    repo_required = False
    ACTION = 'tasks/thumbnail_preparer'

    # App Engine issues HTTP requests to tasks.
    https_required = False

    def get(self):
        # We don't retry this task automatically, because it's looking for
        # everything that doesn't already have a thumbnail every time --
        # anything that doesn't get done now will be retried anyway on the next
        # iteration of the cron job.
        if self.repo:
            for p in (model.Photo.all()
                      .filter('thumbnail_data =', None)
                      .filter('repo =', self.repo)):
                photo.set_thumbnail(p)
        else:
            for repo in model.Repo.list():
                self.add_task_for_repo(repo, 'prepare-thumbnails', self.ACTION)


class DumpCSV(utils.BaseHandler):
    """Dumps a CSV file containing all the records in each repository to Google
    Cloud Storage.
    
    People with BULK_READ API access can download the CSV file.
    
    Currently the CSV file only contains person records.
    
    This task requires special setup to run on a dev app server. See the
    docstring of cloud_storage.CloudStorage class for instruction.
    """
    # TODO(gimite): Include note records in the CSV file.

    repo_required = False
    ACTION = 'tasks/dump_csv'

    # App Engine issues HTTP requests to tasks.
    https_required = False

    # Lifetime of a single task is 10 min. It stops fetching and starts
    # uploading after 4 min, assuming uploading takes similar time as
    # fetching.
    MAX_FETCH_TIME = datetime.timedelta(minutes=4)
    
    def __init__(self, *args, **kwargs):
        super(DumpCSV, self).__init__(*args, **kwargs)
        self.storage = cloud_storage.CloudStorage()

    def task_name(self):
        return 'dump-csv'

    def schedule_next_task(self, cursor, timestamp):
        """Schedule the next task for to carry on with this query.
        """
        self.add_task_for_repo(
                self.repo,
                self.task_name(),
                self.ACTION,
                cursor=cursor,
                timestamp=str(calendar.timegm(timestamp.utctimetuple())))

    def get(self):
        if self.repo:
            self.run_task_for_repo(self.repo)
        else:
            # Sets lifetime of objects in Google Cloud Storage to 2 days. This
            # cleans up old CSV files, while it makes sure that it doesn't
            # delete CSV files users are currently downloading. Note that CSV
            # files are updated every 24 hours.
            #
            # The lifetime is applied globally for all objects in the bucket.
            # This is OK because Cloud Storage is only used for CSV files for
            # now. It may need a way to control lifetime per object (see the
            # docstring of cloud_storage.CloudStorage) if it starts using
            # Cloud Storage for other purposes.
            #
            # It is enough to call this only once for the bucket, but here is
            # just a convenient place to call it.
            self.storage.set_objects_lifetime(lifetime_days=2)

            for repo in model.Repo.list_active():
                self.add_task_for_repo(repo, self.task_name(), self.ACTION)

    def run_task_for_repo(self, repo):
        start_time = utils.get_utcnow()
        timestamp = self.params.timestamp or start_time
        is_first = not self.params.cursor

        query = model.Person.all_in_repo(repo).order('entry_date')
        if self.params.cursor:
            query.with_cursor(self.params.cursor)

        filtered_writer = record_writer.PersonWithNoteCsvWriter(
            StringIO.StringIO(), write_header=is_first)
        full_writer = record_writer.PersonWithNoteCsvWriter(
            StringIO.StringIO(), write_header=is_first)

        has_data = False
        scan_completed = False
        while True:
            persons = query.fetch(limit=FETCH_LIMIT)
            if persons:
                has_data = True
            else:
                scan_completed = True
                break

            full_records = self.get_person_records_with_notes(repo, persons)
            full_writer.write(full_records)

            filtered_records = copy.deepcopy(full_records)
            utils.filter_sensitive_fields(filtered_records)
            filtered_writer.write(filtered_records)

            if utils.get_utcnow() >= start_time + self.MAX_FETCH_TIME:
                break
            query.with_cursor(query.cursor())

        for kind, writer in [
                ('filtered', filtered_writer), ('full', full_writer)]:
            base_name = '%s-persons-%s-%s' % (
                repo, kind, timestamp.strftime('%Y-%m-%d-%H%M%S'))
            final_csv_name = '%s.csv' % base_name
            temp_csv_name = '%s.temp.csv' % base_name

            if is_first:
                self.storage.insert_object(
                    final_csv_name, 'text/csv', writer.io.getvalue())
            elif has_data:
                # Creates a temporary CSV file with new records, and append it to
                # the final CSV file.
                self.storage.insert_object(
                    temp_csv_name, 'text/csv', writer.io.getvalue())
                self.storage.compose_objects(
                    [final_csv_name, temp_csv_name], final_csv_name, 'text/csv')

            if scan_completed:
                key = 'latest_%s_csv_object_name' % kind
                config.set_for_repo(repo, **{key: final_csv_name})

        if not scan_completed:
            self.schedule_next_task(query.cursor(), timestamp)

    def get_person_records_with_notes(self, repo, persons):
        records = []
        for person in persons:
            person_record = PFIF.person_to_dict(person)
            notes = person.get_notes()
            if notes:
                for note in notes:
                    note_record = PFIF.note_to_dict(note)
                    if note.hidden:
                        note_record['text'] = ''
                    records.append(utils.join_person_and_note_record(
                        person_record, note_record))
            else:
                # Add a row with blank note fields.
                # Uses join_person_and_note_record() here too to prefix field
                # names consistently.
                records.append(utils.join_person_and_note_record(
                    person_record, None))
        return records
