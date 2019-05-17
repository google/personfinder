# Copyright 2019 Google Inc.
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

from google.appengine.ext import db

from model import Person
from server_tests_base import ServerTestsBase
import utils


class InputEscapingTests(ServerTestsBase):
    """Tests for safe handling of user input.

    There's two sets of tests in here:
    - Tests that text is escaped. These tests need not cover every form field,
      since Django is doing the work for us. We're just testing a few fields to
      ensure Django autoescaping isn't disabled by accident or something.
    - Tests that URLs are sanitized. We're doing this ourselves, so it needs to
      include every URL field.
    """

    SCRIPT_CONTENT = '<script type="text/javascript">alert("hello")</script>'

    def test_record_content_escaped(self):
        self.go('/haiti/create')
        create_form = self.s.doc.cssselect_one('form')
        # Stuff that's expected to be regular text (i.e., not links or something
        # like that) is escaped automatically by Django, so we don't need to
        # test the complete list of fields. We'll test a few of them just to
        # make sure Django autoescaping doesn't accidentally get disabled.
        self.s.submit(create_form,
                      own_info='no',
                      given_name=InputEscapingTests.SCRIPT_CONTENT,
                      family_name=InputEscapingTests.SCRIPT_CONTENT,
                      author_name=InputEscapingTests.SCRIPT_CONTENT,
                      description=InputEscapingTests.SCRIPT_CONTENT)
        # Check that the record creation went through and we're on the view page.
        assert 'hello' in self.s.doc.content
        # Check that the <script> tag is not included.
        assert '<script>' not in self.s.doc.content
        # Check that the content was included, but escaped.
        assert '&lt;' in self.s.doc.content

    def test_note_content_escaped(self):
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            author_name='_test1_author_name',
            entry_date=ServerTestsBase.TEST_DATETIME,
            full_name='_test1_full_name',
            sex='male',
            date_of_birth='1970-01-01',
            age='50-60',
            latest_status='believed_missing'
        ))
        self.go('/haiti/view?id=test.google.com/person.123&lang=en')
        self.s.submit(self.s.doc.cssselect_one('input.add-note'))
        note_form = self.s.doc.cssselect_one('form')
        params = {'own_info': 'no',
                  'given_name': InputEscapingTests.SCRIPT_CONTENT,
                  'family_name': InputEscapingTests.SCRIPT_CONTENT,
                  'author_name': InputEscapingTests.SCRIPT_CONTENT,
                  'text': InputEscapingTests.SCRIPT_CONTENT}
        details_page = self.s.submit(note_form, **params)

    def test_xss_photo(self):
        person, note = self.setup_person_and_note()
        photo = self.setup_photo(person)
        note_photo = self.setup_photo(note)
        for record in [person, note]:
            doc = self.go('/haiti/view?id=' + person.record_id)
            assert record.photo_url not in doc.content
            record.photo_url = 'http://xyz.com/abc.jpg'
            record.put()
            doc = self.go('/haiti/view?id=' + person.record_id)
            assert '//xyz.com/abc.jpg' in doc.content
            record.photo_url = 'bad_things://xyz'
            record.put()
            doc = self.go('/haiti/view?id=' + person.record_id)
            assert record.photo_url not in doc.content

    def test_xss_source_url(self):
        person, note = self.setup_person_and_note()
        doc = self.go('/haiti/view?id=' + person.record_id)
        assert person.source_url in doc.content
        person.source_url = 'javascript:alert(1);'
        person.put()
        doc = self.go('/haiti/view?id=' + person.record_id)
        assert person.source_url not in doc.content

    def test_xss_profile_urls(self):
        profile_urls = ['http://abc.com', 'http://def.org', 'http://ghi.net']
        person, note = self.setup_person_and_note()
        person.profile_urls = '\n'.join(profile_urls)
        person.put()
        doc = self.go('/haiti/view?id=' + person.record_id)
        for profile_url in profile_urls:
            assert profile_url in doc.content
        XSS_URL_INDEX = 1
        profile_urls[XSS_URL_INDEX] = 'javascript:alert(1);'
        person.profile_urls = '\n'.join(profile_urls)
        person.put()
        doc = self.go('/haiti/view?id=' + person.record_id)
        for i, profile_url in enumerate(profile_urls):
            if i == XSS_URL_INDEX:
                assert profile_url not in doc.content
            else:
                assert profile_url in doc.content
