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

"""PFIF 1.1 - 1.4 parsing and serialization (see http://zesty.ca/pfif/).

This module converts between PFIF XML documents (PFIF 1.1, 1.2, 1.3, or 1.4) and
plain Python dictionaries that have PFIF 1.4 field names as keys (always 1.4)
and Unicode strings as values.  Some useful constants are also defined here
according to the PFIF specification.  Use parse() to parse PFIF 1.1, 1.2, 1.3,
or 1.4; use PFIF_1_1, PFIF_1_2, PFIF_1_3, or PFIF_1_4 to serialize to the
desired version."""

__author__ = 'kpy@google.com (Ka-Ping Yee) and many other Googlers'

import StringIO
import logging
import os
import re
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

# Fields to preserve in a placeholder for an expired record.
PLACEHOLDER_FIELDS = [
    'person_record_id',
    'source_date',
    'entry_date',
    'expiry_date'
]

# A dict mapping old field names to the new field names in PFIF 1.4,
# for backward compatibility with older PFIF versions.
RENAMED_FIELDS = {
    'home_zip': 'home_postal_code',  # Renamed in PFIF 1.2
    'first_name': 'given_name',      # Renamed in PFIF 1.4
    'last_name': 'family_name',      # Renamed in PFIF 1.4
    'found': 'author_made_contact',  # Renamed in PFIF 1.4
    'other': 'description',          # Renamed in PFIF 1.4
}

DESCRIPTION_FIELD_LABEL = 'description:'

def xml_escape(s):
    # XML may only contain the following characters (even after entity
    # references are expanded).  See: http://www.w3.org/TR/REC-xml/#charsets
    s = re.sub(ur'''[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd]''', '', s)
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def convert_description_to_other(desc):
    """Converts 'description' in PFIF 1.4 to 'other' in older versions."""
    INDENT_DEPTH = 4
    # Do not add description label if it's already there, so when exporting and
    # importing the same person record, we don't duplicate the label.
    if not desc.strip() or desc.startswith(DESCRIPTION_FIELD_LABEL):
        return desc
    # Indent the text and prepend the description label.
    return DESCRIPTION_FIELD_LABEL + '\n' + ' ' * INDENT_DEPTH + \
        ('\n' + ' ' * INDENT_DEPTH).join(desc.split('\n')).rstrip(' ')

def maybe_convert_other_to_description(other):
    """Converts 'other' in PFIF 1.3 and earlier to 'description' in PFIF 1.4 if
    'other' has only 'description' field. Otherwise it returns 'other' without
    modifying it, so we don't lose any information."""
    description_lines = []
    has_description_field = False
    for line in other.splitlines(True):
        if line.startswith(DESCRIPTION_FIELD_LABEL):
            has_description_field = True
            line = line[len(DESCRIPTION_FIELD_LABEL):]
            if not line.strip():
                continue
        elif re.match(r'\S+:', line):
            return other
        description_lines.append(line.strip(' \t'))
    if not has_description_field:
        return other
    return ''.join(description_lines)


class PfifVersion:
    def __init__(self, version, ns, fields, mandatory_fields, serializers):
        self.version = version
        self.ns = ns
        # A dict mapping each record type to a list of its fields in order.
        self.fields = fields
        # A dict mapping each record type to a list of its mandatory fields.
        # TODO(ryok): we should validate that imported records have these
        # mandatory fields populated.
        self.mandatory_fields = mandatory_fields
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
            if record.get(field) or field in self.mandatory_fields[type]:
                escaped_value = xml_escape(record.get(field, ''))
                file.write(indent + '<pfif:%s>%s</pfif:%s>\n' %
                           (field, escaped_value.encode('utf-8'), field))

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
        """Converts a person or note record from a Python object (with PFIF 1.4
        field names as attributes) to a Python dictionary (with the given field
        names as keys, and Unicode strings as values)."""
        record = {}
        for field in fields:
            maybe_renamed_field = field
            if not hasattr(entity, field):
                maybe_renamed_field = RENAMED_FIELDS.get(field, field)
            value = getattr(entity, maybe_renamed_field, None)
            if value:
                # For backward compatibility with PFIF 1.3 and earlier.
                if field == 'other' and maybe_renamed_field == 'description':
                    value = convert_description_to_other(value)
                record[field] = self.serializers.get(field, nop)(value)
        return record

    def person_to_dict(self, entity, expired=False):
        dict = self.entity_to_dict(entity, self.fields['person'])
        if expired:  # Clear all fields except those needed for the placeholder.
            for field in set(dict.keys()) - set(PLACEHOLDER_FIELDS):
                del dict[field]
        return dict

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
    'author_made_contact': format_boolean,
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
    },
    {
        'person': ['person_record_id', 'first_name', 'last_name'],
        'note': ['note_record_id', 'author_name', 'source_date', 'text'],
    },
    SERIALIZERS)

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
    },
    {
        'person': ['person_record_id', 'first_name', 'last_name'],
        'note': ['note_record_id', 'author_name', 'source_date', 'text'],
    },
    SERIALIZERS)

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
    },
    {
        'person': ['person_record_id', 'source_date', 'full_name'],
        'note': ['note_record_id', 'author_name', 'source_date', 'text'],
    },
    SERIALIZERS)

