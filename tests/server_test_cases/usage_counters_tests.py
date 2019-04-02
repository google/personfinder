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

import model

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
                      text='_note_text',  # unspecified note status
                      author_name='_note_author_name')

    def test_person_counter(self):
        """Test if person counter increment correctly"""
        num_persons = 3
        # create num_persons of person's records
        for _ in range(num_persons):
            self.create_person_record()
        counters = model.UsageCounter.get('haiti')
        assert counters.person == 3
        #doc = self.go_as_admin('/global/admin/statistics')
        #assert 'haiti' in doc.text
        #assert '# Persons' in doc.text
        ## num_persons of persons are created
        #persons = doc.cssselect_one('#haiti-persons')
        #assert persons.text == str(num_persons)

    def test_note_counter(self):
        """Test of note counter increment correctly"""
        num_notes = 5
        # create a num_notes of note records
        for _ in range(num_notes):
            self.add_person_and_note_record()
        counters = model.UsageCounter.get('haiti')
        assert counters.note == 5
        assert counters.unspecified == 5
        #doc = self.go_as_admin('/global/admin/statistics')
        #assert 'haiti' in doc.text
        #assert '# Notes' in doc.text
        ## one person's record and num_notes of notes are created
        #notes = doc.cssselect_one('#haiti-notes')
        #assert notes.text == str(num_notes)
        # test unspecified status note counter
        #unspecified_status = doc.cssselect_one('#haiti-num_notes_unspecified')
        #assert unspecified_status.text == str(num_notes)

    def test_is_note_author_counter(self):
        """Test if the is_note_author_counter increment when choose
        I want to input my own information in the create form"""
        doc = self.go('/japan/create?given_name=_test_given_name&'
                      'family_name=_test_family_name&role=provide')
        form = doc.cssselect_one('form')
        self.s.submit(form,
                      own_info='yes',  # status == 'is_note_author'
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      text='_note_text')
        counters = model.UsageCounter.get('japan')
        assert counters.is_note_author == 1
        #doc = self.go_as_admin('/global/admin/statistics')
        #assert 'japan' in doc.text
        #is_note_author_counter = doc.cssselect_one('#japan-num_notes_is_note_author')
        #assert is_note_author_counter.text == '1'

    def test_status_counter(self):
        """Test of counter increment based on the given status_name"""
        def increment_counter_and_assert(status_name, amount):
            self.create_person_record()
            for _ in range(amount):
              self.s.submit(self.s.doc.cssselect_one('input.add-note'))
              self.s.submit(self.s.doc.cssselect_one('form'),
                            own_info='no',
                            author_made_contact='yes',
                            status=status_name,
                            text='_note_text',
                            author_name='_note_author_name')
            counters = model.UsageCounter.get('haiti')
            assert getattr(counters, status_name) == amount
            #doc = self.go_as_admin('/global/admin/statistics')
            #assert 'haiti' in doc.text
            #assert status_name in doc.text
            #status_name_counter = doc.cssselect_one('#haiti-num_notes_' + status_name)
            #assert status_name_counter.text == str(amount)

        increment_counter_and_assert('is_note_author', 3)
        increment_counter_and_assert('believed_alive', 5)
        increment_counter_and_assert('believed_dead', 2)
        increment_counter_and_assert('believed_missing', 4)
        increment_counter_and_assert('information_sought', 6)
