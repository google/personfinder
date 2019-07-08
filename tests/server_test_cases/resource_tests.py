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

from model import *
from resources import Resource, ResourceBundle
from server_tests_base import ServerTestsBase


class ResourceTests(ServerTestsBase):
    """Tests that verify the Resource mechanism."""
    def test_resource_override(self):
        """Verifies that Resources in the datastore override files on disk."""
        # Should render normally.
        doc = self.go('/haiti/create')
        assert 'xyz' not in doc.content

        # This Resource should override the create.html.template file.
        bundle = ResourceBundle(key_name='1')
        key1 = Resource(parent=bundle,
                        key_name='create.html.template',
                        content='xyz{{env.repo}}xyz').put()
        doc = self.go('/haiti/create')
        assert 'xyzhaitixyz' not in doc.content  # old template is still cached

        # The new template should take effect after 1 second.
        self.advance_utcnow(seconds=1.1)
        doc = self.go('/haiti/create')
        assert 'xyzhaitixyz' in doc.content

        # A plain .html Resource should override the .html.template Resource.
        key2 = Resource(parent=bundle,
                        key_name='create.html', content='xyzxyzxyz').put()
        self.advance_utcnow(seconds=1.1)
        doc = self.go('/haiti/create')
        assert 'xyzxyzxyz' in doc.content

        # After removing both Resources, should fall back to the original file.
        db.delete([key1, key2])
        self.advance_utcnow(seconds=1.1)
        doc = self.go('/haiti/create')
        assert 'xyz' not in doc.content


class CounterTests(ServerTestsBase):
    """Tests related to Counters."""

    def test_tasks_count(self):
        """Tests the counting task."""
        # Add two Persons and two Notes in the 'haiti' repository.
        db.put([Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            author_name='_test1_author_name',
            entry_date=ServerTestsBase.TEST_DATETIME,
            full_name='_test1_full_name',
            sex='male',
            date_of_birth='1970-01-01',
            age='50-60',
            latest_status='believed_missing'
        ), Note(
            key_name='haiti:test.google.com/note.123',
            repo='haiti',
            person_record_id='haiti:test.google.com/person.123',
            entry_date=ServerTestsBase.TEST_DATETIME,
            status='believed_missing'
        ), Person(
            key_name='haiti:test.google.com/person.456',
            repo='haiti',
            author_name='_test2_author_name',
            entry_date=ServerTestsBase.TEST_DATETIME,
            full_name='_test2_full_name',
            sex='female',
            date_of_birth='1970-02-02',
            age='30-40',
            latest_found=True
        ), Note(
            key_name='haiti:test.google.com/note.456',
            repo='haiti',
            person_record_id='haiti:test.google.com/person.456',
            entry_date=ServerTestsBase.TEST_DATETIME,
            author_made_contact=True
        )])

        # Run the counting task (should finish counting in a single run).
        doc = self.go_as_admin('/haiti/tasks/count/person')

        # Check the resulting counters.
        assert Counter.get_count('haiti', 'person.all') == 2
        assert Counter.get_count('haiti', 'person.sex=male') == 1
        assert Counter.get_count('haiti', 'person.sex=female') == 1
        assert Counter.get_count('haiti', 'person.sex=other') == 0
        assert Counter.get_count('haiti', 'person.found=TRUE') == 1
        assert Counter.get_count('haiti', 'person.found=') == 1
        assert Counter.get_count('haiti', 'person.status=believed_missing') == 1
        assert Counter.get_count('haiti', 'person.status=') == 1
        assert Counter.get_count('pakistan', 'person.all') == 0

        # Add a Person in the 'pakistan' repository.
        db.put(Person(
            key_name='pakistan:test.google.com/person.789',
            repo='pakistan',
            author_name='_test3_author_name',
            entry_date=ServerTestsBase.TEST_DATETIME,
            full_name='_test3_full_name',
            sex='male',
            date_of_birth='1970-03-03',
            age='30-40',
        ))

        # Re-run the counting tasks for both repositories.
        doc = self.go('/haiti/tasks/count/person')
        doc = self.go('/pakistan/tasks/count/person')

        # Check the resulting counters.
        assert Counter.get_count('haiti', 'person.all') == 2
        assert Counter.get_count('pakistan', 'person.all') == 1

        # Check that the counted value shows up correctly on the main page.
        doc = self.go('/haiti?flush=*')
        assert 'Currently tracking' not in doc.text

        # Counts less than 100 should not be shown.
        db.put(Counter(scan_name=u'person', repo=u'haiti', last_key=u'',
                       count_all=5L))
        doc = self.go('/haiti?flush=*')
        assert 'Currently tracking' not in doc.text

        db.put(Counter(scan_name=u'person', repo=u'haiti', last_key=u'',
                       count_all=86L))
        doc = self.go('/haiti?flush=*')
        assert 'Currently tracking' not in doc.text

        # Counts should be rounded to the nearest 100.
        db.put(Counter(scan_name=u'person', repo=u'haiti', last_key=u'',
                       count_all=278L))
        doc = self.go('/haiti?flush=*')
        assert 'Currently tracking about 300 records' in doc.text

        # If we don't flush, the previously rendered page should stay cached.
        db.put(Counter(scan_name=u'person', repo=u'haiti', last_key=u'',
                       count_all=411L))
        doc = self.go('/haiti')
        assert 'Currently tracking about 300 records' in doc.text

        # After 10 seconds, the cached page should expire.
        # The counter is also separately cached in memcache, so we have to
        # flush memcache to make the expiry of the cached page observable.
        self.advance_utcnow(seconds=11)
        doc = self.go('/haiti?flush=memcache')
        assert 'Currently tracking about 400 records' in doc.text
