#!/usr/bin/python2.5
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

import calendar
import datetime
import optparse
import os
import pytest
import re
import simplejson
import sys
import tempfile
import time
import unittest
import urlparse

from google.appengine.api import images

import config
from const import ROOT_URL, PERSON_STATUS_TEXT, NOTE_STATUS_TEXT
import download_feed
from model import *
from photo import MAX_IMAGE_DIMENSION
import remote_api
from resources import Resource, ResourceBundle
import reveal
import scrape
import setup_pf as setup
from test_pfif import text_diff
from text_query import TextQuery
import utils

TEST_DATETIME = datetime.datetime(2010, 1, 1, 0, 0, 0)
TEST_TIMESTAMP = calendar.timegm((2010, 1, 1, 0, 0, 0, 0, 0, 0))

NOTE_STATUS_OPTIONS = [
  '',
  'information_sought',
  'is_note_author',
  'believed_alive',
  'believed_missing',
  'believed_dead'
]

last_star = time.time()  # timestamp of the last message that started with '*'.

def log(message, *args):
    """Prints a timestamped message to stderr (handy for debugging or profiling
    tests).  If the message starts with '*', the clock will be reset to zero."""
    global last_star
    now = time.time()
    if isinstance(message, unicode):
        message = message.encode('utf-8')
    else:
        message = str(message)
    print >>sys.stderr, '%6.2f:' % (now - last_star), message, args or ''
    if message[:1] == '*':
        last_star = now

def configure_api_logging(repo='*', enable=True):
    db.delete(ApiActionLog.all())
    config.set_for_repo(repo, api_action_logging=enable)

def verify_api_log(action, api_key='test_key', person_records=None,
                   people_skipped=None, note_records=None, notes_skipped=None):
    action_logs = ApiActionLog.all().fetch(1)
    assert action_logs
    entry = action_logs[0]
    assert entry.action == action \
        and entry.api_key == api_key, \
        'api_key=%s, action=%s' % (entry.api_key, entry.action)
    if person_records:
        assert person_records == entry.person_records
    if people_skipped:
        assert people_skipped == entry.people_skipped
    if note_records:
        assert note_records == entry.note_records
    if notes_skipped:
        assert notes_skipped == entry.notes_skipped

def text_all_logs():
    return '\n'.join(['UserActionLog: action=%s entity_kind=%s' % (
        log.action, log.entity_kind)
        for log in UserActionLog.all().fetch(10)])

def verify_user_action_log(action, entity_kind, fetch_limit=10, **kwargs):
    logs = UserActionLog.all().order('-time').fetch(fetch_limit)
    for log in logs:
        if log.action == action and log.entity_kind == entity_kind:
            for key, value in kwargs.iteritems():
                assert getattr(log, key) == value
            return  # verified
    assert False, text_all_logs()  # not verified

def get_test_data(filename):
    return open(os.path.join(os.environ['TESTS_DIR'], filename)).read()

def assert_params_conform(url, required_params=None, forbidden_params=None):
    """Enforces the presence and non-presence of URL parameters.

    If required_params or forbidden_params is set, this function asserts that
    the given URL contains or does not contain those parameters, respectively.
    """
    required_params = required_params or {}
    forbidden_params = forbidden_params or {}

    # TODO(kpy): Decode the URL, don't match against it directly like this.
    for key, value in required_params.iteritems():
        param_regex = r'\b%s=%s\b' % (re.escape(key), re.escape(value))
        assert re.search(param_regex, url), \
            'URL %s must contain %s=%s' % (url, key, value)

    for key, value in forbidden_params.iteritems():
        param_regex = r'\b%s=%s\b' % (re.escape(key), re.escape(value))
        assert not re.search(param_regex, url), \
            'URL %s must not contain %s=%s' % (url, key, value)


class TestsBase(unittest.TestCase):
    """Base class for test cases."""
    import pytest
    hostport = pytest.config.hostport
    mail_server = pytest.config.mail_server

    # Entities of these kinds won't be wiped between tests
    kinds_to_keep = ['Authorization', 'ConfigEntry', 'Repo']

    def setUp(self):
        """Sets up a scrape Session for each test."""
        # See http://zesty.ca/scrape for documentation on scrape.
        self.s = scrape.Session(verbose=1)
        self.set_utcnow_for_test(TEST_TIMESTAMP, flush='*')

    def tearDown(self):
        """Resets the datastore."""
        setup.wipe_datastore(keep=self.kinds_to_keep)

    def path_to_url(self, path):
        return 'http://%s/personfinder%s' % (self.hostport, path)

    def go(self, path, **kwargs):
        """Navigates the scrape Session to the given path on the test server."""
        return self.s.go(self.path_to_url(path), **kwargs)

    def go_as_admin(self, path, **kwargs):
        """Navigates to the given path with an admin login."""
        scrape.setcookies(self.s.cookiejar, self.hostport,
                          ['dev_appserver_login=admin@example.com:True:1'])
        return self.go(path, **kwargs)

    def set_utcnow_for_test(self, new_utcnow, flush=''):
        """Sets the utils.get_utcnow() clock locally and on the server, and
        optionally also flushes caches on the server.

        Args:
          new_utcnow: A datetime, timestamp, or None to revert to real time.
          flush: Names of caches to flush (see main.flush_caches).
        """
        if new_utcnow is None:
            param = 'real'
        elif isinstance(new_utcnow, (int, float)):
            param = str(new_utcnow)
        else:
            param = calendar.timegm(new_utcnow.utctimetuple())
        path = '/?utcnow=%s&flush=%s' % (param, flush)
        # Requesting '/' gives a fast redirect; to save time, don't follow it.
        scrape.Session(verbose=0).go(self.path_to_url(path), redirects=0)
        utils.set_utcnow_for_test(new_utcnow)

    def advance_utcnow(self, days=0, seconds=0):
        """Advances the utils.get_utcnow() clock locally and on the server."""
        new_utcnow = utils.get_utcnow() + datetime.timedelta(days, seconds)
        self.set_utcnow_for_test(new_utcnow)
        return new_utcnow

    def setup_person_and_note(self, domain='haiti.personfinder.google.org'):
        """Puts a Person with associated Note into the datastore, returning
        (now, person, note) for testing.  This creates an original record
        by default; to make a clone record, pass in a domain name."""
        person = Person(
            key_name='haiti:%s/person.123' % domain,
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_given_name _test_family_name',
            given_name='_test_given_name',
            family_name='_test_family_name',
            source_date=TEST_DATETIME,
            entry_date=TEST_DATETIME
        )
        person.update_index(['old', 'new'])
        note = Note(
            key_name='haiti:%s/note.456' % domain,
            repo='haiti',
            author_email='test2@example.com',
            person_record_id='%s/person.123' % domain,
            source_date=TEST_DATETIME,
            entry_date=TEST_DATETIME,
            text='Testing'
        )
        db.put([person, note])
        return person, note

    def setup_photo(self, record):
        """Stores a Photo for the given Person or Note record, for testing."""
        photo = Photo.create(record.repo, image_data='xyz')
        photo.put()
        record.photo = photo
        record.photo_url = isinstance(record, Note) and \
            '_test_photo_url_for_note' or '_test_photo_url'
        record.put()
        return photo

    def assert_equal_urls(self, actual, expected):
        """Asserts that the two URLs are equal ignoring the order of the query
        parameters.
        """
        parsed_actual = urlparse.urlparse(actual)
        parsed_expected = urlparse.urlparse(expected)
        self.assertEqual(parsed_actual.scheme, parsed_expected.scheme)
        self.assertEqual(parsed_actual.netloc, parsed_expected.netloc)
        self.assertEqual(parsed_actual.path, parsed_expected.path)
        self.assertEqual(
            urlparse.parse_qs(parsed_actual.query),
            urlparse.parse_qs(parsed_expected.query))
        self.assertEqual(parsed_actual.fragment, parsed_expected.fragment)


class ReadOnlyTests(TestsBase):
    """Tests that don't modify data go here."""

    def setUp(self):
        """Sets up a scrape Session for each test."""
        self.s = scrape.Session(verbose=1)
        # These tests don't rely on utcnow, so don't bother to set it.

    def tearDown(self):
        # These tests don't write anything, so no need to reset the datastore.
        pass

    def test_noconfig(self):
        """Check the home page with no config (generic welcome page)."""
        doc = self.go('/')
        assert 'You are now running Person Finder.' in doc.text

    def test_home(self):
        """Check the generic home page."""
        doc = self.go('/global/home.html')
        assert 'You are now running Person Finder.' in doc.text

    def test_tos(self):
        """Check the generic TOS page."""
        doc = self.go('/global/tos.html')
        assert 'Terms of Service' in doc.text

    def test_start(self):
        """Check the start page with no language specified."""
        doc = self.go('/haiti')
        assert 'I\'m looking for someone' in doc.text

    def test_start_english(self):
        """Check the start page with English language specified."""
        doc = self.go('/haiti?lang=en')
        assert 'I\'m looking for someone' in doc.text

    def test_start_french(self):
        """Check the French start page."""
        doc = self.go('/haiti?lang=fr')
        assert 'Je recherche quelqu\'un' in doc.text

    def test_start_creole(self):
        """Check the Creole start page."""
        doc = self.go('/haiti?lang=ht')
        assert u'Mwen ap ch\u00e8che yon moun' in doc.text

    def test_language_xss(self):
        """Regression test for an XSS vulnerability in the 'lang' parameter."""
        doc = self.go('/haiti?lang="<script>alert(1)</script>')
        assert '<script>' not in doc.content

    def test_language_cookie_caching(self):
        """Regression test for caching the wrong language."""

        # Run a session where the default language is English
        en_session = self.s = scrape.Session(verbose=1)

        doc = self.go('/haiti?lang=en')  # sets cookie
        assert 'I\'m looking for someone' in doc.text

        doc = self.go('/haiti')
        assert 'I\'m looking for someone' in doc.text

        # Run a separate session where the default language is French
        fr_session = self.s = scrape.Session(verbose=1)

        doc = self.go('/haiti?lang=fr')  # sets cookie
        assert 'Je recherche quelqu\'un' in doc.text

        doc = self.go('/haiti')
        assert 'Je recherche quelqu\'un' in doc.text

        # Check that this didn't screw up the language for the other session
        self.s = en_session

        doc = self.go('/haiti')
        assert 'I\'m looking for someone' in doc.text

    def test_charsets(self):
        """Checks that pages are delivered in the requested charset."""

        # Try with no specified charset.
        doc = self.go('/haiti?lang=ja', charset=scrape.RAW)
        assert self.s.headers['content-type'] == 'text/html; charset=utf-8'
        meta = doc.firsttag('meta', http_equiv='content-type')
        assert meta['content'] == 'text/html; charset=utf-8'
        # UTF-8 encoding of text (U+5B89 U+5426 U+60C5 U+5831) in title
        assert '\xe5\xae\x89\xe5\x90\xa6\xe6\x83\x85\xe5\xa0\xb1' in doc.content

        # Try with a specific requested charset.
        doc = self.go('/haiti?lang=ja&charsets=shift_jis',
                      charset=scrape.RAW)
        assert self.s.headers['content-type'] == 'text/html; charset=shift_jis'
        meta = doc.firsttag('meta', http_equiv='content-type')
        assert meta['content'] == 'text/html; charset=shift_jis'
        # Shift_JIS encoding of title text
        assert '\x88\xc0\x94\xdb\x8f\xee\x95\xf1' in doc.content

        # Confirm that spelling of charset is preserved.
        doc = self.go('/haiti?lang=ja&charsets=Shift-JIS',
                      charset=scrape.RAW)
        assert self.s.headers['content-type'] == 'text/html; charset=Shift-JIS'
        meta = doc.firsttag('meta', http_equiv='content-type')
        assert meta['content'] == 'text/html; charset=Shift-JIS'
        # Shift_JIS encoding of title text
        assert '\x88\xc0\x94\xdb\x8f\xee\x95\xf1' in doc.content

        # Confirm that UTF-8 takes precedence.
        doc = self.go('/haiti?lang=ja&charsets=Shift-JIS,utf8',
                      charset=scrape.RAW)
        assert self.s.headers['content-type'] == 'text/html; charset=utf-8'
        meta = doc.firsttag('meta', http_equiv='content-type')
        assert meta['content'] == 'text/html; charset=utf-8'
        # UTF-8 encoding of title text
        assert '\xe5\xae\x89\xe5\x90\xa6\xe6\x83\x85\xe5\xa0\xb1' in doc.content

    def test_kddi_charsets(self):
        """Checks that pages are delivered in Shift_JIS if the user agent is a
        feature phone by KDDI."""
        self.s.agent = 'KDDI-HI31 UP.Browser/6.2.0.5 (GUI) MMP/2.0'
        doc = self.go('/haiti?lang=ja', charset=scrape.RAW)
        assert self.s.headers['content-type'] == 'text/html; charset=Shift_JIS'
        meta = doc.firsttag('meta', http_equiv='content-type')
        assert meta['content'] == 'text/html; charset=Shift_JIS'
        # Shift_JIS encoding of title text
        assert '\x88\xc0\x94\xdb\x8f\xee\x95\xf1' in doc.content
        
    def test_query(self):
        """Check the query page."""
        doc = self.go('/haiti/query')
        button = doc.firsttag('input', type='submit')
        assert button['value'] == 'Search for this person'

        doc = self.go('/haiti/query?role=provide')
        button = doc.firsttag('input', type='submit')
        assert button['value'] == 'Provide information about this person'

    def test_results(self):
        """Check the results page."""
        doc = self.go('/haiti/results?query=xy')
        assert 'We have nothing' in doc.text

    def test_create(self):
        """Check the create page."""
        doc = self.go('/haiti/create')
        assert 'Identify who you are looking for' in doc.text

        doc = self.go('/haiti/create?role=provide')
        assert 'Identify who you have information about' in doc.text

        params = [
            'role=provide',
            'family_name=__FAMILY_NAME__',
            'given_name=__GIVEN_NAME__',
            'home_street=__HOME_STREET__',
            'home_neighborhood=__HOME_NEIGHBORHOOD__',
            'home_city=__HOME_CITY__',
            'home_state=__HOME_STATE__',
            'home_postal_code=__HOME_POSTAL_CODE__',
            'description=__DESCRIPTION__',
            'photo_url=__PHOTO_URL__',
            'clone=yes',
            'author_name=__AUTHOR_NAME__',
            'author_phone=__AUTHOR_PHONE__',
            'author_email=__AUTHOR_EMAIL__',
            'source_url=__SOURCE_URL__',
            'source_date=__SOURCE_DATE__',
            'source_name=__SOURCE_NAME__',
            'status=believed_alive',
            'text=__TEXT__',
            'last_known_location=__LAST_KNOWN_LOCATION__',
            'author_made_contact=yes',
            'phone_of_found_person=__PHONE_OF_FOUND_PERSON__',
            'email_of_found_person=__EMAIL_OF_FOUND_PERSON__'
        ]
        doc = self.go('/haiti/create?' + '&'.join(params))
        tag = doc.firsttag('input', name='family_name')
        assert tag['value'] == '__FAMILY_NAME__'

        tag = doc.firsttag('input', name='given_name')
        assert tag['value'] == '__GIVEN_NAME__'

        tag = doc.firsttag('input', name='home_street')
        assert tag['value'] == '__HOME_STREET__'

        tag = doc.firsttag('input', name='home_neighborhood')
        assert tag['value'] == '__HOME_NEIGHBORHOOD__'

        tag = doc.firsttag('input', name='home_city')
        assert tag['value'] == '__HOME_CITY__'

        tag = doc.firsttag('input', name='home_state')
        assert tag['value'] == '__HOME_STATE__'

        tag = doc.firsttag('input', name='home_postal_code')
        assert tag['value'] == '__HOME_POSTAL_CODE__'

        tag = doc.first('textarea', name='description')
        assert tag.text == '__DESCRIPTION__'

        tag = doc.firsttag('input', name='photo_url')
        assert tag['value'] == '__PHOTO_URL__'

        tag = doc.firsttag('input', id='clone_yes')
        assert tag['checked'] == 'checked'

        tag = doc.firsttag('input', name='author_name')
        assert tag['value'] == '__AUTHOR_NAME__'

        tag = doc.firsttag('input', name='author_phone')
        assert tag['value'] == '__AUTHOR_PHONE__'

        tag = doc.firsttag('input', name='author_email')
        assert tag['value'] == '__AUTHOR_EMAIL__'

        tag = doc.firsttag('input', name='source_url')
        assert tag['value'] == '__SOURCE_URL__'

        tag = doc.firsttag('input', name='source_date')
        assert tag['value'] == '__SOURCE_DATE__'

        tag = doc.firsttag('input', name='source_name')
        assert tag['value'] == '__SOURCE_NAME__'

        tag = doc.first('select', name='status')
        tag = doc.firsttag('option', value='believed_alive')
        assert tag['selected'] == 'selected'

        tag = doc.first('textarea', name='text')
        assert tag.text == '__TEXT__'

        tag = doc.first('textarea', name='last_known_location')
        assert tag.text == '__LAST_KNOWN_LOCATION__'

        tag = doc.firsttag('input', id='author_made_contact_yes')
        assert tag['checked'] == 'checked'

        tag = doc.firsttag('input', name='phone_of_found_person')
        assert tag['value'] == '__PHONE_OF_FOUND_PERSON__'

        tag = doc.firsttag('input', name='email_of_found_person')
        assert tag['value'] == '__EMAIL_OF_FOUND_PERSON__'

    def test_view(self):
        """Check the view page."""
        doc = self.go('/haiti/view')
        assert 'No person id was specified' in doc.text

    def test_multiview(self):
        """Check the multiview page."""
        doc = self.go('/haiti/multiview')
        assert 'Compare these records' in doc.text

    def test_photo(self):
        """Check the photo page."""
        doc = self.go('/haiti/photo')
        assert 'Photo id is unspecified or invalid' in doc.text

    def test_static(self):
        """Check that the static files are accessible."""
        doc = self.go('/static/no-photo.gif')
        self.assertEqual(self.s.status, 200)
        assert doc.content.startswith('GIF89a')

    def test_embed(self):
        """Check the embed page."""
        doc = self.go('/haiti/embed')
        assert 'Embedding' in doc.text

    def test_gadget(self):
        """Check the gadget page."""
        doc = self.go('/haiti/gadget')
        assert '<Module>' in doc.content
        assert 'application/xml' in self.s.headers['content-type']

    def test_sitemap(self):
        """Check the sitemap generator."""
        doc = self.go('/haiti/sitemap')
        assert '</sitemapindex>' in doc.content

        doc = self.go('/haiti/sitemap?shard_index=1')
        assert '</urlset>' in doc.content

    def test_config_repo_titles(self):
        doc = self.go('/haiti')
        assert 'Haiti Earthquake' in doc.first('h1').text

        doc = self.go('/pakistan')
        assert 'Pakistan Floods' in doc.first('h1').text

    def test_config_language_menu_options(self):
        doc = self.go('/haiti')
        assert doc.first('option', u'Fran\xe7ais')
        assert doc.first('option', u'Krey\xf2l')
        assert not doc.all('option', u'\u0627\u0631\u062F\u0648')  # Urdu

        doc = self.go('/pakistan')
        assert doc.first('option',u'\u0627\u0631\u062F\u0648')  # Urdu
        assert not doc.all('option', u'Fran\xe7ais')

    def test_config_keywords(self):
        doc = self.go('/haiti')
        meta = doc.firsttag('meta', name='keywords')
        assert 'tremblement' in meta['content']

        doc = self.go('/pakistan')
        meta = doc.firsttag('meta', name='keywords')
        assert 'pakistan flood' in meta['content']

    def test_css(self):
        """Check that the CSS files are accessible."""
        doc = self.go('/global/css?lang=en&ui=default')
        assert 'body {' in doc.content
        doc = self.go('/global/css?lang=en&ui=small')
        assert 'body {' in doc.content
        doc = self.go('/global/css?lang=en&ui=light')
        assert 'Apache License' in doc.content
        doc = self.go('/global/css?lang=ar&ui=default')
        assert 'body {' in doc.content


