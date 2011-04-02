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

"""Support for importing records in batches, with error detection.

This module converts Python dictionaries into datastore entities.
The values of all dictionary fields are Unicode strings."""

__author__ = 'kpy@google.com (Ka-Ping Yee) and many other Googlers'

import datetime
import logging
import model
import prefix
import re
import sys
import subscribe

from google.appengine.api import datastore_errors

from model import *
from utils import validate_sex, validate_status, get_utcnow
from utils import validate_approximate_date, validate_age

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
            string.strip().lower() in ['true', '1'])

def create_person(subdomain, fields):
    """Creates a Note entity in the given subdomain's repository with the given
    field values.  If 'fields' contains a 'person_record_id', calling put() on
    the resulting entity will overwrite any existing (original or clone) record
    with the same person_record_id.  Otherwise, a new original person record is
    created in the given subdomain."""
    person_fields = dict(
        entry_date=get_utcnow(),
        author_name=strip(fields.get('author_name')),
        author_email=strip(fields.get('author_email')),
        author_phone=strip(fields.get('author_phone')),
        source_name=strip(fields.get('source_name')),
        source_url=strip(fields.get('source_url')),
        source_date=validate_datetime(fields.get('source_date')),
        first_name=strip(fields.get('first_name')),
        last_name=strip(fields.get('last_name')),
        sex=validate_sex(fields.get('sex')),
        date_of_birth=validate_approximate_date(fields.get('date_of_birth')),
        age=validate_age(fields.get('age')),
        home_street=strip(fields.get('home_street')),
        home_neighborhood=strip(fields.get('home_neighborhood')),
        home_city=strip(fields.get('home_city')),
        home_state=strip(fields.get('home_state')),
        # Fall back to 'home_zip' for backward compatibility with PFIF 1.1.
        home_postal_code=strip(
            fields.get('home_postal_code', fields.get('home_zip'))),
        home_country=strip(fields.get('home_country')),
        photo_url=strip(fields.get('photo_url')),
        other=fields.get('other')
    )

    record_id = strip(fields.get('person_record_id'))
    if record_id:  # create a record that might overwrite an existing one
        if is_clone(subdomain, record_id):
            return Person.create_clone(subdomain, record_id, **person_fields)
        else:
            return Person.create_original_with_record_id(
                subdomain, record_id, **person_fields)
    else:  # create a new original record
        return Person.create_original(subdomain, **person_fields)

def create_note(subdomain, fields):
    """Creates a Note entity in the given subdomain's repository with the given
    field values.  If 'fields' contains a 'note_record_id', calling put() on
    the resulting entity will overwrite any existing (original or clone) record
    with the same note_record_id.  Otherwise, a new original note record is
    created in the given subdomain."""
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
        found=validate_boolean(fields.get('found')),
        email_of_found_person=strip(fields.get('email_of_found_person')),
        phone_of_found_person=strip(fields.get('phone_of_found_person')),
        last_known_location=strip(fields.get('last_known_location')),
        text=fields.get('text'),
    )

    record_id = strip(fields.get('note_record_id'))
    if record_id:  # create a record that might overwrite an existing one
        if is_clone(subdomain, record_id):
            return Note.create_clone(subdomain, record_id, **note_fields)
        else:
            return Note.create_original_with_record_id(
                subdomain, record_id, **note_fields)
    else:  # create a new original record
        return Note.create_original(subdomain, **note_fields)

def filter_new_notes(entities, subdomain):
    """Filter the notes which are new."""
    notes = []
    for entity in entities:
        # Send an an email notification for new notes only
        if isinstance(entity, Note):
            if not Note.get(subdomain, entity.get_note_record_id()):
                notes.append(entity)
    return notes


def send_notifications(notes, persons, handler):
    """For each note, send a notification to subscriber.

    Args:
       notes: List of notes for which to send notification.
       persons: Dictionary of persons impacted by the notes,
                indexed by person_record_id.
       handler: Handler used to send email notidication.
    """
    for note in notes:
        person = persons[note.person_record_id]
        subscribe.send_notifications(person, [note], handler)

def import_records(subdomain, domain, converter, records,
                   mark_notes_reviewed=False, handler=None):
    """Convert and import a list of entries into a subdomain's respository.

    Args:
        subdomain: Identifies the repository in which to store the records.
        domain: Accept only records that have this original domain.  Only one
            original domain may be imported at a time.
        converter: A function to transform a dictionary of fields to a
            datastore entity.  This function may throw an exception if there
            is anything wrong with the input fields and import_records will
            skip the bad record.  The key_name of the resulting datastore
            entity must begin with domain + '/', or the record will be skipped.
        records: A list of dictionaries representing the entries.
        mark_notes_reviewed: If true, mark the new notes as reviewed.
        handler: Handler to use to send Email notification for notes. If no handler,
           then, we do not send an email.

    Returns:
        The number of passed-in records that were written (not counting other
        Person records that were updated because they have new Notes), a list
        of (error_message, record) pairs for the skipped records, and the
        number of records processed in total.
    """
    if domain == HOME_DOMAIN:  # not allowed, must be a subdomain
        raise ValueError('Cannot import into domain %r' % HOME_DOMAIN)

    persons = {}  # Person entities to write
    notes = {}  # Note entities to write
    skipped = []  # entities skipped due to an error
    total = 0  # total number of entities for which conversion was attempted
    for fields in records:
        total += 1
        try:
            entity = converter(subdomain, fields)
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
            entity.reviewed = mark_notes_reviewed
            notes[entity.record_id] = entity

    # We keep two dictionaries 'persons' and 'extra_persons', with disjoint
    # key sets: Person entities for the records passed in to import_records() 
    # go in 'persons', and any other Person entities affected by the import go
    # in 'extra_persons'.  The two dictionaries are kept separate in order to
    # produce a count of records written that only counts 'persons'.
    extra_persons = {}  # updated Persons other than those being imported

    # For each Note, update the latest_* fields on the associated Person.
    # We do these updates in dictionaries keyed by person_record_id so that
    # multiple updates for one person_record_id will mutate the same object.
    for note in notes.values():
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
            person = Person.get(subdomain, note.person_record_id)
            if not person:
                continue
            extra_persons[note.person_record_id] = person
        person.update_from_note(note)

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
            new_notes = filter_new_notes(entities[:MAX_PUT_BATCH], subdomain)
        written_batch = put_batch(entities[:MAX_PUT_BATCH])
        written += written_batch
        # If we have new_notes and results did not fail then send notifications.
        if new_notes and written_batch:
            send_notifications(new_notes, all_persons, handler)
        entities[:MAX_PUT_BATCH] = []

    # Also store the other updated Persons, but don't count them.
    entities = extra_persons.values()
    while entities:
        put_batch(entities[:MAX_PUT_BATCH])
        entities[:MAX_PUT_BATCH] = []

    return written, skipped, total
