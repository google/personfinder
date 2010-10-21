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
import prefix
import re
import sys

from google.appengine.api import datastore_errors

from model import *
from utils import validate_sex, validate_status
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
        return False  # A missing value is a boolean.
    return (isinstance(string, basestring) and
            string.strip().lower() in ['true', '1'])

def create_person(subdomain, fields):
    """Creates a Note entity in the given subdomain's repository with the given
    field values.  If 'fields' contains a 'person_record_id', calling put() on
    the resulting entity will overwrite any existing (original or clone) record
    with the same person_record_id.  Otherwise, a new original person record is
    created in the given subdomain."""
    person_fields = dict(
        entry_date=datetime.datetime.now(),
        author_name=strip(fields.get('author_name')),
        author_email=strip(fields.get('author_email')),
        author_phone=strip(fields.get('author_phone')),
        source_name=strip(fields.get('source_name')),
        source_url=strip(fields.get('source_url')),
        source_date=validate_datetime(fields.get('source_date')),
        first_name=strip(fields['first_name']),
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
        other=fields.get('other'),
        last_update_date=datetime.datetime.now(),
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

def import_records(subdomain, domain, converter, records):
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

    Returns:
        The number of records written, a list of (error_message, record) pairs
        for the skipped records, and the number of records processed in total.
    """
    if domain == HOME_DOMAIN:  # not allowed, must be a subdomain
        raise ValueError('Cannot import into domain %r' % HOME_DOMAIN)

    batch = []
    uncounted_batch = []  # for auxiliary writes that are not counted
    written = 0
    skipped = []
    total = 0
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
        if hasattr(entity, 'update_index'):
            entity.update_index(['old', 'new'])
        if hasattr(entity, 'update_person'):
            person = entity.update_person()
            if person:
                uncounted_batch.append(person)
        batch.append(entity)
        if len(batch) >= MAX_PUT_BATCH:
            written += put_batch(batch)
            batch = []
        if len(uncounted_batch) >= MAX_PUT_BATCH:
            put_batch(uncounted_batch)
            uncounted_batch = []
    if batch:
        written += put_batch(batch)
    if uncounted_batch:
        put_batch(uncounted_batch)
    return written, skipped, total