class PersonNoteTests(TestsBase):
    """Tests that modify Person and Note entities in the datastore go here.
    The contents of the datastore will be reset for each test."""

    def assert_error_deadend(self, page, *fragments):
        """Assert that the given page is a dead-end.

        Checks to make sure there's an error message that contains the given
        fragments.  On failure, fail assertion.  On success, step back.
        """
        error_message = page.first(class_=re.compile(r'.*\berror\b.*'))
        for fragment in fragments:
            assert fragment in error_message.text, (
                '%s missing from error message' % fragment)
        self.s.back()

    # The verify_ functions below implement common fragments of the testing
    # workflow that are assembled below in the test_ methods.

    def verify_results_page(self, num_results, all_have=(), some_have=(),
                            status=()):
        """Verifies conditions on the results page common to seeking and
        providing.  Verifies that all of the results contain all of the
        strings in all_have and that at least one of the results has each
        of some_have.

        Precondition: the current session must be on the results page
        Postcondition: the current session is still on the results page
        """

        # Check that the results are as expected
        result_titles = self.s.doc.all(class_='resultDataTitle')
        assert len(result_titles) == num_results
        for title in result_titles:
            for text in all_have:
                assert text in title.content, \
                    '%s must have %s' % (title.content, text)
        for text in some_have:
            assert any(text in title.content for title in result_titles), \
                'One of %s must have %s' % (result_titles, text)
        if status:
            result_statuses = self.s.doc.all(class_='resultDataPersonFound')
            assert len(result_statuses) == len(status)
            for expected_status, result_status in zip(status, result_statuses):
                assert expected_status in result_status.content, \
                    '"%s" missing expected status: "%s"' % (
                    result_status, expected_status)

    def verify_unsatisfactory_results(self):
        """Verifies the clicking the button at the bottom of the results page.

        Precondition: the current session must be on the results page
        Postcondition: the current session is on the create new record page
        """

        # Click the button to create a new record
        found = False
        for results_form in self.s.doc.all('form'):
            if 'Create a new record' in results_form.content:
                self.s.submit(results_form)
                found = True
        assert found, "didn't find Create a new record in any form"

    def verify_create_form(self, prefilled_params=None, unfilled_params=None):
        """Verifies the behavior of the create form.

        Verifies that the form must contain prefilled_params (a dictionary)
        and may not have any defaults for unfilled_params.

        Precondition: the current session is on the create new record page
        Postcondition: the current session is still on the create page
        """

        create_form = self.s.doc.first('form')
        for key, value in (prefilled_params or {}).iteritems():
            assert create_form.params[key] == value
        for key in unfilled_params or ():
            assert not create_form.params[key]

        # Try to submit without filling in required fields
        self.assert_error_deadend(
            self.s.submit(create_form), 'required', 'try again')

    def verify_note_form(self):
        """Verifies the behavior of the add note form.

        Precondition: the current session is on a page with a note form.
        Postcondition: the current session is still on a page with a note form.
        """

        note_form = self.s.doc.first('form')
        assert 'Tell us the status of this person' in note_form.content
        self.assert_error_deadend(
            self.s.submit(note_form), 'required', 'try again')

    def verify_details_page(self, num_notes, details=None):
        """Verifies the content of the details page.

        Verifies that the details contain the given number of notes and the
        given details.

        Precondition: the current session is on the details page
        Postcondition: the current session is still on the details page
        """

        # Do not assert params.  Upon reaching the details page, you've lost
        # the difference between seekers and providers and the param is gone.
        details = details or {}
        details_page = self.s.doc

        # Person info is stored in matching 'label' and 'value' cells.
        fields = dict(zip(
            [label.text.strip() for label in details_page.all(class_='label')],
            details_page.all(class_='value')))
        for label, value in details.iteritems():
            assert fields[label].text.strip() == value

        actual_num_notes = len(details_page.first(class_='self-notes').all(class_='view note'))
        assert actual_num_notes == num_notes, \
            'expected %s notes, instead was %s' % (num_notes, actual_num_notes)

    def verify_click_search_result(self, n, url_test=lambda u: None):
        """Simulates clicking the nth search result (where n is zero-based).

        Also passes the URL followed to the given url_test function for checking.
        This function should raise an AssertionError on failure.

        Precondition: the current session must be on the results page
        Postcondition: the current session is on the person details page
        """

        # Get the list of links.
        results = self.s.doc.first('div', class_='searchResults')
        result_link = results.all('a', class_='result-link')[n]

        # Verify and then follow the link.
        url_test(result_link['href'])
        self.s.go(result_link['href'])

    def verify_update_notes(self, author_made_contact, note_body, author,
                            status, **kwargs):
        """Verifies the process of adding a new note.

        Posts a new note with the given parameters.

        Precondition: the current session must be on the details page
        Postcondition: the current session is still on the details page
        """

        # Do not assert params.  Upon reaching the details page, you've lost
        # the difference between seekers and providers and the param is gone.
        details_page = self.s.doc
        num_initial_notes = len(details_page.first(class_='self-notes').all(class_='view note'))
        note_form = details_page.first('form')

        params = dict(kwargs)
        params['text'] = note_body
        params['author_name'] = author
        expected = params.copy()
        params['author_made_contact'] = (author_made_contact and 'yes') or 'no'
        if status:
            params['status'] = status
            expected['status'] = str(NOTE_STATUS_TEXT.get(status))

        details_page = self.s.submit(note_form, **params)
        notes = details_page.first(class_='self-notes').all(class_='view note')
        assert len(notes) == num_initial_notes + 1
        new_note = notes[-1]
        for field, text in expected.iteritems():
            if field in ['note_photo_url']:
                url = utils.strip_url_scheme(text)
                assert url in new_note.content, \
                    'Note content %r missing %r' % (new_note.content, url)
            else:
                assert text in new_note.text, \
                    'Note text %r missing %r' % (new_note.text, text)

        # Show this text if and only if the person has been contacted
        assert ('This person has been in contact with someone'
                in new_note.text) == author_made_contact

    def verify_email_sent(self, message_count=1):
        """Verifies email was sent, firing manually from the taskqueue
        if necessary.  """
        # Explicitly fire the send-mail task if necessary
        doc = self.go_as_admin('/_ah/admin/tasks?queue=send-mail')
        try:
            for button in doc.alltags('button', class_='ae-taskqueues-run-now'):
                doc = self.s.submit(d.first('form', name='queue_run_now'),
                                    run_now=button.id)
        except scrape.ScrapeError, e:
            # button not found, assume task completed
            pass
        # taskqueue takes a second to actually queue up multiple requests,
        # so we pause here to allow that to happen.
        count = 0
        while len(self.mail_server.messages) < message_count and count < 10:
            count += 1
            time.sleep(.1)

        self.assertEqual(message_count, len(self.mail_server.messages))

    def test_robots(self):
        """Check that <meta name="robots"> tags appear on the right pages."""
        person = Person(
            key_name='haiti:test.google.com/person.111',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name',
            entry_date=datetime.datetime.utcnow())
        person.update_index(['old', 'new'])
        person.put()

        # Robots are okay on the start page.
        doc = self.go('/haiti')
        assert not doc.alltags('meta', name='robots')

        # Robots are not okay on the view page.
        doc = self.go('/haiti/view?id=test.google.com/person.111')
        assert '_test_full_name' in doc.content
        assert doc.firsttag('meta', name='robots', content='noindex')

        # Robots are not okay on the results page.
        doc = self.go('/haiti/results?role=seek&query=_test_full_name')
        assert '_test_full_name' in doc.content
        assert doc.firsttag('meta', name='robots', content='noindex')

    def test_have_information_small(self):
        """Follow the I have information flow on the small-sized embed."""

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None, required_params={}, forbidden_params={}):
            required_params.setdefault('role', 'provide')
            required_params.setdefault('ui', 'small')
            assert_params_conform(url or self.s.url,
                                  required_params=required_params,
                                  forbidden_params=forbidden_params)

        # Start on the home page and click the "I'm looking for someone" button
        self.go('/haiti?ui=small')
        search_page = self.s.follow('I have information about someone')
        search_form = search_page.first('form')
        assert 'I have information about someone' in search_form.content

        self.assert_error_deadend(
            self.s.submit(search_form),
            'Enter the person\'s given and family names.')

        self.assert_error_deadend(
            self.s.submit(search_form, given_name='_test_given_name'),
            'Enter the person\'s given and family names.')

        self.s.submit(search_form,
                      given_name='_test_given_name',
                      family_name='_test_family_name')
        assert_params()

        # Because the datastore is empty, should see the 'follow this link'
        # text. Click the link.
        create_page = self.s.follow('Follow this link to create a new record')

        assert 'ui=small' not in self.s.url
        given_name_input = create_page.firsttag('input', name='given_name')
        assert '_test_given_name' in given_name_input.content
        family_name_input = create_page.firsttag('input', name='family_name')
        assert '_test_family_name' in family_name_input.content

        # Create a person to search for:
        person = Person(
            key_name='haiti:test.google.com/person.111',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            given_name='_test_given_name',
            family_name='_test_family_name',
            full_name='_test_given_name _test_family_name',
            entry_date=datetime.datetime.utcnow(),
            text='_test A note body')
        person.update_index(['old', 'new'])
        person.put()

        # Try the search again, and should get some results
        self.s.submit(search_form,
                      given_name='_test_given_name',
                      family_name='_test_family_name')
        assert_params()
        assert 'There is one existing record' in self.s.doc.content, \
            ('existing record not found in: %s' %
             utils.encode(self.s.doc.content))

        results_page = self.s.follow('Click here to view results.')
        # make sure the results page has the person on it.
        assert '_test_given_name _test_family_name' in results_page.content, \
            'results page: %s' % utils.encode(results_page.content)

        # test multiple results
        # Create another person to search for:
        person = Person(
            key_name='haiti:test.google.com/person.211',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            given_name='_test_given_name',
            family_name='_test_family_name',
            full_name='_test_given_name _test_family_name',
            entry_date=datetime.datetime.utcnow(),
            text='_test A note body')
        person.update_index(['old', 'new'])
        person.put()

        # Try the search again, and should get some results
        self.s.submit(search_form,
                      given_name='_test_given_name',
                      family_name='_test_family_name')
        assert_params()
        assert 'There are 2 existing records with similar names' \
            in self.s.doc.content, \
            ('existing record not found in: %s' %
             utils.encode(self.s.doc.content))

        results_page = self.s.follow('Click here to view results.')
        # make sure the results page has the people on it.
        assert 'person.211' in results_page.content, \
            'results page: %s' % utils.encode(results_page.content)
        assert 'person.111' in results_page.content, \
            'results page: %s' % utils.encode(results_page.content)


    def test_seeking_someone_small(self):
        """Follow the seeking someone flow on the small-sized embed."""

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            assert_params_conform(
                url or self.s.url, {'role': 'seek', 'ui': 'small'})

        # Start on the home page and click the "I'm looking for someone" button
        self.go('/haiti?ui=small')
        search_page = self.s.follow('I\'m looking for someone')
        search_form = search_page.first('form')
        assert 'Search for this person' in search_form.content

        # Try a search, which should yield no results.
        self.s.submit(search_form, query='_test_given_name')
        assert_params()
        self.verify_results_page(0)
        assert_params()
        assert self.s.doc.firsttag('a', class_='create-new-record')

        person = Person(
            key_name='haiti:test.google.com/person.111',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            given_name='_test_given_name',
            family_name='_test_family_name',
            full_name='_test_given_name _test_family_name',
            entry_date=datetime.datetime.utcnow(),
            text='_test A note body')
        person.update_index(['old', 'new'])
        person.put()

        assert_params()

        # Now the search should yield a result.
        self.s.submit(search_form, query='_test_given_name')
        assert_params()
        link = self.s.doc.firsttag('a', class_='results-found')
        assert 'query=_test_given_name' in link.content


    def test_seeking_someone_regular(self):
        """Follow the seeking someone flow on the regular-sized embed."""

        # Set utcnow to match source date
        SOURCE_DATETIME = datetime.datetime(2001, 1, 1, 0, 0, 0)
        self.set_utcnow_for_test(SOURCE_DATETIME)
        test_source_date = SOURCE_DATETIME.strftime('%Y-%m-%d')

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            assert_params_conform(
                url or self.s.url, {'role': 'seek'}, {'ui': 'small'})

        # Start on the home page and click the "I'm looking for someone" button
        self.go('/haiti')
        search_page = self.s.follow('I\'m looking for someone')
        search_form = search_page.first('form')
        assert 'Search for this person' in search_form.content

        # Try a search, which should yield no results.
        self.s.submit(search_form, query='_test_given_name')
        assert_params()
        self.verify_results_page(0)
        assert_params()
        self.verify_unsatisfactory_results()
        assert_params()

        # Submit the create form with minimal information.
        create_form = self.s.doc.first('form')
        self.s.submit(create_form,
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      author_name='_test_author_name')

        # For now, the date of birth should be hidden.
        assert 'birth' not in self.s.content.lower()

        self.verify_details_page(0, details={
            'Full name:': '_test_given_name _test_family_name',
            'Author\'s name:': '_test_author_name'})

        # Now the search should yield a result.
        self.s.submit(search_form, query='_test_given_name')
        assert_params()
        self.verify_results_page(1, all_have=(['_test_given_name']),
                                 some_have=(['_test_given_name']),
                                 status=(['Unspecified']))
        self.verify_click_search_result(0, assert_params)
        # set the person entry_date to something in order to make sure adding
        # note doesn't update
        person = Person.all().filter('given_name =', '_test_given_name').get()
        person.entry_date = datetime.datetime(2006, 6, 6, 6, 6, 6)
        db.put(person)
        self.verify_details_page(0)
        self.verify_note_form()
        self.verify_update_notes(
            False, '_test A note body', '_test A note author', None)
        self.verify_update_notes(
            True, '_test Another note body', '_test Another note author',
            'believed_alive',
            last_known_location='Port-au-Prince',
            note_photo_url='http://xyz')

        # Check that a UserActionLog entry was created.
        verify_user_action_log('mark_alive', 'Note',
                               repo='haiti',
                               detail='_test_given_name _test_family_name',
                               ip_address='',
                               Note_text='_test Another note body',
                               Note_status='believed_alive')

        # Add a note with status == 'believed_dead'.
        # By default allow_believed_dead_via_ui = True for repo 'haiti'.
        self.verify_update_notes(
            True, '_test Third note body', '_test Third note author',
            'believed_dead')
        # Check that a UserActionLog entry was created.
        verify_user_action_log('mark_dead', 'Note',
                               repo='haiti',
                               detail='_test_given_name _test_family_name',
                               ip_address='127.0.0.1',
                               Note_text='_test Third note body',
                               Note_status='believed_dead')

        person = Person.all().filter('given_name =', '_test_given_name').get()
        assert person.entry_date == datetime.datetime(2006, 6, 6, 6, 6, 6)

        self.s.submit(search_form, query='_test_given_name')
        assert_params()
        self.verify_results_page(
            1, all_have=['_test_given_name'], some_have=['_test_given_name'],
            status=['Someone has received information that this person is dead']
        )

        # test for default_expiry_days config:
        config.set_for_repo('haiti', default_expiry_days=10)

        # Submit the create form with complete information
        self.s.submit(create_form,
                      author_name='_test_author_name',
                      author_email='_test_author_email',
                      author_phone='_test_author_phone',
                      clone='yes',
                      source_name='_test_source_name',
                      source_date=test_source_date,
                      source_url='_test_source_url',
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      alternate_given_names='_test_alternate_given_names',
                      alternate_family_names='_test_alternate_family_names',
                      sex='female',
                      date_of_birth='1955',
                      age='52',
                      home_street='_test_home_street',
                      home_neighborhood='_test_home_neighborhood',
                      home_city='_test_home_city',
                      home_state='_test_home_state',
                      home_postal_code='_test_home_postal_code',
                      home_country='_test_home_country',
                      photo_url='_test_photo_url',
                      profile_url1='http://www.facebook.com/_test_account1',
                      profile_url2='http://www.twitter.com/_test_account2',
                      profile_url3='http://www.foo.com/_test_account3',
                      expiry_option='foo',
                      description='_test_description')

        self.verify_details_page(0, details={
            'Full name:': '_test_given_name _test_family_name',
            'Alternate names:': '_test_alternate_given_names _test_alternate_family_names',
            'Sex:': 'female',
            # 'Date of birth:': '1955',  # currently hidden
            'Age:': '52',
            'Street name:': '_test_home_street',
            'Neighborhood:': '_test_home_neighborhood',
            'City:': '_test_home_city',
            'Province or state:': '_test_home_state',
            'Postal or zip code:': '_test_home_postal_code',
            'Home country:': '_test_home_country',
            'Profile page 1:': 'Facebook',
            'Profile page 2:': 'Twitter',
            'Profile page 3:': 'www.foo.com',
            'Author\'s name:': '_test_author_name',
            'Author\'s phone number:': '(click to reveal)',
            'Author\'s e-mail address:': '(click to reveal)',
            'Original URL:': 'Link',
            'Original posting date:': 'Jan. 1, 2001, midnight UTC',
            'Original site name:': '_test_source_name',
            'Expiry date of this record:': 'Jan. 11, 2001, midnight UTC'})

        # Check the icons and the links are there.
        assert 'facebook-16x16.png' in self.s.doc.content
        assert 'twitter-16x16.png' in self.s.doc.content
        assert 'http://www.facebook.com/_test_account1' in self.s.doc.content
        assert 'http://www.twitter.com/_test_account2' in self.s.doc.content
        assert 'http://www.foo.com/_test_account3' in self.s.doc.content

    def test_time_zones(self):
        # Japan should show up in JST due to its configuration.
        db.put([Person(
            key_name='japan:test.google.com/person.111',
            repo='japan',
            full_name='_family_name _given_name',
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6),
            entry_date=datetime.datetime.utcnow(),
        ), Note(
            key_name='japan:test.google.com/note.222',
            person_record_id='test.google.com/person.111',
            author_name='Fred',
            repo='japan',
            text='foo',
            source_date=datetime.datetime(2001, 2, 3, 7, 8, 9),
            entry_date=datetime.datetime.utcnow(),
        )])

        self.go('/japan/view?id=test.google.com/person.111&lang=en')
        self.verify_details_page(1, {
            'Original posting date:': 'Feb. 3, 2001, 1:05 p.m. JST'
        })
        assert (
            'Posted by Fred on Feb. 3, 2001, 4:08 p.m. JST' in self.s.doc.text)

        self.go('/japan/multiview?id1=test.google.com/person.111'
                '&lang=en')
        assert 'Feb. 3, 2001, 1:05 p.m. JST' in self.s.doc.text, \
            text_diff('', self.s.doc.text)

        # Other repositories should show up in UTC.
        db.put([Person(
            key_name='haiti:test.google.com/person.111',
            repo='haiti',
            full_name='_given_name _family_name',
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6),
            entry_date=datetime.datetime.utcnow(),
        ), Note(
            key_name='haiti:test.google.com/note.222',
            person_record_id='test.google.com/person.111',
            author_name='Fred',
            repo='haiti',
            text='foo',
            source_date=datetime.datetime(2001, 2, 3, 7, 8, 9),
            entry_date=datetime.datetime.utcnow(),
        )])

        self.go('/haiti/view?id=test.google.com/person.111&lang=en')
        self.verify_details_page(1, {
            'Original posting date:': 'Feb. 3, 2001, 4:05 a.m. UTC'
        })
        assert (
            'Posted by Fred on Feb. 3, 2001, 7:08 a.m. UTC' in self.s.doc.text)
        self.go('/haiti/multiview?id1=test.google.com/person.111'
                '&lang=en')
        assert 'Feb. 3, 2001, 4:05 a.m. UTC' in self.s.doc.text

    def test_new_indexing(self):
        """First create new entry with new_search param then search for it"""

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            assert_params_conform(
                url or self.s.url, {'role': 'seek'}, {'ui': 'small'})

        # Start on the home page and click the "I'm looking for someone" button
        self.go('/haiti')
        search_page = self.s.follow('I\'m looking for someone')
        search_form = search_page.first('form')
        assert 'Search for this person' in search_form.content

        # Try a search, which should yield no results.
        self.s.submit(search_form, query='ABCD EFGH IJKL MNOP')
        assert_params()
        self.verify_results_page(0)
        assert_params()
        self.verify_unsatisfactory_results()
        assert_params()

        # Submit the create form with a valid given and family name
        self.s.submit(self.s.doc.first('form'),
                      given_name='ABCD EFGH',
                      family_name='IJKL MNOP',
                      alternate_given_names='QRST UVWX',
                      alternate_family_names='YZ01 2345',
                      author_name='author_name')

        # Try a middle-name match.
        self.s.submit(search_form, query='EFGH')
        self.verify_results_page(1, all_have=(['ABCD EFGH']))

        # Try a middle-name non-match.
        self.s.submit(search_form, query='ABCDEF')
        self.verify_results_page(0)

        # Try a middle-name prefix match.
        self.s.submit(search_form, query='MNO')
        self.verify_results_page(1, all_have=(['ABCD EFGH']))

        # Try a multiword match.
        self.s.submit(search_form, query='MNOP IJK ABCD EFG')
        self.verify_results_page(1, all_have=(['ABCD EFGH']))

        # Try an alternate-name prefix non-match.
        self.s.submit(search_form, query='QRS')
        self.verify_results_page(0)

        # Try a multiword match on an alternate name.
        self.s.submit(search_form, query='ABCD EFG QRST UVWX')
        self.verify_results_page(1, all_have=(['ABCD EFGH']))

    def test_indexing_japanese_names(self):
        """Index Japanese person's names and make sure they are searchable."""

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            assert_params_conform(
                url or self.s.url, {'role': 'seek'}, {'ui': 'small'})

        Repo(key_name='japan-test').put()
        # Kanji's are segmented character by character.
        config.set_for_repo('japan-test', min_query_word_length=1)
        config.set_for_repo('japan-test', use_family_name=True)
        config.set_for_repo('japan-test', family_name_first=True)
        config.set_for_repo('japan-test', use_alternate_names=True)

        # Start on the home page and click the "I'm looking for someone" button
        self.go('/japan-test')
        search_page = self.s.follow('I\'m looking for someone')
        search_form = search_page.first('form')
        assert 'Search for this person' in search_form.content

        # Try a search, which should yield no results.
        self.s.submit(search_form, query='山田 太郎')
        assert_params()
        self.verify_results_page(0)
        assert_params()
        self.verify_unsatisfactory_results()
        assert_params()

        # Submit the create form with a valid given and family name.
        self.s.submit(self.s.doc.first('form'),
                      family_name='山田',
                      given_name='太郎',
                      alternate_family_names='やまだ',
                      alternate_given_names='たろう',
                      author_name='author_name')

        # Try a family name match.
        self.s.submit(search_form, query='山田')
        self.verify_results_page(1, all_have=([u'山田 太郎',
                                               u'やまだ たろう']))

        # Try a full name prefix match.
        self.s.submit(search_form, query='山田太')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try a full name match, where given and family names are not segmented.
        self.s.submit(search_form, query='山田太郎')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try an alternate family name match.
        self.s.submit(search_form, query='やまだ')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try an alternate name match with given name and family name segmented.
        self.s.submit(search_form, query='やまだ たろう')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try an alternate name match without given name and family name
        # segmented.
        self.s.submit(search_form, query='やまだたろう')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try an alternate name prefix match, but we don't index prefixes for
        # alternate names.
        self.s.submit(search_form, query='やまだたろ')
        self.verify_results_page(0)

        # Try an alternate family name match with katakana variation.
        self.s.submit(search_form, query='ヤマダ')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try an alternate family name match with romaji variation.
        self.s.submit(search_form, query='YAMADA')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

    def test_have_information_regular(self):
        """Follow the "I have information" flow on the regular-sized embed."""

        # Set utcnow to match source date
        SOURCE_DATETIME = datetime.datetime(2001, 1, 1, 0, 0, 0)
        self.set_utcnow_for_test(SOURCE_DATETIME)
        test_source_date = SOURCE_DATETIME.strftime('%Y-%m-%d')

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            assert_params_conform(
                url or self.s.url, {'role': 'provide'}, {'ui': 'small'})

        self.go('/haiti')
        search_page = self.s.follow('I have information about someone')
        search_form = search_page.first('form')
        assert 'I have information about someone' in search_form.content

        self.assert_error_deadend(
            self.s.submit(search_form),
            'Enter the person\'s given and family names.')

        self.assert_error_deadend(
            self.s.submit(search_form, given_name='_test_given_name'),
            'Enter the person\'s given and family names.')

        self.s.submit(search_form,
                      given_name='_test_given_name',
                      family_name='_test_family_name')
        assert_params()
        # Because the datastore is empty, should go straight to the create page

        self.verify_create_form(prefilled_params={
            'given_name': '_test_given_name',
            'family_name': '_test_family_name'})
        self.verify_note_form()

        # Submit the create form with minimal information
        create_form = self.s.doc.first('form')
        self.s.submit(create_form,
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      author_name='_test_author_name',
                      text='_test A note body')

        self.verify_details_page(1, details={
            'Full name:': '_test_given_name _test_family_name',
            'Author\'s name:': '_test_author_name'})

        # Verify that UserActionLog entries are created for 'add' action.
        verify_user_action_log('add', 'Person', repo='haiti')
        verify_user_action_log('add', 'Note', repo='haiti')

        # Try the search again, and should get some results
        self.s.submit(search_form,
                      given_name='_test_given_name',
                      family_name='_test_family_name')
        assert_params()
        self.verify_results_page(
            1, all_have=('_test_given_name', '_test_family_name'))
        self.verify_click_search_result(0, assert_params)

        # For now, the date of birth should be hidden.
        assert 'birth' not in self.s.content.lower()
        self.verify_details_page(1)

        self.verify_note_form()
        self.verify_update_notes(
            False, '_test A note body', '_test A note author', None)
        self.verify_update_notes(
            True, '_test Another note body', '_test Another note author',
            None, last_known_location='Port-au-Prince',
            note_photo_url='http://xyz')

        # Submit the create form with complete information
        self.s.submit(create_form,
                      author_name='_test_author_name',
                      author_email='_test_author_email',
                      author_phone='_test_author_phone',
                      clone='yes',
                      source_name='_test_source_name',
                      source_date=test_source_date,
                      source_url='_test_source_url',
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      alternate_given_names='_test_alternate_given_names',
                      alternate_family_names='_test_alternate_family_names',
                      sex='male',
                      date_of_birth='1970-01',
                      age='30-40',
                      home_street='_test_home_street',
                      home_neighborhood='_test_home_neighborhood',
                      home_city='_test_home_city',
                      home_state='_test_home_state',
                      home_postal_code='_test_home_postal_code',
                      home_country='_test_home_country',
                      photo_url='_test_photo_url',
                      profile_url1='http://www.facebook.com/_test_account',
                      expiry_option='20',
                      description='_test_description',
                      add_note='yes',
                      author_made_contact='yes',
                      status='believed_dead',
                      email_of_found_person='_test_email_of_found_person',
                      phone_of_found_person='_test_phone_of_found_person',
                      last_known_location='_test_last_known_location',
                      text='_test A note body',
                      note_photo_url='_test_note_photo_url')

        self.verify_details_page(1, details={
            'Full name:': '_test_given_name _test_family_name',
            'Alternate names:': '_test_alternate_given_names _test_alternate_family_names',
            'Sex:': 'male',
            # 'Date of birth:': '1970-01',  # currently hidden
            'Age:': '30-40',
            'Street name:': '_test_home_street',
            'Neighborhood:': '_test_home_neighborhood',
            'City:': '_test_home_city',
            'Province or state:': '_test_home_state',
            'Postal or zip code:': '_test_home_postal_code',
            'Home country:': '_test_home_country',
            'Profile page 1:': 'Facebook',
            'Author\'s name:': '_test_author_name',
            'Author\'s phone number:': '(click to reveal)',
            'Author\'s e-mail address:': '(click to reveal)',
            'Original URL:': 'Link',
            'Original posting date:': 'Jan. 1, 2001, midnight UTC',
            'Original site name:': '_test_source_name',
            'Expiry date of this record:': 'Jan. 21, 2001, midnight UTC'})

        # Check that UserActionLog entries were created.
        verify_user_action_log('add', 'Person', repo='haiti')
        verify_user_action_log('add', 'Note', repo='haiti')
        verify_user_action_log('mark_dead', 'Note',
                               repo='haiti',
                               detail='_test_given_name _test_family_name',
                               ip_address='127.0.0.1',
                               Note_text='_test A note body',
                               Note_status='believed_dead')

    def test_multiview(self):
        """Test the page for marking duplicate records."""
        db.put([Person(
            key_name='haiti:test.google.com/person.111',
            repo='haiti',
            author_name='_author_name_1',
            author_email='_author_email_1',
            author_phone='_author_phone_1',
            entry_date=TEST_DATETIME,
            full_name='_full_name_1',
            alternate_names='_alternate_names_1',
            sex='male',
            date_of_birth='1970-01-01',
            age='31-41',
            photo_url='http://photo1',
            profile_urls='''http://www.facebook.com/_account_1
http://www.twitter.com/_account_1
http://www.foo.com/_account_1''',
        ), Person(
            key_name='haiti:test.google.com/person.222',
            repo='haiti',
            author_name='_author_name_2',
            author_email='_author_email_2',
            author_phone='_author_phone_2',
            entry_date=TEST_DATETIME,
            full_name='_full_name_2',
            alternate_names='_alternate_names_2',
            sex='male',
            date_of_birth='1970-02-02',
            age='32-42',
            photo_url='http://photo2',
            profile_urls='http://www.facebook.com/_account_2',
        ), Person(
            key_name='haiti:test.google.com/person.333',
            repo='haiti',
            author_name='_author_name_3',
            author_email='_author_email_3',
            author_phone='_author_phone_3',
            entry_date=TEST_DATETIME,
            full_name='_full_name_3',
            alternate_names='_alternate_names_3',
            sex='male',
            date_of_birth='1970-03-03',
            age='33-43',
            photo_url='http://photo3',
        )])

        # All three records should appear on the multiview page.
        doc = self.go('/haiti/multiview' +
                      '?id1=test.google.com/person.111' +
                      '&id2=test.google.com/person.222' +
                      '&id3=test.google.com/person.333')
        assert '_full_name_1' in doc.content
        assert '_full_name_2' in doc.content
        assert '_full_name_3' in doc.content
        assert '_alternate_names_1' in doc.content
        assert '_alternate_names_2' in doc.content
        assert '_alternate_names_3' in doc.content
        assert '31-41' in doc.content
        assert '32-42' in doc.content
        assert '33-43' in doc.content
        assert 'http://photo1' in doc.content
        assert 'http://photo2' in doc.content
        assert 'http://photo3' in doc.content
        assert 'http://www.facebook.com/_account_1' in doc.content
        assert 'http://www.twitter.com/_account_1' in doc.content
        assert 'http://www.foo.com/_account_1' in doc.content
        assert 'http://www.facebook.com/_account_2' in doc.content

        # Mark all three as duplicates.
        button = doc.firsttag('input', value='Yes, these are the same person')
        doc = self.s.submit(button, text='duplicate test', author_name='foo')

        # We should arrive back at the first record, with two duplicate notes.
        assert self.s.status == 200
        assert 'id=test.google.com%2Fperson.111' in self.s.url
        assert 'Possible duplicates' in doc.content
        assert '_full_name_2' in doc.content
        assert '_full_name_3' in doc.content

        p = Person.get('haiti', 'test.google.com/person.111')
        assert len(p.get_linked_persons()) == 2
        # Ask for detailed information on the duplicate markings.
        doc = self.s.follow('Show who marked these duplicates')
        assert '_full_name_1' in doc.content
        notes = doc.first(class_='self-notes').all('div', class_='view note')
        assert len(notes) == 2, str(doc.content.encode('ascii', 'ignore'))
        # We don't know which note comes first as they are created almost
        # simultaneously.
        note_222 = notes[0] if 'person.222' in notes[0].text else notes[1]
        note_333 = notes[0] if 'person.333' in notes[0].text else notes[1]
        assert 'Posted by foo' in note_222.text
        assert 'duplicate test' in note_222.text
        assert ('This record is a duplicate of test.google.com/person.222' in
                note_222.text)
        assert 'Posted by foo' in note_333.text
        assert 'duplicate test' in note_333.text
        assert ('This record is a duplicate of test.google.com/person.333' in
                note_333.text)

    def test_reveal(self):
        """Test the hiding and revealing of contact information in the UI."""
        db.put([Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            author_name='_reveal_author_name',
            author_email='_reveal_author_email',
            author_phone='_reveal_author_phone',
            entry_date=TEST_DATETIME,
            full_name='_reveal_full_name',
            sex='male',
            date_of_birth='1970-01-01',
            age='30-40',
        ), Person(
            key_name='haiti:test.google.com/person.456',
            repo='haiti',
            author_name='_reveal_author_name',
            author_email='_reveal_author_email',
            author_phone='_reveal_author_phone',
            entry_date=datetime.datetime.now(),
            full_name='_reveal_full_name',
            sex='male',
            date_of_birth='1970-01-01',
            age='30-40',
        ), Note(
            key_name='haiti:test.google.com/note.456',
            repo='haiti',
            author_name='_reveal_note_author_name',
            author_email='_reveal_note_author_email',
            author_phone='_reveal_note_author_phone',
            entry_date=TEST_DATETIME,
            email_of_found_person='_reveal_email_of_found_person',
            phone_of_found_person='_reveal_phone_of_found_person',
            person_record_id='test.google.com/person.123',
        )])

        # All contact information should be hidden by default.
        doc = self.go('/haiti/view?id=test.google.com/person.123')
        assert '_reveal_author_email' not in doc.content
        assert '_reveal_author_phone' not in doc.content
        assert '_reveal_note_author_email' not in doc.content
        assert '_reveal_note_author_phone' not in doc.content
        assert '_reveal_email_of_found_person' not in doc.content
        assert '_reveal_phone_of_found_person' not in doc.content

        # Clicking the '(click to reveal)' link should bring the user
        # to a captcha turing test page.
        reveal_region = doc.first('a',  u'(click to reveal)')
        url = reveal_region.get('href', '')
        doc = self.go(url[url.find('/haiti/reveal'):])
        assert 'iframe' in doc.content
        assert 'recaptcha_response_field' in doc.content

        # Try to continue with an invalid captcha response. Get redirected
        # back to the same page.
        button = doc.firsttag('input', value='Proceed')
        doc = self.s.submit(button)
        assert 'iframe' in doc.content
        assert 'recaptcha_response_field' in doc.content

        # Continue as if captcha is valid. All information should be viewable.
        doc = self.s.submit(button, test_mode='yes')
        assert '_reveal_author_email' in doc.content
        assert '_reveal_author_phone' in doc.content
        assert '_reveal_note_author_email' in doc.content
        assert '_reveal_note_author_phone' in doc.content
        assert '_reveal_email_of_found_person' in doc.content
        assert '_reveal_phone_of_found_person' in doc.content

        # Start over. Information should no longer be viewable.
        doc = self.go('/haiti/view?id=test.google.com/person.123')
        assert '_reveal_author_email' not in doc.content
        assert '_reveal_author_phone' not in doc.content
        assert '_reveal_note_author_email' not in doc.content
        assert '_reveal_note_author_phone' not in doc.content
        assert '_reveal_email_of_found_person' not in doc.content
        assert '_reveal_phone_of_found_person' not in doc.content

        # Other person's records should also be invisible.
        doc = self.go('/haiti/view?id=test.google.com/person.456')
        assert '_reveal_author_email' not in doc.content
        assert '_reveal_author_phone' not in doc.content
        assert '_reveal_note_author_email' not in doc.content
        assert '_reveal_note_author_phone' not in doc.content
        assert '_reveal_email_of_found_person' not in doc.content
        assert '_reveal_phone_of_found_person' not in doc.content

        # All contact information should be hidden on the multiview page, too.
        doc = self.go('/haiti/multiview' +
                      '&id1=test.google.com/person.123' +
                      '&id2=test.google.com/person.456')
        assert '_reveal_author_email' not in doc.content
        assert '_reveal_author_phone' not in doc.content
        assert '_reveal_note_author_email' not in doc.content
        assert '_reveal_note_author_phone' not in doc.content
        assert '_reveal_email_of_found_person' not in doc.content
        assert '_reveal_phone_of_found_person' not in doc.content

        # Now supply a valid revelation signature.
        signature = reveal.sign(u'multiview:test.google.com/person.123', 10)
        doc = self.go('/haiti/multiview' +
                      '?id1=test.google.com/person.123' +
                      '&signature=' + signature)
        assert '_reveal_author_email' in doc.content
        assert '_reveal_author_phone' in doc.content
        # Notes are not shown on the multiview page.

    def test_show_domain_source(self):
        """Test that we show domain of source for records coming from API."""

        data = get_test_data('test.pfif-1.2-source.xml')
        self.go('/haiti/api/write?key=domain_test_key',
                data=data, type='application/xml')

        # On Search results page,  we should see Provided by: domain
        doc = self.go('/haiti/results?role=seek&query=_test_last_name')
        assert 'Provided by: mytestdomain.com' in doc.content
        assert '_test_last_name' in doc.content

        # On details page, we should see Provided by: domain
        doc = self.go('/haiti/view?lang=en&id=mytestdomain.com/person.21009')
        assert 'Provided by: mytestdomain.com' in doc.content
        assert '_test_last_name' in doc.content

    def test_global_domain_key(self):
        """Test that we honor global domain keys."""
        data = get_test_data('global-test.pfif-1.2-source.xml')
        self.go('/haiti/api/write?key=global_test_key',
                data=data, type='application/xml')

        # On Search results page,  we should see Provided by: domain
        doc = self.go(
            '/haiti/results?role=seek&query=_test_last_name')
        assert 'Provided by: globaltestdomain.com' in doc.content
        assert '_test_last_name' in doc.content

        # On details page, we should see Provided by: domain
        doc = self.go(
            '/haiti/view?lang=en&id=globaltestdomain.com/person.21009'
            )
        assert 'Provided by: globaltestdomain.com' in doc.content
        assert '_test_last_name' in doc.content

    def test_note_status(self):
        """Test the posting and viewing of the note status field in the UI."""
        status_class = re.compile(r'\bstatus\b')

        # allow_believed_dead_via_ui = True
        config.set_for_repo('haiti', allow_believed_dead_via_ui=True)

        # Check that the right status options appear on the create page.
        doc = self.go('/haiti/create?role=provide')
        note = doc.first(class_='fields-table note')
        options = note.first('select', name='status').all('option')
        assert len(options) == len(NOTE_STATUS_OPTIONS)
        for option, text in zip(options, NOTE_STATUS_OPTIONS):
            assert text in option.attrs['value']

        # Create a record with no status and get the new record's ID.
        form = doc.first('form')
        doc = self.s.submit(form,
                            given_name='_test_given',
                            family_name='_test_family',
                            author_name='_test_author',
                            text='_test_text')
        view_url = self.s.url

        # Check that the right status options appear on the view page.
        doc = self.s.go(view_url)
        note = doc.first(class_='fields-table note')
        options = note.first('select', name='status').all('option')
        assert len(options) == len(NOTE_STATUS_OPTIONS)
        for option, text in zip(options, NOTE_STATUS_OPTIONS):
            assert text in option.attrs['value']

        # Advance the clock. The new note has a newer source_date by this.
        # This makes sure that the new note appears at the bottom of the view
        # page.
        self.advance_utcnow(seconds=1)

        # Set the status in a note and check that it appears on the view page.
        form = doc.first('form')
        self.s.submit(form, author_name='_test_author2', text='_test_text',
                      status='believed_alive')
        doc = self.s.go(view_url)
        note = doc.last(class_='view note')
        assert 'believed_alive' in note.content, \
            text_diff('believed_alive', note.content)
        assert 'believed_dead' not in note.content, \
            text_diff('believed_dead', note.content)
        # Check that a UserActionLog entry was created.
        verify_user_action_log('mark_alive', 'Note',
                               repo='haiti',
                               detail='_test_given _test_family',
                               ip_address='',
                               Note_text='_test_text',
                               Note_status='believed_alive')
        db.delete(UserActionLog.all().fetch(10))

        # Set status to is_note_author, but don't check author_made_contact.
        self.s.submit(form,
                      author_name='_test_author',
                      text='_test_text',
                      status='is_note_author')
        self.assert_error_deadend(
            self.s.submit(form,
                          author_name='_test_author',
                          text='_test_text',
                          status='is_note_author'),
            'in contact', 'Status of this person')

        # Check that a UserActionLog entry was not created.
        assert not UserActionLog.all().get()

        # allow_believed_dead_via_ui = False
        config.set_for_repo('japan', allow_believed_dead_via_ui=False)

        # Check that believed_dead option does not appear on the create page
        doc = self.go('/japan/create?role=provide')
        note = doc.first(class_='fields-table note')
        options = note.first('select', name='status').all('option')
        assert len(options) == len(NOTE_STATUS_OPTIONS) - 1
        for option, text in zip(options, NOTE_STATUS_OPTIONS):
            assert text in option.attrs['value']
            assert option.attrs['value'] != 'believed_dead'

        # Create a record with no status and get the new record's ID.
        form = doc.first('form')
        doc = self.s.submit(form,
                            given_name='_test_given',
                            family_name='_test_family',
                            author_name='_test_author',
                            text='_test_text')
        view_url = self.s.url

        # Check that the believed_dead option does not appear
        # on the view page.
        doc = self.s.go(view_url)
        note = doc.first(class_='fields-table note')
        options = note.first('select', name='status').all('option')
        assert len(options) == len(NOTE_STATUS_OPTIONS) - 1
        for option, text in zip(options, NOTE_STATUS_OPTIONS):
            assert text in option.attrs['value']
            assert option.attrs['value'] != 'believed_dead'

        # Advance the clock. Same as above.
        self.advance_utcnow(seconds=1)

        # Set the status in a note and check that it appears on the view page.
        form = doc.first('form')
        self.s.submit(form, author_name='_test_author2', text='_test_text',
                                    status='believed_alive')
        doc = self.s.go(view_url)
        note = doc.last(class_='view note')
        assert 'believed_alive' in note.content
        assert 'believed_dead' not in note.content

        # Check that a UserActionLog entry was created.
        verify_user_action_log('mark_alive', 'Note',
                               repo='japan',
                               detail='_test_family _test_given',
                               ip_address='',
                               Note_text='_test_text',
                               Note_status='believed_alive')
        db.delete(UserActionLog.all().fetch(10))

        # Advance the clock. Same as above.
        self.advance_utcnow(seconds=1)

        # Set status to believed_dead, but allow_believed_dead_via_ui is false.
        self.s.submit(form,
                      author_name='_test_author',
                      text='_believed_dead_test_text',
                      status='believed_dead')
        self.assert_error_deadend(
            self.s.submit(form,
                          author_name='_test_author',
                          text='_test_text',
                          status='believed_dead'),
            'Not authorized', 'believed_dead')

        # Check that a UserActionLog entry was not created.
        assert not UserActionLog.all().get()

    def test_api_write_pfif_1_4(self):
        """Post a single entry as PFIF 1.4 using the upload API."""
        data = get_test_data('test.pfif-1.4.xml')
        self.go('/haiti/api/write?version=1.4&key=test_key',
                data=data, type='application/xml')
        person = Person.get('haiti', 'test.google.com/person.21009')
        assert person.full_name == u'_test_full_name1\n_test_full_name2'
        assert person.given_name == u'_test_given_name'
        assert person.family_name == u'_test_family_name'
        assert person.alternate_names == \
            u'_test_alternate_name1\n_test_alternate_name2'
        assert person.description == u'_test_description'
        assert person.sex == u'female'
        assert person.date_of_birth == u'1970-01'
        assert person.age == u'35-45'
        assert person.author_name == u'_test_author_name'
        assert person.author_email == u'_test_author_email'
        assert person.author_phone == u'_test_author_phone'
        assert person.home_street == u'_test_home_street'
        assert person.home_neighborhood == u'_test_home_neighborhood'
        assert person.home_city == u'_test_home_city'
        assert person.home_state == u'_test_home_state'
        assert person.home_postal_code == u'_test_home_postal_code'
        assert person.home_country == u'US'
        assert person.record_id == u'test.google.com/person.21009'
        assert person.photo_url == u'_test_photo_url'
        assert person.profile_urls == u'_test_profile_url1\n_test_profile_url2'
        assert person.source_name == u'_test_source_name'
        assert person.source_url == u'_test_source_url'
        assert person.source_date == datetime.datetime(2000, 1, 1, 0, 0, 0)
        # Current date should replace the provided entry_date.
        self.assertEqual(utils.get_utcnow(), person.entry_date)

        # The latest_status property should come from the third Note.
        assert person.latest_status == u'is_note_author'
        assert person.latest_status_source_date == \
            datetime.datetime(2000, 1, 18, 20, 21, 22)

        # The latest_found property should come from the fourth Note.
        assert person.latest_found == False
        assert person.latest_found_source_date == \
            datetime.datetime(2000, 1, 18, 20, 0, 0)

        notes = person.get_notes()
        assert len(notes) == 4
        notes.sort(key=lambda note: note.record_id)

        note = notes[0]
        assert note.author_name == u'_test_author_name'
        assert note.author_email == u'_test_author_email'
        assert note.author_phone == u'_test_author_phone'
        assert note.email_of_found_person == u'_test_email_of_found_person'
        assert note.phone_of_found_person == u'_test_phone_of_found_person'
        assert note.last_known_location == u'_test_last_known_location'
        assert note.record_id == u'test.google.com/note.27009'
        assert note.person_record_id == u'test.google.com/person.21009'
        assert note.text == u'_test_text'
        assert note.photo_url == u'_test_note_photo_url'
        assert note.source_date == datetime.datetime(2000, 1, 16, 4, 5, 6)
        # Current date should replace the provided entry_date.
        assert note.entry_date == utils.get_utcnow()
        assert note.author_made_contact == False
        assert note.status == u'believed_missing'
        assert note.linked_person_record_id == u'test.google.com/person.999'
        assert note.reviewed == False

        note = notes[1]
        assert note.author_name == u'inna-testing'
        assert note.author_email == u'inna-testing@gmail.com'
        assert note.author_phone == u'inna-testing-number'
        assert note.email_of_found_person == u''
        assert note.phone_of_found_person == u''
        assert note.last_known_location == u'19.16592425362802 -71.9384765625'
        assert note.record_id == u'test.google.com/note.31095'
        assert note.person_record_id == u'test.google.com/person.21009'
        assert note.text == u'new comment - testing'
        assert note.source_date == datetime.datetime(2000, 1, 17, 14, 15, 16)
        # Current date should replace the provided entry_date.
        assert note.entry_date.year == utils.get_utcnow().year
        assert note.author_made_contact == True
        assert note.status == ''
        assert not note.linked_person_record_id
        assert note.reviewed == False

        # Just confirm that a missing author_made_contact tag is parsed as None.
        # We already checked all the other fields above.
        note = notes[2]
        assert note.author_made_contact == None
        assert note.status == u'is_note_author'
        assert note.reviewed == False

        note = notes[3]
        assert note.author_made_contact == False
        assert note.status == u'believed_missing'
        assert note.reviewed == False

    # TODO(ryok): Remove support for legacy URLs in mid-January 2012.
    def test_api_write_pfif_1_2_legacy_url(self):
        """Post a single entry as PFIF 1.2 using the API at its old URL."""
        person = Person.get('haiti', 'test.google.com/person.21009')
        assert person is None

        self.s.go('http://%s/api/write?subdomain=haiti&key=test_key' %
                      self.hostport,
                  data=get_test_data('test.pfif-1.2.xml'),
                  type='application/xml')
        person = Person.get('haiti', 'test.google.com/person.21009')
        assert person is not None
        assert person.given_name == u'_test_first_name'

    def test_api_write_pfif_1_2(self):
        """Post a single entry as PFIF 1.2 using the upload API."""
        data = get_test_data('test.pfif-1.2.xml')
        self.go('/haiti/api/write?key=test_key',
                data=data, type='application/xml')
        person = Person.get('haiti', 'test.google.com/person.21009')
        assert person.given_name == u'_test_first_name'
        assert person.family_name == u'_test_last_name'
        assert person.full_name == u'_test_first_name _test_last_name'
        assert person.description == u'_test_description'
        assert person.sex == u'female'
        assert person.date_of_birth == u'1970-01'
        assert person.age == u'35-45'
        assert person.author_name == u'_test_author_name'
        assert person.author_email == u'_test_author_email'
        assert person.author_phone == u'_test_author_phone'
        assert person.home_street == u'_test_home_street'
        assert person.home_neighborhood == u'_test_home_neighborhood'
        assert person.home_city == u'_test_home_city'
        assert person.home_state == u'_test_home_state'
        assert person.home_postal_code == u'_test_home_postal_code'
        assert person.home_country == u'US'
        assert person.record_id == u'test.google.com/person.21009'
        assert person.photo_url == u'_test_photo_url'
        assert person.source_name == u'_test_source_name'
        assert person.source_url == u'_test_source_url'
        assert person.source_date == datetime.datetime(2000, 1, 1, 0, 0, 0)
        # Current date should replace the provided entry_date.
        self.assertEqual(utils.get_utcnow(), person.entry_date)

        # The latest_status property should come from the third Note.
        assert person.latest_status == u'is_note_author'
        assert person.latest_status_source_date == \
            datetime.datetime(2000, 1, 18, 20, 21, 22)

        # The latest_found property should come from the fourth Note.
        assert person.latest_found == False
        assert person.latest_found_source_date == \
            datetime.datetime(2000, 1, 18, 20, 0, 0)

        notes = person.get_notes()
        assert len(notes) == 4
        notes.sort(key=lambda note: note.record_id)

        note = notes[0]
        assert note.author_name == u'_test_author_name'
        assert note.author_email == u'_test_author_email'
        assert note.author_phone == u'_test_author_phone'
        assert note.email_of_found_person == u'_test_email_of_found_person'
        assert note.phone_of_found_person == u'_test_phone_of_found_person'
        assert note.last_known_location == u'_test_last_known_location'
        assert note.record_id == u'test.google.com/note.27009'
        assert note.person_record_id == u'test.google.com/person.21009'
        assert note.text == u'_test_text'
        assert note.source_date == datetime.datetime(2000, 1, 16, 4, 5, 6)
        # Current date should replace the provided entry_date.
        assert note.entry_date == utils.get_utcnow()
        assert note.author_made_contact == False
        assert note.status == u'believed_missing'
        assert note.linked_person_record_id == u'test.google.com/person.999'
        assert note.reviewed == False

        note = notes[1]
        assert note.author_name == u'inna-testing'
        assert note.author_email == u'inna-testing@gmail.com'
        assert note.author_phone == u'inna-testing-number'
        assert note.email_of_found_person == u''
        assert note.phone_of_found_person == u''
        assert note.last_known_location == u'19.16592425362802 -71.9384765625'
        assert note.record_id == u'test.google.com/note.31095'
        assert note.person_record_id == u'test.google.com/person.21009'
        assert note.text == u'new comment - testing'
        assert note.source_date == datetime.datetime(2000, 1, 17, 14, 15, 16)
        # Current date should replace the provided entry_date.
        assert note.entry_date.year == utils.get_utcnow().year
        assert note.author_made_contact == True
        assert note.status == ''
        assert not note.linked_person_record_id
        assert note.reviewed == False

        # Just confirm that a missing author_made_contact tag is parsed as None.
        # We already checked all the other fields above.
        note = notes[2]
        assert note.author_made_contact == None
        assert note.status == u'is_note_author'
        assert note.reviewed == False

        note = notes[3]
        assert note.author_made_contact == False
        assert note.status == u'believed_missing'
        assert note.reviewed == False

    def test_api_write_pfif_1_2_note(self):
        """Post a single note-only entry as PFIF 1.2 using the upload API."""
        # Create person records that the notes will attach to.
        configure_api_logging()
        Person(key_name='haiti:test.google.com/person.21009',
               repo='haiti',
               full_name='_test_full_name_1',
               entry_date=datetime.datetime(2001, 1, 1, 1, 1, 1)).put()
        Person(key_name='haiti:test.google.com/person.21010',
               repo='haiti',
               full_name='_test_full_name_2',
               entry_date=datetime.datetime(2002, 2, 2, 2, 2, 2)).put()

        data = get_test_data('test.pfif-1.2-note.xml')
        self.go('/haiti/api/write?key=test_key',
                data=data, type='application/xml')

        verify_api_log(ApiActionLog.WRITE)

        person = Person.get('haiti', 'test.google.com/person.21009')
        assert person
        notes = person.get_notes()
        assert len(notes) == 1
        note = notes[0]
        assert note.author_name == u'_test_author_name'
        assert note.author_email == u'_test_author_email'
        assert note.author_phone == u'_test_author_phone'
        assert note.email_of_found_person == u'_test_email_of_found_person'
        assert note.phone_of_found_person == u'_test_phone_of_found_person'
        assert note.last_known_location == u'_test_last_known_location'
        assert note.record_id == u'test.google.com/note.27009'
        assert note.person_record_id == u'test.google.com/person.21009'
        assert note.text == u'_test_text'
        assert note.source_date == datetime.datetime(2000, 1, 16, 7, 8, 9)
        # Current date should replace the provided entry_date.
        self.assertEqual(note.entry_date, utils.get_utcnow())
        assert note.author_made_contact == False
        assert note.status == u'believed_missing'
        assert note.linked_person_record_id == u'test.google.com/person.999'
        assert note.reviewed == False

        # Found flag and status should have propagated to the Person.
        assert person.latest_found == False
        assert person.latest_found_source_date == note.source_date
        assert person.latest_status == u'believed_missing'
        assert person.latest_status_source_date == note.source_date

        person = Person.get('haiti', 'test.google.com/person.21010')
        assert person
        notes = person.get_notes()
        assert len(notes) == 1
        note = notes[0]
        assert note.author_name == u'inna-testing'
        assert note.author_email == u'inna-testing@gmail.com'
        assert note.author_phone == u'inna-testing-number'
        assert note.email_of_found_person == u''
        assert note.phone_of_found_person == u''
        assert note.last_known_location == u'19.16592425362802 -71.9384765625'
        assert note.record_id == u'test.google.com/note.31095'
        assert note.person_record_id == u'test.google.com/person.21010'
        assert note.text == u'new comment - testing'
        assert note.source_date == datetime.datetime(2000, 1, 17, 17, 18, 19)
        # Current date should replace the provided entry_date.
        assert note.entry_date == utils.get_utcnow()
        assert note.author_made_contact is None
        assert note.status == u'is_note_author'
        assert not note.linked_person_record_id
        assert note.reviewed == False

        # Status should have propagated to the Person, but not found.
        assert person.latest_found is None
        assert person.latest_found_source_date is None
        assert person.latest_status == u'is_note_author'
        assert person.latest_status_source_date == note.source_date

    def test_api_write_pfif_1_1(self):
        """Post a single entry as PFIF 1.1 using the upload API."""
        data = get_test_data('test.pfif-1.1.xml')
        self.go('/haiti/api/write?key=test_key',
                data=data, type='application/xml')
        person = Person.get('haiti', 'test.google.com/person.21009')
        assert person.given_name == u'_test_first_name'
        assert person.family_name == u'_test_last_name'
        assert person.full_name == u'_test_first_name _test_last_name'
        assert person.description == u'_test_description'
        assert person.author_name == u'_test_author_name'
        assert person.author_email == u'_test_author_email'
        assert person.author_phone == u'_test_author_phone'
        assert person.home_city == u'_test_home_city'
        assert person.home_street == u'_test_home_street'
        assert person.home_neighborhood == u'_test_home_neighborhood'
        assert person.home_state == u'_test_home_state'
        assert person.home_postal_code == u'_test_home_zip'
        assert person.record_id == u'test.google.com/person.21009'
        assert person.photo_url == u'_test_photo_url'
        assert person.source_name == u'_test_source_name'
        assert person.source_url == u'_test_source_url'
        assert person.source_date == datetime.datetime(2000, 1, 1, 0, 0, 0)
        # Current date should replace the provided entry_date.
        self.assertEqual(utils.get_utcnow(), person.entry_date)

        # The latest_found property should come from the first Note.
        self.assertTrue(person.latest_found)
        assert person.latest_found_source_date == \
            datetime.datetime(2000, 1, 16, 1, 2, 3)

        # There's no status field in PFIF 1.1.
        assert person.latest_status == ''
        assert person.latest_status_source_date is None

        notes = person.get_notes()
        assert len(notes) == 2
        notes.sort(key=lambda note: note.record_id)

        note = notes[0]
        assert note.author_name == u'_test_author_name'
        assert note.author_email == u'_test_author_email'
        assert note.author_phone == u'_test_author_phone'
        assert note.email_of_found_person == u'_test_email_of_found_person'
        assert note.phone_of_found_person == u'_test_phone_of_found_person'
        assert note.last_known_location == u'_test_last_known_location'
        assert note.record_id == u'test.google.com/note.27009'
        assert note.text == u'_test_text'
        assert note.source_date == datetime.datetime(2000, 1, 16, 1, 2, 3)
        # Current date should replace the provided entry_date.
        assert note.entry_date == utils.get_utcnow()
        assert note.author_made_contact == True
        assert note.reviewed == False

        note = notes[1]
        assert note.author_name == u'inna-testing'
        assert note.author_email == u'inna-testing@gmail.com'
        assert note.author_phone == u'inna-testing-number'
        assert note.email_of_found_person == u''
        assert note.phone_of_found_person == u''
        assert note.last_known_location == u'19.16592425362802 -71.9384765625'
        assert note.record_id == u'test.google.com/note.31095'
        assert note.text == u'new comment - testing'
        assert note.source_date == datetime.datetime(2000, 1, 17, 11, 12, 13)
        # Current date should replace the provided entry_date.
        assert note.entry_date.year == utils.get_utcnow().year
        assert note.author_made_contact is None
        assert note.reviewed == False

    def test_api_write_bad_key(self):
        """Attempt to post an entry with an invalid API key."""
        data = get_test_data('test.pfif-1.2.xml')
        self.go('/haiti/api/write?key=bad_key',
                data=data, type='application/xml')
        assert self.s.status == 403

    def test_api_write_empty_record(self):
        """Verify that empty entries are accepted."""
        doc = self.go('/haiti/api/write?key=test_key',
                data='''
<pfif xmlns="http://zesty.ca/pfif/1.2">
  <person>
    <person_record_id>test.google.com/person.empty</person_record_id>
  </person>
</pfif>''', type='application/xml')

        # The Person record should have been accepted.
        person_status = doc.first('status:write')
        self.assertEquals(person_status.first('status:written').text, '1')

        # An empty Person entity should be in the datastore.
        person = Person.get('haiti', 'test.google.com/person.empty')

    def test_api_write_wrong_domain(self):
        """Attempt to post an entry with a domain that doesn't match the key."""
        data = get_test_data('test.pfif-1.2.xml')
        doc = self.go('/haiti/api/write?key=other_key',
                      data=data, type='application/xml')

        # The Person record should have been rejected.
        person_status = doc.first('status:write')
        assert person_status.first('status:written').text == '0'
        assert ('Not in authorized domain' in
                person_status.first('status:error').text)

        # Both of the Note records should have been rejected.
        note_status = person_status.next('status:write')
        assert note_status.first('status:written').text == '0'
        first_error = note_status.first('status:error')
        second_error = first_error.next('status:error')
        assert 'Not in authorized domain' in first_error.text
        assert 'Not in authorized domain' in second_error.text

    def test_api_write_log_skipping(self):
        """Test skipping bad note entries."""
        configure_api_logging()
        data = get_test_data('test.pfif-1.2-badrecord.xml')
        self.go('/haiti/api/write?key=test_key',
                data=data, type='application/xml')
        assert self.s.status == 200, \
            'status = %s, content=%s' % (self.s.status, self.s.content)
        # verify we logged the write.
        verify_api_log(ApiActionLog.WRITE, person_records=1, people_skipped=1)

    def test_api_write_reviewed_note(self):
        """Post reviewed note entries."""
        data = get_test_data('test.pfif-1.2.xml')
        self.go('/haiti/api/write?key=reviewed_test_key',
                data=data, type='application/xml')
        person = Person.get('haiti', 'test.google.com/person.21009')
        notes = person.get_notes()
        assert len(notes) == 4
        # Confirm all notes are marked reviewed.
        for note in notes:
            assert note.reviewed == True

    def test_api_believed_dead_permission(self):
        """ Test whether the API key is authorized to report a person dead. """
        # Add the associated person record to the datastore
        data = get_test_data('test.pfif-1.2.xml')
        self.go('/haiti/api/write?key=test_key',
                data=data, type='application/xml')

        # Test authorized key.
        data = get_test_data('test.pfif-1.2-believed-dead.xml')
        doc = self.go(
            '/haiti/api/write?key=allow_believed_dead_test_key',
            data=data, type='application/xml')
        person = Person.get('haiti', 'test.google.com/person.21009')
        notes = person.get_notes()
        # Confirm the newly-added note with status believed_dead
        for note in notes:
            if note.note_record_id == 'test.google.com/note.218':
                assert note.status == 'believed_dead'

        # Test unauthorized key.
        doc = self.go(
            '/haiti/api/write?key=not_allow_believed_dead_test_key',
            data=data, type='application/xml')
        # The Person record should not be updated
        person_status = doc.first('status:write')
        assert person_status.first('status:written').text == '0'
        # The Note record should be rejected with error message
        note_status = person_status.next('status:write')
        assert note_status.first('status:parsed').text == '1'
        assert note_status.first('status:written').text == '0'
        assert ('Not authorized to post notes with the status \"believed_dead\"'
                in note_status.first('status:error').text)

    def test_api_subscribe_unsubscribe(self):
        """Subscribe and unsubscribe to e-mail updates for a person via API"""
        SUBSCRIBE_EMAIL = 'testsubscribe@example.com'
        db.put(Person(
            key_name='haiti:test.google.com/person.111',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name',
            entry_date=datetime.datetime.utcnow()
        ))
        person = Person.get('haiti', 'test.google.com/person.111')
        # Reset the MailThread queue _before_ making any requests
        # to the server, else risk errantly deleting messages
        self.mail_server.messages = []

        # Invalid key
        data = {
            'id': 'test.google.com/person.111',
            'lang': 'ja',
            'subscribe_email': SUBSCRIBE_EMAIL
        }
        self.go('/haiti/api/subscribe?key=test_key', data=data)
        self.assertEquals(403, self.s.status)
        assert 'invalid authorization' in self.s.content, \
            text_diff('invalid authorization', self.s.doc.content)

        # Invalid person
        data = {
            'id': 'test.google.com/person.123',
            'lang': 'ja',
            'subscribe_email': SUBSCRIBE_EMAIL
        }
        self.go('/haiti/api/subscribe?key=subscribe_key', data=data)
        assert 'Invalid person_record_id' in self.s.content

        # Empty email
        data = {
            'id': 'test.google.com/person.123',
            'lang': 'ja',
        }
        self.go('/haiti/api/subscribe?key=subscribe_key', data=data)
        assert 'Invalid email address' in self.s.content

        # Invalid email
        data = {
            'id': 'test.google.com/person.123',
            'lang': 'ja',
            'subscribe_email': 'junk'
        }
        self.go('/haiti/api/subscribe?key=subscribe_key', data=data)
        assert 'Invalid email address' in self.s.content, \
            text_diff('Invalid email address', self.s.content)

        # Valid subscription
        data = {
            'id': 'test.google.com/person.111',
            'lang': 'en',
            'subscribe_email': SUBSCRIBE_EMAIL
        }
        configure_api_logging()
        self.go('/haiti/api/subscribe?key=subscribe_key', data=data)
        # verify we logged the subscribe.
        verify_api_log(ApiActionLog.SUBSCRIBE, api_key='subscribe_key')

        subscriptions = person.get_subscriptions()
        assert 'Success' in self.s.content
        assert len(subscriptions) == 1
        assert subscriptions[0].email == SUBSCRIBE_EMAIL
        assert subscriptions[0].language == 'en'
        self.verify_email_sent()
        message = self.mail_server.messages[0]

        assert message['to'] == [SUBSCRIBE_EMAIL]
        assert 'do-not-reply@' in message['from']
        assert '_test_full_name' in message['data']
        assert 'view?id=test.google.com%2Fperson.111' in message['data']

        # Duplicate subscription
        self.go('/haiti/api/subscribe?key=subscribe_key', data=data)
        assert 'Already subscribed' in self.s.content
        assert len(subscriptions) == 1
        assert subscriptions[0].email == SUBSCRIBE_EMAIL
        assert subscriptions[0].language == 'en'

        # Already subscribed with new language
        data['lang'] = 'fr'
        self.go('/haiti/api/subscribe?key=subscribe_key', data=data)
        subscriptions = person.get_subscriptions()
        assert 'Success' in self.s.content
        assert len(subscriptions) == 1
        assert subscriptions[0].email == SUBSCRIBE_EMAIL
        assert subscriptions[0].language == 'fr'

        # Unsubscribe
        del data['lang']
        configure_api_logging()
        self.go('/haiti/api/unsubscribe?key=subscribe_key', data=data)
        assert 'Success' in self.s.content
        assert len(person.get_subscriptions()) == 0

        # verify we logged the unsub.
        verify_api_log(ApiActionLog.UNSUBSCRIBE, api_key='subscribe_key')

        # Unsubscribe non-existent subscription
        self.go('/haiti/api/unsubscribe?key=subscribe_key', data=data)
        assert 'Not subscribed' in self.s.content
        assert len(person.get_subscriptions()) == 0

    def test_api_read(self):
        """Fetch a single record as PFIF (1.1 - 1.4) via the read API."""
        db.put([Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            entry_date=datetime.datetime(2002, 2, 2, 2, 2, 2),
            author_email='_read_author_email',
            author_name='_read_author_name',
            author_phone='_read_author_phone',
            given_name='_read_given_name',
            family_name='_read_family_name',
            full_name='_first_dot_last',
            alternate_names='_read_alternate_name1\n_read_alternate_name2',
            description='_read_description & < > "',
            sex='female',
            date_of_birth='1970-01-01',
            age='40-50',
            home_city='_read_home_city',
            home_neighborhood='_read_home_neighborhood',
            home_state='_read_home_state',
            home_street='_read_home_street',
            home_postal_code='_read_home_postal_code',
            home_country='_read_home_country',
            photo_url='_read_photo_url',
            source_name='_read_source_name',
            source_url='_read_source_url',
            source_date=datetime.datetime(2001, 1, 1, 1, 1, 1),
            profile_urls='_read_profile_url1\n_read_profile_url2',
        ), Note(
            key_name='haiti:test.google.com/note.456',
            repo='haiti',
            author_email='_read_author_email',
            author_name='_read_author_name',
            author_phone='_read_author_phone',
            email_of_found_person='_read_email_of_found_person',
            last_known_location='_read_last_known_location',
            person_record_id='test.google.com/person.123',
            linked_person_record_id='test.google.com/person.888',
            phone_of_found_person='_read_phone_of_found_person',
            text='_read_text',
            photo_url='_read_note_photo_url',
            source_date=datetime.datetime(2005, 5, 5, 5, 5, 5),
            entry_date=datetime.datetime(2006, 6, 6, 6, 6, 6),
            author_made_contact=True,
            status='believed_missing'
        )])
        # check for logging as well
        configure_api_logging()

        # Fetch a PFIF 1.1 document.
        # Note that author_email, author_phone, email_of_found_person, and
        # phone_of_found_person are omitted intentionally (see
        # utils.filter_sensitive_fields).
        doc = self.go('/haiti/api/read' +
                      '?id=test.google.com/person.123&version=1.1')
        expected_content = \
