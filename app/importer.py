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

"""Support for importing records in batches, with error detection.

This module converts Python dictionaries into datastore entities.
The values of all dictionary fields are Unicode strings."""

__author__ = 'kpy@google.com (Ka-Ping Yee) and many other Googlers'

import datetime
import logging
import re
import sys

from google.appengine.api import datastore_errors

import subscribe
from model import *
from utils import validate_sex, validate_status, validate_approximate_date, \
                  validate_age, get_utcnow, get_full_name

DEFAULT_PUT_RETRIES = 3
MAX_PUT_BATCH = 100

def utf8_decoder(dict_reader):
    """Yields a dictionary where all string values are converted to Unicode.

    Args:
        dict_reader: An iterable that yields dictionaries with string values

    Yields:
        A dictionary with all string values converted to Unicode.
    """
    for record in dict_reader:
        for key in record:
            value = record[key]
            if isinstance(value, str):
                record[key] = value.decode('utf-8')
        yield record

def put_batch(batch, retries=DEFAULT_PUT_RETRIES):
    for attempt in range(retries):
        try:
            db.put(batch)
            logging.info('Imported records: %d' % len(batch))
            return len(batch)
        except:
            type, value, traceback = sys.exc_info()
            logging.warn('Retrying batch: %s' % value)
    return 0

date_re = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z$')

def strip(string_or_none):
    if not string_or_none:
        return ''
    return string_or_none.strip() or ''

def validate_datetime(datetime_or_datestring):
    if isinstance(datetime_or_datestring, datetime.datetime):
        return datetime_or_datestring
    if not datetime_or_datestring:
        return None  # A missing value is okay.
    match = date_re.match(datetime_or_datestring)
    if match:
        return datetime.datetime(*map(int, match.groups()))
    raise ValueError('Bad datetime: %r' % datetime_or_datestring)

def validate_boolean(string):
    if not string:
        return None  # A missing value is okay.
    return (isinstance(string, basestring) and
            string.strip().lower() in ['true', 'yes', 'y', '1'])

def create_person(repo, fields):
    """Creates a Person entity in the given repository with the given field
    values.  If 'fields' contains a 'person_record_id', calling put() on the
    resulting entity will overwrite any existing (original or clone) record
    with the same person_record_id.  Otherwise, a new original person record is
    created in the given repository."""
    person_fields = dict(
        entry_date=get_utcnow(),
        expiry_date=validate_datetime(fields.get('expiry_date')),
        author_name=strip(fields.get('author_name')),
        author_email=strip(fields.get('author_email')),
        author_phone=strip(fields.get('author_phone')),
        source_name=strip(fields.get('source_name')),
        source_url=strip(fields.get('source_url')),
        source_date=validate_datetime(fields.get('source_date')),
        full_name=strip(fields.get('full_name')),
        given_name=strip(fields.get('given_name')),
        family_name=strip(fields.get('family_name')),
        alternate_names=strip(fields.get('alternate_names')),
        description=strip(fields.get('description')),
        sex=validate_sex(fields.get('sex')),
        date_of_birth=validate_approximate_date(fields.get('date_of_birth')),
        age=validate_age(fields.get('age')),
        home_street=strip(fields.get('home_street')),
        home_neighborhood=strip(fields.get('home_neighborhood')),
        home_city=strip(fields.get('home_city')),
        home_state=strip(fields.get('home_state')),
        home_postal_code=strip(fields.get('home_postal_code')),
        home_country=strip(fields.get('home_country')),
        photo_url=strip(fields.get('photo_url')),
        profile_urls=strip(fields.get('profile_urls')),
    )

    # For PFIF 1.3 or older, populate full_name (it was an optional field
    # before), using given_name and family_name if it is empty.
    if not person_fields['full_name'].strip():
        person_fields['full_name'] = get_full_name(
            person_fields['given_name'],
            person_fields['family_name'],
            config.Configuration(repo))
    # TODO(liuhsinwen): Separate existed and non-existed record id and
    # increment person counter for new records
    record_id = strip(fields.get('person_record_id'))
    if record_id:  # create a record that might overwrite an existing one
        if is_clone(repo, record_id):
            return Person.create_clone(repo, record_id, **person_fields)
        else:
            return Person.create_original_with_record_id(
                repo, record_id, **person_fields)
    else:  # create a new original record
        # TODO(liuhsinwen): fix performance problem by incrementing the counter
        # by the number of upload records
        # UsageCounter.increment_person_counter(repo)
        return Person.create_original(repo, **person_fields)

