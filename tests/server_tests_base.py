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
from __future__ import print_function

import calendar
import datetime
import email
import email.header
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


last_star = time.time()  # timestamp of the last message that started with '*'.


class ServerTestsBase(unittest.TestCase):

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

    """Base class for test cases."""
    hostport = pytest.config.hostport
    mail_server = pytest.config.mail_server

    # Entities of these kinds won't be wiped between tests
    kinds_to_keep = ['Authorization', 'ConfigEntry', 'Repo']

    def setUp(self):
        """Sets up a scrape Session for each test."""
        # See http://zesty.ca/scrape for documentation on scrape.
        self.s = scrape.Session(verbose=1)
        self.set_utcnow_for_test(ServerTestsBase.TEST_TIMESTAMP, flush='*')
        config.set(xsrf_token_key='abc123')

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

    def run_task(self, path, **kwargs):
        # This is like go(), but with garbage data to trick scrape.py into doing
        # a POST request. If not for the fact that we're moving to Django and
        # going to be able to use the Django test client going forward, I'd do
        # this in a cleaner way, but it doesn't seem worth it for stuff we know
        # we have to rewrite.
        if 'data' in kwargs:
            return self.go(path, kwargs)
        else:
            return self.go(path, data={'garbage': 'thatmeansnothing'})

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
        # This isn't a real path, but that's ok, we just need some path that's
        # served by webapp2 rather than Django.
        path = '/webapp2path?utcnow=%s&flush=%s' % (param, flush)
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
            sex='female',
            age='52',
            home_city='_test_home_city',
            home_state='_test_home_state',
            source_date=ServerTestsBase.TEST_DATETIME,
            entry_date=ServerTestsBase.TEST_DATETIME,
            latest_status='believed_alive',
        )
        person.update_index(['old', 'new'])
        note = Note(
            key_name='haiti:%s/note.456' % domain,
            repo='haiti',
            author_email='test2@example.com',
            person_record_id='%s/person.123' % domain,
            source_date=ServerTestsBase.TEST_DATETIME,
            entry_date=ServerTestsBase.TEST_DATETIME,
            text='Testing',
            status='believed_alive',
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

    def get_email_payload(self, message):
        """Gets the payload (body) of the email.
        It performs base-64 decoding if needed.
        """
        m = email.message_from_string(message['data'])
        result = ''
        for part in m.walk():
            p = part.get_payload(decode=True)
            if p: result += p
        return result

    def get_email_subject(self, message):
        """Gets the subject of the email.
        It performs RFC 2047 decoding if needed."""
        m = email.message_from_string(message['data'])
        result = ''
        for s, encoding in email.header.decode_header(m['Subject']):
            assert encoding is None or encoding == 'utf-8'
            result += s
        return result

    def log(self, message, *args):
        """Prints a timestamped message to stderr (handy for debugging or profiling
        tests).  If the message starts with '*', the clock will be reset to zero."""
        global last_star
        now = time.time()
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        else:
            message = str(message)
        print('%6.2f:' % (now - last_star), message, args or '', file=sys.stderr)
        if message[:1] == '*':
            last_star = now

    def configure_api_logging(self, repo='*', enable=True):
        db.delete(ApiActionLog.all())
        config.set_for_repo(repo, api_action_logging=enable)

    def verify_api_log(self, action, api_key='test_key', person_records=None,
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

    def text_all_logs(self, ):
        return '\n'.join(['UserActionLog: action=%s entity_kind=%s' % (
            self.log.action, self.log.entity_kind)
            for self.log in UserActionLog.all().fetch(10)])

    def verify_user_action_log(self, action, entity_kind, fetch_limit=10, **kwargs):
        logs = UserActionLog.all().order('-time').fetch(fetch_limit)
        for self.log in logs:
            if self.log.action == action and self.log.entity_kind == entity_kind:
                for key, value in kwargs.iteritems():
                    assert getattr(self.log, key) == value
                return  # verified
        assert False, self.text_all_logs()  # not verified

    def get_test_filepath(self, filename):
        return os.path.join(os.environ['TESTS_DIR'], filename)

    def get_test_data(self, filename):
        return open(self.get_test_filepath(filename)).read()

    def assert_params_conform(self, url, required_params=None, forbidden_params=None):
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