'''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>2002-02-02T02:02:02Z</pfif:entry_date>
    <pfif:author_name>_read_author_name</pfif:author_name>
    <pfif:source_name>_read_source_name</pfif:source_name>
    <pfif:source_date>2001-01-01T01:01:01Z</pfif:source_date>
    <pfif:source_url>_read_source_url</pfif:source_url>
    <pfif:first_name>_read_given_name</pfif:first_name>
    <pfif:last_name>_read_family_name</pfif:last_name>
    <pfif:home_city>_read_home_city</pfif:home_city>
    <pfif:home_state>_read_home_state</pfif:home_state>
    <pfif:home_neighborhood>_read_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_street>_read_home_street</pfif:home_street>
    <pfif:home_zip>_read_home_postal_code</pfif:home_zip>
    <pfif:photo_url>_read_photo_url</pfif:photo_url>
    <pfif:other>description:
    _read_description &amp; &lt; &gt; "</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
      <pfif:entry_date>2006-06-06T06:06:06Z</pfif:entry_date>
      <pfif:author_name>_read_author_name</pfif:author_name>
      <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:last_known_location>_read_last_known_location</pfif:last_known_location>
      <pfif:text>_read_text</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>
'''
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # Fetch a PFIF 1.2 document.
        # Note that date_of_birth, author_email, author_phone,
        # email_of_found_person, and phone_of_found_person are omitted
        # intentionally (see utils.filter_sensitive_fields).
        doc = self.go('/haiti/api/read' +
                      '?id=test.google.com/person.123&version=1.2')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>2002-02-02T02:02:02Z</pfif:entry_date>
    <pfif:author_name>_read_author_name</pfif:author_name>
    <pfif:source_name>_read_source_name</pfif:source_name>
    <pfif:source_date>2001-01-01T01:01:01Z</pfif:source_date>
    <pfif:source_url>_read_source_url</pfif:source_url>
    <pfif:first_name>_read_given_name</pfif:first_name>
    <pfif:last_name>_read_family_name</pfif:last_name>
    <pfif:sex>female</pfif:sex>
    <pfif:age>40-50</pfif:age>
    <pfif:home_street>_read_home_street</pfif:home_street>
    <pfif:home_neighborhood>_read_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_city>_read_home_city</pfif:home_city>
    <pfif:home_state>_read_home_state</pfif:home_state>
    <pfif:home_postal_code>_read_home_postal_code</pfif:home_postal_code>
    <pfif:home_country>_read_home_country</pfif:home_country>
    <pfif:photo_url>_read_photo_url</pfif:photo_url>
    <pfif:other>description:
    _read_description &amp; &lt; &gt; "</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
      <pfif:entry_date>2006-06-06T06:06:06Z</pfif:entry_date>
      <pfif:author_name>_read_author_name</pfif:author_name>
      <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:status>believed_missing</pfif:status>
      <pfif:last_known_location>_read_last_known_location</pfif:last_known_location>
      <pfif:text>_read_text</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>
