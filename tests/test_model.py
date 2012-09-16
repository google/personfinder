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
from utils import get_utcnow, set_utcnow_for_test

class ModelTests(unittest.TestCase):
    '''Test the loose odds and ends.'''

    def setUp(self):
        set_utcnow_for_test(datetime(2010, 1, 1))
        self.p1 = model.Person.create_original(
            'haiti',
            given_name='John',
            family_name='Smith',
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
            expiry_date=datetime(2010, 2, 1))
        self.p2 = model.Person.create_original(
            'haiti',
            given_name='Tzvika',
            family_name='Hartman',
            home_street='Herzl St.',
            home_city='Tel Aviv',
            home_state='Israel',
            entry_date=datetime(2010, 1, 1),
            expiry_date=datetime(2010, 3, 1))
        self.p3 = model.Person.create_original(
            'haiti',
            given_name='Third',
            family_name='Person',
            home_street='Main St.',
            home_city='San Francisco',
            home_state='California',
            entry_date=datetime(2010, 1, 1),
            expiry_date=datetime(2020, 3, 1))
        self.key_p1 = db.put(self.p1)
        self.key_p2 = db.put(self.p2)
        self.key_p3 = db.put(self.p3)

        # Link p2 and p3 to p1
        self.n1_1 = model.Note.create_original(
            'haiti',
            person_record_id=self.p1.record_id,
            linked_person_record_id=self.p2.record_id,
            status=u'believed_missing',
            author_email='note1.author@example.com',
            author_made_contact=False,
            photo_url='http://example.com/note1.photo.jpg',
            entry_date=get_utcnow(),
            source_date=datetime(2000, 1, 1))
        self.n1_2 = model.Note.create_original(
            'haiti',
            person_record_id=self.p1.record_id,
            author_made_contact=True,
            entry_date=get_utcnow(),
            source_date=datetime(2000, 2, 2))
        self.n1_3 = model.Note.create_original(
            'haiti',
            person_record_id=self.p1.record_id,
            linked_person_record_id=self.p3.record_id,
            entry_date=get_utcnow(),
            source_date=datetime(2000, 3, 3))
        # Link p1 and p3 to p2
        self.n2_1 = model.Note.create_original(
            'haiti',
            person_record_id=self.p2.record_id,
            linked_person_record_id=self.p1.record_id,
            entry_date=get_utcnow(),
            source_date=datetime(2000, 1, 1))
        self.n2_2 = model.Note.create_original(
            'haiti',
            person_record_id=self.p2.record_id,
            linked_person_record_id=self.p3.record_id,
            entry_date=get_utcnow(),
            source_date=datetime(2000, 2, 2))
        # Link p2 and p1 to p3
        self.n3_1 = model.Note.create_original(
            'haiti',
            person_record_id=self.p3.record_id,
            linked_person_record_id=self.p2.record_id,
            entry_date=get_utcnow(),
            source_date=datetime(2000, 1, 1))
        self.n3_2 = model.Note.create_original(
            'haiti',
            person_record_id=self.p3.record_id,
            linked_person_record_id=self.p1.record_id,
            entry_date=get_utcnow(),
            source_date=datetime(2000, 2, 2))
        self.key_n1_1 = db.put(self.n1_1)
        self.key_n1_2 = db.put(self.n1_2)
        self.key_n1_3 = db.put(self.n1_3)
        self.key_n2_1 = db.put(self.n2_1)
        self.key_n2_2 = db.put(self.n2_2)
        self.key_n3_1 = db.put(self.n3_1)
        self.key_n3_2 = db.put(self.n3_2)

        # Update the Person entity according to the Note.
        self.p1.update_from_note(self.n1_1)
        self.p1.update_from_note(self.n1_2)
        self.p1.update_from_note(self.n1_3)
        self.p2.update_from_note(self.n2_1)
        self.p2.update_from_note(self.n2_2)
        self.p3.update_from_note(self.n3_1)
        self.p3.update_from_note(self.n3_2)
        db.put(self.p1)
        db.put(self.p2)
        db.put(self.p3)

        self.to_delete = [self.p1, self.p2, self.p3,
                          self.n1_1, self.n1_2, self.n1_3,
                          self.n2_1, self.n2_2,
                          self.n3_1, self.n3_2]

    def tearDown(self):
        db.delete(self.to_delete)

    def test_associated_emails(self):
        emails = self.p1.get_associated_emails()
        expected = set(['alice.smith@gmail.com', u'note1.author@example.com'])
        assert emails == expected, \
            'associated emails %s, expected %s' % (emails, expected)

    def test_person(self):
        assert self.p1.given_name == 'John'
        assert self.p1.photo_url == ''
        assert self.p1.is_clone() == False
        assert model.Person.get('haiti', self.p1.record_id).record_id == \
            self.p1.record_id
        assert model.Person.get('haiti', self.p2.record_id).record_id == \
            self.p2.record_id
        assert model.Person.get('haiti', self.p1.record_id).record_id != \
            self.p2.record_id

        # Testing prefix properties
        assert hasattr(self.p1, 'given_name_n_')
        assert hasattr(self.p1, 'home_street_n1_')
        assert hasattr(self.p1, 'home_postal_code_n2_')

        # Testing indexing properties
        assert self.p1._fields_to_index_properties == \
            ['given_name', 'family_name', 'full_name']
        assert self.p1._fields_to_index_by_prefix_properties == \
            ['given_name', 'family_name', 'full_name']

        # Test propagation of Note fields to Person.
        assert self.p1.latest_status == u'believed_missing'  # from first note
        assert self.p1.latest_status_source_date == datetime(2000, 1, 1)
        assert self.p1.latest_found == True  # from second note
        assert self.p1.latest_found_source_date == datetime(2000, 2, 2)

        # Adding a Note with only 'author_made_contact' should not affect
        # 'last_status'.
        n1_3 = model.Note.create_original(
            'haiti', person_record_id=self.p1.record_id,
            author_made_contact=False, entry_date=get_utcnow(),
            source_date=datetime(2000, 3, 3))
        self.p1.update_from_note(n1_3)
        assert self.p1.latest_status == u'believed_missing'
        assert self.p1.latest_status_source_date == datetime(2000, 1, 1)
        assert self.p1.latest_found == False
        assert self.p1.latest_found_source_date == datetime(2000, 3, 3)

        # Adding a Note with only 'status' should not affect 'last_found'.
        n1_4 = model.Note.create_original(
            'haiti', person_record_id=self.p1.record_id,
            author_made_contact=None, status=u'is_note_author',
            entry_date=get_utcnow(),
            source_date=datetime(2000, 4, 4))
        self.p1.update_from_note(n1_4)
        assert self.p1.latest_status == u'is_note_author'
        assert self.p1.latest_status_source_date == datetime(2000, 4, 4)
        assert self.p1.latest_found == False
        assert self.p1.latest_found_source_date == datetime(2000, 3, 3)

        # Adding an older Note should not affect either field.
        n1_5 = model.Note.create_original(
            'haiti', person_record_id=self.p1.record_id,
            author_made_contact=True, status=u'believed_alive',
            entry_date=get_utcnow(),
            source_date=datetime(2000, 1, 2))
        self.p1.update_from_note(n1_5)
        assert self.p1.latest_status == u'is_note_author'
        assert self.p1.latest_status_source_date == datetime(2000, 4, 4)
        assert self.p1.latest_found == False
        assert self.p1.latest_found_source_date == datetime(2000, 3, 3)

        # Adding a Note with a date in between should affect only one field.
        n1_6 = model.Note.create_original(
            'haiti', person_record_id=self.p1.record_id,
            author_made_contact=True, status=u'believed_alive',
            entry_date=get_utcnow(),
            source_date=datetime(2000, 3, 4))
        self.p1.update_from_note(n1_6)
        assert self.p1.latest_status == u'is_note_author'
        assert self.p1.latest_status_source_date == datetime(2000, 4, 4)
        assert self.p1.latest_found == True
        assert self.p1.latest_found_source_date == datetime(2000, 3, 4)

    def test_note(self):
        assert self.n1_1.is_clone() == False
        assert self.n1_1.status == 'believed_missing'
        assert self.n1_1.author_email == 'note1.author@example.com'
        assert self.n1_1.author_made_contact == False
        assert self.n1_1.photo_url == 'http://example.com/note1.photo.jpg'
        notes = self.p1.get_notes()
        note_ids = [notes[i].record_id for i in range(len(notes))]
        assert self.n1_1.record_id in note_ids
        assert self.n1_2.record_id in note_ids
        assert self.n1_3.record_id in note_ids

        assert model.Note.get('haiti', self.n1_1.record_id).record_id == \
            self.n1_1.record_id
        assert model.Note.get('haiti', self.n1_2.record_id).record_id == \
            self.n1_2.record_id

    def test_linked_persons(self):
        assert self.p2.record_id in self.p1.get_linked_person_ids()
        assert self.p3.record_id in self.p1.get_linked_person_ids()
        assert self.p1.record_id in self.p2.get_linked_person_ids()
        assert self.p3.record_id in self.p2.get_linked_person_ids()

    def test_linked_persons(self):
        assert self.p1.record_id in self.p3.get_linked_person_ids()
        assert self.p2.record_id in self.p3.get_linked_person_ids()
        assert len(self.p2.get_linked_person_ids()) == \
            len(self.p2.get_linked_persons())

    def test_all_linked_persons(self):
        p1_linked = self.p1.get_all_linked_persons()
        p2_linked = self.p2.get_all_linked_persons()
        p3_linked = self.p3.get_all_linked_persons()
        assert len(p1_linked) == 2

        p1_linked_ids = sorted([p.record_id for p in p1_linked] + \
                                   [self.p1.record_id])
        p2_linked_ids = sorted([p.record_id for p in p2_linked] + \
                                   [self.p2.record_id])
        p3_linked_ids = sorted([p.record_id for p in p3_linked] + \
                                   [self.p3.record_id])
        assert p1_linked_ids == p2_linked_ids
        assert p1_linked_ids == p3_linked_ids


    def test_subscription(self):
        sd = 'haiti'
        email1 = 'one@example.com'
        email2 = 'two@example.com'
        s1 = model.Subscription.create(sd, self.p1.record_id, email1, 'fr')
        s2 = model.Subscription.create(sd, self.p1.record_id, email2, 'en')
        key_s1 = db.put(s1)
        key_s2 = db.put(s2)

        assert model.Subscription.get(sd, self.p1.record_id, email1) is not None
        assert model.Subscription.get(sd, self.p1.record_id, email2) is not None
        assert model.Subscription.get(sd, self.p2.record_id, email1) is None
        assert model.Subscription.get(sd, self.p2.record_id, email2) is None
        assert len(self.p1.get_subscriptions()) == 2
        assert len(self.p2.get_subscriptions()) == 0

        s3 = model.Subscription.create(sd, self.p1.record_id, email2, 'ar')
        key_s3 = db.put(s3)
        assert len(self.p1.get_subscriptions()) == 2
        assert model.Subscription.get(
            sd, self.p1.record_id, email2).language == 'ar'
        db.delete([key_s1, key_s2, key_s3])

    def test_past_due(self):
        """Make sure Person records are detected as past due correctly."""
        def assert_past_due_count(expected):
            actual = len(list(model.Person.past_due_records(repo='haiti')))
            assert actual == expected

        assert_past_due_count(0)
        set_utcnow_for_test(datetime(2010, 2, 15))
        assert_past_due_count(1)
        set_utcnow_for_test(datetime(2010, 3, 15))
        assert_past_due_count(2)

    def test_put_expiry_flags(self):
        # Try put_expiry_flags when the record has not expired yet.
        assert not self.p1.is_expired
        self.p1.put_expiry_flags()

        # Both entities should be unexpired.
        p1 = db.get(self.p1.key())
        assert p1.expiry_date
        assert not p1.is_expired
        assert p1.given_name == 'John'
        n1_1 = db.get(self.n1_1.key())
        assert not n1_1.is_expired

        # Advance past the expiry date and try again.
        set_utcnow_for_test(datetime(2010, 2, 3))
        p1.put_expiry_flags()

        # Both entities should be expired.
        p1 = db.get(self.p1.key())
        assert p1.is_expired
        assert p1.given_name == 'John'
        assert p1.source_date == datetime(2010, 2, 3)
        assert p1.entry_date == datetime(2010, 2, 3)
        assert p1.expiry_date == datetime(2010, 2, 1)
        n1_1 = db.get(self.n1_1.key())
        assert n1_1.is_expired

    def test_wipe_contents(self):
        # Advance past the expiry date.
        set_utcnow_for_test(datetime(2010, 2, 3))
        # original_creation_date is auto_now_add, so we override it here.
        self.p1.original_creation_date = datetime(2010, 1, 3)
        self.p1.put()
        self.p1.put_expiry_flags()

        # Try wiping the contents.
        self.p1.wipe_contents()

        p1 = db.get(self.p1.key())
        assert p1.is_expired
        assert p1.given_name == None
        assert p1.source_date == datetime(2010, 2, 3)
        assert p1.entry_date == datetime(2010, 2, 3)
        # verify we preserve the original_creation_date
        assert p1.original_creation_date == datetime(2010, 1, 3)
        assert p1.expiry_date == datetime(2010, 2, 1)
        assert not db.get(self.n1_1.key())

    def test_count_name_chars(self):
        """Regression test for arbitrary characters in a count_name."""
        counter = model.Counter.get_unfinished_or_create('haiti', 'person')
        counter.put()
        self.to_delete.append(counter)

        counter.increment(u'arbitrary \xef characters \u5e73 here')
        counter.put()  # without encode_count_name, this threw an exception


if __name__ == '__main__':
    unittest.main()