def create_note(repo, fields):
    """Creates a Note entity in the given repository with the given field
    values.  If 'fields' contains a 'note_record_id', calling put() on the
    resulting entity will overwrite any existing (original or clone) record
    with the same note_record_id.  Otherwise, a new original note record is
    created in the given repository."""
    assert strip(fields.get('person_record_id')), 'person_record_id is required'
    assert strip(fields.get('source_date')), 'source_date is required'
    note_fields = dict(
        person_record_id=strip(fields['person_record_id']),
        linked_person_record_id=strip(fields.get('linked_person_record_id')),
        author_name=strip(fields.get('author_name')),
        author_email=strip(fields.get('author_email')),
        author_phone=strip(fields.get('author_phone')),
        source_date=validate_datetime(fields.get('source_date')),
        status=validate_status(fields.get('status')),
        author_made_contact=validate_boolean(fields.get('author_made_contact')),
        email_of_found_person=strip(fields.get('email_of_found_person')),
        phone_of_found_person=strip(fields.get('phone_of_found_person')),
        last_known_location=strip(fields.get('last_known_location')),
        text=fields.get('text'),
        photo_url=fields.get('photo_url'),
        entry_date=get_utcnow(),
    )
    # TODO(liuhsinwen): Separate existed and non-existed record id and
    # increment note counter for new records
    record_id = strip(fields.get('note_record_id'))
    if record_id:  # create a record that might overwrite an existing one
        if is_clone(repo, record_id):
            return Note.create_clone(repo, record_id, **note_fields)
        else:
            return Note.create_original_with_record_id(
                repo, record_id, **note_fields)
    else:  # create a new original record
        # TODO(liuhsinwen): fix performance problem by incrementing the counter
        # by the number of upload notes
        # UsageCounter.increment_note_counter(repo)
        return Note.create_original(repo, **note_fields)

def filter_new_notes(entities, repo):
    """Filter the notes which are new."""
    notes = []
    for entity in entities:
        # Send an an email notification for new notes only
        if isinstance(entity, Note):
            if not Note.get(repo, entity.get_note_record_id()):
                notes.append(entity)
    return notes


def send_notifications(handler, persons, notes):
    """For each note, send a notification to subscriber.

    Args:
       notes: List of notes for which to send notification.
       persons: Dictionary of persons impacted by the notes,
                indexed by person_record_id.
       handler: Handler used to send email notification.
    """
    for note in notes:
        person = persons[note.person_record_id]
        subscribe.send_notifications(handler, person, [note])


def notes_match(a, b):
    fields = ['person_record_id', 'author_name', 'author_email', 'author_phone',
              'source_date', 'status', 'author_made_contact',
              'email_of_found_person', 'phone_of_found_person',
              'last_known_location', 'text', 'photo_url']
    return [getattr(a, f) for f in fields] == [getattr(b, f) for f in fields]