'''
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # Fetch a PFIF 1.3 document.
        # Note that date_of_birth, author_email, author_phone,
        # email_of_found_person, and phone_of_found_person are omitted
        # intentionally (see utils.filter_sensitive_fields).
        doc = self.go('/haiti/api/read' +
                      '?id=test.google.com/person.123&version=1.3')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>2002-02-02T02:02:02Z</pfif:entry_date>
    <pfif:author_name>_read_author_name</pfif:author_name>
    <pfif:source_name>_read_source_name</pfif:source_name>
    <pfif:source_date>2001-01-01T01:01:01Z</pfif:source_date>
    <pfif:source_url>_read_source_url</pfif:source_url>
    <pfif:full_name>_first_dot_last</pfif:full_name>
    <pfif:first_name>_read_given_name</pfif:first_name>
    <pfif:last_name>_read_family_name</pfif:last_name>
    <pfif:sex>female</pfif:sex>
    <pfif:age>40-50</pfif:age>
    <pfif:home_street>_read_home_street</pfif:home_street>
    <pfif:home_neighborhood>_read_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_city>_read_home_city</pfif:home_city>
    <pfif:home_state>_read_home_state</pfif:home_state>
    <pfif:home_postal_code>_read_home_postal_code</pfif:home_postal_code>
    <pfif:home_country>_read_home_country</pfif:home_country>
    <pfif:photo_url>_read_photo_url</pfif:photo_url>
    <pfif:other>description:
    _read_description &amp; &lt; &gt; "</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
      <pfif:entry_date>2006-06-06T06:06:06Z</pfif:entry_date>
      <pfif:author_name>_read_author_name</pfif:author_name>
      <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:status>believed_missing</pfif:status>
      <pfif:last_known_location>_read_last_known_location</pfif:last_known_location>
      <pfif:text>_read_text</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>
'''
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # Fetch a PFIF 1.4 document.
        # Note that date_of_birth, author_email, author_phone,
        # email_of_found_person, and phone_of_found_person are omitted
        # intentionally (see utils.filter_sensitive_fields).
        doc = self.go('/haiti/api/read' +
                      '?id=test.google.com/person.123&version=1.4')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.4">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>2002-02-02T02:02:02Z</pfif:entry_date>
    <pfif:author_name>_read_author_name</pfif:author_name>
    <pfif:source_name>_read_source_name</pfif:source_name>
    <pfif:source_date>2001-01-01T01:01:01Z</pfif:source_date>
    <pfif:source_url>_read_source_url</pfif:source_url>
    <pfif:full_name>_first_dot_last</pfif:full_name>
    <pfif:given_name>_read_given_name</pfif:given_name>
    <pfif:family_name>_read_family_name</pfif:family_name>
    <pfif:alternate_names>_read_alternate_name1
_read_alternate_name2</pfif:alternate_names>
    <pfif:description>_read_description &amp; &lt; &gt; "</pfif:description>
    <pfif:sex>female</pfif:sex>
    <pfif:age>40-50</pfif:age>
    <pfif:home_street>_read_home_street</pfif:home_street>
    <pfif:home_neighborhood>_read_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_city>_read_home_city</pfif:home_city>
    <pfif:home_state>_read_home_state</pfif:home_state>
    <pfif:home_postal_code>_read_home_postal_code</pfif:home_postal_code>
    <pfif:home_country>_read_home_country</pfif:home_country>
    <pfif:photo_url>_read_photo_url</pfif:photo_url>
    <pfif:profile_urls>_read_profile_url1
_read_profile_url2</pfif:profile_urls>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
      <pfif:entry_date>2006-06-06T06:06:06Z</pfif:entry_date>
      <pfif:author_name>_read_author_name</pfif:author_name>
      <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
      <pfif:author_made_contact>true</pfif:author_made_contact>
      <pfif:status>believed_missing</pfif:status>
      <pfif:last_known_location>_read_last_known_location</pfif:last_known_location>
      <pfif:text>_read_text</pfif:text>
      <pfif:photo_url>_read_note_photo_url</pfif:photo_url>
    </pfif:note>
  </pfif:person>
</pfif:pfif>
'''
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # Verify that 1.4 is the default version.
        default_doc = self.go('/haiti/api/read?id=test.google.com/person.123')
        assert default_doc.content == doc.content

        # Fetch a PFIF 1.2 document, with full read authorization.
        doc = self.go('/haiti/api/read?key=full_read_key' +
                      '&id=test.google.com/person.123&version=1.2')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>2002-02-02T02:02:02Z</pfif:entry_date>
    <pfif:author_name>_read_author_name</pfif:author_name>
    <pfif:author_email>_read_author_email</pfif:author_email>
    <pfif:author_phone>_read_author_phone</pfif:author_phone>
    <pfif:source_name>_read_source_name</pfif:source_name>
    <pfif:source_date>2001-01-01T01:01:01Z</pfif:source_date>
    <pfif:source_url>_read_source_url</pfif:source_url>
    <pfif:first_name>_read_given_name</pfif:first_name>
    <pfif:last_name>_read_family_name</pfif:last_name>
    <pfif:sex>female</pfif:sex>
    <pfif:date_of_birth>1970-01-01</pfif:date_of_birth>
    <pfif:age>40-50</pfif:age>
    <pfif:home_street>_read_home_street</pfif:home_street>
    <pfif:home_neighborhood>_read_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_city>_read_home_city</pfif:home_city>
    <pfif:home_state>_read_home_state</pfif:home_state>
    <pfif:home_postal_code>_read_home_postal_code</pfif:home_postal_code>
    <pfif:home_country>_read_home_country</pfif:home_country>
    <pfif:photo_url>_read_photo_url</pfif:photo_url>
    <pfif:other>description:
    _read_description &amp; &lt; &gt; "</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
      <pfif:entry_date>2006-06-06T06:06:06Z</pfif:entry_date>
      <pfif:author_name>_read_author_name</pfif:author_name>
      <pfif:author_email>_read_author_email</pfif:author_email>
      <pfif:author_phone>_read_author_phone</pfif:author_phone>
      <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:status>believed_missing</pfif:status>
      <pfif:email_of_found_person>_read_email_of_found_person</pfif:email_of_found_person>
      <pfif:phone_of_found_person>_read_phone_of_found_person</pfif:phone_of_found_person>
      <pfif:last_known_location>_read_last_known_location</pfif:last_known_location>
      <pfif:text>_read_text</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>
'''
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)


    def test_read_key(self):
        """Verifies that when read_auth_key_required is set, an authorization
        key is required to read data from the API or feeds."""
        db.put([Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            entry_date=datetime.datetime(2002, 2, 2, 2, 2, 2),
            author_email='_read_author_email',
            author_name='_read_author_name',
            author_phone='_read_author_phone',
            given_name='_read_given_name',
            family_name='_read_family_name',
            full_name='_read_given_name _read_family_name',
            alternate_names='_read_alternate_name1\n_read_alternate_name2',
            description='_read_description & < > "',
            sex='female',
            date_of_birth='1970-01-01',
            age='40-50',
            home_city='_read_home_city',
            home_neighborhood='_read_home_neighborhood',
            home_state='_read_home_state',
            home_street='_read_home_street',
            home_postal_code='_read_home_postal_code',
            home_country='_read_home_country',
            photo_url='_read_photo_url',
            profile_urls='_read_profile_url1\n_read_profile_url2',
            source_name='_read_source_name',
            source_url='_read_source_url',
            source_date=datetime.datetime(2001, 1, 1, 1, 1, 1),
        ), Note(
            key_name='haiti:test.google.com/note.456',
            repo='haiti',
            author_email='_read_author_email',
            author_name='_read_author_name',
            author_phone='_read_author_phone',
            email_of_found_person='_read_email_of_found_person',
            last_known_location='_read_last_known_location',
            person_record_id='test.google.com/person.123',
            linked_person_record_id='test.google.com/person.888',
            phone_of_found_person='_read_phone_of_found_person',
            text='_read_text',
            photo_url='_read_note_photo_url',
            source_date=datetime.datetime(2005, 5, 5, 5, 5, 5),
            entry_date=datetime.datetime(2006, 6, 6, 6, 6, 6),
            author_made_contact=True,
            status='believed_missing'
        )])

        config.set_for_repo('haiti', read_auth_key_required=True)
        try:
            # Fetch a PFIF 1.2 document from a domain that requires a read key.
            # Without an authorization key, the request should fail.
            doc = self.go('/haiti/api/read' +
                          '?id=test.google.com/person.123&version=1.2')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a non-read authorization key, the request should fail.
            doc = self.go('/haiti/api/read?key=test_key' +
                          '&id=test.google.com/person.123&version=1.2')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a valid read authorization key, the request should succeed.
            doc = self.go('/haiti/api/read?key=read_key' +
                          '&id=test.google.com/person.123&version=1.2')
            assert '_read_given_name' in doc.content

            # Fetch the person feed from a domain that requires a read key.
            # Without an authorization key, the request should fail.
            doc = self.go('/haiti/feeds/person')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a non-read authorization key, the request should fail.
            doc = self.go('/haiti/feeds/person?key=test_key')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a valid read authorization key, the request should succeed.
            doc = self.go('/haiti/feeds/person?key=read_key')
            assert '_read_author_name' in doc.content

            # Fetch the note feed from a domain that requires a read key.
            # Without an authorization key, the request should fail.
            doc = self.go('/haiti/feeds/note')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a non-read authorization key, the request should fail.
            doc = self.go('/haiti/feeds/note?key=test_key')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a valid read authorization key, the request should succeed.
            doc = self.go('/haiti/feeds/note?key=read_key')
            assert '_read_text' in doc.content

            # Repo feed does not require authorization key.
            doc = self.go('/global/feeds/repo')
            assert 'haiti' in doc.content

        finally:
            config.set_for_repo('haiti', read_auth_key_required=False)


    def test_api_read_with_non_ascii(self):
        """Fetch a record containing non-ASCII characters using the read API.
        This tests PFIF 1.1 - 1.4."""
        expiry_date = TEST_DATETIME + datetime.timedelta(days=1)
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            entry_date=TEST_DATETIME,
            expiry_date=expiry_date,
            author_name=u'a with acute = \u00e1',
            source_name=u'c with cedilla = \u00e7',
            source_url=u'e with acute = \u00e9',
            full_name=u'arabic alif = \u0627',
            given_name=u'greek alpha = \u03b1',
            family_name=u'hebrew alef = \u05d0',
            alternate_names=u'japanese a = \u3042',
            profile_urls=u'korean a = \uc544',
        ))

        # Fetch a PFIF 1.1 document.
        doc = self.go('/haiti/api/read?id=test.google.com/person.123'
                      '&version=1.1') #, charset='UTF-8')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>2010-01-01T00:00:00Z</pfif:entry_date>
    <pfif:author_name>a with acute = \xc3\xa1</pfif:author_name>
    <pfif:source_name>c with cedilla = \xc3\xa7</pfif:source_name>
    <pfif:source_url>e with acute = \xc3\xa9</pfif:source_url>
    <pfif:first_name>greek alpha = \xce\xb1</pfif:first_name>
    <pfif:last_name>hebrew alef = \xd7\x90</pfif:last_name>
  </pfif:person>
</pfif:pfif>
'''
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # Fetch a PFIF 1.2 document.
        configure_api_logging()
        doc = self.go('/haiti/api/read?id=test.google.com/person.123'
                      '&version=1.2')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>2010-01-01T00:00:00Z</pfif:entry_date>
    <pfif:author_name>a with acute = \xc3\xa1</pfif:author_name>
    <pfif:source_name>c with cedilla = \xc3\xa7</pfif:source_name>
    <pfif:source_url>e with acute = \xc3\xa9</pfif:source_url>
    <pfif:first_name>greek alpha = \xce\xb1</pfif:first_name>
    <pfif:last_name>hebrew alef = \xd7\x90</pfif:last_name>
  </pfif:person>
</pfif:pfif>
''', doc.content)
        # verify the log was written.
        verify_api_log(ApiActionLog.READ, api_key='')

        # Fetch a PFIF 1.3 document.
        doc = self.go('/haiti/api/read?' +
                      'id=test.google.com/person.123&version=1.3')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>2010-01-01T00:00:00Z</pfif:entry_date>
    <pfif:expiry_date>2010-01-02T00:00:00Z</pfif:expiry_date>
    <pfif:author_name>a with acute = \xc3\xa1</pfif:author_name>
    <pfif:source_name>c with cedilla = \xc3\xa7</pfif:source_name>
    <pfif:source_date></pfif:source_date>
    <pfif:source_url>e with acute = \xc3\xa9</pfif:source_url>
    <pfif:full_name>arabic alif = \xd8\xa7</pfif:full_name>
    <pfif:first_name>greek alpha = \xce\xb1</pfif:first_name>
    <pfif:last_name>hebrew alef = \xd7\x90</pfif:last_name>
  </pfif:person>
</pfif:pfif>
'''
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # Fetch a PFIF 1.4 document.
        doc = self.go('/haiti/api/read?' +
                      'id=test.google.com/person.123&version=1.4')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.4">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>2010-01-01T00:00:00Z</pfif:entry_date>
    <pfif:expiry_date>2010-01-02T00:00:00Z</pfif:expiry_date>
    <pfif:author_name>a with acute = \xc3\xa1</pfif:author_name>
    <pfif:source_name>c with cedilla = \xc3\xa7</pfif:source_name>
    <pfif:source_date></pfif:source_date>
    <pfif:source_url>e with acute = \xc3\xa9</pfif:source_url>
    <pfif:full_name>arabic alif = \xd8\xa7</pfif:full_name>
    <pfif:given_name>greek alpha = \xce\xb1</pfif:given_name>
    <pfif:family_name>hebrew alef = \xd7\x90</pfif:family_name>
    <pfif:alternate_names>japanese a = \xe3\x81\x82</pfif:alternate_names>
    <pfif:profile_urls>korean a = \xec\x95\x84</pfif:profile_urls>
  </pfif:person>
</pfif:pfif>
'''
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # Verify that PFIF 1.4 is the default version.
        default_doc = self.go('/haiti/api/read?id=test.google.com/person.123')
        assert default_doc.content == doc.content


    def test_search_api(self):
        """Verifies that the search API returns persons and notes correctly.
        Also check that it optionally requires a search-enabled API key."""
        # Add a first person to datastore.
        self.go('/haiti/create')
        self.s.submit(self.s.doc.first('form'),
                      given_name='_search_given_name',
                      family_name='_search_1st_family_name',
                      author_name='_search_1st_author_name')
        # Add a note for this person.
        self.s.submit(self.s.doc.first('form'),
                      author_made_contact='yes',
                      text='this is text for first person',
                      author_name='_search_1st_note_author_name')
        # Add a 2nd person with same given name but different family name.
        self.go('/haiti/create')
        self.s.submit(self.s.doc.first('form'),
                      given_name='_search_given_name',
                      family_name='_search_2nd_family_name',
                      author_name='_search_2nd_author_name')
        record_id_2 = self.s.doc.first('form').params['id']
        # Add a note for this 2nd person.
        self.s.submit(self.s.doc.first('form'),
                      author_made_contact='yes',
                      text='this is text for second person',
                      author_name='_search_2nd_note_author_name')

        config.set_for_repo('haiti', search_auth_key_required=True)
        try:
            # Make a search without a key, it should fail as config requires
            # a search_key.
            doc = self.go('/haiti/api/search' +
                          '?q=_search_1st_family_name')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a non-search authorization key, the request should fail.
            doc = self.go('/haiti/api/search?key=test_key' +
                          '&q=_search_1st_family_name')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a valid search authorization key, the request should succeed.
            configure_api_logging()
            doc = self.go('/haiti/api/search?key=search_key' +
                          '&q=_search_1st_family_name')
            assert self.s.status not in [403, 404]
            # verify we logged the search.
            verify_api_log(ApiActionLog.SEARCH, api_key='search_key')

            # Make sure we return the first record and not the 2nd one.
            assert '_search_1st_family_name' in doc.content
            assert '_search_2nd_family_name' not in doc.content
            # Check we also retrieved the first note and not the second one.
            assert '_search_1st_author_name' in doc.content
            assert '_search_2nd_author_name' not in doc.content

            # Check that we can retrieve a person by record ID.
            doc = self.go('/haiti/api/search?key=search_key&id=' + record_id_2)

            # Make sure we return the second record and not the first one.
            assert '_search_1st_family_name' not in doc.content
            assert '_search_2nd_family_name' in doc.content
            # Check we also retrieved the second note and not the first one.
            assert '_search_1st_author_name' not in doc.content
            assert '_search_2nd_author_name' in doc.content

            # Check that we can retrieve several persons matching a query
            # and check their notes are also retrieved.
            doc = self.go('/haiti/api/search?key=search_key' +
                          '&q=_search_given_name')
            assert self.s.status not in [403,404]
            # Check we found the 2 records.
            assert '_search_1st_family_name' in doc.content
            assert '_search_2nd_family_name' in doc.content
            # Check we also retrieved the notes.
            assert '_search_1st_note_author_name' in doc.content
            assert '_search_2nd_note_author_name' in doc.content

            # If no results are found we return an empty pfif file
            doc = self.go('/haiti/api/search?key=search_key' +
                          '&q=_wrong_family_name')
            assert self.s.status not in [403,404]
            empty_pfif = '''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.4">
</pfif:pfif>
'''
            assert (empty_pfif == doc.content), \
                text_diff(empty_pfif, doc.content)

            # Check that we can get results without a key if no key is required.
            config.set_for_repo('haiti', search_auth_key_required=False)
            doc = self.go('/haiti/api/search?' +
                          'q=_search_given_name')
            assert self.s.status not in [403,404]
            # Check we found 2 records.
            assert '_search_1st_family_name' in doc.content
            assert '_search_2nd_family_name' in doc.content
            # Check we also retrieved the notes.
            assert '_search_1st_note_author_name' in doc.content
            assert '_search_2nd_note_author_name' in doc.content

            # Check that max_result is working fine
            config.set_for_repo('haiti', search_auth_key_required=False)
            doc = self.go('/haiti/api/search?' +
                          'q=_search_given_name&max_results=1')
            assert self.s.status not in [403,404]
            # Check we found only 1 record. Note that we can't rely on
            # which record it found.
            assert len(re.findall(
                '<pfif:given_name>_search_given_name', doc.content)) == 1
            assert len(re.findall('<pfif:person>', doc.content)) == 1

            # Check we also retrieved exactly one note.
            assert len(re.findall('<pfif:note>', doc.content)) == 1
        finally:
            config.set_for_repo('haiti', search_auth_key_required=False)


    def test_person_feed(self):
        """Fetch a single person using the PFIF Atom feed."""
        configure_api_logging()
        db.put([Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            entry_date=datetime.datetime(2002, 2, 2, 2, 2, 2),
            author_email='_feed_author_email',
            author_name='_feed_author_name',
            author_phone='_feed_author_phone',
            full_name='_feed_full_name1\n_feed_full_name2',
            given_name='_feed_given_name',
            family_name='_feed_family_name',
            alternate_names='_feed_alternate_name1\n_feed_alternate_name2',
            description='_feed_description & < > "',
            sex='male',
            date_of_birth='1975',
            age='30-40',
            home_street='_feed_home_street',
            home_neighborhood='_feed_home_neighborhood',
            home_city='_feed_home_city',
            home_state='_feed_home_state',
            home_postal_code='_feed_home_postal_code',
            home_country='_feed_home_country',
            photo_url='_feed_photo_url',
            profile_urls='_feed_profile_url1\n_feed_profile_url2',
            source_name='_feed_source_name',
            source_url='_feed_source_url',
            source_date=datetime.datetime(2001, 1, 1, 1, 1, 1),
        ), Note(
            key_name='haiti:test.google.com/note.456',
            repo='haiti',
            author_email='_feed_author_email',
            author_name='_feed_author_name',
            author_phone='_feed_author_phone',
            email_of_found_person='_feed_email_of_found_person',
            last_known_location='_feed_last_known_location',
            person_record_id='test.google.com/person.123',
            linked_person_record_id='test.google.com/person.888',
            phone_of_found_person='_feed_phone_of_found_person',
            text='_feed_text',
            photo_url='_feed_note_photo_url',
            source_date=datetime.datetime(2005, 5, 5, 5, 5, 5),
            entry_date=datetime.datetime(2006, 6, 6, 6, 6, 6),
            author_made_contact=True,
            status='is_note_author'
        )])

        note = None
        # Feeds use PFIF 1.4 by default.
        # Note that date_of_birth, author_email, author_phone,
        # email_of_found_person, and phone_of_found_person are omitted
        # intentionally (see utils.filter_sensitive_fields).
        # TODO(kpy): This is consistent with the PFIF spec, but it seems weird
        # that the <feed>'s <updated> element contains the entry_date whereas
        # the <person>'s <updated> element is the source_date.  Per RFC 4287,
        # entry_date is probably a better choice.
        doc = self.go('/haiti/feeds/person')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.4">
  <id>http://%s/personfinder/haiti/feeds/person</id>
  <title>%s</title>
  <subtitle>PFIF Person Feed generated by Person Finder at %s</subtitle>
  <updated>2002-02-02T02:02:02Z</updated>
  <link rel="self">http://%s/personfinder/haiti/feeds/person</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:entry_date>2002-02-02T02:02:02Z</pfif:entry_date>
      <pfif:author_name>_feed_author_name</pfif:author_name>
      <pfif:source_name>_feed_source_name</pfif:source_name>
      <pfif:source_date>2001-01-01T01:01:01Z</pfif:source_date>
      <pfif:source_url>_feed_source_url</pfif:source_url>
      <pfif:full_name>_feed_full_name1
_feed_full_name2</pfif:full_name>
      <pfif:given_name>_feed_given_name</pfif:given_name>
      <pfif:family_name>_feed_family_name</pfif:family_name>
      <pfif:alternate_names>_feed_alternate_name1
_feed_alternate_name2</pfif:alternate_names>
      <pfif:description>_feed_description &amp; &lt; &gt; "</pfif:description>
      <pfif:sex>male</pfif:sex>
      <pfif:age>30-40</pfif:age>
      <pfif:home_street>_feed_home_street</pfif:home_street>
      <pfif:home_neighborhood>_feed_home_neighborhood</pfif:home_neighborhood>
      <pfif:home_city>_feed_home_city</pfif:home_city>
      <pfif:home_state>_feed_home_state</pfif:home_state>
      <pfif:home_postal_code>_feed_home_postal_code</pfif:home_postal_code>
      <pfif:home_country>_feed_home_country</pfif:home_country>
      <pfif:photo_url>_feed_photo_url</pfif:photo_url>
      <pfif:profile_urls>_feed_profile_url1
_feed_profile_url2</pfif:profile_urls>
      <pfif:note>
        <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
        <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
        <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
        <pfif:entry_date>2006-06-06T06:06:06Z</pfif:entry_date>
        <pfif:author_name>_feed_author_name</pfif:author_name>
        <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
        <pfif:author_made_contact>true</pfif:author_made_contact>
        <pfif:status>is_note_author</pfif:status>
        <pfif:last_known_location>_feed_last_known_location</pfif:last_known_location>
        <pfif:text>_feed_text</pfif:text>
        <pfif:photo_url>_feed_note_photo_url</pfif:photo_url>
      </pfif:note>
    </pfif:person>
    <id>pfif:test.google.com/person.123</id>
    <title>_feed_full_name1</title>
    <author>
      <name>_feed_author_name</name>
    </author>
    <updated>2001-01-01T01:01:01Z</updated>
    <source>
      <title>%s</title>
    </source>
    <content>_feed_full_name1</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport,
       self.hostport)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # verify we logged the read.
        verify_api_log(ApiActionLog.READ, api_key='')

        # Test the omit_notes parameter.
        doc = self.go('/haiti/feeds/person?omit_notes=yes')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.4">
  <id>http://%s/personfinder/haiti/feeds/person?omit_notes=yes</id>
  <title>%s</title>
  <subtitle>PFIF Person Feed generated by Person Finder at %s</subtitle>
  <updated>2002-02-02T02:02:02Z</updated>
  <link rel="self">http://%s/personfinder/haiti/feeds/person?omit_notes=yes</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:entry_date>2002-02-02T02:02:02Z</pfif:entry_date>
      <pfif:author_name>_feed_author_name</pfif:author_name>
      <pfif:source_name>_feed_source_name</pfif:source_name>
      <pfif:source_date>2001-01-01T01:01:01Z</pfif:source_date>
      <pfif:source_url>_feed_source_url</pfif:source_url>
      <pfif:full_name>_feed_full_name1
_feed_full_name2</pfif:full_name>
      <pfif:given_name>_feed_given_name</pfif:given_name>
      <pfif:family_name>_feed_family_name</pfif:family_name>
      <pfif:alternate_names>_feed_alternate_name1
_feed_alternate_name2</pfif:alternate_names>
      <pfif:description>_feed_description &amp; &lt; &gt; "</pfif:description>
      <pfif:sex>male</pfif:sex>
      <pfif:age>30-40</pfif:age>
      <pfif:home_street>_feed_home_street</pfif:home_street>
      <pfif:home_neighborhood>_feed_home_neighborhood</pfif:home_neighborhood>
      <pfif:home_city>_feed_home_city</pfif:home_city>
      <pfif:home_state>_feed_home_state</pfif:home_state>
      <pfif:home_postal_code>_feed_home_postal_code</pfif:home_postal_code>
      <pfif:home_country>_feed_home_country</pfif:home_country>
      <pfif:photo_url>_feed_photo_url</pfif:photo_url>
      <pfif:profile_urls>_feed_profile_url1
_feed_profile_url2</pfif:profile_urls>
    </pfif:person>
    <id>pfif:test.google.com/person.123</id>
    <title>_feed_full_name1</title>
    <author>
      <name>_feed_author_name</name>
    </author>
    <updated>2001-01-01T01:01:01Z</updated>
    <source>
      <title>%s</title>
    </source>
    <content>_feed_full_name1</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport,
       self.hostport)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # Fetch the entry, with full read authorization.
        doc = self.go('/haiti/feeds/person?key=full_read_key')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.4">
  <id>http://%s/personfinder/haiti/feeds/person?key=full_read_key</id>
  <title>%s</title>
  <subtitle>PFIF Person Feed generated by Person Finder at %s</subtitle>
  <updated>2002-02-02T02:02:02Z</updated>
  <link rel="self">http://%s/personfinder/haiti/feeds/person?key=full_read_key</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:entry_date>2002-02-02T02:02:02Z</pfif:entry_date>
      <pfif:author_name>_feed_author_name</pfif:author_name>
      <pfif:author_email>_feed_author_email</pfif:author_email>
      <pfif:author_phone>_feed_author_phone</pfif:author_phone>
      <pfif:source_name>_feed_source_name</pfif:source_name>
      <pfif:source_date>2001-01-01T01:01:01Z</pfif:source_date>
      <pfif:source_url>_feed_source_url</pfif:source_url>
      <pfif:full_name>_feed_full_name1
_feed_full_name2</pfif:full_name>
      <pfif:given_name>_feed_given_name</pfif:given_name>
      <pfif:family_name>_feed_family_name</pfif:family_name>
      <pfif:alternate_names>_feed_alternate_name1
_feed_alternate_name2</pfif:alternate_names>
      <pfif:description>_feed_description &amp; &lt; &gt; "</pfif:description>
      <pfif:sex>male</pfif:sex>
      <pfif:date_of_birth>1975</pfif:date_of_birth>
      <pfif:age>30-40</pfif:age>
      <pfif:home_street>_feed_home_street</pfif:home_street>
      <pfif:home_neighborhood>_feed_home_neighborhood</pfif:home_neighborhood>
      <pfif:home_city>_feed_home_city</pfif:home_city>
      <pfif:home_state>_feed_home_state</pfif:home_state>
      <pfif:home_postal_code>_feed_home_postal_code</pfif:home_postal_code>
      <pfif:home_country>_feed_home_country</pfif:home_country>
      <pfif:photo_url>_feed_photo_url</pfif:photo_url>
      <pfif:profile_urls>_feed_profile_url1
