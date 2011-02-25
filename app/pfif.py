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

"""PFIF 1.1 and 1.2 parsing and serialization (see http://zesty.ca/pfif/).

This module converts between PFIF XML documents and plain Python dictionaries
that have Unicode strings as values.  Some useful constants are also defined
here according to the PFIF specification.  Use parse() to parse either PFIF
1.1, 1.2, or 1.3; use PFIF_1_1, PFIF_1_2, or PFIF_1_3 to serialize to the 
desired version."""

__author__ = 'kpy@google.com (Ka-Ping Yee) and many other Googlers'

import StringIO
import datetime
import logging
import os
import re
import time
import xml.sax
import xml.sax.handler

# Possible values for the 'sex' field on a person record.
PERSON_SEX_VALUES = [
    '',  # unspecified
    'female',
    'male',
    'other'
]

# Possible values for the 'status' field on a note record.
NOTE_STATUS_VALUES = [
    '',  # unspecified
    'information_sought',
    'is_note_author',
    'believed_alive',
    'believed_missing',
    'believed_dead',
]

def xml_escape(s):
    # XML may only contain the following characters (even after entity
    # references are expanded).  See: http://www.w3.org/TR/REC-xml/#charsets
    s = re.sub(ur'''[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd]''', '', s)
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')


class PfifVersion:
    def __init__(self, version, ns, fields, serializers):
        self.version = version
        self.ns = ns
        # A dict mapping each record type to a list of its fields in order.
        self.fields = fields
        # A dict mapping field names to serializer functions.
        self.serializers = serializers

    def check_tag(self, (ns, local), parent=None):
        """Given a namespace-qualified tag and its parent, returns the PFIF
        type or field name if the tag is valid, or None if the tag is not
        recognized."""
        if ns == self.ns:
            if not parent or local in self.fields[parent]:
                return local

    def write_fields(self, file, type, record, indent=''):
        """Writes PFIF tags for a record's fields."""
        for field in self.fields[type]:
            if record.get(field):
                file.write(
                    indent + '<pfif:%s>%s</pfif:%s>\n' %
                    (field, xml_escape(record[field]).encode('utf-8'), field))

    def write_person(self, file, person, notes=[], indent=''):
        """Writes PFIF for a person record and a list of its note records."""
        file.write(indent + '<pfif:person>\n')
        self.write_fields(file, 'person', person, indent + '  ')
        for note in notes:
            self.write_note(file, note, indent + '  ')
        file.write(indent + '</pfif:person>\n')

    def write_note(self, file, note, indent=''):
        """Writes PFIF for a note record."""
        file.write(indent + '<pfif:note>\n')
        self.write_fields(file, 'note', note, indent + '  ')
        file.write(indent + '</pfif:note>\n')

    def write_file(self, file, persons, get_notes_for_person=lambda p: []):
        """Takes a list of person records and a function that gets the list
        of note records for each person, and writes PFIF to the given file
        object.  Each record is a plain dictionary of strings."""
        file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        file.write('<pfif:pfif xmlns:pfif="%s">\n' % self.ns)
        for person in persons:
            self.write_person(file, person, get_notes_for_person(person), '  ')
        file.write('</pfif:pfif>\n')

    def entity_to_dict(self, entity, fields):
        """Convert an entity to a Python dictionary of Unicode strings."""
        record = {}
        for field in fields:
            if field == 'home_zip' and not hasattr(entity, field):
                # Translate to home_zip for compatibility with PFIF 1.1.
                value = getattr(entity, 'home_postal_code', None)
            else:
                value = getattr(entity, field, None)
            if value:
                record[field] = SERIALIZERS.get(field, nop)(value)
        return record

    def person_to_dict(self, entity):
        return self.entity_to_dict(entity, self.fields['person'])

    def note_to_dict(self, entity):
        return self.entity_to_dict(entity, self.fields['note'])


# Serializers that convert Python values to PFIF strings.
def nop(value):
    return value

def format_boolean(value):
    return value and 'true' or 'false'

def format_utc_datetime(dt):
    return dt and dt.replace(microsecond=0).isoformat() + 'Z' or ''

SERIALIZERS = {  # Serialization functions (for fields that need conversion).
    'found': format_boolean,
    'source_date': format_utc_datetime,
    'entry_date': format_utc_datetime,
    'expiry_date': format_utc_datetime
}

PFIF_1_1 = PfifVersion(
    '1.1',
    'http://zesty.ca/pfif/1.1',
    {
        'person': [  # Fields of a <person> element, in PFIF 1.1 standard order.
            'person_record_id',
            'entry_date',
            'author_name',
            'author_email',
            'author_phone',
            'source_name',
            'source_date',
            'source_url',
            'first_name',
            'last_name',
            'home_city',
            'home_state',
            'home_neighborhood',
            'home_street',
            'home_zip',
            'photo_url',
            'other',
        ],
        'note': [  # Fields of a <note> element, in PFIF 1.1 standard order.
            'note_record_id',
            'entry_date',
            'author_name',
            'author_email',
            'author_phone',
            'source_date',
            'found',
            'email_of_found_person',
            'phone_of_found_person',
            'last_known_location',
            'text',
        ]
    }, SERIALIZERS)

