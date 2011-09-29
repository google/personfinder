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

"""Tests for importer.py."""

import datetime
import unittest

from google.appengine.ext import db
from nose.tools import assert_raises

import model
import importer


class ImporterTests(unittest.TestCase):
    """Test the import utilities."""

    def tearDown(self):
        db.delete(model.Person.all())
        db.delete(model.Note.all())

    def test_strip(self):
        assert importer.strip('') == ''
        assert importer.strip(None) == ''
        assert importer.strip(0) == ''
        assert importer.strip(' ') == ''
        assert importer.strip(' \t') == ''
        assert importer.strip('\t ') == ''
        assert importer.strip(' \n ') == ''
        assert importer.strip('abc') == 'abc'
        assert importer.strip('a b\tc ') == 'a b\tc'
        assert importer.strip(' a b\tc\t') == 'a b\tc'

    def test_validate_datetime(self):
        assert importer.validate_datetime('2010-01-01T00:00:00Z') == \
            datetime.datetime(2010, 1, 1, 0, 0, 0)
        assert importer.validate_datetime('2010-01-01T01:23:45Z') == \
            datetime.datetime(2010, 1, 1, 1, 23, 45)

        assert importer.validate_datetime('') == None
        assert importer.validate_datetime(0) == None

        assert_raises(ValueError, importer.validate_datetime, ' ')
        assert_raises(ValueError, importer.validate_datetime, '2010-02-28')
        assert_raises(
            ValueError, importer.validate_datetime, '2010-02-28 01:23:45')
        assert_raises(
            ValueError, importer.validate_datetime, '2010-02-28 01:23:45Z')
        assert_raises(
            ValueError, importer.validate_datetime, '2010-02-28 1:23:45')

        # Invalid format
        assert_raises(
            ValueError, importer.validate_datetime, '2010-02-28T1:23:45Z')
        # Invalid date
        assert_raises(
            ValueError, importer.validate_datetime, '2010-02-29T01:23:45Z')
        # Invalid time
        assert_raises(
            ValueError, importer.validate_datetime, '2010-01-01T25:00:00Z')

    def test_validate_boolean(self):
        assert importer.validate_boolean('true')
        assert importer.validate_boolean('TRUE')
        assert importer.validate_boolean('True')
        assert importer.validate_boolean('trUe')
        assert importer.validate_boolean('1')

        assert not importer.validate_boolean('false')
        assert not importer.validate_boolean('ture')
        assert not importer.validate_boolean('')
        assert not importer.validate_boolean(None)
        assert not importer.validate_boolean(1)

    def test_create_person(self):
        # clone record
        fields = {'first_name': ' Zhi\n',
                  'last_name': ' Qiao',
                  'person_record_id': '  test_domain/person_1 '}
        person = importer.create_person('haiti', fields)
        assert hasattr(person, 'entry_date')
        assert hasattr(person, 'last_modified')
        assert person.first_name == 'Zhi'
        assert person.last_name == 'Qiao'
        assert person.record_id == 'test_domain/person_1'
        assert person.key().kind() == 'Person'
        assert person.key().id() == None
        assert person.key().name() == 'haiti:test_domain/person_1'

        # original record with new record_id
        fields = {'first_name': ' Zhi\n',
                  'last_name': ' Qiao'}
        person = importer.create_person('haiti', fields)
        assert person.record_id.startswith(
            'haiti.%s/person.' % model.HOME_DOMAIN)

        # original record with specified record_id
        fields = {'first_name': ' Zhi\n',
                  'last_name': ' Qiao',
                  'person_record_id': model.HOME_DOMAIN + '/person.23 '}
        person = importer.create_person('haiti', fields)
        assert person.record_id == model.HOME_DOMAIN + '/person.23'

    def test_create_note(self):
        # clone record
        fields = {'note_record_id': ' test_domain/note_1',
                  'person_record_id': '  test_domain/person_1 '}

        # source_date should be required.
        assert_raises(AssertionError, importer.create_note, 'haiti', fields)

        # With source_date, the conversion should succeed.
        fields['source_date'] = '2010-01-02T12:34:56Z'
        note = importer.create_note('haiti', fields)
        assert note.record_id == 'test_domain/note_1'
        assert note.person_record_id == 'test_domain/person_1'
        assert note.status == ''
        assert note.key().kind() == 'Note'
        assert note.key().id() == None
        assert note.key().name() == 'haiti:test_domain/note_1'

        # original record
        fields = {'person_record_id': '  test_domain/person_1 ',
                  'source_date': '2010-01-02T03:04:05Z'}
        note = importer.create_note('haiti', fields)
        assert note.record_id.startswith('haiti.%s/note.' % model.HOME_DOMAIN)
        assert note.person_record_id == 'test_domain/person_1'

    def test_import_person_records(self):
        records = []
        for i in range(20):
            first_name = "first_name_%d" % i
            last_name = "last_name_%d" % i

            source_date = "2010-01-01T01:23:45Z"
            record_id = "test_domain/%d" % i

            # Records 0, 8, and 16 have bad domains.
            if not i % 8:
                record_id = "other_domain/%d" % i
            # Records 0, 9, and 18 have invalid dates.
            elif not i % 9:
                source_date = "2010-01-01 01:23:45"

            records.append({'first_name': first_name,
                            'last_name': last_name,
                            'person_record_id': record_id,
                            'source_date': source_date})
        written, skipped, total = importer.import_records(
            'haiti', 'test_domain', importer.create_person, records, False,
            True, None)

        assert written == 15
        assert len(skipped) == 5
        assert skipped[0] == (
            'Not in authorized domain: u\'other_domain/0\'', {
                'first_name': 'first_name_0',
                'last_name': 'last_name_0',
                'source_date': '2010-01-01T01:23:45Z',
                'person_record_id': 'other_domain/0'
            })
        assert skipped[3] == (
            'Not in authorized domain: u\'other_domain/16\'', {
                'first_name': 'first_name_16',
                'last_name': 'last_name_16',
                'source_date': '2010-01-01T01:23:45Z',
                'person_record_id': 'other_domain/16'
            })
        assert skipped[2] == (
            'ValueError: Bad datetime: \'2010-01-01 01:23:45\'', {
                'first_name': 'first_name_9',
                'last_name': 'last_name_9',
                'source_date': '2010-01-01 01:23:45',
                'person_record_id': 'test_domain/9'
            })
        assert skipped[4] == (
            'ValueError: Bad datetime: \'2010-01-01 01:23:45\'', {
                'first_name': 'first_name_18',
                'last_name': 'last_name_18',
                'source_date': '2010-01-01 01:23:45',
                'person_record_id': 'test_domain/18'
            })
        assert total == 20

        # Also confirm that 15 records were put into the datastore.
        assert model.Person.all().count() == 15

    def test_import_note_records(self):
        records = []
        for i in range(20):
            source_date = '2010-01-01T01:23:45Z'
            note_id = 'test_domain/record_%d' % i
            person_id = 'test_domain/person_%d' % i

            # Records 0, 8, and 16 have bad note record domains.
            if not i % 8:
                note_id = 'other_domain/record_%d' % i
            # Records 0, 9, and 18 have bad person record domains.
            # This should not matter for note records.
            elif not i % 9:
                person_id = 'other_domain/person_%d' % i
            # Records 0, 5, 10, and 15 have invalid dates.
            elif not i % 5:
                source_date = '2010-01-01 01:23:45'

            records.append({'person_record_id': person_id,
                            'note_record_id': note_id,
                            'source_date': source_date})
        written, skipped, total = importer.import_records(
            'haiti', 'test_domain', importer.create_note, records, False,
            True, None)

        assert written == 14
        assert len(skipped) == 6
        assert skipped[0] == (
            'Not in authorized domain: u\'other_domain/record_0\'', {
                'person_record_id': 'test_domain/person_0',
                'source_date': '2010-01-01T01:23:45Z',
                'note_record_id': 'other_domain/record_0'
            })
        assert skipped[2] == (
            'Not in authorized domain: u\'other_domain/record_8\'', {
                'person_record_id': 'test_domain/person_8',
                'source_date': '2010-01-01T01:23:45Z',
                'note_record_id': 'other_domain/record_8'
            })
        assert skipped[1] == (
            'ValueError: Bad datetime: \'2010-01-01 01:23:45\'', {
                'person_record_id': 'test_domain/person_5',
                'source_date': '2010-01-01 01:23:45',
                'note_record_id': 'test_domain/record_5'
            })
        assert skipped[4] == (
            'ValueError: Bad datetime: \'2010-01-01 01:23:45\'', {
                'person_record_id': 'test_domain/person_15',
                'source_date': '2010-01-01 01:23:45',
                'note_record_id': 'test_domain/record_15'
            })
        assert total == 20
        # Also confirm that 14 records were put into the datastore.
        assert model.Note.all().count() == 14
        # Confirm all records are NOT marked reviewed.
        for note in model.Note.all():
            assert note.reviewed == False

    def test_authorize_write_believed_dead_note_records(self):
        # Prepare input data
        records = []
        for i in range(20):
            source_date = '2010-01-01T01:23:45Z'
            note_id = 'test_domain/record_%d' % i
            person_id = 'test_domain/person_%d' % i
            status = 'unspecified'

            # Records 0, 8, and 16 have status 'believed_dead'.
            if not i % 8:
                status = 'believed_dead'
           
            records.append({'person_record_id': person_id,
                            'note_record_id': note_id,
                            'source_date': source_date,
                            'status': status})
 
        # Disallow import notes with status 'believed_dead'.        
        written, skipped, total = importer.import_records(
            'haiti', 'test_domain', importer.create_note, records, False,
            False, None)

        assert written == 17
        assert len(skipped) == 3
        assert skipped[0] == (
            'Not authorized to post notes with the status'
            ' \"believed_dead\"', {
                'person_record_id': 'test_domain/person_0',
                'source_date': '2010-01-01T01:23:45Z',
                'note_record_id': 'test_domain/record_0',
                'status': 'believed_dead'
            })
        assert skipped[1] == (
            'Not authorized to post notes with the status'
            ' \"believed_dead\"', {
                'person_record_id': 'test_domain/person_8',
                'source_date': '2010-01-01T01:23:45Z',
                'note_record_id': 'test_domain/record_8',
                'status': 'believed_dead'
            })
        assert skipped[2] == (
            'Not authorized to post notes with the status'
            ' \"believed_dead\"', {
                'person_record_id': 'test_domain/person_16',
                'source_date': '2010-01-01T01:23:45Z',
                'note_record_id': 'test_domain/record_16',
                'status': 'believed_dead'
            })

        assert total == 20
        assert model.Note.all().count() == 17


    def test_import_reviewed_note_records(self):
        records = []
        for i in range(3):
            source_date = '2010-01-01T01:23:45Z'
            note_id = 'test_domain/record_%d' % i
            person_id = 'test_domain/person_%d' % i
            records.append({'person_record_id': person_id,
                            'note_record_id': note_id,
                            'source_date': source_date})

        # Import reviewed notes.
        written, skipped, total = importer.import_records(
            'haiti', 'test_domain', importer.create_note, records, True,
            True, None)

        assert written == 3
        assert len(skipped) == 0
        assert total == 3
        # Confirm all records are marked reviewed.
        for note in model.Note.all():
            assert note.reviewed == True


if __name__ == "__main__":
    unittest.main()