_feed_profile_url2</pfif:profile_urls>
      <pfif:note>
        <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
        <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
        <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
        <pfif:entry_date>2006-06-06T06:06:06Z</pfif:entry_date>
        <pfif:author_name>_feed_author_name</pfif:author_name>
        <pfif:author_email>_feed_author_email</pfif:author_email>
        <pfif:author_phone>_feed_author_phone</pfif:author_phone>
        <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
        <pfif:author_made_contact>true</pfif:author_made_contact>
        <pfif:status>is_note_author</pfif:status>
        <pfif:email_of_found_person>_feed_email_of_found_person</pfif:email_of_found_person>
        <pfif:phone_of_found_person>_feed_phone_of_found_person</pfif:phone_of_found_person>
        <pfif:last_known_location>_feed_last_known_location</pfif:last_known_location>
        <pfif:text>_feed_text</pfif:text>
        <pfif:photo_url>_feed_note_photo_url</pfif:photo_url>
      </pfif:note>
    </pfif:person>
    <id>pfif:test.google.com/person.123</id>
    <title>_feed_full_name1</title>
    <author>
      <name>_feed_author_name</name>
      <email>_feed_author_email</email>
    </author>
    <updated>2001-01-01T01:01:01Z</updated>
    <source>
      <title>%s</title>
    </source>
    <content>_feed_full_name1</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport,
       self.hostport)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

    def test_note_feed(self):
        """Fetch a single note using the PFIF Atom feed."""
        db.put([Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            entry_date=datetime.datetime(2002, 2, 2, 2, 2, 2),
            full_name='_feed_full_name',
        ), Note(
            key_name='haiti:test.google.com/note.456',
            repo='haiti',
            person_record_id='test.google.com/person.123',
            linked_person_record_id='test.google.com/person.888',
            author_email='_feed_author_email',
            author_name='_feed_author_name',
            author_phone='_feed_author_phone',
            email_of_found_person='_feed_email_of_found_person',
            last_known_location='_feed_last_known_location',
            phone_of_found_person='_feed_phone_of_found_person',
            text='_feed_text',
            photo_url='_feed_photo_url_for_note',
            source_date=datetime.datetime(2005, 5, 5, 5, 5, 5),
            entry_date=datetime.datetime(2006, 6, 6, 6, 6, 6),
            author_made_contact=True,
            status='believed_dead'
        )])

        # Feeds use PFIF 1.4 by default.
        # Note that author_email, author_phone, email_of_found_person, and
        # phone_of_found_person are omitted intentionally (see
        # utils.filter_sensitive_fields).
        doc = self.go('/haiti/feeds/note')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.4">
  <id>http://%s/personfinder/haiti/feeds/note</id>
  <title>%s</title>
  <subtitle>PFIF Note Feed generated by Person Finder at %s</subtitle>
  <updated>2006-06-06T06:06:06Z</updated>
  <link rel="self">http://%s/personfinder/haiti/feeds/note</link>
  <entry>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
      <pfif:entry_date>2006-06-06T06:06:06Z</pfif:entry_date>
      <pfif:author_name>_feed_author_name</pfif:author_name>
      <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
      <pfif:author_made_contact>true</pfif:author_made_contact>
      <pfif:status>believed_dead</pfif:status>
      <pfif:last_known_location>_feed_last_known_location</pfif:last_known_location>
      <pfif:text>_feed_text</pfif:text>
      <pfif:photo_url>_feed_photo_url_for_note</pfif:photo_url>
    </pfif:note>
    <id>pfif:test.google.com/note.456</id>
    <title>_feed_text</title>
    <author>
      <name>_feed_author_name</name>
    </author>
    <updated>2006-06-06T06:06:06Z</updated>
    <content>_feed_text</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

    def test_person_feed_with_bad_chars(self):
        """Fetch a person whose fields contain characters that are not
        legally representable in XML, using the PFIF Atom feed."""
        # See: http://www.w3.org/TR/REC-xml/#charsets
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            entry_date=datetime.datetime(2002, 2, 2, 2, 2, 2),
            author_name=u'illegal character (\x01)',
            full_name=u'illegal character (\x02)',
            given_name=u'illegal character (\x1a)',
            family_name=u'illegal character (\ud800)',
            source_date=datetime.datetime(2001, 1, 1, 1, 1, 1)
        ))

        # Note that author_email, author_phone, email_of_found_person, and
        # phone_of_found_person are omitted intentionally (see
        # utils.filter_sensitive_fields).
        doc = self.go('/haiti/feeds/person')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.4">
  <id>http://%s/personfinder/haiti/feeds/person</id>
  <title>%s</title>
  <subtitle>PFIF Person Feed generated by Person Finder at %s</subtitle>
  <updated>2002-02-02T02:02:02Z</updated>
  <link rel="self">http://%s/personfinder/haiti/feeds/person</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:entry_date>2002-02-02T02:02:02Z</pfif:entry_date>
      <pfif:author_name>illegal character ()</pfif:author_name>
      <pfif:source_date>2001-01-01T01:01:01Z</pfif:source_date>
      <pfif:full_name>illegal character ()</pfif:full_name>
      <pfif:given_name>illegal character ()</pfif:given_name>
      <pfif:family_name>illegal character ()</pfif:family_name>
    </pfif:person>
    <id>pfif:test.google.com/person.123</id>
    <title>illegal character ()</title>
    <author>
      <name>illegal character ()</name>
    </author>
    <updated>2001-01-01T01:01:01Z</updated>
    <source>
      <title>%s</title>
    </source>
    <content>illegal character ()</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport,
       self.hostport)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

    def test_person_feed_with_non_ascii(self):
        """Fetch a person whose fields contain non-ASCII characters,
        using the PFIF Atom feed."""
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            entry_date=datetime.datetime(2002, 2, 2, 2, 2, 2),
            author_name=u'a with acute = \u00e1',
            source_name=u'c with cedilla = \u00e7',
            source_url=u'e with acute = \u00e9',
            full_name=u'chinese a = \u4e9c',
            given_name=u'greek alpha = \u03b1',
            family_name=u'hebrew alef = \u05d0',
            alternate_names=u'japanese a = \u3042',
            profile_urls=u'korean a = \uc544',
            source_date=datetime.datetime(2001, 1, 1, 1, 1, 1)
        ))

        # Note that author_email, author_phone, email_of_found_person, and
        # phone_of_found_person are omitted intentionally (see
        # utils.filter_sensitive_fields).
        doc = self.go('/haiti/feeds/person')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.4">
  <id>http://%s/personfinder/haiti/feeds/person</id>
  <title>%s</title>
  <subtitle>PFIF Person Feed generated by Person Finder at %s</subtitle>
  <updated>2002-02-02T02:02:02Z</updated>
  <link rel="self">http://%s/personfinder/haiti/feeds/person</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:entry_date>2002-02-02T02:02:02Z</pfif:entry_date>
      <pfif:author_name>a with acute = \xc3\xa1</pfif:author_name>
      <pfif:source_name>c with cedilla = \xc3\xa7</pfif:source_name>
      <pfif:source_date>2001-01-01T01:01:01Z</pfif:source_date>
      <pfif:source_url>e with acute = \xc3\xa9</pfif:source_url>
      <pfif:full_name>chinese a = \xe4\xba\x9c</pfif:full_name>
      <pfif:given_name>greek alpha = \xce\xb1</pfif:given_name>
      <pfif:family_name>hebrew alef = \xd7\x90</pfif:family_name>
      <pfif:alternate_names>japanese a = \xe3\x81\x82</pfif:alternate_names>
      <pfif:profile_urls>korean a = \xec\x95\x84</pfif:profile_urls>
    </pfif:person>
    <id>pfif:test.google.com/person.123</id>
    <title>chinese a = \xe4\xba\x9c</title>
    <author>
      <name>a with acute = \xc3\xa1</name>
    </author>
    <updated>2001-01-01T01:01:01Z</updated>
    <source>
      <title>%s</title>
    </source>
    <content>chinese a = \xe4\xba\x9c</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport,
       self.hostport)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

    def test_person_feed_parameters(self):
        """Test the max_results, skip, and min_entry_date parameters."""
        db.put([Person(
            key_name='haiti:test.google.com/person.%d' % i,
            repo='haiti',
            entry_date=datetime.datetime(2000, 1, 1, i, i, i),
            full_name='_test_full_name.%d' % i,
        ) for i in range(1, 21)])  # Create 20 persons.

        def assert_ids(*ids):
            person_ids = re.findall(r'record_id>test.google.com/person.(\d+)',
                                    self.s.doc.content)
            assert map(int, person_ids) == list(ids)

        # Should get records in reverse chronological order by default.
        doc = self.go('/haiti/feeds/person')
        assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12, 11)

        # Fewer results.
        doc = self.go('/haiti/feeds/person?max_results=1')
        assert_ids(20)
        doc = self.go('/haiti/feeds/person?max_results=9')
        assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12)

        # More results.
        doc = self.go('/haiti/feeds/person?max_results=12')
        assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9)

        # Skip some results.
        doc = self.go('/haiti/feeds/person?skip=12&max_results=5')
        assert_ids(8, 7, 6, 5, 4)

        # Should get records in forward chronological order with min_entry_date.
        doc = self.go('/haiti/feeds/person' +
                      '?min_entry_date=2000-01-01T18:18:18Z')
        assert_ids(18, 19, 20)

        doc = self.go('/haiti/feeds/person' +
                      '?min_entry_date=2000-01-01T03:03:03Z')
        assert_ids(3, 4, 5, 6, 7, 8, 9, 10, 11, 12)

        doc = self.go('/haiti/feeds/person?' +
                      'min_entry_date=2000-01-01T03:03:04Z')
        assert_ids(4, 5, 6, 7, 8, 9, 10, 11, 12, 13)

    def test_note_feed_parameters(self):
        """Test the max_results, skip, min_entry_date, and person_record_id
        parameters."""
        entities = []
        for i in range(1, 3):  # Create person.1 and person.2.
            entities.append(Person(
                key_name='haiti:test.google.com/person.%d' % i,
                repo='haiti',
                entry_date=datetime.datetime(2000, 1, 1, i, i, i),
                full_name='_test_full_name',
            ))
        for i in range(1, 6):  # Create notes 1-5 on person.1.
            entities.append(Note(
                key_name='haiti:test.google.com/note.%d' % i,
                repo='haiti',
                person_record_id='test.google.com/person.1',
                entry_date=datetime.datetime(2000, 1, 1, i, i, i)
            ))
        for i in range(6, 18):  # Create notes 6-17 on person.2.
            entities.append(Note(
                key_name='haiti:test.google.com/note.%d' % i,
                repo='haiti',
                person_record_id='test.google.com/person.2',
                entry_date=datetime.datetime(2000, 1, 1, i, i, i)
            ))
        for i in range(18, 21):  # Create notes 18-20 on person.1.
            entities.append(Note(
                key_name='haiti:test.google.com/note.%d' % i,
                repo='haiti',
                person_record_id='test.google.com/person.1',
                entry_date=datetime.datetime(2000, 1, 1, i, i, i)
            ))
        db.put(entities)

        def assert_ids(*ids):
            note_ids = re.findall(r'record_id>test.google.com/note.(\d+)',
                                  self.s.doc.content)
            self.assertEquals(map(int, note_ids), list(ids))

        # Should get records in reverse chronological order by default.
        doc = self.go('/haiti/feeds/note')
        assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12, 11)

        # Fewer results.
        doc = self.go('/haiti/feeds/note?max_results=1')
        assert_ids(20)
        doc = self.go('/haiti/feeds/note?max_results=9')
        assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12)

        # More results.
        doc = self.go('/haiti/feeds/note?max_results=12')
        assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9)

        # Skip some results.
        doc = self.go('/haiti/feeds/note?skip=12&max_results=5')
        assert_ids(8, 7, 6, 5, 4)

        # Should get records in forward chronological order.
        doc = self.go('/haiti/feeds/note' +
                      '?min_entry_date=2000-01-01T18:18:18Z')
        assert_ids(18, 19, 20)

        doc = self.go('/haiti/feeds/note' +
                      '?min_entry_date=2000-01-01T03:03:03Z')
        assert_ids(3, 4, 5, 6, 7, 8, 9, 10, 11, 12)

        doc = self.go('/haiti/feeds/note' +
                      '?min_entry_date=2000-01-01T03:03:04Z')
        assert_ids(4, 5, 6, 7, 8, 9, 10, 11, 12, 13)

        # Filter by person_record_id.
        doc = self.go('/haiti/feeds/note' +
                      '?person_record_id=test.google.com/person.1')
        assert_ids(20, 19, 18, 5, 4, 3, 2, 1)

        doc = self.go('/haiti/feeds/note' +
                      '?person_record_id=test.google.com/person.2')
        assert_ids(17, 16, 15, 14, 13, 12, 11, 10, 9, 8)

        doc = self.go('/haiti/feeds/note' +
                      '?person_record_id=test.google.com/person.2' +
                      '&max_results=11')
        assert_ids(17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7)

        doc = self.go('/haiti/feeds/note' +
                      '?person_record_id=test.google.com/person.1' +
                      '&min_entry_date=2000-01-01T03:03:03Z')
        assert_ids(3, 4, 5, 18, 19, 20)

        doc = self.go('/haiti/feeds/note' +
                      '?person_record_id=test.google.com/person.1' +
                      '&min_entry_date=2000-01-01T03:03:04Z')
        assert_ids(4, 5, 18, 19, 20)

        doc = self.go('/haiti/feeds/note' +
                      '?person_record_id=test.google.com/person.2' +
                      '&min_entry_date=2000-01-01T06:06:06Z')
        assert_ids(6, 7, 8, 9, 10, 11, 12, 13, 14, 15)

    def test_head_request(self):
        db.put(Person(
            key_name='haiti:test.google.com/person.111',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name',
            entry_date=datetime.datetime.utcnow()
        ))
        url, status, message, headers, content, charset = scrape.fetch(
            'http://' + self.hostport +
            '/personfinder/haiti/view?id=test.google.com/person.111',
            method='HEAD')
        assert status == 200
        assert content == ''


    def test_api_read_status(self):
        """Test the reading of the note status field at /api/read and /feeds."""

        # A missing status should not appear as a tag.
        db.put(Person(
            key_name='haiti:test.google.com/person.1001',
            repo='haiti',
            entry_date=TEST_DATETIME,
            full_name='_status_full_name',
            author_name='_status_author_name'
        ))
        doc = self.go('/haiti/api/read' +
                      '?id=test.google.com/person.1001')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/haiti/feeds/person')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/haiti/feeds/note')
        assert '<pfif:status>' not in doc.content

        # An unspecified status should not appear as a tag.
        db.put(Note(
            key_name='haiti:test.google.com/note.2002',
            repo='haiti',
            person_record_id='test.google.com/person.1001',
            entry_date=TEST_DATETIME
        ))
        doc = self.go('/haiti/api/read' +
                      '?id=test.google.com/person.1001')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/haiti/feeds/person')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/haiti/feeds/note')
        assert '<pfif:status>' not in doc.content

        # An empty status should not appear as a tag.
        db.put(Note(
            key_name='haiti:test.google.com/note.2002',
            repo='haiti',
            person_record_id='test.google.com/person.1001',
            status='',
            entry_date=TEST_DATETIME
        ))
        doc = self.go('/haiti/api/read' +
                      '?id=test.google.com/person.1001')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/haiti/feeds/person')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/haiti/feeds/note')
        assert '<pfif:status>' not in doc.content

        # When the status is specified, it should appear in the feed.
        db.put(Note(
            key_name='haiti:test.google.com/note.2002',
            repo='haiti',
            person_record_id='test.google.com/person.1001',
            entry_date=TEST_DATETIME,
            status='believed_alive'
        ))
        doc = self.go('/haiti/api/read' +
                      '?id=test.google.com/person.1001')
        assert '<pfif:status>believed_alive</pfif:status>' in doc.content
        doc = self.go('/haiti/feeds/person')
        assert '<pfif:status>believed_alive</pfif:status>' in doc.content
        doc = self.go('/haiti/feeds/note')
        assert '<pfif:status>believed_alive</pfif:status>' in doc.content

    def test_delete_clone(self):
        """Confirms that attempting to delete clone records produces the
        appropriate UI message."""
        person, note = self.setup_person_and_note('test.google.com')

        # Check that there is a Delete button on the view page.
        p123_id = 'test.google.com/person.123'
        doc = self.go('/haiti/view?id=' + p123_id)
        button = doc.firsttag('input', value='Delete this record')
        # verify no extend button for clone record
        extend_button = None
        try:
            doc.firsttag('input', id='extend_btn')
        except scrape.ScrapeError:
            pass
        assert not extend_button, 'Didn\'t expect to find expiry extend button'

        # Check that the deletion confirmation page shows the right message.
        doc = self.s.follow_button(button)
        assert 'we might later receive another copy' in doc.text

        # Click the button to delete a record.
        button = doc.firsttag('input', value='Yes, delete the record')
        doc = self.s.submit(button)

        # Check to make sure that the user was redirected to the same page due
        # to an invalid captcha.
        assert 'delete the record for "_test_given_name ' + \
               '_test_family_name"' in doc.text
        assert 'incorrect-captcha-sol' in doc.content

        # Continue with a valid captcha (faked, for purpose of test). Check the
        # sent messages for proper notification of related e-mail accounts.
        doc = self.go(
            '/haiti/delete',
            data='id=test.google.com/person.123&' +
                 'reason_for_deletion=spam_received&test_mode=yes')

        # Both entities should be gone.
        assert not db.get(person.key())
        assert not db.get(note.key())

        # Clone deletion cannot be undone, so no e-mail should have been sent.
        assert len(self.mail_server.messages) == 0

    def test_expire_clone(self):
        """Confirms that an expiring delete clone record behaves properly."""
        person, note = self.setup_person_and_note('test.google.com')

        # Check that they exist
        p123_id = 'test.google.com/person.123'
        self.advance_utcnow(days=40)
        # Both entities should be there.
        assert db.get(person.key())
        assert db.get(note.key())

        doc = self.go('/haiti/view?id=' + p123_id)
        self.advance_utcnow(days=1)  # past the default 40-day expiry period
        # run the delete_old task
        doc = self.go('/haiti/tasks/delete_old')
        # Both entities should be gone.
        assert not db.get(person.key())
        assert not db.get(note.key())

        # Clone deletion cannot be undone, so no e-mail should have been sent.
        assert len(self.mail_server.messages) == 0

    def test_default_expiration_config(self):
        """Verifies that the default expiration config setting works."""
        config.set_for_repo('haiti', default_expiration_days=10)
        person, note = self.setup_person_and_note('test.google.com')
        # original_creation_date is auto_now, so we tweak it first.
        person.original_creation_date = person.source_date
        person.source_date = None
        person.put()
        assert person.original_creation_date == TEST_DATETIME, '%s != %s' % (
            person.original_creation_date, TEST_DATETIME)

        self.advance_utcnow(days=11)  # past the configured 10-day expiry period
        # run the delete_old task
        doc = self.go('/haiti/tasks/delete_old')
        # Both entities should be gone.
        assert not db.get(person.key())
        assert not db.get(note.key())

    def test_photo(self):
        """Checks that a stored photo can be retrieved."""
        person, note = self.setup_person_and_note()
        photo = self.setup_photo(person)
        note_photo = self.setup_photo(note)
        for photo in [photo, note_photo]:
            id = photo.key().name().split(':')[1]
            # Should be available in the 'haiti' repo.
            doc = self.go('/haiti/photo?id=%s' % id)
            assert self.s.status == 200
            assert doc.content == 'xyz'
            # Should not be available in a different repo.
            self.go('/pakistan/photo?id=%s' % id)
            assert self.s.status == 404

    def test_xss_photo(self):
        person, note = self.setup_person_and_note()
        photo = self.setup_photo(person)
        note_photo = self.setup_photo(note)
        for record in [person, note]:
            doc = self.go('/haiti/view?id=' + person.record_id)
            assert record.photo_url not in doc.content
            record.photo_url = 'http://xyz'
            record.put()
            doc = self.go('/haiti/view?id=' + person.record_id)
            assert '//xyz' in doc.content
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
        profile_urls = ['http://abc', 'http://def', 'http://ghi']
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

    def test_extend_expiry(self):
        """Verify that extension of the expiry date works as expected."""
        person, note = self.setup_person_and_note()
        doc = self.go('/haiti/view?id=' + person.record_id)
        # With no expiry date, there should be no extend button.
        try:
            tag = doc.firsttag('input', id='extend_btn')
            assert True, 'unexpectedly found tag %s' % s
        except scrape.ScrapeError:
            pass
        # Now add an expiry date.
        expiry_date = TEST_DATETIME + datetime.timedelta(days=18)
        person.expiry_date = expiry_date
        db.put([person])

        # Advance time to within one day of expiry.
        self.advance_utcnow(days=17, seconds=1)
        # There should be an expiration warning.
        doc = self.go('/haiti/view?id=' + person.record_id)
        assert 'Warning: this record will expire' in doc.text
        button = doc.firsttag('input', id='extend_btn')
        assert button, 'Failed to find expiry extend button'
        extend_url = '/haiti/extend?id=' + person.record_id
        doc = self.s.submit(button, url=extend_url)
        assert 'extend the expiration' in doc.text
        # Click the extend button.
        doc = self.s.follow_button(button)
        assert 'extend the expiration' in doc.text
        # Click the button on the confirmation page.
        button = doc.firsttag('input', value='Yes, extend the record')
        doc = self.s.submit(button)
        # Verify that we failed the captcha.
        assert 'extend the expiration' in doc.text
        assert 'incorrect-captcha-sol' in doc.content
        # Simulate passing the captcha.
        doc = self.go('/haiti/extend',
                      data='id=' + str(person.record_id) + '&test_mode=yes')
        # Verify that the expiry date was extended.
        person = Person.get('haiti', person.record_id)
        self.assertEquals(expiry_date + datetime.timedelta(days=60),
                          person.expiry_date)
        # Verify that the expiration warning is gone.
        doc = self.go('/haiti/view?id=' + person.record_id)
        assert 'Warning: this record will expire' not in doc.text

    def test_disable_and_enable_notes(self):
        """Test disabling and enabling notes for a record through the UI. """
        person, note = self.setup_person_and_note()
        p123_id = 'haiti.personfinder.google.org/person.123'
        # View the record and click the button to disable comments.
        doc = self.go('/haiti/view?' + 'id=' + p123_id)
        button = doc.firsttag('input',
                              value='Disable notes on this record')
        doc = self.s.follow_button(button)
        assert 'disable notes on ' \
               '"_test_given_name _test_family_name"' in doc.text
        button = doc.firsttag(
            'input',
            value='Yes, ask the record author to disable notes')
        doc = self.s.submit(button)

        # Check to make sure that the user was redirected to the same page due
        # to an invalid captcha.
        assert 'disable notes on ' \
               '"_test_given_name _test_family_name"' in doc.text, \
               'missing expected status from %s' % doc.text
        assert 'incorrect-captcha-sol' in doc.content

        # Continue with a valid captcha (faked, for purpose of test). Check
        # that a proper message has been sent to the record author.
        doc = self.go(
            '/haiti/disable_notes',
            data='id=haiti.personfinder.google.org/person.123&test_mode=yes')
        self.verify_email_sent(1)
        messages = sorted(self.mail_server.messages, key=lambda m: m['to'][0])
        assert messages[0]['to'] == ['test@example.com']
        words = ' '.join(messages[0]['data'].split())
        assert ('[Person Finder] Disable notes on '
                '"_test_given_name _test_family_name"?' in words), words
        assert 'the author of this record' in words
        assert 'follow this link within 3 days' in words
        confirm_disable_notes_url = re.search(
            '(/haiti/confirm_disable_notes.*)', messages[0]['data']).group(1)
        assert confirm_disable_notes_url
        # The author confirm disabling comments using the URL in the e-mail.
        # Clicking the link should take you to the confirm_disable_commments
        # page (no CAPTCHA) where you can click the button to confirm.
        doc = self.go(confirm_disable_notes_url)
        assert 'reason_for_disabling_notes' in doc.content, doc.content
        assert 'The record will still be visible on this site' in doc.text, \
            utils.encode(doc.text)
        button = doc.firsttag(
            'input',
            value='Yes, disable notes on this record.')
        doc = self.s.submit(button,
                            reason_for_disabling_notes='spam_received')

        # The Person record should now be marked as notes_disabled.
        person = Person.get('haiti', person.record_id)
        assert person.notes_disabled

        # Check the notification messages sent to related e-mail accounts.
        self.verify_email_sent(3)
        messages = sorted(self.mail_server.messages[1:], key=lambda m: m['to'][0])

        # After sorting by recipient, the second message should be to the
        # person author, test@example.com (sorts after test2@example.com).
        assert messages[1]['to'] == ['test@example.com']
        words = ' '.join(messages[1]['data'].split())
        assert ('[Person Finder] Notes are now disabled for '
                '"_test_given_name _test_family_name"' in words), words

        # The first message should be to the note author, test2@example.com.
        assert messages[0]['to'] == ['test2@example.com']
        words = ' '.join(messages[0]['data'].split())
        assert ('[Person Finder] Notes are now disabled for '
                '"_test_given_name _test_family_name"' in words), words

        # Make sure that a UserActionLog row was created.
        verify_user_action_log('disable_notes', 'Person', repo='haiti',
            entity_key_name='haiti:haiti.personfinder.google.org/person.123',
            detail='spam_received')

        # Redirect to view page, now we should not show the add_note panel,
        # instead, we show message and a button to enable comments.
        assert not 'Tell us the status of this person' in doc.content
        assert not 'add_note' in doc.content
        assert 'The author has disabled notes on ' \
               'this record.' in doc.content

        # Click the enable_notes button should lead to enable_notes
        # page with a CAPTCHA.
        button = doc.firsttag('input',
                              value='Enable notes on this record')
        doc = self.s.follow_button(button)
        assert 'enable notes on ' \
               '"_test_given_name _test_family_name"' in doc.text
        button = doc.firsttag(
            'input',
            value='Yes, ask the record author to enable notes')
        doc = self.s.submit(button)

        # Check to make sure that the user was redirected to the same page due
        # to an invalid captcha.
        assert 'enable notes on ' \
               '"_test_given_name _test_family_name"' in doc.text
        assert 'incorrect-captcha-sol' in doc.content

        # Continue with a valid captcha. Check that a proper message
        # has been sent to the record author.
        doc = self.go(
            '/haiti/enable_notes',
            data='id=haiti.personfinder.google.org/person.123&test_mode=yes')
        assert 'confirm that you want to enable notes on this record.' \
            in doc.text, utils.encode(doc.text)
        # Check that a request email has been sent to the author.
        self.verify_email_sent(4)
        messages = sorted(self.mail_server.messages[3:],
                          key=lambda m: m['to'][0])
        assert messages[0]['to'] == ['test@example.com']
        words = ' '.join(messages[0]['data'].split())
        assert ('[Person Finder] Enable notes on '
                '"_test_given_name _test_family_name"?' in words), words
        assert 'the author of this record' in words, words
        assert 'follow this link within 3 days' in words, words
        confirm_enable_notes_url = re.search(
            '(/haiti/confirm_enable_notes.*)', messages[0]['data']).group(1)
        assert confirm_enable_notes_url
        # The author confirm enabling comments using the URL in the e-mail.
        # Clicking the link should take you to the confirm_enable_commments
        # page which verifies the token and immediately redirect to view page.
        doc = self.go(confirm_enable_notes_url)

        # The Person record should now have notes_disabled = False.
        person = Person.get('haiti', person.record_id)
        assert not person.notes_disabled

        # Check the notification messages sent to related e-mail accounts.
        self.verify_email_sent(6)
        messages = sorted(self.mail_server.messages[4:],
                          key=lambda m: m['to'][0])
        assert messages[1]['to'] == ['test@example.com']
        words = ' '.join(messages[1]['data'].split())
        assert ('[Person Finder] Notes are now enabled on ' +
                '"_test_given_name _test_family_name"' in words), words
        assert messages[0]['to'] == ['test2@example.com']
        words = ' '.join(messages[0]['data'].split())
        assert ('[Person Finder] Notes are now enabled on ' +
                '"_test_given_name _test_family_name"' in words), words

        # Make sure that a UserActionLog row was created.
        verify_user_action_log('enable_notes', 'Person', repo='haiti',
            entity_key_name='haiti:haiti.personfinder.google.org/person.123')

        # In the view page, now we should see add_note panel,
        # also, we show the button to disable comments.
        assert 'Tell us the status of this person' in doc.content
        assert 'add_note' in doc.content
        assert 'Save this record' in doc.content
        assert 'Disable notes on this record' in doc.content

    def test_detect_note_with_bad_words(self):
        """Checks that we can config the subdomain by adding a list of
        bad words. And notes that contain these bad words will be asked
        for email confirmation before posted."""
        # Config subdomain with list of bad words.
        config.set_for_repo('haiti', bad_words='bad, words')

        # Set utcnow to match source date
        self.set_utcnow_for_test(datetime.datetime(2001, 1, 1, 0, 0, 0))
        test_source_date = utils.get_utcnow().strftime('%Y-%m-%d')

        # Create a new person record with bad words in the note.
        doc = self.go('/haiti/create?given_name=_test_given_name&'
                      'family_name=_test_family_name&role=provide')

        create_form = doc.first('form')
        # Submit the create form with complete information.
        # Note contains bad words
        self.s.submit(create_form,
                      author_name='_test_author_name',
                      author_email='test1@example.com',
                      author_phone='_test_author_phone',
                      clone='no',
                      source_name='_test_source_name',
                      source_date=test_source_date,
                      source_url='_test_source_url',
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      expiry_option='20',
                      description='_test_description',
                      add_note='yes',
                      author_made_contact='yes',
                      status='believed_dead',
                      text='_test A note with bad words.')

        # Ask for author's email address.
        assert 'enter your e-mail address below' in self.s.doc.text
        assert 'author_email' in self.s.doc.content
        author_email = self.s.doc.firsttag('input', id='author_email')
        button = self.s.doc.firsttag('input', value='Send email')
        doc = self.s.submit(button,
                            author_email='test1@example.com')
        assert 'Your request has been processed successfully' in doc.text

        # Verify that the note is not shown, but the person record
        # is created, and the note_with_bad_word is created.
        person = Person.all().get()
        view_url = '/haiti/view?id=' + person.record_id
        doc = self.go(view_url)
        assert 'No notes have been posted' in doc.text

        note_with_bad_words = NoteWithBadWords.all().get()
        assert note_with_bad_words
        assert not note_with_bad_words.confirmed
        assert note_with_bad_words.person_record_id == person.record_id
        assert note_with_bad_words.author_email == 'test1@example.com'

        note = Note.all().get()
        assert not note

        # Check that a UserActionLog row was created for 'add' action.
        verify_user_action_log('add', 'NoteWithBadWords', repo='haiti')

        # Verify that an email is sent to note author
        self.verify_email_sent(1)
        messages = sorted(self.mail_server.messages, key=lambda m: m['to'][0])
        assert messages[0]['to'] == ['test1@example.com']
        words = ' '.join(messages[0]['data'].split())
        assert ('[Person Finder] Confirm your note on '
                '"_test_given_name _test_family_name"' in words)
        assert 'follow this link within 3 days' in words
        confirm_post_flagged_note_url = re.search(
            'http:.*', messages[0]['data']).group()

        # Note author confirms the post.
        doc = self.s.go(confirm_post_flagged_note_url)
        # Check that the note with bad words is shown now.
        assert '_test A note with bad words' in doc.text

        # Check a note is created in datastore
        note = Note.all().get()
        assert note
        assert note.status == 'believed_dead'

        # Check that NoteWithBadWords is linked to the newly created copy
        note_with_bad_words = NoteWithBadWords.all().get()
        assert note_with_bad_words.confirmed
        assert note_with_bad_words.confirmed_copy_id == note.get_record_id()

        note.delete()
        note_with_bad_words.delete()

        # Check that person record is updated
        person = Person.all().get()
        assert person.latest_status == 'believed_dead'

        # Check that a UserActionLog row was created for 'mark_dead' action.
        keyname = 'haiti:%s' % note.get_record_id()
        verify_user_action_log('mark_dead', 'Note', repo='haiti',
                               entity_key_name=keyname)

        # Add a note with bad words to the existing person record.
        doc = self.s.go(view_url)
        button = doc.firsttag('input', value='Save this record')
        note_form = doc.first('form')

        self.s.submit(note_form,
                      author_name='_test_author2',
                      text='_test add note with bad words.',
                      status='believed_alive')

        # Ask for author's email address.
        assert 'enter your e-mail address below' in self.s.doc.text
        assert 'author_email' in self.s.doc.content
        author_email = self.s.doc.firsttag('input', id='author_email')
        button = self.s.doc.firsttag('input', value='Send email')
        doc = self.s.submit(button,
                            author_email='test2@example.com')
        assert 'request has been processed successfully' in self.s.doc.text

        # Verify that new note is not shown.
        doc = self.s.go(view_url)
        assert 'No notes have been posted' in doc.text

        # Verify that person record and note record are not updated
        person = Person.all().get()
        assert person.latest_status == 'believed_dead'

        note = Note.all().get()
        assert not note

        note_with_bad_words = NoteWithBadWords.all().get()
        assert note_with_bad_words.status == 'believed_alive'
        assert not note_with_bad_words.confirmed
        assert note_with_bad_words.person_record_id == person.record_id
        assert note_with_bad_words.author_email == 'test2@example.com'

        # Check that a UserActionLog row was created for 'add' action.
        verify_user_action_log('add', 'NoteWithBadWords', repo='haiti')

        # Verify that an email is sent to note author
        self.verify_email_sent(2)
        messages = sorted(self.mail_server.messages, key=lambda m: m['to'][0])
        assert messages[1]['to'] == ['test2@example.com']
        words = ' '.join(messages[1]['data'].split())
        assert ('[Person Finder] Confirm your note on '
                '"_test_given_name _test_family_name"' in words)
        assert 'follow this link within 3 days' in words
        confirm_post_flagged_note_url = re.search(
            'http:.*', messages[1]['data']).group()

        # Note author confirms the post.
        doc = self.s.go(confirm_post_flagged_note_url)
        # Check that the note with bad words is shown now.
        assert '_test add note with bad words' in doc.text

        # Check a note is created in datastore
        note = Note.all().get()
        assert note.status == 'believed_alive'
        assert note.author_email == 'test2@example.com'

        # Check that NoteWithBadWords is linked to the newly created copy
        note_with_bad_words = NoteWithBadWords.all().get()
        assert note_with_bad_words.confirmed
        assert note_with_bad_words.confirmed_copy_id == note.get_record_id()

        # Check that person record is updated
        person = Person.all().get()
        assert person.latest_status == 'believed_alive'

        # Check that a UserActionLog row was created for 'mark_alive' action.
        keyname = "haiti:%s" % note.get_record_id()
        verify_user_action_log('mark_alive', 'Note', repo='haiti',
                               entity_key_name=keyname)


    def test_delete_and_restore(self):
        """Checks that deleting a record through the UI, then undeleting
        it using the link in the deletion notification, causes the record to
        disappear and reappear correctly, produces e-mail notifications,
        and has the correct effect on the outgoing API and feeds."""
        person, note = self.setup_person_and_note()
        photo = self.setup_photo(person)
        note_photo = self.setup_photo(note)

        # Advance time by one day.
        now = self.advance_utcnow(days=1)

        p123_id = 'haiti.personfinder.google.org/person.123'
        # Visit the page and click the button to delete a record.
        doc = self.go('/haiti/view?' + 'id=' + p123_id)
        button = doc.firsttag('input', value='Delete this record')
        doc = self.s.follow_button(button)
        assert 'delete the record for "_test_given_name ' + \
               '_test_family_name"' in doc.text, utils.encode(doc.text)
        button = doc.firsttag('input', value='Yes, delete the record')
        doc = self.s.submit(button)

        # Check to make sure that the user was redirected to the same page due
        # to an invalid captcha.
        assert 'delete the record for "_test_given_name ' + \
               '_test_family_name"' in doc.text
        assert 'The record has been deleted' not in doc.text
        assert 'incorrect-captcha-sol' in doc.content

        # Continue with a valid captcha (faked, for purpose of test). Check the
        # sent messages for proper notification of related e-mail accounts.
        doc = self.go(
            '/haiti/delete',
            data='id=haiti.personfinder.google.org/person.123&' +
                 'reason_for_deletion=spam_received&test_mode=yes')
        assert 'The record has been deleted' in doc.text

        # Should send 2 messages: one to person author, one to note author.
        self.verify_email_sent(2)
        messages = sorted(self.mail_server.messages, key=lambda m: m['to'][0])

        # After sorting by recipient, the second message should be to the
        # person author, test@example.com (sorts after test2@example.com).
        assert messages[1]['to'] == ['test@example.com']
        words = ' '.join(messages[1]['data'].split())
        assert ('Subject: [Person Finder] Deletion notice for ' +
                '"_test_given_name _test_family_name"' in words)
        assert 'the author of this record' in words
        assert 'restore it by following this link' in words
        restore_url = re.search('/haiti/restore.*', messages[1]['data']).group()

        # The first message should be to the note author, test2@example.com.
        assert messages[0]['to'] == ['test2@example.com']
        words = ' '.join(messages[0]['data'].split())
        assert ('Subject: [Person Finder] Deletion notice for ' +
                '"_test_given_name _test_family_name"' in words)
        assert 'the author of a note on this record' in words
        assert 'restore it by following this link' not in words

        # The Person and Note records should now be marked expired.
        person = db.get(person.key())
        assert person.is_expired
        assert person.source_date == now
        assert person.entry_date == now
        assert person.expiry_date == now
        note = db.get(note.key())
        assert note.is_expired

        # The Person and Note records should be inaccessible.
        assert not Person.get('haiti', person.record_id)
        assert not Note.get('haiti', note.record_id)

        # Make sure that a UserActionLog row was created.
        verify_user_action_log('delete', 'Person', repo='haiti',
            entity_key_name='haiti:haiti.personfinder.google.org/person.123',
            detail='spam_received')

        assert db.get(photo.key())
        assert db.get(note_photo.key())

        # Search for the record. Make sure it does not show up.
        doc = self.go('/haiti/results?role=seek&' +
                      'query=_test_given_name+_test_family_name')
        assert 'No results found' in doc.text

        # The read API should expose an expired record.
        doc = self.go('/haiti/api/read?'
                      'id=haiti.personfinder.google.org/person.123')  # PFIF 1.4
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.4">
  <pfif:person>
    <pfif:person_record_id>haiti.personfinder.google.org/person.123</pfif:person_record_id>
    <pfif:entry_date>2010-01-02T00:00:00Z</pfif:entry_date>
    <pfif:expiry_date>2010-01-02T00:00:00Z</pfif:expiry_date>
    <pfif:source_date>2010-01-02T00:00:00Z</pfif:source_date>
    <pfif:full_name></pfif:full_name>
  </pfif:person>