def import_records(repo, domain, converter, records,
                   mark_notes_reviewed=False,
                   believed_dead_permission=False,
                   handler=None,
                   omit_duplicate_notes=False):
    """Convert and import a list of entries into a respository.

    Args:
        repo: Identifies the repository in which to store the records.
        domain: Accept only records that have this original domain.  Only one
            original domain may be imported at a time.
        converter: A function to transform a dictionary of fields to a
            datastore entity.  This function may throw an exception if there
            is anything wrong with the input fields and import_records will
            skip the bad record.  The key_name of the resulting datastore
            entity must begin with domain + '/', or the record will be skipped.
        records: A list of dictionaries representing the entries.
        mark_notes_reviewed: If true, mark the new notes as reviewed.
        believed_dead_permission: If true, allow importing notes with status
            as 'believed_dead'; otherwise skip the note and return an error.
        handler: Handler to use to send e-mail notification for notes.  If this
            is None, then we do not send e-mail.
        omit_duplicate_notes: If true, skip any Notes that are identical to
            existing Notes on the same Person.

    Returns:
        The number of passed-in records that were written (not counting other
        Person records that were updated because they have new Notes), a list
        of (error_message, record) pairs for the skipped records, and the
        number of records processed in total.
    """
    persons = {}  # Person entities to write
    # Note entries in the records (incliding ones skipped later) with their
    # original fields.
    input_notes_with_fields = []
    skipped = []  # entities skipped due to an error
    total = 0  # total number of entities for which conversion was attempted

    for fields in records:
        total += 1
        try:
            entity = converter(repo, fields)
        except (KeyError, ValueError, AssertionError,
                datastore_errors.BadValueError), e:
            skipped.append((e.__class__.__name__ + ': ' + str(e), fields))
            continue
        if entity.original_domain != domain:
            skipped.append(
                ('Not in authorized domain: %r' % entity.record_id, fields))
            continue
        if isinstance(entity, Person):
            entity.update_index(['old', 'new'])
            persons[entity.record_id] = entity
        if isinstance(entity, Note):
            input_notes_with_fields.append((entity, fields))

    # Note entities to write
    notes = {}
    # Updated Persons other than those being imported.
    #
    # We keep two dictionaries 'persons' and 'extra_persons', with disjoint
    # key sets: Person entities for the records passed in to import_records()
    # go in 'persons', and any other Person entities affected by the import go
    # in 'extra_persons'.  The two dictionaries are kept separate in order to
    # produce a count of records written that only counts 'persons'.
    extra_persons = {}

    for (note, fields) in input_notes_with_fields:
        if note.person_record_id in persons:
            # This Note belongs to a Person that is being imported.
            person = persons[note.person_record_id]
        elif note.person_record_id in extra_persons:
            # This Note belongs to some other Person that is not part of this
            # import and is already being updated due to another Note.
            person = extra_persons[note.person_record_id]
        else:
            # This Note belongs to some other Person that is not part of this
            # import and this is the first such Note in this import.
            person = Person.get(repo, note.person_record_id)

        if not person:
            skipped.append(
                ('There is no person record with the person_record_id %r'
                    % note.person_record_id,
                 fields))
            continue
        # Check whether reporting 'believed_dead' in note is permitted.
        if not believed_dead_permission and note.status == 'believed_dead':
            skipped.append(
                ('Not authorized to post notes with ' \
                 'the status \"believed_dead\"',
                 fields))
            continue
        # Check whether commenting is already disabled by record author.
        if person.notes_disabled:
            skipped.append(
                ('The author has disabled new commenting on this record',
                 fields))
            continue
        # Check whether the note is a duplicate.
        if omit_duplicate_notes:
            other_notes = Note.get_by_person_record_id(
                repo, note.person_record_id, filter_expired=False)
            if any(notes_match(note, other_note) for other_note in other_notes):
                skipped.append(
                    ('This is a duplicate of an existing note', fields))
                continue

        note.reviewed = mark_notes_reviewed
        notes[note.record_id] = note
        if note.person_record_id not in persons:
            extra_persons[note.person_record_id] = person

        # Update the latest_* fields on the associated Person for the note.
        # We do these updates in dictionaries keyed by person_record_id so that
        # multiple updates for one person_record_id will mutate the same object.
        person.update_from_note(note)

    # TODO(kpy): Don't overwrite existing Persons with newer source_dates.

    # Now store the imported Persons and Notes, and count them.
    entities = persons.values() + notes.values()
    all_persons = dict(persons, **extra_persons)
    written = 0
    while entities:
        # The presence of a handler indicates we should notify subscribers 
        # for any new notes being written. We do not notify on 
        # "re-imported" existing notes to avoid spamming subscribers.
        new_notes = []
        if handler:
            new_notes = filter_new_notes(entities[:MAX_PUT_BATCH], repo)
        written_batch = put_batch(entities[:MAX_PUT_BATCH])
        written += written_batch
        # If we have new_notes and results did not fail then send notifications.
        if new_notes and written_batch:
            send_notifications(handler, all_persons, new_notes)
        entities[:MAX_PUT_BATCH] = []

    # Also store the other updated Persons, but don't count them.
    entities = extra_persons.values()
    while entities:
        put_batch(entities[:MAX_PUT_BATCH])
        entities[:MAX_PUT_BATCH] = []

    return written, skipped, total
