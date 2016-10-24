#!/usr/bin/python2.7
# encoding: utf-8
# Copyright 2016 Google Inc.
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

from server_tests_base import ServerTestsBase

class AdminSummaryTests(ServerTestsBase):
    """Tests that the counter for persons and notes records are working"""

    def create_person_record(self):
        """Create a new person record in haiti repo, direct to view page."""
        doc = self.go('/haiti/create')
        form = doc.cssselect_one('form')
        return self.s.submit(form,
                      own_info='no',
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      author_name='_test_author_name')

    def add_person_and_note_record(self):
        """Add a new note in haiti repo, redirect to view page."""
        self.create_person_record()  # person's view page
        self.s.submit(
            self.s.doc.cssselect_one('input.add-note'))  # add note page
        return self.s.submit(self.s.doc.cssselect_one('form'),
                      own_info='no',
                      author_made_contact='yes',
                      text='_note_text',
                      author_name='_note_author_name')

    def test_person_counter(self):
        """Test if person_counter increment correctly"""
        num_persons = 3
        # create num_persons of person's records
        for _ in range(num_persons):
            self.create_person_record()
        doc = self.go_as_admin('/global/admin/statistics')
        assert 'haiti' in doc.text
        assert '# Persons' in doc.text
        # num_persons of persons are created
        repo = doc.cssselect_one('#haiti-repo')
        persons = doc.cssselect_one('#haiti-persons')
        assert persons.text == str(num_persons)

    def test_note_counter(self):
        """Test of note_counter increment correctly"""
        num_notes = 5
        # create a num_notes of note records
        for _ in range(num_notes):
            self.add_person_and_note_record()
        doc = self.go_as_admin('/global/admin/statistics')
        assert 'haiti' in doc.text
        assert '# Notes' in doc.text
        # one person's record and num_notes of notes are created
        notes = doc.cssselect_one('#haiti-notes')
        assert notes.text == str(num_notes)