</pfif:pfif>
'''
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # The outgoing person feed should contain an expired record.
        doc = self.go('/haiti/feeds/person')  # PFIF 1.4
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.4">
  <id>http://%s/personfinder/haiti/feeds/person</id>
  <title>%s</title>
  <subtitle>PFIF Person Feed generated by Person Finder at %s</subtitle>
  <updated>2010-01-02T00:00:00Z</updated>
  <link rel="self">http://%s/personfinder/haiti/feeds/person</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>haiti.personfinder.google.org/person.123</pfif:person_record_id>
      <pfif:entry_date>2010-01-02T00:00:00Z</pfif:entry_date>
      <pfif:expiry_date>2010-01-02T00:00:00Z</pfif:expiry_date>
      <pfif:source_date>2010-01-02T00:00:00Z</pfif:source_date>
      <pfif:full_name></pfif:full_name>
    </pfif:person>
    <id>pfif:haiti.personfinder.google.org/person.123</id>
    <author>
    </author>
    <updated>2010-01-02T00:00:00Z</updated>
    <source>
      <title>%s</title>
    </source>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport,
       self.hostport)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        doc = self.go('/haiti/feeds/person?version=1.3')  # PFIF 1.3
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.3">
  <id>http://%s/personfinder/haiti/feeds/person?version=1.3</id>
  <title>%s</title>
  <subtitle>PFIF Person Feed generated by Person Finder at %s</subtitle>
  <updated>2010-01-02T00:00:00Z</updated>
  <link rel="self">http://%s/personfinder/haiti/feeds/person?version=1.3</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>haiti.personfinder.google.org/person.123</pfif:person_record_id>
      <pfif:entry_date>2010-01-02T00:00:00Z</pfif:entry_date>
      <pfif:expiry_date>2010-01-02T00:00:00Z</pfif:expiry_date>
      <pfif:source_date>2010-01-02T00:00:00Z</pfif:source_date>
      <pfif:full_name></pfif:full_name>
    </pfif:person>
    <id>pfif:haiti.personfinder.google.org/person.123</id>
    <author>
    </author>
    <updated>2010-01-02T00:00:00Z</updated>
    <source>
      <title>%s</title>
    </source>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport,
       self.hostport)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        doc = self.go('/haiti/feeds/person?version=1.2')  # PFIF 1.2
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.2">
  <id>http://%s/personfinder/haiti/feeds/person?version=1.2</id>
  <title>%s</title>
  <subtitle>PFIF Person Feed generated by Person Finder at %s</subtitle>
  <updated>2010-01-02T00:00:00Z</updated>
  <link rel="self">http://%s/personfinder/haiti/feeds/person?version=1.2</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>haiti.personfinder.google.org/person.123</pfif:person_record_id>
      <pfif:entry_date>2010-01-02T00:00:00Z</pfif:entry_date>
      <pfif:source_date>2010-01-02T00:00:00Z</pfif:source_date>
      <pfif:first_name></pfif:first_name>
      <pfif:last_name></pfif:last_name>
    </pfif:person>
    <id>pfif:haiti.personfinder.google.org/person.123</id>
    <author>
    </author>
    <updated>2010-01-02T00:00:00Z</updated>
    <source>
      <title>%s</title>
    </source>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport,
       self.hostport)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # Advance time by one day.
        now = self.advance_utcnow(days=1)

        # Restore the record using the URL in the e-mail.  Clicking the link
        # should take you to a CAPTCHA page to confirm.
        doc = self.go(restore_url)
        assert 'captcha' in doc.content

        # Fake a valid captcha and actually reverse the deletion
        form = doc.first('form', action=re.compile('.*/restore'))
        doc = self.s.submit(form, test_mode='yes')
        assert 'Identifying information' in doc.text
        assert '_test_given_name _test_family_name' in doc.text

        assert Person.get('haiti', 'haiti.personfinder.google.org/person.123')
        note = Note.get('haiti', 'haiti.personfinder.google.org/note.456')
        assert note
        self.assertEquals([note.record_id],
                          [n.record_id for n in person.get_notes()])
        assert 'Testing' in doc.text, \
            'Testing not in: %s' % str(doc.text.encode('ascii', 'ignore'))

        new_id = self.s.url[self.s.url.find('id=')+3:]
        new_id = new_id.replace('%2F', '/')

        # Make sure that Person/Note records are now visible, with all
        # of their original attributes from prior to deletion.
        person = Person.get_by_key_name('haiti:' + new_id)
        notes = Note.get_by_person_record_id('haiti', person.record_id)
        assert person
        assert len(notes) == 1

        assert person.author_name == '_test_author_name'
        assert person.author_email == 'test@example.com'
        assert person.full_name == '_test_given_name _test_family_name'
        assert person.given_name == '_test_given_name'
        assert person.family_name == '_test_family_name'
        assert person.photo_url == '_test_photo_url'
        assert person.repo == 'haiti'
        assert person.source_date == now
        assert person.entry_date == now
        assert person.expiry_date == now + datetime.timedelta(days=60)
        assert not person.is_expired

        assert notes[0].author_email == 'test2@example.com'
        assert notes[0].text == 'Testing'
        assert notes[0].person_record_id == new_id
        assert not notes[0].is_expired

        # Search for the record. Make sure it shows up.
        doc = self.go('/haiti/results?role=seek&' +
                      'query=_test_given_name+_test_family_name')
        assert 'No results found' not in doc.text

        # The read API should show a record with all the fields present,
        # as if the record was just written with new field values.
        doc = self.go('/haiti/api/read?'
                      'id=haiti.personfinder.google.org/person.123')  # PFIF 1.4
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.4">
  <pfif:person_record_id>haiti.personfinder.google.org/person.123</pfif:person_record_id>
  <pfif:entry_date>2010-01-03T00:00:00Z</pfif:entry_date>
  <pfif:expiry_date>2010-03-03T00:00:00Z</pfif:expiry_date>
  <pfif:author_name>_test_author_name</pfif:author_name>
  <pfif:source_date>2010-01-02T00:00:00Z</pfif:source_date>
  <pfif:full_name>_test_given_name _test_family_name</pfif:full_name>
  <pfif:given_name>_test_given_name</pfif:given_name>
  <pfif:family_name>_test_family_name</pfif:family_name>
  <pfif:photo_url>_test_photo_url</pfif:photo_url>
  <pfif:note>
    <pfif:note_record_id>haiti.personfinder.google.org/note.456</pfif:note_record_id>
    <pfif:person_record_id>haiti.personfinder.google.org/person.123</pfif:person_record_id>
    <pfif:entry_date>2010-01-01T00:00:00Z</pfif:entry_date>
    <pfif:author_name></pfif:author_name>
    <pfif:source_date>2010-01-01T00:00:00Z</pfif:source_date>
    <pfif:text>Testing</pfif:text>
  </pfif:note>
</pfif:pfif>
'''

        # The outgoing feed should contain a complete record also.
        doc = self.go('/haiti/feeds/person')  # PFIF 1.4
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.4">
  <id>http://%s/personfinder/haiti/feeds/person</id>
  <title>%s</title>
  <subtitle>PFIF Person Feed generated by Person Finder at %s</subtitle>
  <updated>2010-01-03T00:00:00Z</updated>
  <link rel="self">http://%s/personfinder/haiti/feeds/person</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>haiti.personfinder.google.org/person.123</pfif:person_record_id>
      <pfif:entry_date>2010-01-03T00:00:00Z</pfif:entry_date>
      <pfif:expiry_date>2010-03-04T00:00:00Z</pfif:expiry_date>
      <pfif:author_name>_test_author_name</pfif:author_name>
      <pfif:source_date>2010-01-03T00:00:00Z</pfif:source_date>
      <pfif:full_name>_test_given_name _test_family_name</pfif:full_name>
      <pfif:given_name>_test_given_name</pfif:given_name>
      <pfif:family_name>_test_family_name</pfif:family_name>
      <pfif:photo_url>_test_photo_url</pfif:photo_url>
      <pfif:note>
        <pfif:note_record_id>haiti.personfinder.google.org/note.456</pfif:note_record_id>
        <pfif:person_record_id>haiti.personfinder.google.org/person.123</pfif:person_record_id>
        <pfif:entry_date>2010-01-01T00:00:00Z</pfif:entry_date>
        <pfif:author_name></pfif:author_name>
        <pfif:source_date>2010-01-01T00:00:00Z</pfif:source_date>
        <pfif:text>Testing</pfif:text>
        <pfif:photo_url>_test_photo_url_for_note</pfif:photo_url>
      </pfif:note>
    </pfif:person>
    <id>pfif:haiti.personfinder.google.org/person.123</id>
    <title>_test_given_name _test_family_name</title>
    <author>
      <name>_test_author_name</name>
    </author>
    <updated>2010-01-03T00:00:00Z</updated>
    <source>
      <title>%s</title>
    </source>
    <content>_test_given_name _test_family_name</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport,
       self.hostport)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # Confirm that restoration notifications were sent.
        assert len(self.mail_server.messages) == 4
        messages = sorted(self.mail_server.messages[2:], key=lambda m: m['to'][0])

        # After sorting by recipient, the second message should be to the
        # person author, test@example.com (sorts after test2@example.com).
        assert messages[1]['to'] == ['test@example.com']
        words = ' '.join(messages[1]['data'].split())
        assert ('Subject: [Person Finder] Record restoration notice for ' +
                '"_test_given_name _test_family_name"' in words)

        # The first message should be to the note author, test2@example.com.
        assert messages[0]['to'] == ['test2@example.com']
        words = ' '.join(messages[0]['data'].split())
        assert ('Subject: [Person Finder] Record restoration notice for ' +
                '"_test_given_name _test_family_name"' in words)

    def test_delete_and_wipe(self):
        """Checks that deleting a record through the UI, then waiting until
        after the expiration grace period ends, causes the record to
        disappear and be deleted permanently from the datastore, leaving
        behind the appropriate placeholder in the outgoing API and feeds."""
        person, note = self.setup_person_and_note()
        photo = self.setup_photo(person)
        note_photo = self.setup_photo(note)

        now = self.advance_utcnow(days=1)

        # Simulate a deletion request with a valid Turing test response.
        # (test_delete_and_restore already tests this flow in more detail.)
        doc = self.go('/haiti/delete',
                      data='id=haiti.personfinder.google.org/person.123&' +
                           'reason_for_deletion=spam_received&test_mode=yes')

        # Run the DeleteExpired task.
        doc = self.go('/haiti/tasks/delete_expired')

        # The Person and Note records should be marked expired but retain data.
        person = db.get(person.key())
        assert person.is_expired
        assert person.full_name == '_test_given_name _test_family_name'
        assert person.source_date == now
        assert person.entry_date == now
        assert person.expiry_date == now
        note = db.get(note.key())
        assert note.is_expired
        assert note.text == 'Testing'

        # The Photos should still be there.
        assert db.get(photo.key())
        assert db.get(note_photo.key())

        # The Person and Note records should be inaccessible.
        assert not Person.get('haiti', person.record_id)
        assert not Note.get('haiti', note.record_id)

        # Search for the record. Make sure it does not show up.
        doc = self.go('/haiti/results?role=seek&' +
                      'query=_test_given_name+_test_family_name')
        assert 'No results found' in doc.text

        # The read API should expose an expired record.
        doc = self.go('/haiti/api/read'
                      '?id=haiti.personfinder.google.org/person.123')
        expected_content = '''<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.4">
  <pfif:person>
    <pfif:person_record_id>haiti.personfinder.google.org/person.123</pfif:person_record_id>
    <pfif:entry_date>2010-01-02T00:00:00Z</pfif:entry_date>
    <pfif:expiry_date>2010-01-02T00:00:00Z</pfif:expiry_date>
    <pfif:source_date>2010-01-02T00:00:00Z</pfif:source_date>
    <pfif:full_name></pfif:full_name>
  </pfif:person>
</pfif:pfif>
'''
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        self.verify_email_sent(2) # notification for delete.
        self.mail_server.messages = []

        # Advance time past the end of the 3-day expiration grace period.
        now = self.advance_utcnow(days=4)

        # Run the DeleteExpired task.
        doc = self.go('/haiti/tasks/delete_expired')

        # The Person record should still exist but now be empty.
        # The timestamps should be unchanged.

        self.verify_email_sent(0) # no notification for wipe.
        person = db.get(person.key())
        assert person.is_expired
        assert person.full_name == None, \
            'found full_name: %s' % person.full_name
        assert person.source_date == datetime.datetime(2010, 1, 2, 0, 0, 0)
        assert person.entry_date == datetime.datetime(2010, 1, 2, 0, 0, 0)
        assert person.expiry_date == datetime.datetime(2010, 1, 2, 0, 0, 0)

        # The Note and Photos should be gone.
        assert not db.get(note.key())
        assert not db.get(photo.key())
        assert not db.get(note_photo.key())

        # The placeholder exposed by the read API should be unchanged.
        doc = self.go('/haiti/api/read'
                      '?id=haiti.personfinder.google.org/person.123')
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # The Person and Note records should be inaccessible.
        assert not Person.get('haiti', person.record_id)
        assert not Note.get('haiti', note.record_id)

        # Search for the record. Make sure it does not show up.
        doc = self.go('/haiti/results?role=seek&' +
                      'query=_test_given_name+_test_family_name')
        assert 'No results found' in doc.text

    def test_incoming_expired_record(self):
        """Tests that an incoming expired record can cause an existing record
        to expire and be deleted."""
        person, note = self.setup_person_and_note('test.google.com')
        assert person.given_name == '_test_given_name'

        now = self.advance_utcnow(days=1)

        # Simulate the arrival of an update that expires this record.
        data = '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.4">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>2010-01-02T00:00:00Z</pfif:entry_date>
    <pfif:expiry_date>2010-01-02T00:00:00Z</pfif:expiry_date>
    <pfif:source_date>2001-01-02T00:00:00Z</pfif:source_date>
    <pfif:full_name></pfif:full_name>
  </pfif:person>
