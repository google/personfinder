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

"""Tests for model.py."""

from datetime import datetime
from google.appengine.ext import db
import unittest
import model
import logging


class ModelTests(unittest.TestCase):
    '''Test the loose odds and ends.'''

    def setUp(self):
        self.p1 = model.Person.create_original(
            'haiti',
            first_name='John',
            last_name='Smith',
            home_street='Washington St.',
            home_city='Los Angeles',
            home_state='California',
            home_postal_code='11111',
            home_neighborhood='Good Neighborhood',
            author_name='Alice Smith',
            author_phone='111-111-1111',
            author_email='alice.smith@gmail.com',
            source_url='https://www.source.com',
            source_date=datetime(2010, 1, 1),
            source_name='Source Name',
            entry_date=datetime(2010, 1, 1),
            other='')
        self.p2 = model.Person.create_original(
            'haiti',
            first_name='Tzvika',
            last_name='Hartman',
            home_street='Herzl St.',
            home_city='Tel Aviv',
            home_state='Israel',
            entry_date=datetime(2010, 1, 1),
            other='')
        self.key_p1 = db.put(self.p1)
        self.key_p2 = db.put(self.p2)

        self.n1_1 = model.Note.create_original(
            'haiti',
            person_record_id=self.p1.record_id,
            linked_person_record_id=self.p2.record_id,
            status=u'believed_missing',
            found=False,
            source_date=datetime(2000, 1, 1))
        self.n1_2 = model.Note.create_original(
            'haiti',
            person_record_id=self.p1.record_id,
            found=True,
            source_date=datetime(2000, 2, 2))
        self.key_n1_1 = db.put(self.n1_1)
        self.key_n1_2 = db.put(self.n1_2)

        # Update the Person entity according to the Note.
        self.p1.update_from_note(self.n1_1)
        self.p1.update_from_note(self.n1_2)
        db.put(self.p1)

    def tearDown(self):
        db.delete([self.key_p1, self.key_p2, self.key_n1_1, self.key_n1_2])

    def test_person(self):
        assert self.p1.first_name == 'John'
        assert self.p1.photo_url == ''
        assert self.p1.is_clone() == False
        assert model.Person.get('haiti', self.p1.record_id).record_id == \
            self.p1.record_id
        assert model.Person.get('haiti', self.p2.record_id).record_id == \
            self.p2.record_id
        assert model.Person.get('haiti', self.p1.record_id).record_id != \
            self.p2.record_id

        # Testing prefix properties
        assert hasattr(self.p1, 'first_name_n_')
        assert hasattr(self.p1, 'home_street_n1_')
        assert hasattr(self.p1, 'home_postal_code_n2_')

        # Testing indexing properties
        assert self.p1._fields_to_index_properties == \
            ['first_name', 'last_name']
        assert self.p1._fields_to_index_by_prefix_properties == \
            ['first_name', 'last_name']

        # Test propagation of Note fields to Person.
        assert self.p1.latest_status == u'believed_missing'  # from first note
        assert self.p1.latest_status_source_date == datetime(2000, 1, 1)
        assert self.p1.latest_found == True  # from second note
        assert self.p1.latest_found_source_date == datetime(2000, 2, 2)

        # Adding a Note with only 'found' should not affect 'last_status'.
        n1_3 = model.Note.create_original(
            'haiti', person_record_id=self.p1.record_id, found=False,
            source_date=datetime(2000, 3, 3))
        self.p1.update_from_note(n1_3)
        assert self.p1.latest_status == u'believed_missing'
        assert self.p1.latest_status_source_date == datetime(2000, 1, 1)
        assert self.p1.latest_found == False
        assert self.p1.latest_found_source_date == datetime(2000, 3, 3)

        # Adding a Note with only 'status' should not affect 'last_found'.
        n1_4 = model.Note.create_original(
            'haiti', person_record_id=self.p1.record_id,
            found=None, status=u'is_note_author',
            source_date=datetime(2000, 4, 4))
        self.p1.update_from_note(n1_4)
        assert self.p1.latest_status == u'is_note_author'
        assert self.p1.latest_status_source_date == datetime(2000, 4, 4)
        assert self.p1.latest_found == False
        assert self.p1.latest_found_source_date == datetime(2000, 3, 3)

        # Adding an older Note should not affect either field.
        n1_5 = model.Note.create_original(
            'haiti', person_record_id=self.p1.record_id,
            found=True, status=u'believed_alive',
            source_date=datetime(2000, 1, 2))
        self.p1.update_from_note(n1_5)
        assert self.p1.latest_status == u'is_note_author'
        assert self.p1.latest_status_source_date == datetime(2000, 4, 4)
        assert self.p1.latest_found == False
        assert self.p1.latest_found_source_date == datetime(2000, 3, 3)

        # Adding a Note with a date in between should affect only one field.
        n1_6 = model.Note.create_original(
            'haiti', person_record_id=self.p1.record_id,
            found=True, status=u'believed_alive',
            source_date=datetime(2000, 3, 4))
        self.p1.update_from_note(n1_6)
        assert self.p1.latest_status == u'is_note_author'
        assert self.p1.latest_status_source_date == datetime(2000, 4, 4)
        assert self.p1.latest_found == True
        assert self.p1.latest_found_source_date == datetime(2000, 3, 4)
        
        # Adding email to list of subscribers
        email1='author@example.com'
        email2='author2@example.com'
        self.p1.add_subscriber(email1)
        assert self.p1.subscribed_persons.count(email1) == 1
        assert self.p1.subscribed_persons.count(email2) == 0

    def test_note(self):
        assert self.n1_1.is_clone() == False

        assert self.p1.get_notes()[0].record_id == self.n1_1.record_id
        assert self.p1.get_notes()[1].record_id == self.n1_2.record_id
        assert self.p1.get_linked_persons()[0].record_id == self.p2.record_id
        assert self.p2.get_linked_persons() == []

        assert model.Note.get('haiti', self.n1_1.record_id).record_id == \
            self.n1_1.record_id
        assert model.Note.get('haiti', self.n1_2.record_id).record_id == \
            self.n1_2.record_id

if __name__ == '__main__':
    unittest.main()
