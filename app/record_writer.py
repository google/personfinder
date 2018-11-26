#!/usr/bin/python2.7
# Copyright 2018 Google Inc.
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

"""Classes to write both types of records in different formats."""


import csv

import pfif
import utils


PFIF = pfif.PFIF_VERSIONS[pfif.PFIF_DEFAULT_VERSION]


def get_person_note_joined_record_fields():
    """Returns a list of field names in a joined record of a person and a note.
    """
    joined_fields = []
    for person_field in PFIF.fields['person']:
        joined_field = utils.get_field_name_for_joined_record(
            person_field, 'person')
        joined_fields.append(joined_field)
    for note_field in PFIF.fields['note']:
        joined_field = utils.get_field_name_for_joined_record(
            note_field, 'note')
        if joined_field not in joined_fields:
            joined_fields.append(joined_field)
    return joined_fields


class RecordCsvWriter(object):
    """Base class to write records in CSV format."""

    def __init__(self, io, fields=None, write_header=True):
        """Initializer.
        
        Args:
            io (io): CSV is written to this.
            fields (list of str): A custom list of fields which are written.
            write_header (bool): Write the header row at the beginning.
        """
        self.io = io
        if fields:
            self.fields = fields
        self.writer = csv.writer(self.io)
        if write_header:
            self.writer.writerow(self.fields)

    def write(self, records):
        """Writes rows with records.
        
        Args:
            records (list of dict): A list of dictionaries which represent records.
        """
        for record in records:
            self.writer.writerow([
                record.get(name, '').encode('utf-8') for name in self.fields])
        self.io.flush()

    def close(self):
        """Closes the IO."""
        self.io.close()


class PersonCsvWriter(RecordCsvWriter):
    """A class to write person records in CSV format."""

    fields = PFIF.fields['person']


class NoteCsvWriter(RecordCsvWriter):
    """A class to write note records in CSV format."""

    fields = PFIF.fields['note']

    
class PersonWithNoteCsvWriter(RecordCsvWriter):
    """A class to write a joined record of person and note in CSV format."""

    fields = get_person_note_joined_record_fields()


class RecordXmlWriter(object):
    """Base class to write records in XML format."""

    def __init__(self, io, fields=None):
        """Initializer.
        
        Args:
            io: XML is written to this IO object.
            fields: A custom list of fields which are written.
        """
        self.io = io
        self.io.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.io.write('<pfif:pfif xmlns:pfif="%s">\n' % PFIF.ns)

    def write(self, records):
        """Writes rows with records.
        
        Args:
            records: A list of dictionaries which represent records.
        """
        for record in records:
            self.write_record(self.io, record, indent='  ')
        self.io.flush()

    def close(self):
        """Closes the IO."""
        self.io.write('</pfif:pfif>\n')
        self.io.close()


class PersonXmlWriter(RecordXmlWriter):
    """A class to write person records in XML format."""

    write_record = PFIF.write_person


class NoteXmlWriter(RecordXmlWriter):
    """A class to write note records in XML format."""

    write_record = PFIF.write_note