</pfif:pfif>
'''
        self.go('/haiti/api/write?key=test_key',
                data=data, type='application/xml')

        now = self.advance_utcnow(days=1)

        # Run the DeleteExpired task.
        self.go('/haiti/tasks/delete_expired').content

        # The Person record should be hidden but not yet gone.
        # The timestamps should reflect the time that the record was hidden.
        assert not Person.get('haiti', person.record_id)
        assert not db.get(person.key())
        # The Note record should be gone.
        assert not db.get(note.key())

        # The read API should show the same expired record as before.
        doc = self.go(
            '/haiti/api/read?id=test.google.com/person.123')  # PFIF 1.4
        expected_content = 'No person record with ID test.google.com/person.123'
        assert expected_content in doc.content

    def test_mark_notes_as_spam(self):
        person = Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name',
            entry_date=datetime.datetime.now()
        )
        person.update_index(['new', 'old'])
        note = Note(
            key_name='haiti:test.google.com/note.456',
            repo='haiti',
            author_email='test2@example.com',
            person_record_id='test.google.com/person.123',
            entry_date=TEST_DATETIME,
            text='TestingSpam'
        )
        db.put([person, note])
        person = Person.get('haiti', 'test.google.com/person.123')
        assert len(person.get_notes()) == 1

        assert Note.get('haiti', 'test.google.com/note.456')

        # Visit the page and click the button to mark a note as spam.
        # Bring up confirmation page.
        doc = self.go('/haiti/view?id=test.google.com/person.123')
        doc = self.s.follow('Report spam')
        assert 'Are you sure' in doc.text
        assert 'TestingSpam' in doc.text
        assert 'captcha' not in doc.content

        button = doc.firsttag('input', value='Yes, update the note')
        doc = self.s.submit(button)
        assert 'Notes for this person' in doc.text
        assert 'This note has been marked as spam.' in doc.text
        assert 'Not spam' in doc.text
        assert 'Reveal note' in doc.text

        # When a note is flagged, these new links appear.
        assert doc.first('a', id='reveal-note')
        assert doc.first('a', id='hide-note')
        # When a note is flagged, the contents of the note are hidden.
        assert doc.first('div', class_='contents')['style'] == 'display: none;'

        # Make sure that a UserActionLog entry was created.
        assert len(UserActionLog.all().fetch(10)) == 1

        # The flagged note's content should be empty in all APIs and feeds.
        doc = self.go('/haiti/api/read?id=test.google.com/person.123')
        assert 'TestingSpam' not in doc.content
        doc = self.go('/haiti/api/search?q=_test_full_name')
        assert 'TestingSpam' not in doc.content
        doc = self.go('/haiti/feeds/note')
        assert 'TestingSpam' not in doc.content
        doc = self.go('/haiti/feeds/person')
        assert 'TestingSpam' not in doc.content
        doc_feed_note = self.go( \
            '/haiti/feeds/note?person_record_id=test.google.com/person.123')
        assert doc_feed_note.first('pfif:text').text == ''
        doc_feed_person = self.go( \
            '/haiti/feeds/person?person_record_id=test.google.com/person.123')
        assert doc_feed_person.first('pfif:note').first('pfif:text').text == ''

        # Unmark the note as spam.
        doc = self.go('/haiti/view?id=test.google.com/person.123')
        doc = self.s.follow('Not spam')
        assert 'Are you sure' in doc.text
        assert 'TestingSpam' in doc.text
        assert 'captcha' in doc.content

        # Make sure it redirects to the same page with error
        doc = self.s.submit(button)
        assert 'incorrect-captcha-sol' in doc.content
        assert 'Are you sure' in doc.text
        assert 'TestingSpam' in doc.text

        # Simulate successful completion of the Turing test.
        doc = self.s.submit(button, test_mode='yes')
        assert 'This note has been marked as spam.' not in doc.text
        assert 'Notes for this person' in doc.text, utils.encode(doc.text)
        assert 'Report spam' in doc.text

        # Make sure that a second UserActionLog entry was created
        assert len(UserActionLog.all().fetch(10)) == 2

        # Note should be visible in all APIs and feeds.
        doc = self.go('/haiti/api/read?id=test.google.com/person.123')
        assert 'TestingSpam' in doc.content
        doc = self.go('/haiti/api/search?q=_test_full_name')
        assert 'TestingSpam' in doc.content
        doc = self.go('/haiti/feeds/note')
        assert 'TestingSpam' in doc.content
        doc = self.go('/haiti/feeds/person')
        assert 'TestingSpam' in doc.content

    def test_subscriber_notifications(self):
        """Tests that notifications are sent when a record is updated."""
        SUBSCRIBER_1 = 'example1@example.com'
        SUBSCRIBER_2 = 'example2@example.com'

        db.put([Person(
            key_name='haiti:test.google.com/person.1',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name1',
            entry_date=datetime.datetime.utcnow(),
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6),
        ), Person(
            key_name='haiti:test.google.com/person.2',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name2',
            entry_date=datetime.datetime.utcnow(),
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6),
        ), Person(
            key_name='haiti:test.google.com/person.3',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name3',
            entry_date=datetime.datetime.utcnow(),
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6),
        ), Note(
            key_name='haiti:test.google.com/note.1',
            repo='haiti',
            person_record_id='test.google.com/person.1',
            text='Testing',
            entry_date=datetime.datetime.utcnow(),
        ), Note(
            key_name='haiti:test.google.com/note.2',
            repo='haiti',
            person_record_id='test.google.com/person.2',
            linked_person_record_id='test.google.com/person.3',
            text='Testing',
            entry_date=datetime.datetime.utcnow(),
        ), Note(
            key_name='haiti:test.google.com/note.3',
            repo='haiti',
            person_record_id='test.google.com/person.3',
            linked_person_record_id='test.google.com/person.2',
            text='Testing',
            entry_date=datetime.datetime.utcnow(),
        ), Subscription(
            key_name='haiti:test.google.com/person.1:example1@example.com',
            repo='haiti',
            person_record_id='test.google.com/person.1',
            email=SUBSCRIBER_1,
            language='fr',
        ), Subscription(
            key_name='haiti:test.google.com/person.2:example2@example.com',
            repo='haiti',
            person_record_id='test.google.com/person.2',
            email=SUBSCRIBER_2,
            language='fr',
        )])

        # Reset the MailThread queue _before_ making any requests
        # to the server, else risk errantly deleting messages
        self.mail_server.messages = []

        # Visit the details page and add a note, triggering notification
        # to the subscriber.
        doc = self.go('/haiti/view?id=test.google.com/person.1')
        self.verify_details_page(1)
        self.verify_note_form()
        self.verify_update_notes(False, '_test A note body',
                                 '_test A note author',
                                 status='information_sought')
        self.verify_details_page(2)
        self.verify_email_sent()

        # Verify email data
        message = self.mail_server.messages[0]
        assert message['to'] == [SUBSCRIBER_1]
        assert 'do-not-reply@' in message['from']
        assert '_test_full_name1' in message['data']
        # Subscription is French, email should be, too
        assert 'recherche des informations' in message['data']
        assert '_test A note body' in message['data']
        assert 'view?id=test.google.com%2Fperson.1' in message['data']

        # Reset the MailThread queue
        self.mail_server.messages = []

        # Visit the multiview page and link Persons 1 and 2
        doc = self.go('/haiti/multiview' +
                      '?id1=test.google.com/person.1' +
                      '&id2=test.google.com/person.2')
        button = doc.firsttag('input', value='Yes, these are the same person')
        doc = self.s.submit(button, text='duplicate test', author_name='foo')

        # Verify subscribers were notified
        self.verify_email_sent(2)

        # Verify email details
        message_1 = self.mail_server.messages[0]
        assert message_1['to'] == [SUBSCRIBER_1]
        assert 'do-not-reply@' in message_1['from']
        assert '_test_full_name1' in message_1['data']
        message_2 = self.mail_server.messages[1]
        assert message_2['to'] == [SUBSCRIBER_2]
        assert 'do-not-reply@' in message_2['from']
        assert '_test_full_name2' in message_2['data']

        # Reset the MailThread queue
        self.mail_server.messages = []

        # Post a note on the person.3 details page and verify that
        # subscribers to Persons 1 and 2 are each notified once.
        doc = self.go('/haiti/view?id=test.google.com/person.3')
        self.verify_note_form()
        self.verify_update_notes(False, '_test A note body',
                                 '_test A note author',
                                 status='information_sought')
        self.verify_details_page(1)
        self.verify_email_sent(2)
        message_1 = self.mail_server.messages[0]
        assert message_1['to'] == [SUBSCRIBER_1]
        message_2 = self.mail_server.messages[1]
        assert message_2['to'] == [SUBSCRIBER_2]

    def test_subscriber_notifications_from_api_note(self):
        "Tests that a notification is sent when a note is added through API"
        SUBSCRIBER = 'example1@example.com'

        db.put([Person(
            key_name='haiti:test.google.com/person.21009',
            repo='haiti',
            record_id = u'test.google.com/person.21009',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name',
            entry_date=datetime.datetime(2000, 1, 6, 6),
        ), Subscription(
            key_name='haiti:test.google.com/person.21009:example1@example.com',
            repo='haiti',
            person_record_id='test.google.com/person.21009',
            email=SUBSCRIBER,
            language='fr'
        )])

        # Check there is no note in current db.
        person = Person.get('haiti', 'test.google.com/person.21009')
        assert person.full_name == u'_test_full_name'
        notes = person.get_notes()
        assert len(notes) == 0

        # Reset the MailThread queue _before_ making any requests
        # to the server, else risk errantly deleting messages
        self.mail_server.messages = []

        # Send a Note through Write API. It should send a notification.
        data = get_test_data('test.pfif-1.2-notification.xml')
        self.go('/haiti/api/write?key=test_key',
                data=data, type='application/xml')
        notes = person.get_notes()
        assert len(notes) == 1

        # Verify 1 email was sent.
        self.verify_email_sent()
        self.mail_server.messages = []

        # If we try to add it again, it should not send a notification.
        self.go('/haiti/api/write?key=test_key',
                data=data, type='application/xml')
        notes = person.get_notes()
        assert len(notes) == 1
        self.verify_email_sent(0)

    def test_subscribe_and_unsubscribe(self):
        """Tests subscribing to notifications on notes."""
        SUBSCRIBE_EMAIL = 'testsubscribe@example.com'

        db.put(Person(
            key_name='haiti:test.google.com/person.111',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name',
            entry_date=datetime.datetime.utcnow()
        ))
        person = Person.get('haiti', 'test.google.com/person.111')

        # Reset the MailThread queue _before_ making any requests
        # to the server, else risk errantly deleting messages
        self.mail_server.messages = []

        doc = self.go('/haiti/view?id=test.google.com/person.111')
        assert 'Subscribe to updates about this person' in doc.text
        button = doc.firsttag('input', id='subscribe_btn')
        doc = self.s.follow_button(button)

        # Empty email is an error.
        button = doc.firsttag('input', value='Subscribe')
        doc = self.s.submit(button)
        assert 'Invalid e-mail address. Please try again.' in doc.text
        assert len(person.get_subscriptions()) == 0

        # Invalid captcha response is an error
        self.s.back()
        button = doc.firsttag('input', value='Subscribe')
        doc = self.s.submit(button, subscribe_email=SUBSCRIBE_EMAIL)
        assert 'iframe' in doc.content
        assert 'recaptcha_response_field' in doc.content
        assert len(person.get_subscriptions()) == 0

        # Invalid email is an error (even with valid captcha)
        INVALID_EMAIL = 'test@example'
        doc = self.s.submit(
            button, subscribe_email=INVALID_EMAIL, test_mode='yes')
        assert 'Invalid e-mail address. Please try again.' in doc.text
        assert len(person.get_subscriptions()) == 0

        # Valid email and captcha is success
        self.s.back()
        doc = self.s.submit(
            button, subscribe_email=SUBSCRIBE_EMAIL, test_mode='yes')
        assert 'successfully subscribed. ' in doc.text
        assert '_test_full_name' in doc.text
        subscriptions = person.get_subscriptions()
        assert len(subscriptions) == 1
        assert subscriptions[0].email == SUBSCRIBE_EMAIL
        assert subscriptions[0].language == 'en'

        self.verify_email_sent()
        message = self.mail_server.messages[0]

        assert message['to'] == [SUBSCRIBE_EMAIL]
        assert 'do-not-reply@' in message['from']
        assert '_test_full_name' in message['data']
        assert 'view?id=test.google.com%2Fperson.111' in message['data']

        # Already subscribed person is shown info page
        self.s.back()
        doc = self.s.submit(
            button, subscribe_email=SUBSCRIBE_EMAIL, test_mode='yes')
        assert 'already subscribed. ' in doc.text
        assert 'for _test_full_name' in doc.text
        assert len(person.get_subscriptions()) == 1

        # Already subscribed person with new language is success
        self.s.back()
        doc = self.s.submit(
            button, subscribe_email=SUBSCRIBE_EMAIL, test_mode='yes', lang='fr')
        assert u'maintenant abonn\u00E9' in doc.text
        assert '_test_full_name' in doc.text
        subscriptions = person.get_subscriptions()
        assert len(subscriptions) == 1
        assert subscriptions[0].email == SUBSCRIBE_EMAIL
        assert subscriptions[0].language == 'fr'

        # Test the unsubscribe link in the email
        unsub_url = re.search('(/haiti/unsubscribe.*)', message['data']).group(1)
        doc = self.go(unsub_url)
        # "You have successfully unsubscribed." in French.
        assert u'Vous vous \u00eates bien d\u00e9sabonn\u00e9.' in doc.content
        assert len(person.get_subscriptions()) == 0

    def test_config_use_family_name(self):
        # use_family_name=True
        d = self.go('/haiti/create')
        assert d.first('label', for_='given_name').text.strip() == 'Given name:'
        assert d.first('label', for_='family_name').text.strip() == 'Family name:'
        assert d.firsttag('input', name='given_name')
        assert d.firsttag('input', name='family_name')
        assert d.first('label', for_='alternate_given_names').text.strip() == \
            'Alternate given names:'
        assert d.first('label', for_='alternate_family_names').text.strip() == \
            'Alternate family names:'
        assert d.firsttag('input', name='alternate_given_names')
        assert d.firsttag('input', name='alternate_family_names')

        self.s.submit(d.first('form'),
                      given_name='_test_given',
                      family_name='_test_family',
                      alternate_given_names='_test_alternate_given',
                      alternate_family_names='_test_alternate_family',
                      author_name='_test_author')
        person = Person.all().get()
        d = self.go('/haiti/view?id=%s' % person.record_id)
        f = d.first('div', class_='name section').all('div', class_='field')
        assert f[0].first('span', class_='label').text.strip() == 'Full name:'
        assert f[0].first('span', class_='value').text.strip() == \
            '_test_given _test_family'
        assert f[1].first('span', class_='label').text.strip() == \
            'Alternate names:'
        assert f[1].first('span', class_='value').text.strip() == \
            '_test_alternate_given _test_alternate_family'

        self.go('/haiti/results?query=_test_given+_test_family')
        self.verify_results_page(1, all_have=([
            '_test_given _test_family',
            '(_test_alternate_given _test_alternate_family)']))
        person.delete()

        # use_family_name=False
        d = self.go('/pakistan/create')
        assert d.first('label', for_='given_name').text.strip() == 'Name:'
        assert not d.all('label', for_='family_name')
        assert d.firsttag('input', name='given_name')
        assert not d.alltags('input', name='family_name')
        assert 'Given name' not in d.text
        assert 'Family name' not in d.text

        self.s.submit(d.first('form'),
                      given_name='_test_given',
                      family_name='_test_family',
                      author_name='_test_author')
        person = Person.all().get()
        d = self.go(
            '/pakistan/view?id=%s' % person.record_id)
        f = d.first('div', class_='name section').all('div', class_='field')
        assert f[0].first('span', class_='label').text.strip() == 'Full name:'
        assert f[0].first('span', class_='value').text.strip() == '_test_given'
        assert 'Given name' not in d.text
        assert 'Family name' not in d.text
        assert '_test_family' not in d.first('body').text

        self.go('/pakistan/results?query=_test_given+_test_family')
        self.verify_results_page(1)
        first_title = self.s.doc.first(class_='resultDataTitle').content
        assert '_test_given' in first_title
        assert '_test_family' not in first_title
        person.delete()


    def test_config_family_name_first(self):
        # family_name_first=True
        doc = self.go('/japan/create?lang=en')
        given_label = doc.first('label', for_='given_name')
        family_label = doc.first('label', for_='family_name')
        assert given_label.text.strip() == 'Given name:'
        assert family_label.text.strip() == 'Family name:'
        assert family_label.start < given_label.start

        given_input = doc.firsttag('input', name='given_name')
        family_input = doc.firsttag('input', name='family_name')
        assert family_input.start < given_input.start

        alternate_given_label = doc.first('label', for_='alternate_given_names')
        alternate_family_label = doc.first('label', for_='alternate_family_names')
        assert alternate_given_label.text.strip() == 'Alternate given names:'
        assert alternate_family_label.text.strip() == 'Alternate family names:'
        assert alternate_family_label.start < alternate_given_label.start

        alternate_given_input = doc.firsttag(
            'input', name='alternate_given_names')
        alternate_family_input = doc.firsttag(
            'input', name='alternate_family_names')
        assert alternate_family_input.start < alternate_given_input.start

        self.s.submit(doc.first('form'),
                      given_name='_test_given',
                      family_name='_test_family',
                      alternate_given_names='_test_alternate_given',
                      alternate_family_names='_test_alternate_family',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/japan/view?id=%s&lang=en' % person.record_id)
        f = doc.first('div', class_='name section').all('div', class_='field')
        assert f[0].first('span', class_='label').text.strip() == 'Full name:'
        assert f[0].first('span', class_='value').text.strip() == \
            '_test_family _test_given'
        assert f[1].first('span', class_='label').text.strip() == \
            'Alternate names:'
        assert f[1].first('span', class_='value').text.strip() == \
            '_test_alternate_family _test_alternate_given'

        self.go('/japan/results?query=_test_family+_test_given&lang=en')
        self.verify_results_page(1, all_have=([
            '_test_family _test_given',
            '(_test_alternate_family _test_alternate_given)']))
        person.delete()

        # family_name_first=False
        doc = self.go('/haiti/create')
        given_label = doc.first('label', for_='given_name')
        family_label = doc.first('label', for_='family_name')
        assert given_label.text.strip() == 'Given name:'
        assert family_label.text.strip() == 'Family name:'
        assert family_label.start > given_label.start

        given_input = doc.firsttag('input', name='given_name')
        family_input = doc.firsttag('input', name='family_name')
        assert family_input.start > given_input.start

        alternate_given_label = doc.first('label', for_='alternate_given_names')
        alternate_family_label = doc.first('label', for_='alternate_family_names')
        assert alternate_given_label.text.strip() == 'Alternate given names:'
        assert alternate_family_label.text.strip() == 'Alternate family names:'
        assert alternate_family_label.start > alternate_given_label.start

        alternate_given_input = doc.firsttag(
            'input', name='alternate_given_names')
        alternate_family_input = doc.firsttag(
            'input', name='alternate_family_names')
        assert alternate_family_input.start > alternate_given_input.start

        self.s.submit(doc.first('form'),
                      given_name='_test_given',
                      family_name='_test_family',
                      alternate_given_names='_test_alternate_given',
                      alternate_family_names='_test_alternate_family',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/haiti/view?id=%s' % person.record_id)
        f = doc.first('div', class_='name section').all('div', class_='field')
        assert f[0].first('span', class_='label').text.strip() == 'Full name:'
        assert f[0].first('span', class_='value').text.strip() == \
            '_test_given _test_family'
        assert f[1].first('span', class_='label').text.strip() == \
            'Alternate names:'
        assert f[1].first('span', class_='value').text.strip() == \
            '_test_alternate_given _test_alternate_family'

        self.go('/haiti/results?query=_test_given+_test_family')
        self.verify_results_page(1, all_have=([
            '_test_given _test_family',
            '(_test_alternate_given _test_alternate_family)']))
        person.delete()

    def test_config_use_alternate_names(self):
        # use_alternate_names=True
        config.set_for_repo('haiti', use_alternate_names=True)
        d = self.go('/haiti/create')
        assert d.first('label', for_='alternate_given_names').text.strip() == \
            'Alternate given names:'
        assert d.first('label', for_='alternate_family_names').text.strip() == \
            'Alternate family names:'
        assert d.firsttag('input', name='alternate_given_names')
        assert d.firsttag('input', name='alternate_family_names')

        self.s.submit(d.first('form'),
                      given_name='_test_given',
                      family_name='_test_family',
                      alternate_given_names='_test_alternate_given',
                      alternate_family_names='_test_alternate_family',
                      author_name='_test_author')
        person = Person.all().get()
        d = self.go('/haiti/view?id=%s' % person.record_id)
        f = d.first('div', class_='name section').all('div', class_='field')
        assert f[1].first('span', class_='label').text.strip() == \
            'Alternate names:'
        assert f[1].first('span', class_='value').text.strip() == \
            '_test_alternate_given _test_alternate_family'

        self.go('/haiti/results?query=_test_given+_test_family')
        self.verify_results_page(1, all_have=([
            '_test_given _test_family',
            '(_test_alternate_given _test_alternate_family)']))
        person.delete()

        # use_alternate_names=False
        config.set_for_repo('pakistan', use_alternate_names=False)
        d = self.go('/pakistan/create')
        assert not d.all('label', for_='alternate_given_names')
        assert not d.all('label', for_='alternate_family_names')
        assert not d.alltags('input', name='alternate_given_names')
        assert not d.alltags('input', name='alternate_family_names')
        assert 'Alternate given names' not in d.text
        assert 'Alternate family names' not in d.text

        self.s.submit(d.first('form'),
                      given_name='_test_given',
                      family_name='_test_family',
                      alternate_given_names='_test_alternate_given',
                      alternate_family_names='_test_alternate_family',
                      author_name='_test_author')
        person = Person.all().get()
        d = self.go(
            '/pakistan/view?id=%s' % person.record_id)
        assert 'Alternate names' not in d.text
        assert '_test_alternate_given' not in d.text
        assert '_test_alternate_family' not in d.text

        self.go('/pakistan/results?query=_test_given+_test_family')
        self.verify_results_page(1)
        first_title = self.s.doc.first(class_='resultDataTitle').content
        assert '_test_given' in first_title
        assert '_test_alternate_given' not in first_title
        assert '_test_alternate_family' not in first_title
        person.delete()


    def test_config_allow_believed_dead_via_ui(self):
        # allow_believed_dead_via_ui=True
        config.set_for_repo('haiti', allow_believed_dead_via_ui=True)
        doc = self.go('/haiti/create')
        self.s.submit(doc.first('form'),
                      given_name='_test_given',
                      family_name='_test_family',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/haiti/view?id=%s' % person.record_id)
        assert doc.all('option', value='believed_dead')

        # allow_believed_dead_via_ui=False
        config.set_for_repo('japan', allow_believed_dead_via_ui=False)
        doc = self.go('/japan/create')
        self.s.submit(doc.first('form'),
                      given_name='_test_given',
                      family_name='_test_family',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/japan/view?id=%s' % person.record_id)
        assert not doc.all('option', value='believed_dead')


    def test_config_use_postal_code(self):
        # use_postal_code=True
        doc = self.go('/haiti/create')
        assert doc.first('label', for_='home_postal_code')
        assert doc.firsttag('input', name='home_postal_code')

        self.s.submit(doc.first('form'),
                      given_name='_test_given',
                      family_name='_test_family',
                      home_postal_code='_test_12345',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/haiti/view?id=%s' % person.record_id)
        assert 'Postal or zip code' in doc.text
        assert '_test_12345' in doc.text
        person.delete()

        # use_postal_code=False
        doc = self.go('/pakistan/create')
        assert not doc.all('label', for_='home_postal_code')
        assert not doc.alltags('input', name='home_postal_code')

        self.s.submit(doc.first('form'),
                      given_name='_test_given',
                      family_name='_test_family',
                      home_postal_code='_test_12345',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/pakistan/view?id=%s' % person.record_id)
        assert 'Postal or zip code' not in doc.text
        assert '_test_12345' not in doc.text
        person.delete()

    def test_legacy_redirect(self):
        # enable legacy redirects.
        config.set(missing_repo_redirect_enabled=True)
        self.s.go('http://%s/?subdomain=japan' % self.hostport,
                  redirects=0)
        self.assertEqual(self.s.status, 301)
        self.assertEqual(self.s.headers['location'],
                         'http://google.org/personfinder/japan/')

        self.s.go('http://%s/feeds/person/create?full_name=foo&subdomain=japan'
                  % self.hostport, redirects=0)
        self.assertEqual(self.s.status, 301)
        self.assertEqual(
            self.s.headers['location'],
            'http://google.org/personfinder/japan/feeds/person/create'
            '?full_name=foo')

        # disable legacy redirects, which lands us on main.
        config.set(missing_repo_redirect_enabled=False)
        self.s.go('http://%s/?subdomain=japan' % self.hostport,
                  redirects=0)
        self.assertEqual(self.s.status, 200)
        # we land in the same bad old place
        self.assertEqual(self.s.url,
                         'http://%s/?subdomain=japan' % self.hostport)

    def test_create_and_seek_with_nondefault_charset(self):
        """Follow the basic create/seek flow with non-default charset
        (Shift_JIS).

        Verify:
        - "charsets" query parameter is passed around
        - Query parameters (encoded in Shift_JIS) are handled correctly
        """

        # Japanese translation of "I have information about someone"
        ja_i_have_info = (
            u'\u5b89\u5426\u60c5\u5831\u3092\u63d0\u4f9b\u3057\u305f\u3044')
        # Japanese translation of "I'm looking for someone"
        ja_looking_for_someone = (
            u'\u4eba\u3092\u63a2\u3057\u3066\u3044\u308b')
        test_given_name = u'\u592a\u90ce'
        test_family_name = u'\u30b0\u30fc\u30b0\u30eb'

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            assert_params_conform(
                url or self.s.url, {'charsets': 'shift_jis'})

        # Start on the home page and click the
        # "I have information about someone" button
        self.go('/haiti?lang=ja&charsets=shift_jis')
        query_page = self.s.follow(ja_i_have_info)
        assert_params()
        query_form = query_page.first('form')

        # Input a given name and a family name.
        create_page = self.s.submit(query_form,
                      given_name=test_given_name,
                      family_name=test_family_name)
        assert_params()
        create_form = create_page.first('form')

        # Submit a person record.
        self.s.submit(create_form,
                      given_name=test_given_name,
                      family_name=test_family_name,
                      author_name='_test_author_name',
                      text='_test_text',
                      author_made_contact='yes')
        assert_params()

        # Start on the home page and click the
        # "I'm looking for someone" button
        self.go('/haiti?lang=ja&charsets=shift_jis')
        search_page = self.s.follow(ja_looking_for_someone)
        assert_params()
        search_form = search_page.first('form')

        # Search for the record just submitted.
        self.s.submit(
            search_form, query=u'%s %s' % (test_given_name, test_family_name))
        assert_params()
        self.verify_results_page(1, all_have=([test_given_name]),
                                 some_have=([test_given_name]))

        self.verify_click_search_result(0, assert_params)


class PhotoTests(TestsBase):
    """Tests that verify photo upload and serving."""
    def submit_create(self, **kwargs):
        doc = self.go('/haiti/create?role=provide')
        form = doc.first('form')
        return self.s.submit(form,
                             given_name='_test_given_name',
                             family_name='_test_family_name',
                             author_name='_test_author_name',
                             text='_test_text',
                             **kwargs)

    def test_upload_photo(self):
        """Verifies a photo is uploaded and properly served on the server."""
        # Create a new person record with a profile photo.
        photo = file('tests/testdata/small_image.png')
        original_image = images.Image(photo.read())
        doc = self.submit_create(photo=photo)
        # Verify the image is uploaded and displayed on the view page.
        photos = doc.alltags('img', class_='photo')
        assert len(photos) == 1
        # Verify the image is served properly by checking the image metadata.
        doc = self.s.go(photos[0].attrs['src'])
        image = images.Image(doc.content)
        assert image.format == images.PNG
        assert image.width == original_image.width
        assert image.height == original_image.height
        # Follow the link on the image and verify the same image is served.
        doc = self.s.follow(photos[0].enclosing('a'))
        image = images.Image(doc.content)
        assert image.format == images.PNG
        assert image.width == original_image.width
        assert image.height == original_image.height

    def test_upload_photos_with_transformation(self):
        """Uploads both profile photo and note photo and verifies the images are
        properly transformed and served on the server i.e., jpg is converted to
        png and a large image is resized to match MAX_IMAGE_DIMENSION."""
        # Create a new person record with a profile photo and a note photo.
        photo = file('tests/testdata/small_image.jpg')
        note_photo = file('tests/testdata/large_image.png')
        original_image = images.Image(photo.read())
        doc = self.submit_create(photo=photo, note_photo=note_photo)
        # Verify the images are uploaded and displayed on the view page.
        photos = doc.alltags('img', class_='photo')
        assert len(photos) == 2
        # Verify the profile image is converted to png.
        doc = self.s.go(photos[0].attrs['src'])
        image = images.Image(doc.content)
        assert image.format == images.PNG
        assert image.width == original_image.width
        assert image.height == original_image.height
        # Verify the note image is resized to match MAX_IMAGE_DIMENSION.
        doc = self.s.go(photos[1].attrs['src'])
        image = images.Image(doc.content)
        assert image.format == images.PNG
        assert image.width == MAX_IMAGE_DIMENSION
        assert image.height == MAX_IMAGE_DIMENSION

    def test_upload_empty_photo(self):
        """Uploads an empty image and verifies no img tag in the view page."""
        # Create a new person record with a zero-byte profile photo.
        photo = file('tests/testdata/empty_image.png')
        doc = self.submit_create(photo=photo)
        # Verify there is no img tag in the view page.
        assert '_test_given_name' in doc.text
        photos = doc.alltags('img', class_='photo')
        assert len(photos) == 0

    def test_upload_broken_photo(self):
        """Uploads a broken image and verifies an error message is displayed."""
        # Create a new person record with a broken profile photo.
        photo = file('tests/testdata/broken_image.png')
        doc = self.submit_create(photo=photo)
        # Verify an error message is displayed.
        photos = doc.alltags('img', class_='photo')
        assert len(photos) == 0
        assert 'unrecognized format' in doc.text


class ResourceTests(TestsBase):
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
        Resource(parent=bundle, key_name='foo.txt', content='hello').put()
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content == 'hello'

        # Add a localized Resource.
        fr_key = Resource(parent=bundle, key_name='foo.txt:fr',
                          content='bonjour').put()
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content == 'hello'  # original Resource remains cached

        # The cached version should expire after 1 second.
        self.advance_utcnow(seconds=1.1)
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content == 'bonjour'

        # Change the non-localized Resource.
        Resource(parent=bundle, key_name='foo.txt', content='goodbye').put()
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content == 'bonjour'  # no effect on the localized Resource

        # Remove the localized Resource.
        db.delete(fr_key)
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content == 'bonjour'  # localized Resource remains cached

        # The cached version should expire after 1 second.
        self.advance_utcnow(seconds=1.1)
        doc = self.go('/global/foo.txt?lang=fr')
        assert doc.content == 'goodbye'

    def test_admin_resources(self):
        # Verify that the bundle listing loads.
        doc = self.go_as_admin('/global/admin/resources')

        # Add a new bundle (redirects to the new bundle's resource listing).
        doc = self.s.submit(doc.last('form'), resource_bundle='xyz')
        assert doc.first('a', class_='sel', content='Bundle: xyz')
        bundle = ResourceBundle.get_by_key_name('xyz')
        assert(bundle)

        # Add a resource (redirects to the resource's edit page).
        doc = self.s.submit(doc.first('form'), resource_name='abc')
        assert doc.first('a', class_='sel', content='Resource: abc')

        # The new Resource shouldn't exist in the datastore until it is saved.
        assert not Resource.get_by_key_name('abc', parent=bundle)

        # Enter some content for the resource.
        doc = self.s.submit(doc.first('form'), content='pqr')
        assert Resource.get_by_key_name('abc', parent=bundle).content == 'pqr'

        # Use the breadcrumb navigation bar to go back to the resource listing.
        doc = self.s.follow('Bundle: xyz')

        # Add a localized variant of the resource.
        row = doc.first('td', content='abc').enclosing('tr')
        doc = self.s.submit(row.first('form'), resource_lang='pl')
        assert doc.first('a', class_='sel', content='pl: Polish')

        # Enter some content for the localized resource.
        doc = self.s.submit(doc.first('form'), content='jk')
        assert Resource.get_by_key_name('abc:pl', parent=bundle).content == 'jk'

        # Confirm that both the generic and localized resource are listed.
        doc = self.s.follow('Bundle: xyz')
        assert doc.first('a', class_='resource', content='abc')
        assert doc.first('a', class_='resource', content='pl')

        # Copy all the resources to a new bundle.
        doc = self.s.submit(doc.last('form'), resource_bundle='zzz',
                            resource_bundle_original='xyz')
        parent = ResourceBundle.get_by_key_name('zzz')
        assert Resource.get_by_key_name('abc', parent=parent).content == 'pqr'
        assert Resource.get_by_key_name('abc:pl', parent=parent).content == 'jk'

        # Verify that we can't add a resource to the default bundle.
        bundle = ResourceBundle.get_by_key_name('1')
        assert(bundle)
        doc = self.go_as_admin('/global/admin/resources')
        doc = self.s.follow('1 (default)')
        self.s.submit(doc.first('form'), resource_name='abc')
        assert not Resource.get_by_key_name('abc', parent=bundle)

        # Verify that we can't edit a resource in the default bundle.
        self.s.back()
        doc = self.s.follow('base.html.template')
        self.s.submit(doc.first('form'), content='xyz')
        assert not Resource.get_by_key_name('base.html.template', parent=bundle)

        # Verify that we can't copy resources into the default bundle.
        doc = self.go_as_admin('/global/admin/resources')
        doc = self.s.follow('xyz')
        doc = self.s.submit(doc.last('form'), resource_bundle='1',
                            resource_bundle_original='xyz')
        assert not Resource.get_by_key_name('abc', parent=bundle)

        # Switch the default bundle version.
        doc = self.go_as_admin('/global/admin/resources')
        doc = self.s.submit(doc.first('form'), resource_bundle_default='xyz')
        assert 'xyz (default)' in doc.text
        # Undo.
        doc = self.s.submit(doc.first('form'), resource_bundle_default='1')
        assert '1 (default)' in doc.text


class CounterTests(TestsBase):
    """Tests related to Counters."""

    def test_tasks_count(self):
        """Tests the counting task."""
        # Add two Persons and two Notes in the 'haiti' repository.
        db.put([Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            author_name='_test1_author_name',
            entry_date=TEST_DATETIME,
            full_name='_test1_full_name',
            sex='male',
            date_of_birth='1970-01-01',
            age='50-60',
            latest_status='believed_missing'
        ), Note(
            key_name='haiti:test.google.com/note.123',
            repo='haiti',
            person_record_id='haiti:test.google.com/person.123',
            entry_date=TEST_DATETIME,
            status='believed_missing'
        ), Person(
            key_name='haiti:test.google.com/person.456',
            repo='haiti',
            author_name='_test2_author_name',
            entry_date=TEST_DATETIME,
            full_name='_test2_full_name',
            sex='female',
            date_of_birth='1970-02-02',
            age='30-40',
            latest_found=True
        ), Note(
            key_name='haiti:test.google.com/note.456',
            repo='haiti',
            person_record_id='haiti:test.google.com/person.456',
            entry_date=TEST_DATETIME,
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
            entry_date=TEST_DATETIME,
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


class ConfigTests(TestsBase):
    """Tests related to configuration settings (ConfigEntry entities)."""

    # Repo and ConfigEntry entities should be wiped between tests.
    kinds_to_keep = ['Authorization']

    def tearDown(self):
        TestsBase.tearDown(self)

        # Restore the configuration settings.
        setup.setup_repos()
        setup.setup_configs()

        # Flush the configuration cache.
        config.cache.enable(False)
        self.go('/haiti?lang=en&flush=config')

    def test_config_cache_enabling(self):
        # The tests below flush the resource cache so that the effects of
        # the config cache become visible for testing.

        # Modify the custom title directly in the datastore.
        # With the config cache off, new values should appear immediately.
        config.cache.enable(False)
        db.put(config.ConfigEntry(key_name='haiti:repo_titles',
                                  value='{"en": "FooTitle"}'))
        doc = self.go('/haiti?lang=en&flush=resource')
        assert 'FooTitle' in doc.text
        db.put(config.ConfigEntry(key_name='haiti:repo_titles',
                                  value='{"en": "BarTitle"}'))
        doc = self.go('/haiti?lang=en&flush=resource')
        assert 'BarTitle' in doc.text

        # Now enable the config cache and load the main page again.
        # This should pull the configuration value from database and cache it.
        config.cache.enable(True)
        doc = self.go('/haiti?lang=en&flush=config,resource')
        assert 'BarTitle' in doc.text

        # Modify the custom title directly in the datastore.
        # The old message from the config cache should still be visible because
        # the config cache doesn't know that the datastore changed.
        db.put(config.ConfigEntry(key_name='haiti:repo_titles',
                                  value='{"en": "QuuxTitle"}'))
        doc = self.go('/haiti?lang=en&flush=resource')
        assert 'BarTitle' in doc.text

        # After 10 minutes, the cache should pick up the new value.
        self.advance_utcnow(seconds=601)
        doc = self.go('/haiti?lang=en&flush=resource')
        assert 'QuuxTitle' in doc.text


    def test_config_namespaces(self):
        # Tests the cache's ability to retrieve global or repository-specific
        # configuration entries.
        cfg_sub = config.Configuration('_foo')
        cfg_global = config.Configuration('*')

        config.set_for_repo('*',
                            captcha_private_key='global_abcd',
                            captcha_public_key='global_efgh',
                            translate_api_key='global_hijk')
        assert cfg_global.captcha_private_key == 'global_abcd'
        assert cfg_global.captcha_public_key == 'global_efgh'
        assert cfg_global.translate_api_key == 'global_hijk'

        config.set_for_repo('_foo',
                            captcha_private_key='abcd',
                            captcha_public_key='efgh')
        assert cfg_sub.captcha_private_key == 'abcd'
        assert cfg_sub.captcha_public_key == 'efgh'
        # If a key isn't present for a repository, its value for
        # the global domain is retrieved.
        assert cfg_sub.translate_api_key == 'global_hijk'

    def test_admin_page(self):
        # Load the administration page.
        doc = self.go_as_admin('/haiti/admin')
        self.assertEquals(self.s.status, 200)

        # Activate a new repository.
        assert not Repo.get_by_key_name('xyz')
        create_form = doc.first('form', id='create_repo')
        doc = self.s.submit(create_form, new_repo='xyz')
        assert Repo.get_by_key_name('xyz')

        # Change some settings for the new repository.
        settings_form = doc.first('form', id='save_repo')
        doc = self.s.submit(settings_form,
            language_menu_options='["no"]',
            repo_titles='{"no": "Jordskjelv"}',
            keywords='foo, bar',
            use_family_name='false',
            family_name_first='false',
            use_alternate_names='false',
            use_postal_code='false',
            allow_believed_dead_via_ui='false',
            min_query_word_length='1',
            show_profile_entry='false',
            profile_websites='["http://abc"]',
            map_default_zoom='6',
            map_default_center='[4, 5]',
            map_size_pixels='[300, 300]',
            read_auth_key_required='false',
            start_page_custom_htmls='{"no": "start page message"}',
            results_page_custom_htmls='{"no": "results page message"}',
            view_page_custom_htmls='{"no": "view page message"}',
            seek_query_form_custom_htmls='{"no": "query form message"}',
            bad_words = 'bad, word',
            force_https = 'false'
        )
        self.assertEquals(self.s.status, 200)
        cfg = config.Configuration('xyz')
        self.assertEquals(cfg.language_menu_options, ['no'])
        assert cfg.repo_titles == {'no': 'Jordskjelv'}
        assert cfg.keywords == 'foo, bar'
        assert not cfg.use_family_name
        assert not cfg.family_name_first
        assert not cfg.use_alternate_names
        assert not cfg.use_postal_code
        assert not cfg.allow_believed_dead_via_ui
        assert cfg.min_query_word_length == 1
        assert not cfg.show_profile_entry
        assert cfg.profile_websites == ['http://abc']
        assert cfg.map_default_zoom == 6
        assert cfg.map_default_center == [4, 5]
        assert cfg.map_size_pixels == [300, 300]
        assert not cfg.read_auth_key_required
        assert cfg.bad_words == 'bad, word'
        assert not cfg.force_https

        old_updated_date = cfg.updated_date
        self.advance_utcnow(seconds=1)

        # Change settings again and make sure they took effect.
        settings_form = doc.first('form', id='save_repo')
        doc = self.s.submit(settings_form,
            language_menu_options='["nl"]',
            repo_titles='{"nl": "Aardbeving"}',
            keywords='spam, ham',
            use_family_name='true',
            family_name_first='true',
            use_alternate_names='true',
            use_postal_code='true',
            allow_believed_dead_via_ui='true',
            min_query_word_length='2',
            show_profile_entry='true',
            profile_websites='["http://xyz"]',
            map_default_zoom='7',
            map_default_center='[-3, -7]',
            map_size_pixels='[123, 456]',
            read_auth_key_required='true',
            start_page_custom_htmls='{"nl": "start page message"}',
            results_page_custom_htmls='{"nl": "results page message"}',
            view_page_custom_htmls='{"nl": "view page message"}',
            seek_query_form_custom_htmls='{"nl": "query form message"}',
            bad_words = 'foo, bar',
            force_https = 'true'
        )

        cfg = config.Configuration('xyz')
        assert cfg.language_menu_options == ['nl']
        assert cfg.repo_titles == {'nl': 'Aardbeving'}
        assert cfg.keywords == 'spam, ham'
        assert cfg.use_family_name
        assert cfg.family_name_first
        assert cfg.use_alternate_names
        assert cfg.use_postal_code
        assert cfg.allow_believed_dead_via_ui
        assert cfg.min_query_word_length == 2
        assert cfg.show_profile_entry
        assert cfg.profile_websites == ['http://xyz']
        assert cfg.map_default_zoom == 7
        assert cfg.map_default_center == [-3, -7]
        assert cfg.map_size_pixels == [123, 456]
        assert cfg.read_auth_key_required
        assert cfg.bad_words == 'foo, bar'
        assert cfg.force_https
        # Changing configs other than 'deactivated' or 'test_mode' does not
        # renew 'updated_date'.
        assert cfg.updated_date == old_updated_date

        # Verifies that there is a javascript constant with languages in it
        # (for the dropdown); thus, a language that is NOT used but IS
        # supported should appear
        assert self.s.doc.find('bg')
        assert self.s.doc.find('Bulgarian')

        # Verifies that there is a javascript constant with the previously
        # saved languages and titles in it
        assert self.s.doc.find('nl')
        assert self.s.doc.find('Aardbeving')

    def test_deactivation(self):
        # Load the administration page.
        doc = self.go_as_admin('/haiti/admin')
        assert self.s.status == 200

        cfg = config.Configuration('haiti')
        old_updated_date = cfg.updated_date
        self.advance_utcnow(seconds=1)

        # Deactivate an existing repository.
        settings_form = doc.first('form', id='save_repo')
        doc = self.s.submit(settings_form,
            language_menu_options='["en"]',
            repo_titles='{"en": "Foo"}',
            keywords='foo, bar',
            profile_websites='[]',
            deactivated='true',
            deactivation_message_html='de<i>acti</i>vated',
            start_page_custom_htmls='{"en": "start page message"}',
            results_page_custom_htmls='{"en": "results page message"}',
            view_page_custom_htmls='{"en": "view page message"}',
            seek_query_form_custom_htmls='{"en": "query form message"}',
        )

        cfg = config.Configuration('haiti')
        assert cfg.deactivated
        assert cfg.deactivation_message_html == 'de<i>acti</i>vated'
        # Changing 'deactivated' renews updated_date.
        assert cfg.updated_date != old_updated_date

        # Ensure all paths listed in app.yaml are inaccessible, except /admin.
        for path in ['', '/query', '/results', '/create', '/view',
                     '/multiview', '/reveal', '/photo', '/embed',
                     '/gadget', '/delete', '/sitemap', '/api/read',
                     '/api/write', '/feeds/note', '/feeds/person']:
            doc = self.go('/haiti%s' % path)
            assert 'de<i>acti</i>vated' in doc.content, \
                'path: %s, content: %s' % (path, doc.content)
            assert doc.alltags('form') == []
            assert doc.alltags('input') == []
            assert doc.alltags('table') == []
            assert doc.alltags('td') == []

    def test_the_test_mode(self):
        HTML_PATHS = ['', '/query', '/results', '/create', '/view',
                      '/multiview', '/reveal', '/photo', '/embed', '/delete']

        # First check no HTML pages show the test mode message.
        for path in HTML_PATHS:
            doc = self.go('/haiti%s' % path)
            assert 'currently in test mode' not in doc.content, \
                'path: %s, content: %s' % (path, doc.content)

        # Load the administration page.
        doc = self.go_as_admin('/haiti/admin')
        assert self.s.status == 200

        cfg = config.Configuration('haiti')
        old_updated_date = cfg.updated_date
        self.advance_utcnow(seconds=1)

        # Enable test-mode for an existing repository.
        settings_form = doc.first('form', id='save_repo')
        doc = self.s.submit(settings_form,
            language_menu_options='["en"]',
            repo_titles='{"en": "Foo"}',
            test_mode='true',
            profile_websites='[]',
            start_page_custom_htmls='{"en": "start page message"}',
            results_page_custom_htmls='{"en": "results page message"}',
            view_page_custom_htmls='{"en": "view page message"}',
            seek_query_form_custom_htmls='{"en": "query form message"}')

        cfg = config.Configuration('haiti')
        assert cfg.test_mode
        # Changing 'test_mode' renews updated_date.
        assert cfg.updated_date != old_updated_date

        # Ensure all HTML pages show the test mode message.
        for path in HTML_PATHS:
            doc = self.go('/haiti%s' % path)
            assert 'currently in test mode' in doc.content, \
                'path: %s, content: %s' % (path, doc.content)

    def test_custom_messages(self):
        # Load the administration page.
        doc = self.go_as_admin('/haiti/admin')
        assert self.s.status == 200

        # Edit the custom text fields
        settings_form = doc.first('form', id='save_repo')
        doc = self.s.submit(settings_form,
            language_menu_options='["en"]',
            repo_titles='{"en": "Foo"}',
            keywords='foo, bar',
            profile_websites='[]',
            start_page_custom_htmls=
                '{"en": "<b>English</b> start page message",'
                ' "fr": "<b>French</b> start page message"}',
            results_page_custom_htmls=
                '{"en": "<b>English</b> results page message",'
                ' "fr": "<b>French</b> results page message"}',
            view_page_custom_htmls=
                '{"en": "<b>English</b> view page message",'
                ' "fr": "<b>French</b> view page message"}',
            seek_query_form_custom_htmls=
                '{"en": "<b>English</b> query form message",'
                ' "fr": "<b>French</b> query form message"}',
        )

        cfg = config.Configuration('haiti')
        assert cfg.start_page_custom_htmls == \
            {'en': '<b>English</b> start page message',
             'fr': '<b>French</b> start page message'}
        assert cfg.results_page_custom_htmls == \
            {'en': '<b>English</b> results page message',
             'fr': '<b>French</b> results page message'}
        assert cfg.view_page_custom_htmls == \
            {'en': '<b>English</b> view page message',
             'fr': '<b>French</b> view page message'}
        assert cfg.seek_query_form_custom_htmls == \
            {'en': '<b>English</b> query form message',
             'fr': '<b>French</b> query form message'}

        # Add a person record
        db.put(Person(
            key_name='haiti:test.google.com/person.1001',
            repo='haiti',
            entry_date=TEST_DATETIME,
            full_name='_status_full_name',
            author_name='_status_author_name'
        ))

        # Check for custom message on main page
        doc = self.go('/haiti?flush=*')
        assert 'English start page message' in doc.text
        doc = self.go('/haiti?flush=*&lang=fr')
        assert 'French start page message' in doc.text
        doc = self.go('/haiti?flush=*&lang=ht')
        assert 'English start page message' in doc.text

        # Check for custom messages on results page
        doc = self.go('/haiti/results?query=xy&role=seek&lang=en')
        assert 'English results page message' in doc.text
        assert 'English query form message' in doc.text
        doc = self.go('/haiti/results?query=xy&role=seek&lang=fr')
        assert 'French results page message' in doc.text
        assert 'French query form message' in doc.text
        doc = self.go('/haiti/results?query=xy&role=seek&lang=ht')
        assert 'English results page message' in doc.text
        assert 'English query form message' in doc.text

        # Check for custom message on view page
        doc = self.go('/haiti/view?id=test.google.com/person.1001&lang=en')
        assert 'English view page message' in doc.text
        doc = self.go(
            '/haiti/view?id=test.google.com/person.1001&lang=fr')
        assert 'French view page message' in doc.text
        doc = self.go(
            '/haiti/view?id=test.google.com/person.1001&lang=ht')
        assert 'English view page message' in doc.text


class SecretTests(TestsBase):
    """Tests that manipulate Secret entities."""

    def test_analytics_id(self):
        """Checks that the analytics_id Secret is used for analytics."""
        doc = self.go('/haiti/create')
        assert 'getTracker(' not in doc.content

        db.put(Secret(key_name='analytics_id', secret='analytics_id_xyz'))

        doc = self.go('/haiti/create')
        assert "getTracker('analytics_id_xyz')" in doc.content

    def test_maps_api_key(self):
        """Checks that maps don't appear when there is no maps_api_key."""
        db.put(Person(
            key_name='haiti:test.google.com/person.1001',
            repo='haiti',
            entry_date=TEST_DATETIME,
            full_name='_status_full_name',
            author_name='_status_author_name'
        ))
        doc = self.go('/haiti/create?role=provide')
        assert 'id="clickable_map"' not in doc.content
        doc = self.go('/haiti/view?id=test.google.com/person.1001')
        assert 'id="clickable_map"' not in doc.content

        db.put(Secret(key_name='maps_api_key', secret='maps_api_key_xyz'))

        doc = self.go('/haiti/create?role=provide')
        assert 'maps_api_key_xyz' in doc.content
        assert 'id="clickable_map"' in doc.content
        doc = self.go('/haiti/view?id=test.google.com/person.1001')
        assert 'maps_api_key_xyz' in doc.content
        assert 'id="clickable_map"' in doc.content


class FeedTests(TestsBase):
    """Tests atom feeds.

    TODO(ryok): move feed tests from PersonNoteTests to FeedTests.
    """
    def setUp(self):
        TestsBase.setUp(self)
        configure_api_logging()

    def tearDown(self):
        TestsBase.tearDown(self)
        config.set_for_repo('haiti', deactivated=False)
        config.set_for_repo('japan', test_mode=False)

    def test_repo_feed_non_existing_repo(self):
        self.go('/none/feeds/repo')
        assert self.s.status == 404

    def test_repo_feed_deactivated_repo(self):
        config.set_for_repo('haiti', deactivated=True)
        doc = self.go('/haiti/feeds/repo')
        expected_content = '''\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:gpf="http://schemas.google.com/personfinder/2012"
      xmlns:georss="http://www.georss.org/georss">
  <id>http://%s/personfinder/haiti/feeds/repo</id>
  <title>Person Finder Repository Feed</title>
  <updated>1970-01-01T00:00:00Z</updated>
