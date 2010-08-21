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
  """Yields a dictionary where all string values are converted to unicode.

  Args:
     dict_reader: an iterable that yields dictionaries with some string values

  Yields:
     A dictionary whose with all string values converted to unicode.
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
  return (isinstance(string, basestring)
          and string.strip().lower() in ['true', '1'])

def create_person_optional_last_name(fields, requires_key=True):
  """Creates a Person entity with the given field values, allowing the
  last_name field to be empty."""
  return create_person(fields, requires_key, last_name_optional=True)

def create_person(fields, requires_key=True, last_name_optional=False):
  """Creates a Person entity with the given field values.  Note that storing
  the resulting entity will overwrite an existing entity with the same
  person_record_id, even in the home domain.  If no person_record_id is given,
  the resulting entity will get a new unique id in the home domain."""
  assert strip(fields.get('first_name')), 'first_name is required'
  if not last_name_optional:
    assert strip(fields.get('last_name')), 'last_name is required'
  if requires_key:
    assert strip(fields.get('person_record_id')), 'person_record_id is required'
  person_constructor_dict = dict(
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
      home_postal_code=
          strip(fields.get('home_postal_code', fields.get('home_zip'))),
      home_country=strip(fields.get('home_country')),
      photo_url=strip(fields.get('photo_url')),
      other=fields.get('other'),
      last_update_date=datetime.datetime.now(),
  )

  # If the person_record_id is supplied, set the new entity's key accordingly.
  record_id = strip(fields.get('person_record_id'))
  if record_id:
    if is_original(record_id):  # original record
      person_constructor_dict['key'] = key_from_record_id(record_id, 'Person')
    else:  # clone record
      person_constructor_dict['key_name'] = record_id

  return Person(**person_constructor_dict)

def create_note(fields, requires_key=True):
  """Creates a Note entity with the given field values.  Note that storing
  the resulting entity will overwrite an existing entity with the same
  note_record_id, even in the home domain.  If no note_record_id is given,
  the resulting entity will get a new unique id in the home domain."""
  if requires_key:
    assert strip(fields.get('note_record_id')), 'note_record_id is required'
  assert strip(fields.get('person_record_id')), 'person_record_id is required'
  note_constructor_dict = dict(
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

  # If the note_record_id is supplied, set the new entity's key accordingly.
  record_id = strip(fields.get('note_record_id'))
  if record_id:
    if is_original(record_id):  # original record
      note_constructor_dict['key'] = key_from_record_id(record_id, 'Note')
    else:  # clone record
      note_constructor_dict['key_name'] = record_id

  return Note(**note_constructor_dict)

def import_records(domain, converter, records):
  """Convert and import a list of entries into the datastore.

  Args:
    domain:  String prefix used for all the record keys.  Must match the prefix
      returned by the entity converter.
    converter: A function to transform a dictionary of fields to a datastore
      entity.  This function may throw an exception if there is anything wrong
      with the input fields and import_records will skip the bad record.  The
      key_name of the resulting datastore entity must begin with domain + '/',
      or the record will also be skipped.
    records:  A list of dictionaries representing the entries.

  Returns:
    The number of records written, a list of (error_message, record) pairs for
    the skipped records, and the number of records processed in total.
  """
  batch = []
  written = 0
  skipped = []
  total = 0
  for fields in records:
    total += 1
    try:
      entity = converter(fields)
    except (KeyError, ValueError, AssertionError,
            datastore_errors.BadValueError), e:
      skipped.append((e.__class__.__name__ + ': ' + str(e), fields))
      continue
    key_name = entity.key().name()
    if not key_name.startswith(domain + '/'):
      skipped.append(('Not in authorized domain: %r' % key_name, fields))
      continue
    if hasattr(entity, 'update_index'):
      entity.update_index(['old', 'new'])
    batch.append(entity)
    if len(batch) >= MAX_PUT_BATCH:
      written += put_batch(batch)
      batch = []
  if batch:
    written += put_batch(batch)
  return written, skipped, total