PFIF_1_4 = PfifVersion(
    '1.4',
    'http://zesty.ca/pfif/1.4',
    {
        'person': [  # Fields of a <person> element in PFIF 1.4.
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
            'given_name',
            'family_name',
            'alternate_names',
            'description',
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
            'profile_urls',
        ],
        'note': [  # Fields of a <note> element in PFIF 1.4.
            'note_record_id',
            'person_record_id',
            'linked_person_record_id',
            'entry_date',
            'author_name',
            'author_email',
            'author_phone',
            'source_date',
            'author_made_contact',
            'status',
            'email_of_found_person',
            'phone_of_found_person',
            'last_known_location',
            'text',
            'photo_url',
        ]
    },
    {
        'person': ['person_record_id', 'source_date', 'full_name'],
        'note': ['note_record_id', 'author_name', 'source_date'],
    },
    SERIALIZERS)

PFIF_VERSIONS = {
    '1.1': PFIF_1_1,
    '1.2': PFIF_1_2,
    '1.3': PFIF_1_3,
    '1.4': PFIF_1_4
}

PFIF_DEFAULT_VERSION = '1.3'

assert PFIF_DEFAULT_VERSION in PFIF_VERSIONS

def check_pfif_tag(name, parent=None):
    """Recognizes a PFIF XML tag from any version of PFIF."""
    return PFIF_1_4.check_tag(name, parent) or \
        PFIF_1_3.check_tag(name, parent) or \
        PFIF_1_2.check_tag(name, parent) or \
        PFIF_1_1.check_tag(name, parent)


class Handler(xml.sax.handler.ContentHandler):
    """SAX event handler for parsing PFIF documents."""
    def __init__(self, rename_fields=True):
        # Wether to attempt to rename fields based on RENAMED_FIELDS.
        self.rename_fields = rename_fields
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


def rename_fields(record):
    """Renames fields in PFIF 1.3 and earlier to PFIF 1.4, and also does a
    special conversion for other -> description."""
    for old, new in RENAMED_FIELDS.iteritems():
        if old in record:
            record[new] = record[old]
            # For backward-compatibility with PFIF 1.3 and earlier.
            if old == 'other' and new =='description':
                record[new] = maybe_convert_other_to_description(record[old])
            del record[old]

def parse_file(pfif_utf8_file, rename_fields=True):
    """Reads a UTF-8-encoded PFIF file to give a list of person records and a
    list of note records.  Each record is a plain dictionary of strings,
    with PFIF 1.4 field names as keys if rename_fields is True; otherwise,
    the field names are kept as is in the input XML file."""
    handler = Handler(rename_fields)
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, True)
    parser.setContentHandler(handler)
    parser.parse(pfif_utf8_file)
    if rename_fields:
        for record in handler.person_records + handler.note_records:
            rename_fields(record)
    return handler.person_records, handler.note_records

def parse(pfif_text, rename_fields=True):
    """Takes the text of a PFIF document, as a Unicode string or UTF-8 string,
    and returns a list of person records and a list of note records.  Each
    record is a plain dictionary of strings, with PFIF 1.4 field names as keys
    if rename_fields is True; otherwise, the field names are kept as is in the
    input XML file."""
    if isinstance(pfif_text, unicode):
        pfif_text = pfif_text.decode('utf-8')
    return parse_file(StringIO.StringIO(pfif_text), rename_fields)