</feed>
''' % self.hostport
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

    def test_repo_feed_activated_repo(self):
        doc = self.go('/haiti/feeds/repo')
        expected_content = '''\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:gpf="http://schemas.google.com/personfinder/2012"
      xmlns:georss="http://www.georss.org/georss">
  <id>http://%s/personfinder/haiti/feeds/repo</id>
  <title>Person Finder Repository Feed</title>
  <updated>2010-01-12T00:00:00Z</updated>
  <entry>
    <id>%s/haiti</id>
    <published>2010-01-12T00:00:00Z</published>
    <updated>2010-01-12T00:00:00Z</updated>
    <title xml:lang="en">Haiti Earthquake</title>
    <content type="text/xml">
      <gpf:repo>
        <gpf:title xml:lang="en">Haiti Earthquake</gpf:title>
        <gpf:title xml:lang="ht">Tranbleman Tè an Ayiti</gpf:title>
        <gpf:title xml:lang="fr">Séisme en Haïti</gpf:title>
        <gpf:title xml:lang="es">Terremoto en Haití</gpf:title>
        <gpf:read_auth_key_required>false</gpf:read_auth_key_required>
        <gpf:search_auth_key_required>false</gpf:search_auth_key_required>
        <gpf:test_mode>false</gpf:test_mode>
        <gpf:location>
          <georss:point>18.968637 -72.284546</georss:point>
        </gpf:location>
      </gpf:repo>
    </content>
  </entry>
</feed>
''' % (self.hostport, ROOT_URL)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # verify we logged the repo read.
        verify_api_log(ApiActionLog.REPO, api_key='')

    def test_repo_feed_all_repos(self):
        config.set_for_repo('haiti', deactivated=True)
        config.set_for_repo('japan', test_mode=True)
        config.set_for_repo('japan', updated_date=utils.get_timestamp(
            datetime.datetime(2012, 03, 11)))

        doc = self.go('/global/feeds/repo')
        expected_content = '''\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:gpf="http://schemas.google.com/personfinder/2012"
      xmlns:georss="http://www.georss.org/georss">
  <id>http://%s/personfinder/global/feeds/repo</id>
  <title>Person Finder Repository Feed</title>
  <updated>2012-03-11T00:00:00Z</updated>
  <entry>
    <id>%s/japan</id>
    <published>2011-03-11T00:00:00Z</published>
    <updated>2012-03-11T00:00:00Z</updated>
    <title xml:lang="ja">2011 日本地震</title>
    <content type="text/xml">
      <gpf:repo>
        <gpf:title xml:lang="ja">2011 日本地震</gpf:title>
        <gpf:title xml:lang="en">2011 Japan Earthquake</gpf:title>
        <gpf:title xml:lang="ko"></gpf:title>
        <gpf:title xml:lang="zh-CN">2011 日本地震</gpf:title>
        <gpf:title xml:lang="zh-TW">2011 日本地震</gpf:title>
        <gpf:title xml:lang="pt-BR">2011 Terremoto no Japão</gpf:title>
        <gpf:title xml:lang="es">2011 Terremoto en Japón</gpf:title>
        <gpf:read_auth_key_required>true</gpf:read_auth_key_required>
        <gpf:search_auth_key_required>true</gpf:search_auth_key_required>
        <gpf:test_mode>true</gpf:test_mode>
        <gpf:location>
          <georss:point>38 140.7</georss:point>
        </gpf:location>
      </gpf:repo>
    </content>
  </entry>
  <entry>
    <id>%s/pakistan</id>
    <published>2010-08-06T00:00:00Z</published>
    <updated>2010-08-06T00:00:00Z</updated>
    <title xml:lang="en">Pakistan Floods</title>
    <content type="text/xml">
      <gpf:repo>
        <gpf:title xml:lang="en">Pakistan Floods</gpf:title>
        <gpf:title xml:lang="ur">پاکستانی سیلاب</gpf:title>
        <gpf:read_auth_key_required>false</gpf:read_auth_key_required>
        <gpf:search_auth_key_required>false</gpf:search_auth_key_required>
        <gpf:test_mode>false</gpf:test_mode>
        <gpf:location>
          <georss:point>33.36 73.26</georss:point>
        </gpf:location>
      </gpf:repo>
    </content>
  </entry>
</feed>
''' % (self.hostport, ROOT_URL, ROOT_URL)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # verify we logged the repo read.
        verify_api_log(ApiActionLog.REPO, api_key='')


class DownloadFeedTests(TestsBase):
    """Tests for the tools/download_feed.py script."""
    def setUp(self):
        TestsBase.setUp(self)
        self.setup_person_and_note()
        fd, self.filename = tempfile.mkstemp()
        os.close(fd)

    def tearDown(self):
        os.remove(self.filename)
        TestsBase.tearDown(self)

    def test_download_xml(self):
        url = 'http://%s/personfinder/haiti/feeds/person' % self.hostport
        download_feed.main('-q', '-o', self.filename, url)
        output = open(self.filename).read()
        assert '<pfif:pfif ' in output
        assert '<pfif:person>' in output
        assert '<pfif:given_name>_test_given_name</pfif:given_name>' in output

    def test_download_csv(self):
        url = 'http://%s/personfinder/haiti/feeds/person' % self.hostport
        download_feed.main('-q', '-o', self.filename, '-f', 'csv',
                           '-F', 'family_name,given_name,age', url)
        lines = open(self.filename).readlines()
        assert len(lines) == 2
        assert lines[0].strip() == 'family_name,given_name,age'
        assert lines[1].strip() == '_test_family_name,_test_given_name,'

    def test_download_notes(self):
        url = 'http://%s/personfinder/haiti/feeds/note' % self.hostport
        download_feed.main('-q', '-o', self.filename, '-n', url)
        output = open(self.filename).read()
        assert '<pfif:pfif ' in output
        assert '<pfif:note>' in output
        assert '<pfif:text>Testing</pfif:text>' in output


class ImportTests(TestsBase):
    """Tests for CSV import page at /api/import."""
    def setUp(self):
        TestsBase.setUp(self)
        config.set_for_repo(
            'haiti',
            api_action_logging=True)
        self.filename = None

    def tearDown(self):
        if self.filename:
            os.remove(self.filename)
        TestsBase.tearDown(self)

    def _write_csv_file(self, content):
        # TODO(ryok): We should use StringIO instead of a file on disk. Update
        # scrape.py to support StringIO.
        fd, self.filename = tempfile.mkstemp()
        os.fdopen(fd, 'w').write('\n'.join(content))

    def test_import_no_csv(self):
        """Verifies an error message is shown when no CSV file is uploaded."""
        doc = self.go('/haiti/api/import')
        form = doc.last('form')
        doc = self.s.submit(form, key='test_key')
        assert 'Please specify at least one CSV file.' in doc.text

    def test_import_invalid_authentication_key(self):
        """Verifies an error message is shown when auth key is invalid."""
        self._write_csv_file([
            'person_record_id,source_date,full_name',
            'test.google.com/person1,2013-02-26T09:10:00Z,_test_full_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.last('form')
        doc = self.s.submit(form, key='bad_key', content=open(self.filename))
        assert 'Missing or invalid authorization key' in doc.text

    def test_import_broken_csv(self):
        """Verifies an error message is shown when a broken CSV is imported."""
        self._write_csv_file([
            'person_record_id,source_date,\0full_name',  # contains null
            'test.google.com/person1,2013-02-26T09:10:00Z,_test_full_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.last('form')
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
        form = doc.last('form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))
        assert 'Person records Imported 1 of 1' in re.sub('\\s+', ' ', doc.text)
        assert Person.all().count() == 1
        assert Note.all().count() == 0
        person = Person.all().get()
        assert person.record_id == 'test.google.com/person1'
        assert person.source_date == datetime.datetime(2013, 2, 26, 9, 10, 0)
        assert person.full_name == '_test_full_name'
        verify_api_log(ApiActionLog.WRITE, person_records=1)

    def test_import_one_note(self):
        """Verifies a Note entry is successfully imported."""
        self._write_csv_file([
            'note_record_id,person_record_id,author_name,source_date',
            'test.google.com/note1,test.google.com/person1,' +
            '_test_author_name,2013-02-26T09:10:00Z',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.last('form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))
        assert 'Note records Imported 1 of 1' in re.sub('\\s+', ' ', doc.text)
        assert Person.all().count() == 0
        assert Note.all().count() == 1
        note = Note.all().get()
        assert note.record_id == 'test.google.com/note1'
        assert note.person_record_id == 'test.google.com/person1'
        assert note.author_name == '_test_author_name'
        assert note.source_date == datetime.datetime(2013, 2, 26, 9, 10, 0)
        verify_api_log(ApiActionLog.WRITE, note_records=1)

    def test_import_only_digit_record_id(self):
        """Verifies that a Person entry is successfully imported even if the
        record_id just contains digits, and that the imported record_id is
        prefixed with the write domain associated with auth key."""
        self._write_csv_file([
            'person_record_id,source_date,full_name',
            '1,2013-02-26T09:10:00Z,_test_full_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.last('form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))
        assert 'Person records Imported 1 of 1' in re.sub('\\s+', ' ', doc.text)
        assert Person.all().count() == 1
        assert Note.all().count() == 0
        person = Person.all().get()
        assert person.record_id == 'test.google.com/1'
        assert person.source_date == datetime.datetime(2013, 2, 26, 9, 10, 0)
        assert person.full_name == '_test_full_name'
        verify_api_log(ApiActionLog.WRITE, person_records=1)

    def test_import_domain_dont_match(self):
        """Verifies we reject a Person entry whose record_id domain does not
        match that of authentication key."""
        self._write_csv_file([
            'person_record_id,source_date,full_name',
            'different.google.com/person1,2013-02-26T09:10:00Z,_test_full_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.last('form')
        doc = self.s.submit(form, key='test_key', content=open(self.filename))
        assert 'Person records Imported 0 of 1' in re.sub('\\s+', ' ', doc.text)
        assert 'Not in authorized domain' in doc.text
        assert Person.all().count() == 0
        assert Note.all().count() == 0
        verify_api_log(ApiActionLog.WRITE)

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
        form = doc.last('form')
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
        verify_api_log(ApiActionLog.WRITE, person_records=1, note_records=1)

    def test_import_one_person_and_note_on_single_row(self):
        """Verifies a Note entry and a Person entry on a single row are
        successfully imported."""
        self._write_csv_file([
            'person_record_id,full_name,source_date,note_record_id,author_name',
            'test.google.com/person1,_test_full_name,2013-02-26T09:10:00Z,' +
            'test.google.com/note1,_test_author_name',
            ])
        doc = self.go('/haiti/api/import')
        form = doc.last('form')
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
        verify_api_log(ApiActionLog.WRITE, person_records=1, note_records=1)

# TODO(ryok): fix go_as_operator() and re-enable the tests.
#class ApiKeyManagementTests(TestsBase):
#    """Tests for API key management capabilities."""
#
#    key_management_operator = "op@example.com"
#    
#    def go_as_operator(self, path, **kwargs):
#        """Navigates to the given path with an operator login."""
#        if not self.logged_in_as_operator:
#            scrape.setcookies(self.s.cookiejar, self.hostport,
#                              ['dev_appserver_login=%s:True:1' %
#                                  self.key_management_operator])
#            self.logged_in_as_operator = True
#        return self.go(path, **kwargs)
#
#    def go_as_admin(self, path, **kwargs):
#        """Setting logged_in_as_operator to False."""
#        ret = TestsBase.go_as_admin(self, path, **kwargs)
#        self.logged_in_as_operator = False
#        return ret
#
#    def setUp(self):
#        TestsBase.setUp(self)
#        self.logged_in_as_operator = False
#        config.set_for_repo(
#            'japan',
#            key_management_operators=[self.key_management_operator])
#
#    def test_toppage(self):
#        """Check the main page of API kay management."""
#        url = 'http://%s/personfinder/japan/admin/api_keys' % self.hostport
#        doc = self.go(url, redirects=0)
#        # check if 302
#        assert self.s.status == 302
#        doc = self.go_as_operator(url, redirects=0)
#        assert self.s.status == 200
#        assert 'API Key Management' in doc.text
#        doc = self.go_as_admin(url, redirects=0)
#        assert self.s.status == 200
#        assert 'API Key Management' in doc.text
#
#    def test_manage_key(self):
#        """Check if a new API key is created/updated correctly."""
#        url = 'http://%s/personfinder/japan/admin/api_keys' % self.hostport
#        doc = self.go_as_operator(url)
#        assert self.s.status == 200
#        assert 'API Key Management' in doc.text
#        form = doc.first('form', id='create-or-update-api-key')
#        contact_name = 'Test User'
#        contact_email = 'user@example.com'
#        organization_name = 'Example, Inc.'
#        domain_write_permission = 'example.com'
#        doc = self.s.submit(
#            form,
#            contact_name=contact_name,
#            contact_email=contact_email,
#            organization_name=organization_name,
#            domain_write_permission=domain_write_permission,
#            read_permission='on',
#            full_read_permission='on',
#            search_permission='on',
#            subscribe_permission='on',
#            mark_notes_reviewed='on',
#            is_valid='on',
#        )
#        assert 'A new API key has been created successfully.' in doc.text
#        q = Authorization.all().filter('repo =', 'japan')
#        authorizations = q.fetch(10)
#        assert len(authorizations) == 1
#        authorization = authorizations[0]
#        # Check if the new key is correct.
#        assert authorization.contact_name == contact_name
#        assert authorization.contact_email == contact_email
#        assert authorization.organization_name == organization_name
#        assert authorization.domain_write_permission == domain_write_permission
#        assert authorization.read_permission is True
#        assert authorization.full_read_permission is True
#        assert authorization.search_permission is True
#        assert authorization.subscribe_permission is True
#        assert authorization.mark_notes_reviewed is True
#        assert authorization.is_valid is True
#        # Check if the management log is created correctly.
#        q = ApiKeyManagementLog.all().filter('repo =', 'japan')
#        logs = q.fetch(10)
#        assert len(logs) == 1
#        log = logs[0]
#        assert log.user.email() == self.key_management_operator
#        assert log.authorization.key() == authorization.key()
#        assert log.action == ApiKeyManagementLog.CREATE
#
#        # List the key and click the edit form on the list
#        url = 'http://%s/personfinder/japan/admin/api_keys/list' % self.hostport
#        doc = self.go_as_admin(url)
#        assert self.s.status == 200
#        assert 'Listing API keys for japan' in doc.text
#        form = doc.first('form')
#        doc = self.s.submit(form)
#        assert self.s.status == 200
#        assert 'Detailed information of an API key for japan' in doc.text
#
#        # Update the key
#        contact_name = 'Japanese User'
#        contact_email = 'user@example.jp'
#        organization_name = 'Example, Corp.'
#
#        form = doc.first('form')
#        doc = self.s.submit(
#            form,
#            contact_name=contact_name,
#            contact_email=contact_email,
#            organization_name=organization_name,
#            domain_write_permission='',
#            read_permission='',
#            full_read_permission='',
#            search_permission='',
#            subscribe_permission='',
#            mark_notes_reviewed='',
#            is_valid='',
#            key=str(authorization.key()),
#        )
#        assert 'The API key has been updated successfully.' in doc.text
#        q = Authorization.all().filter('repo =', 'japan')
#        authorizations = q.fetch(10)
#        assert len(authorizations) == 1
#        authorization = authorizations[0]
#        # Check if the new key is correct.
#        assert authorization.contact_name == contact_name
#        assert authorization.contact_email == contact_email
#        assert authorization.organization_name == organization_name
#        assert authorization.domain_write_permission == ''
#        assert authorization.read_permission is False
#        assert authorization.full_read_permission is False
#        assert authorization.search_permission is False
#        assert authorization.subscribe_permission is False
#        assert authorization.mark_notes_reviewed is False
#        assert authorization.is_valid is False
#        # Check if the management log is created correctly.
#        q = ApiKeyManagementLog.all().filter('repo =', 'japan')
#        logs = q.fetch(10)
#        assert len(logs) == 2
#        for log in logs:
#            assert log.user.email() == self.key_management_operator
#            assert log.authorization.key() == authorization.key()
#            if log.action != ApiKeyManagementLog.CREATE:
#                assert log.action == ApiKeyManagementLog.UPDATE
