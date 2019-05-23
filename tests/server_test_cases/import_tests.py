# encoding: utf-8
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

"""Test cases for end-to-end testing.  Run with the server_tests script."""

import datetime
import os
import re
import tempfile
from model import *
from server_tests_base import ServerTestsBase


class ImportTests(ServerTestsBase):
    """Tests for CSV import page at /api/import."""
    def setUp(self):
        ServerTestsBase.setUp(self)
        Repo(
            key_name='haiti',
            activation_status=Repo.ActivationStatus.ACTIVE).put()
        config.set_for_repo(
            'haiti',
            api_action_logging=True)
        self.filename = None

    def tearDown(self):
        if self.filename:
            os.remove(self.filename)
        ServerTestsBase.tearDown(self)

    def _write_csv_file(self, content):
        # TODO(ryok): We should use StringIO instead of a file on disk. Update
        # scrape.py to support StringIO.
        fd, self.filename = tempfile.mkstemp()
        os.fdopen(fd, 'w').write('\n'.join(content))

    def test_import_no_csv(self):
        """Verifies an error message is shown when no CSV file is uploaded."""
        doc = self.go('/haiti/api/import')
        form = doc.cssselect_one('form#persons-import-form')
        doc = self.s.submit(form, key='test_key')
        assert 'Please specify at least one CSV file.' in doc.text

    def test_import_invalid_authentication_key(self):
        """Verifies an error message is shown when auth key is invalid."""
        self._write_csv_file([
            'person_record_id,source_date,full_name',
            'test.google.com/person1,2013-02-26T09:10:00Z,_test_full_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.cssselect_one('form#persons-import-form')
        doc = self.s.submit(form, key='bad_key', content=open(self.filename))
        assert 'Missing or invalid authorization key' in doc.text

    def test_import_broken_csv(self):
        """Verifies an error message is shown when a broken CSV is imported."""
        self._write_csv_file([
            'person_record_id,source_date,\0full_name',  # contains null
            'test.google.com/person1,2013-02-26T09:10:00Z,_test_full_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.cssselect_one('form#persons-import-form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))
        assert 'The CSV file is formatted incorrectly' in doc.text
        assert Person.all().count() == 0
        assert Note.all().count() == 0

    def test_import_one_person(self):
        """Verifies a Person entry is successfully imported."""
        self._write_csv_file([
            'person_record_id,source_date,full_name',
            'test.google.com/person1,2013-02-26T09:10:00Z,_test_full_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.cssselect_one('form#persons-import-form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))
        assert 'Person records Imported 1 of 1' in re.sub('\\s+', ' ', doc.text)
        assert Person.all().count() == 1
        assert Note.all().count() == 0
        person = Person.all().get()
        assert person.record_id == 'test.google.com/person1'
        assert person.source_date == datetime.datetime(2013, 2, 26, 9, 10, 0)
        assert person.full_name == '_test_full_name'
        self.verify_api_log(ApiActionLog.WRITE, person_records=1)

    def test_import_one_note(self):
        """Verifies a Note entry is successfully imported."""
        person = Person(
            key_name='haiti:test.google.com/person1',
            repo='haiti',
            author_name='_test_author_name',
            full_name='_test_given_name _test_family_name',
            given_name='_test_given_name',
            family_name='_test_family_name',
            source_date=ServerTestsBase.TEST_DATETIME,
            entry_date=ServerTestsBase.TEST_DATETIME,
            latest_status='',
        )
        db.put(person)

        self._write_csv_file([
            'note_record_id,person_record_id,author_name,source_date,status',
            'test.google.com/note1,test.google.com/person1,' +
            '_test_author_name,2013-02-26T09:10:00Z,believed_alive',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.cssselect_one('form#notes-import-form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))

        assert 'Note records Imported 1 of 1' in re.sub('\\s+', ' ', doc.text)

        assert Note.all().count() == 1
        note = Note.all().get()
        assert note.record_id == 'test.google.com/note1'
        assert note.person_record_id == 'test.google.com/person1'
        assert note.author_name == '_test_author_name'
        assert note.source_date == datetime.datetime(2013, 2, 26, 9, 10, 0)
        assert note.status == 'believed_alive'

        assert Person.all().count() == 1
        person = Person.all().get()
        assert person.latest_status == 'believed_alive'

        self.verify_api_log(ApiActionLog.WRITE, note_records=1)

    def test_import_only_digit_record_id(self):
        """Verifies that a Person entry is successfully imported even if the
        record_id just contains digits, and that the imported record_id is
        prefixed with the write domain associated with auth key."""
        self._write_csv_file([
            'person_record_id,source_date,full_name',
            '1,2013-02-26T09:10:00Z,_test_full_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.cssselect_one('form#persons-import-form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))
        assert 'Person records Imported 1 of 1' in re.sub('\\s+', ' ', doc.text)
        assert Person.all().count() == 1
        assert Note.all().count() == 0
        person = Person.all().get()
        assert person.record_id == 'test.google.com/1'
        assert person.source_date == datetime.datetime(2013, 2, 26, 9, 10, 0)
        assert person.full_name == '_test_full_name'
        self.verify_api_log(ApiActionLog.WRITE, person_records=1)

    def test_import_domain_dont_match(self):
        """Verifies we reject a Person entry whose record_id domain does not
        match that of authentication key."""
        self._write_csv_file([
            'person_record_id,source_date,full_name',
            'different.google.com/person1,2013-02-26T09:10:00Z,_test_full_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.cssselect_one('form#persons-import-form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))
        assert 'Person records Imported 0 of 1' in re.sub('\\s+', ' ', doc.text)
        assert 'Not in authorized domain' in doc.text
        assert Person.all().count() == 0
        assert Note.all().count() == 0
        self.verify_api_log(ApiActionLog.WRITE)

    def test_import_one_person_and_note_on_separate_rows(self):
        """Verifies a Note entry and a Person entry on separate rows are
        successfully imported."""
        self._write_csv_file([
            'person_record_id,full_name,source_date,note_record_id,author_name',
            'test.google.com/person1,_test_full_name,2013-02-26T09:10:00Z,,',
            'test.google.com/person1,,2013-02-26T09:10:00Z,' +
            'test.google.com/note1,_test_author_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.cssselect_one('form#persons-import-form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))
        assert 'Person records Imported 1 of 1' in re.sub('\\s+', ' ', doc.text)
        assert 'Note records Imported 1 of 1' in re.sub('\\s+', ' ', doc.text)
        assert Person.all().count() == 1
        assert Note.all().count() == 1
        person = Person.all().get()
        assert person.record_id == 'test.google.com/person1'
        assert person.source_date == datetime.datetime(2013, 2, 26, 9, 10, 0)
        assert person.full_name == '_test_full_name'
        note = Note.all().get()
        assert note.record_id == 'test.google.com/note1'
        assert note.person_record_id == 'test.google.com/person1'
        assert note.author_name == '_test_author_name'
        assert note.source_date == datetime.datetime(2013, 2, 26, 9, 10, 0)
        self.verify_api_log(ApiActionLog.WRITE, person_records=1, note_records=1)

    def test_import_one_person_and_note_on_single_row(self):
        """Verifies a Note entry and a Person entry on a single row are
        successfully imported."""
        self._write_csv_file([
            'person_record_id,full_name,source_date,note_record_id,author_name',
            'test.google.com/person1,_test_full_name,2013-02-26T09:10:00Z,' +
            'test.google.com/note1,_test_author_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.cssselect_one('form#persons-import-form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))
        assert 'Person records Imported 1 of 1' in re.sub('\\s+', ' ', doc.text)
        assert 'Note records Imported 1 of 1' in re.sub('\\s+', ' ', doc.text)
        assert Person.all().count() == 1
        assert Note.all().count() == 1
        person = Person.all().get()
        assert person.record_id == 'test.google.com/person1'
        assert person.source_date == datetime.datetime(2013, 2, 26, 9, 10, 0)
        assert person.full_name == '_test_full_name'
        note = Note.all().get()
        assert note.record_id == 'test.google.com/note1'
        assert note.person_record_id == 'test.google.com/person1'
        assert note.author_name == '_test_author_name'
        assert note.source_date == datetime.datetime(2013, 2, 26, 9, 10, 0)
        self.verify_api_log(ApiActionLog.WRITE, person_records=1, note_records=1)

    def test_import_note_for_non_existent_person(self):
        """Verifies a Note entry is not imported if it points to a non-existent
        person_record_id."""
        self._write_csv_file([
            'note_record_id,person_record_id,author_name,source_date,status',
            'test.google.com/note1,test.google.com/non_existent_person,' +
            '_test_author_name,2013-02-26T09:10:00Z,believed_alive',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.cssselect_one('form#notes-import-form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))

        assert 'Note records Imported 0 of 1' in re.sub('\\s+', ' ', doc.text)
        assert 'There is no person record with the person_record_id' in doc.text
        assert Note.all().count() == 0
        self.verify_api_log(ApiActionLog.WRITE)

    def test_import_xlsx(self):
        """Verifies an xlsx file import."""
        doc = self.go('/haiti/api/import')
        form = doc.cssselect_one('form#persons-import-form')
        doc = self.s.submit(form, key='test_key',
            content=open(self.get_test_filepath('persons.xlsx')))
        assert 'Person records Imported 3 of 3' in re.sub('\\s+', ' ', doc.text)
        assert Person.all().count() == 3
        person = Person.all().get()  # check the first Person
        assert person.record_id == 'test.google.com/12345'
        assert person.source_date == datetime.datetime(2013, 11, 12, 7, 26, 0)
        assert person.full_name == 'Mary Example'
        self.verify_api_log(ApiActionLog.WRITE, person_records=3, note_records=0)
