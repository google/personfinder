#!/usr/bin/python2.7
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

    def test_resource_caching(self):
        """Verifies that Resources are cached properly."""
        # There's no file here.
        self.go('/global/foo.txt')
        assert self.s.status == 404
        self.go('/global/foo.txt?lang=fr')
        assert self.s.status == 404

        # Add a Resource to be served as the static file.
        bundle = ResourceBundle(key_name='1')
        Resource(
            parent=bundle, key_name='static/foo.txt', content='hello').put()
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content_bytes == 'hello'

        # Add a localized Resource.
        fr_key = Resource(parent=bundle, key_name='static/foo.txt:fr',
                          content='bonjour').put()
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content_bytes == 'hello'  # original Resource remains cached

        # The cached version should expire after 1 second.
        self.advance_utcnow(seconds=1.1)
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content_bytes == 'bonjour'

        # Change the non-localized Resource.
        Resource(
            parent=bundle, key_name='static/foo.txt', content='goodbye').put()
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content_bytes == 'bonjour'
                # no effect on the localized Resource

        # Remove the localized Resource.
        db.delete(fr_key)
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content_bytes == 'bonjour'
                # localized Resource remains cached

        # The cached version should expire after 1 second.
        self.advance_utcnow(seconds=1.1)
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content_bytes == 'goodbye'

    def test_admin_resources(self):
        # Verify that the bundle listing loads.
        doc = self.go_as_admin('/global/admin/resources')

        # Add a new bundle (redirects to the new bundle's resource listing).
        doc = self.s.submit(doc.cssselect('form')[-1], resource_bundle='xyz')
        assert doc.cssselect_one('a.sel').text == 'Bundle: xyz'
        bundle = ResourceBundle.get_by_key_name('xyz')
        assert bundle

        # Add a resource (redirects to the resource's edit page).
        doc = self.s.submit(doc.cssselect('form')[0], resource_name='abc')
        assert doc.cssselect_one('a.sel').text == 'Resource: abc'

        # The new Resource shouldn't exist in the datastore until it is saved.
        assert not Resource.get_by_key_name('abc', parent=bundle)

        # Enter some content for the resource.
        doc = self.s.submit(doc.cssselect('form')[0], content='pqr')
        assert Resource.get_by_key_name('abc', parent=bundle).content == 'pqr'

        # Use the breadcrumb navigation bar to go back to the resource listing.
        doc = self.s.follow('Bundle: xyz')

        # Add a localized variant of the resource.
        row = doc.xpath_one('//tr[td[normalize-space(.)="abc"]]')
        doc = self.s.submit(row.cssselect('form')[0], resource_lang='pl')
        assert doc.cssselect_one('a.sel').text == 'pl: Polish'

        # Enter some content for the localized resource.
        doc = self.s.submit(doc.cssselect('form')[0], content='jk')
        assert Resource.get_by_key_name('abc:pl', parent=bundle).content == 'jk'

        # Confirm that both the generic and localized resource are listed.
        doc = self.s.follow('Bundle: xyz')
        resource_texts = [a.text for a in doc.cssselect('a.resource')]
        assert 'abc' in resource_texts
        assert 'pl' in resource_texts

        # Copy all the resources to a new bundle.
        doc = self.s.submit(doc.cssselect('form')[-1], resource_bundle='zzz',
                            resource_bundle_original='xyz')
        parent = ResourceBundle.get_by_key_name('zzz')
        assert Resource.get_by_key_name('abc', parent=parent).content == 'pqr'
        assert Resource.get_by_key_name('abc:pl', parent=parent).content == 'jk'

        # Verify that we can't add a resource to the default bundle.
        bundle = ResourceBundle.get_by_key_name('1')
        assert(bundle)
        doc = self.go_as_admin('/global/admin/resources')
        doc = self.s.follow('1 (default)')
        self.s.submit(doc.cssselect('form')[0], resource_name='abc')
        assert not Resource.get_by_key_name('abc', parent=bundle)

        # Verify that we can't edit a resource in the default bundle.
        self.s.back()
        doc = self.s.follow('base.html.template')
        self.s.submit(doc.cssselect('form')[0], content='xyz')
        assert not Resource.get_by_key_name('base.html.template', parent=bundle)

        # Verify that we can't copy resources into the default bundle.
        doc = self.go_as_admin('/global/admin/resources')
        doc = self.s.follow('xyz')
        doc = self.s.submit(doc.cssselect('form')[-1], resource_bundle='1',
                            resource_bundle_original='xyz')
        assert not Resource.get_by_key_name('abc', parent=bundle)

        # Switch the default bundle version.
        doc = self.go_as_admin('/global/admin/resources')
        doc = self.s.submit(
                doc.cssselect('form')[0], resource_bundle_default='xyz')
        assert 'xyz (default)' in doc.text
        # Undo.
        doc = self.s.submit(
                doc.cssselect('form')[0], resource_bundle_default='1')
        assert '1 (default)' in doc.text


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

    def test_admin_dashboard(self):
        """Visits the dashboard page and makes sure it doesn't crash."""
        db.put([Counter(
            scan_name='Person', repo='haiti', last_key='', count_all=278
        ), Counter(
            scan_name='Person', repo='pakistan', last_key='',
            count_all=127
        ), Counter(
            scan_name='Note', repo='haiti', last_key='', count_all=12
        ), Counter(
            scan_name='Note', repo='pakistan', last_key='', count_all=8
        )])
        assert self.go_as_admin('/global/admin/dashboard')
        assert self.s.status == 200