PFIF_1_2 = PfifVersion(
    '1.2',
    'http://zesty.ca/pfif/1.2',
    {
        'person': [  # Fields of a <person> element in PFIF 1.2.
            'person_record_id',
            'entry_date',
            'author_name',
            'author_email',
            'author_phone',
            'source_name',
            'source_date',
            'source_url',
            'first_name',
            'last_name',
            'sex',
            'date_of_birth',
            'age',
            'home_street',
            'home_neighborhood',
            'home_city',
            'home_state',
            'home_postal_code',
            'home_country',
            'photo_url',
            'other',
        ],
        'note': [  # Fields of a <note> element in PFIF 1.2.
            'note_record_id',
            'person_record_id',
            'linked_person_record_id',
            'entry_date',
            'author_name',
            'author_email',
            'author_phone',
            'source_date',
            'found',
            'status',
            'email_of_found_person',
            'phone_of_found_person',
            'last_known_location',
            'text',
        ]
    }, SERIALIZERS)

PFIF_1_3 = PfifVersion(
    '1.3',
    'http://zesty.ca/pfif/1.3',
    {
        'person': [  # Fields of a <person> element in PFIF 1.3.
            'person_record_id',
            'entry_date',
            'expiry_date',
            'author_name',
            'author_email',
            'author_phone',
            'source_name',
            'source_date',
            'source_url',
            'full_name',
            'first_name',
            'last_name',
            'sex',
            'date_of_birth',
            'age',
            'home_street',
            'home_neighborhood',
            'home_city',
            'home_state',
            'home_postal_code',
            'home_country',
            'photo_url',
            'other',
        ],
        'note': [  # Fields of a <note> element in PFIF 1.3.
            'note_record_id',
            'person_record_id',
            'linked_person_record_id',
            'entry_date',
            'author_name',
            'author_email',
            'author_phone',
            'source_date',
            'found',
            'status',
            'email_of_found_person',
            'phone_of_found_person',
            'last_known_location',
            'text',
        ]
    }, SERIALIZERS)

PFIF_VERSIONS = {
    '1.1': PFIF_1_1,
    '1.2': PFIF_1_2,
    '1.3': PFIF_1_3
}

PFIF_DEFAULT_VERSION = '1.2'

assert PFIF_DEFAULT_VERSION in PFIF_VERSIONS

def check_pfif_tag(name, parent=None):
    """Recognizes a PFIF XML tag from either version of PFIF."""
    return PFIF_1_3.check_tag(name, parent) or \
        PFIF_1_2.check_tag(name, parent) or \
        PFIF_1_1.check_tag(name, parent)
 

def split_first_last_name(all_names):
    """Attempt to extract a last name for a person from a multi-first-name."""
    name = re.sub(r'\(.*\)', ' ', all_names)
    name = re.sub(r'\(\S*', ' ', name)
    name = re.sub(r'\d', '', name)
    names = name.split()
    if len(names) > 1:
        last_name = re.search(
            r' (\S*(-+ | -+|-+)?\S+)\s*$', name).group(1).strip()
        return all_names.replace(last_name, ''), last_name.replace(' ', '')


class Handler(xml.sax.handler.ContentHandler):
    """SAX event handler for parsing PFIF documents."""
    def __init__(self):
        self.tags = []
        self.person = {}
        self.note = {}
        self.enclosed_notes = []  # Notes enclosed by the current <person>.
        self.person_records = []
        self.note_records = []

    def startElementNS(self, tag, qname, attrs):
        self.tags.append(tag)
        if check_pfif_tag(tag) == 'person':
            self.person = {}
            self.enclosed_notes = []
        elif check_pfif_tag(tag) == 'note':
            self.note = {}

    def endElementNS(self, tag, qname):
        assert self.tags.pop() == tag
        if check_pfif_tag(tag) == 'person':
            self.person_records.append(self.person)
            if 'person_record_id' in self.person:
                # Copy the person's person_record_id to any enclosed notes.
                for note in self.enclosed_notes:
                    note['person_record_id'] = self.person['person_record_id']
        elif check_pfif_tag(tag) == 'note':
            # Save all parsed notes (whether or not enclosed in <person>).
            self.note_records.append(self.note)
            self.enclosed_notes.append(self.note)

    def append_to_field(self, record, tag, parent, content):
        field = check_pfif_tag(tag, parent)
        if field:
            record[field] = record.get(field, u'') + content
        elif content.strip():
            logging.warn('ignored tag %r with content %r', tag, content)

    def characters(self, content):
        if content and len(self.tags) >= 2:
            parent, tag = self.tags[-2], self.tags[-1]
            if check_pfif_tag(parent) == 'person':
                self.append_to_field(self.person, tag, 'person', content)
            elif check_pfif_tag(parent) == 'note':
                self.append_to_field(self.note, tag, 'note', content)

def parse_file(pfif_utf8_file):
    """Reads a UTF-8-encoded PFIF file to give a list of person records and a
    list of note records.  Each record is a plain dictionary of strings."""
    handler = Handler()
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, True)
    parser.setContentHandler(handler)
    parser.parse(pfif_utf8_file)
    return handler.person_records, handler.note_records

def parse(pfif_text):
    """Takes the text of a PFIF document, as a Unicode string or UTF-8 string,
    and returns a list of person records and a list of note records.  Each
    record is a plain dictionary of strings."""
    if isinstance(pfif_text, unicode):
        pfif_text = pfif_text.decode('utf-8')
    return parse_file(StringIO.StringIO(pfif_text))
