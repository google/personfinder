#!/usr/bin/python2.5
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

"""Starts up an appserver and runs end-to-end tests against it.

Instead of running this script directly, use the 'server_tests' shell script,
which sets up the PYTHONPATH and other necessary environment variables."""

import datetime
import inspect
import logging
import optparse
import os
import re
import signal
import smtpd
import subprocess
import sys
import threading
import time
import traceback
import unittest

from google.appengine.api import mail

import config
from model import *
import remote_api
import reveal
import scrape
import setup

NOTE_STATUS_OPTIONS = [
  '',
  'information_sought',
  'is_note_author',
  'believed_alive',
  'believed_missing',
  'believed_dead'
]


def timed(function):
    def timed_function(*args, **kwargs):
        start = time.time()
        try:
            function(*args, **kwargs)
        finally:
            print '%s: %.1f s' % (function.__name__, time.time() - start)
    return timed_function


class ProcessRunner(threading.Thread):
    """A thread that starts a subprocess, collects its output, and stops it."""

    READY_RE = re.compile('')  # this output means the process is ready
    OMIT_RE = re.compile('INFO ')  # omit these lines from the displayed output
    ERROR_RE = re.compile('ERROR|CRITICAL')  # this output indicates failure

    def __init__(self, name, args):
        threading.Thread.__init__(self)
        self.name = name
        self.args = args
        self.process = None  # subprocess.Popen instance
        self.ready = False  # process is running and ready
        self.failed = False  # process emitted an error message in its output
        self.output = []

    def run(self):
        """Starts the subprocess and collects its output while it runs."""
        self.process = subprocess.Popen(
            self.args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            close_fds=True)

        # Each subprocess needs a thread to be watching it and absorbing its
        # output; otherwise it will block when its stdout pipe buffer fills.
        while self.process.poll() is None:
            line = self.process.stdout.readline()
            if not line:  # process finished
                return
            if self.READY_RE.search(line):
                self.ready = True
            if self.OMIT_RE.search(line):  # filter out these lines
                continue
            if self.ERROR_RE.search(line):  # something went wrong
                self.failed = True
            if line.strip():
                self.output.append(line.strip())

    def stop(self):
        """Terminates the subprocess and returns its status code."""
        if self.process:  # started
            if self.isAlive():  # still running
                os.kill(self.process.pid, signal.SIGKILL)
            else:
                self.failed = self.process.returncode != 0
        self.clean_up()
        if self.failed:
            self.flush_output()
            print >>sys.stderr, '%s failed (status %s).\n' % (
                self.name, self.process.returncode)
        else:
            print >>sys.stderr, '%s stopped.' % self.name

    def flush_output(self):
        """Flushes the buffered output from this subprocess to stderr."""
        self.output, lines_to_print = [], self.output
        if lines_to_print:
            print >>sys.stderr
        for line in lines_to_print:
            print >>sys.stderr, self.name + ': ' + line

    def wait_until_ready(self, timeout=10):
        """Waits until the subprocess has logged that it is ready."""
        fail_time = time.time() + timeout
        while self.isAlive() and not self.ready and time.time() < fail_time:
            for jiffy in range(10):  # wait one second, aborting early if ready
                if not self.ready:
                    time.sleep(0.1)
            if not self.ready:
                self.flush_output()  # after each second, show output
        if self.ready:
            print >>sys.stderr, '%s started.' % self.name
        else:
            raise RuntimeError('%s failed to start.' % self.name)

    def clean_up(self):
        pass


class AppServerRunner(ProcessRunner):
    """Manages a dev_appserver subprocess."""

    READY_RE = re.compile('Running application ' + remote_api.get_app_id())

    def __init__(self, port, smtp_port):
        self.datastore_path = '/tmp/dev_appserver.datastore.%d' % os.getpid()
        ProcessRunner.__init__(self, 'appserver', [
            os.environ['PYTHON'],
            os.path.join(os.environ['APPENGINE_DIR'], 'dev_appserver.py'),
            os.environ['APP_DIR'],
            '--port=%s' % port,
            '--clear_datastore',
            '--datastore_path=%s' % self.datastore_path,
            '--require_indexes',
            '--smtp_host=localhost',
            '--smtp_port=%d' % smtp_port
        ])

    def clean_up(self):
        if os.path.exists(self.datastore_path):
            os.unlink(self.datastore_path)


class MailThread(threading.Thread):
    """Runs an SMTP server and stores the incoming messages."""
    messages = []

    def __init__(self, port):
        threading.Thread.__init__(self)
        self.port = port
        self.stop_requested = False

    def run(self):
        class MailServer(smtpd.SMTPServer):
            def process_message(self, peer, mailfrom, rcpttos, data):
                MailThread.messages.append(
                    {'from': mailfrom, 'to': rcpttos, 'data': data})

        server = MailServer(('localhost', self.port), None)
        print >>sys.stderr, 'SMTP server started.'
        while not self.stop_requested:
            smtpd.asyncore.loop(timeout=0.5, count=1)
        print >>sys.stderr, 'SMTP server stopped.'

    def stop(self):
        self.stop_requested = True

    def wait_until_ready(self, timeout=10):
        pass


def get_test_data(filename):
    return open(os.path.join(remote_api.TESTS_DIR, filename)).read()

def reset_data():
    """Reset the datastore to a known state, populated with test data."""
    setup.reset_datastore()
    Authorization.create(
        'haiti', 'test_key', domain_write_permission='test.google.com').put()
    Authorization.create(
        'haiti', 'other_key', domain_write_permission='other.google.com').put()
    Authorization.create(
        'haiti', 'read_key', read_permission=True).put()
    Authorization.create(
        'haiti', 'full_read_key', full_read_permission=True).put()

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
    verbose = 0
    hostport = None
    kinds_written_by_tests = []

    def setUp(self):
        """Sets up a scrape Session for each test."""
        # See http://zesty.ca/scrape for documentation on scrape.
        self.s = scrape.Session(verbose=self.verbose)

    def go(self, path, **kwargs):
        """Navigates the scrape Session to the given path on the test server."""
        return self.s.go('http://' + self.hostport + path, **kwargs)

    def tearDown(self):
        """Resets the datastore by deleting anything written during a test."""
        if self.kinds_written_by_tests:
            setup.wipe_datastore(*self.kinds_written_by_tests)


class ReadOnlyTests(TestsBase):
    """Tests that don't modify data go here."""

    def test_main(self):
        """Check the main page with no language specified."""
        doc = self.go('/?subdomain=haiti')
        assert 'I\'m looking for someone' in doc.text

    def test_main_english(self):
        """Check the main page with English language specified."""
        doc = self.go('/?subdomain=haiti&lang=en')
        assert 'I\'m looking for someone' in doc.text

    def test_main_french(self):
        """Check the French main page."""
        doc = self.go('/?subdomain=haiti&lang=fr')
        assert 'Je recherche quelqu\'un' in doc.text

    def test_main_creole(self):
        """Check the Creole main page."""
        doc = self.go('/?subdomain=haiti&lang=ht')
        assert u'Mwen ap ch\u00e8che yon moun' in doc.text

    def test_language_links(self):
        """Check that the language links go to the translated main page."""
        doc = self.go('/?subdomain=haiti')

        doc = self.s.follow(u'espa\u00f1ol')
        assert 'Busco a alguien' in doc.text

        doc = self.s.follow(u'Fran\u00e7ais')
        assert 'Je recherche quelqu\'un' in doc.text

        doc = self.go('/?subdomain=pakistan')
        doc = self.s.follow(u'\u0627\u0631\u062f\u0648')
        assert (u'\u0645\u06CC\u06BA \u06A9\u0633\u06CC \u06A9\u0648 ' +
                u'\u062A\u0644\u0627\u0634 \u06A9\u0631 ' +
                u'\u0631\u06C1\u0627 \u06C1\u0648') in doc.text

        doc = self.s.follow(u'English')
        assert 'I\'m looking for someone' in doc.text

    def test_language_xss(self):
        """Regression test for an XSS vulnerability in the 'lang' parameter."""
        doc = self.go('/?subdomain=haiti&lang="<script>alert(1)</script>')
        assert '<script>' not in doc.content

    def test_query(self):
        """Check the query page."""
        doc = self.go('/query?subdomain=haiti')
        button = doc.firsttag('input', type='submit')
        assert button['value'] == 'Search for this person'

        doc = self.go('/query?subdomain=haiti&role=provide')
        button = doc.firsttag('input', type='submit')
        assert button['value'] == 'Provide information about this person'

    def test_results(self):
        """Check the results page."""
        doc = self.go('/results?subdomain=haiti&query=xy')
        assert 'We have nothing' in doc.text

    def test_create(self):
        """Check the create page."""
        doc = self.go('/create?subdomain=haiti')
        assert 'Identify who you are looking for' in doc.text

        doc = self.go('/create?subdomain=haiti&role=provide')
        assert 'Identify who you have information about' in doc.text

    def test_view(self):
        """Check the view page."""
        doc = self.go('/view?subdomain=haiti')
        assert 'No person id was specified' in doc.text

    def test_multiview(self):
        """Check the multiview page."""
        doc = self.go('/multiview?subdomain=haiti')
        assert 'Compare these records' in doc.text

    def test_photo(self):
        """Check the photo page."""
        doc = self.go('/photo?subdomain=haiti')
        assert 'No photo id was specified' in doc.text

    def test_static(self):
        """Check that the static files are accessible."""
        doc = self.go('/static/no-photo.gif?subdomain=haiti')
        assert doc.content.startswith('GIF89a')

        doc = self.go('/static/style.css?subdomain=haiti')
        assert 'body {' in doc.content

    def test_embed(self):
        """Check the embed page."""
        doc = self.go('/embed?subdomain=haiti')
        assert 'Embedding' in doc.text

    def test_gadget(self):
        """Check the gadget page."""
        doc = self.go('/gadget?subdomain=haiti')
        assert '<Module>' in doc.content
        assert 'application/xml' in self.s.headers['content-type']

    def test_developers(self):
        """Check the developer instructions page."""
        doc = self.go('/developers?subdomain=haiti')
        assert 'Downloading Data' in doc.text

    def test_sitemap(self):
        """Check the sitemap generator."""
        doc = self.go('/sitemap?subdomain=haiti')
        assert '</sitemapindex>' in doc.content

        doc = self.go('/sitemap?subdomain=haiti&shard_index=1')
        assert '</urlset>' in doc.content

    def test_config_subdomain_titles(self):
        doc = self.go('/?subdomain=haiti')
        assert 'Haiti Earthquake' in doc.first('h1').text

        doc = self.go('/?subdomain=pakistan')
        assert 'Pakistan Floods' in doc.first('h1').text

    def test_config_language_menu_options(self):
        doc = self.go('/?subdomain=haiti')
        assert doc.first('a', u'Fran\xe7ais')
        assert doc.first('a', u'Krey\xf2l')
        assert not doc.all('a',u'\u0627\u0631\u062F\u0648')  # Urdu

        doc = self.go('/?subdomain=pakistan')
        assert doc.first('a',u'\u0627\u0631\u062F\u0648')  # Urdu
        assert not doc.all('a', u'Fran\xe7ais')

    def test_config_keywords(self):
        doc = self.go('/?subdomain=haiti')
        meta = doc.firsttag('meta', name='keywords')
        assert 'tremblement' in meta['content']

        doc = self.go('/?subdomain=pakistan')
        meta = doc.firsttag('meta', name='keywords')
        assert 'pakistan flood' in meta['content']


class PersonNoteTests(TestsBase):
    """Tests that modify Person and Note entities in the datastore go here.
    The contents of the datastore will be reset for each test."""
    kinds_written_by_tests = [Person, Note, Counter]

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

    def verify_results_page(self, num_results, all_have=(), some_have=()):
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

        # Person info is stored in matching 'label' and 'field' cells.
        fields = dict(zip(
            [label.text.strip() for label in details_page.all(class_='label')],
            details_page.all(class_='field')))
        for label, value in details.iteritems():
            assert fields[label].text.strip() == value

        assert len(details_page.all(class_='view note')) == num_notes

    def verify_click_search_result(self, n, url_test=lambda u: None):
        """Simulates clicking the nth search result (where n is zero-based).

        Also passes the URL followed to the given url_test function for checking.
        This function should raise an AssertionError on failure.

        Precondition: the current session must be on the results page
        Postcondition: the current session is on the person details page
        """

        # Get the list of links.
        results = self.s.doc.first('ul', class_='searchResults')
        result_link = results.all('a', class_='result-link')[n]

        # Verify and then follow the link.
        url_test(result_link['href'])
        self.s.go(result_link['href'])

    def verify_update_notes(self, found, note_body, author, **kwargs):
        """Verifies the process of adding a new note.

        Posts a new note with the given parameters.

        Precondition: the current session must be on the details page
        Postcondition: the current session is still on the details page
        """

        # Do not assert params.  Upon reaching the details page, you've lost
        # the difference between seekers and providers and the param is gone.
        details_page = self.s.doc
        num_initial_notes = len(details_page.all(class_='view note'))
        note_form = details_page.first('form')

        params = dict(kwargs)
        params['found'] = (found and 'yes') or 'no'
        params['text'] = note_body
        params['author_name'] = author

        details_page = self.s.submit(note_form, **params)
        notes = details_page.all(class_='view note')
        assert len(notes) == num_initial_notes + 1
        new_note_text = notes[-1].text
        for text in kwargs.values() + [note_body, author]:
            assert text in new_note_text, \
                'Note text %r missing %r' % (new_note_text, text)

        # Show this text if and only if the person has been found
        assert ('This person has been in contact with someone'
                in new_note_text) == found

    def test_seeking_someone_regular(self):
        """Follow the seeking someone flow on the regular-sized embed."""

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            assert_params_conform(
                url or self.s.url, {'role': 'seek'}, {'small': 'yes'})

        # Start on the home page and click the "I'm looking for someone" button
        self.go('/?subdomain=haiti')
        search_page = self.s.follow('I\'m looking for someone')
        search_form = search_page.first('form')
        assert 'Search for this person' in search_form.content

        # Try a search, which should yield no results.
        self.s.submit(search_form, query='_test_first_name')
        assert_params()
        self.verify_results_page(0)
        assert_params()
        self.verify_unsatisfactory_results()
        assert_params()

        # Submit the create form with minimal information.
        create_form = self.s.doc.first('form')
        self.s.submit(create_form,
                      first_name='_test_first_name',
                      last_name='_test_last_name',
                      author_name='_test_author_name')

        # For now, the date of birth should be hidden.
        assert 'birth' not in self.s.content.lower()

        self.verify_details_page(0, details={
            'Given name:': '_test_first_name',
            'Family name:': '_test_last_name',
            'Author\'s name:': '_test_author_name'})

        # Now the search should yield a result.
        self.s.submit(search_form, query='_test_first_name')
        assert_params()
        self.verify_results_page(1, all_have=(['_test_first_name']),
                                 some_have=(['_test_first_name']))
        self.verify_click_search_result(0, assert_params)
        # set the person entry_date to something in order to make sure adding
        # note doesn't update
        person = Person.all().filter('first_name =', '_test_first_name').get()
        person.entry_date = datetime.datetime(2006, 6, 6, 6, 6, 6)
        db.put(person)
        self.verify_details_page(0)
        self.verify_note_form()
        self.verify_update_notes(
            False, '_test A note body', '_test A note author')
        self.verify_update_notes(
            True, '_test Another note body', '_test Another note author',
            last_known_location='Port-au-Prince')

        person = Person.all().filter('first_name =', '_test_first_name').get()
        assert person.entry_date == datetime.datetime(2006, 6, 6, 6, 6, 6)

        # Submit the create form with complete information
        self.s.submit(create_form,
                      author_name='_test_author_name',
                      author_email='_test_author_email',
                      author_phone='_test_author_phone',
                      clone='yes',
                      source_name='_test_source_name',
                      source_date='2001-01-01',
                      source_url='_test_source_url',
                      first_name='_test_first_name',
                      last_name='_test_last_name',
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
                      description='_test_description')

        self.verify_details_page(0, details={
            'Given name:': '_test_first_name',
            'Family name:': '_test_last_name',
            'Sex:': 'female',
            # 'Date of birth:': '1955',  # currently hidden
            'Age:': '52',
            'Street name:': '_test_home_street',
            'Neighborhood:': '_test_home_neighborhood',
            'City:': '_test_home_city',
            'Province or state:': '_test_home_state',
            'Postal or zip code:': '_test_home_postal_code',
            'Home country:': '_test_home_country',
            'Author\'s name:': '_test_author_name',
            'Author\'s phone number:': '(click to reveal)',
            'Author\'s e-mail address:': '(click to reveal)',
            'Original URL:': 'Link',
            'Original posting date:': '2001-01-01 00:00 UTC',
            'Original site name:': '_test_source_name'})

    def test_new_indexing(self):
        """First create new entry with new_search param then search for it"""

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            assert_params_conform(
                url or self.s.url, {'role': 'seek'}, {'small': 'yes'})

        # Start on the home page and click the "I'm looking for someone" button
        self.go('/?subdomain=haiti')
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

        # Submit the create form with a valid first and last name
        self.s.submit(self.s.doc.first('form'),
                      first_name='ABCD EFGH',
                      last_name='IJKL MNOP',
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

    def test_have_information_regular(self):
        """Follow the "I have information" flow on the regular-sized embed."""

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            assert_params_conform(
                url or self.s.url, {'role': 'provide'}, {'small': 'yes'})

        self.go('/?subdomain=haiti')
        search_page = self.s.follow('I have information about someone')
        search_form = search_page.first('form')
        assert 'I have information about someone' in search_form.content

        self.assert_error_deadend(
            self.s.submit(search_form),
            'Enter the person\'s given and family names.')

        self.assert_error_deadend(
            self.s.submit(search_form, first_name='_test_first_name'),
            'Enter the person\'s given and family names.')

        self.s.submit(search_form,
                      first_name='_test_first_name',
                      last_name='_test_last_name')
        assert_params()
        # Because the datastore is empty, should go straight to the create page

        self.verify_create_form(prefilled_params={
            'first_name': '_test_first_name',
            'last_name': '_test_last_name'})
        self.verify_note_form()

        # Submit the create form with minimal information
        create_form = self.s.doc.first('form')
        self.s.submit(create_form,
                      first_name='_test_first_name',
                      last_name='_test_last_name',
                      author_name='_test_author_name',
                      text='_test A note body')

        self.verify_details_page(1, details={
            'Given name:': '_test_first_name',
            'Family name:': '_test_last_name',
            'Author\'s name:': '_test_author_name'})

        # Try the search again, and should get some results
        self.s.submit(search_form,
                      first_name='_test_first_name',
                      last_name='_test_last_name')
        assert_params()
        self.verify_results_page(
            1, all_have=('_test_first_name', '_test_last_name'))
        self.verify_click_search_result(0, assert_params)

        # For now, the date of birth should be hidden.
        assert 'birth' not in self.s.content.lower()
        self.verify_details_page(1)

        self.verify_note_form()
        self.verify_update_notes(
            False, '_test A note body', '_test A note author')
        self.verify_update_notes(
            True, '_test Another note body', '_test Another note author',
            last_known_location='Port-au-Prince')

        # Submit the create form with complete information
        self.s.submit(create_form,
                      author_name='_test_author_name',
                      author_email='_test_author_email',
                      author_phone='_test_author_phone',
                      clone='yes',
                      source_name='_test_source_name',
                      source_date='2001-01-01',
                      source_url='_test_source_url',
                      first_name='_test_first_name',
                      last_name='_test_last_name',
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
                      description='_test_description',
                      add_note='yes',
                      found='yes',
                      status='believed_alive',
                      email_of_found_person='_test_email_of_found_person',
                      phone_of_found_person='_test_phone_of_found_person',
                      last_known_location='_test_last_known_location',
                      text='_test A note body')

        self.verify_details_page(1, details={
            'Given name:': '_test_first_name',
            'Family name:': '_test_last_name',
            'Sex:': 'male',
            # 'Date of birth:': '1970-01',  # currently hidden
            'Age:': '30-40',
            'Street name:': '_test_home_street',
            'Neighborhood:': '_test_home_neighborhood',
            'City:': '_test_home_city',
            'Province or state:': '_test_home_state',
            'Postal or zip code:': '_test_home_postal_code',
            'Home country:': '_test_home_country',
            'Author\'s name:': '_test_author_name',
            'Author\'s phone number:': '(click to reveal)',
            'Author\'s e-mail address:': '(click to reveal)',
            'Original URL:': 'Link',
            'Original posting date:': '2001-01-01 00:00 UTC',
            'Original site name:': '_test_source_name'})

    def test_multiview(self):
        """Test the page for marking duplicate records."""
        db.put(Person(
            key_name='haiti:test.google.com/person.111',
            subdomain='haiti',
            author_name='_author_name_1',
            author_email='_author_email_1',
            author_phone='_author_phone_1',
            entry_date=datetime.datetime.now(),
            first_name='_first_name_1',
            last_name='_last_name_1',
            sex='male',
            date_of_birth='1970-01-01',
            age='31-41',
        ))
        db.put(Person(
            key_name='haiti:test.google.com/person.222',
            subdomain='haiti',
            author_name='_author_name_2',
            author_email='_author_email_2',
            author_phone='_author_phone_2',
            entry_date=datetime.datetime.now(),
            first_name='_first_name_2',
            last_name='_last_name_2',
            sex='male',
            date_of_birth='1970-02-02',
            age='32-42',
        ))
        db.put(Person(
            key_name='haiti:test.google.com/person.333',
            subdomain='haiti',
            author_name='_author_name_3',
            author_email='_author_email_3',
            author_phone='_author_phone_3',
            entry_date=datetime.datetime.now(),
            first_name='_first_name_3',
            last_name='_last_name_3',
            sex='male',
            date_of_birth='1970-03-03',
            age='33-43',
        ))

        # All three records should appear on the multiview page.
        doc = self.go('/multiview?subdomain=haiti' +
                      '&id1=test.google.com/person.111' +
                      '&id2=test.google.com/person.222' +
                      '&id3=test.google.com/person.333')
        assert '_first_name_1' in doc.content
        assert '_first_name_2' in doc.content
        assert '_first_name_3' in doc.content
        assert '31-41' in doc.content
        assert '32-42' in doc.content
        assert '33-43' in doc.content

        # Mark all three as duplicates.
        button = doc.firsttag('input', value='Yes, these are the same person')
        doc = self.s.submit(button, text='duplicate test', author_name='foo')

        # We should arrive back at the first record, with two duplicate notes.
        assert self.s.status == 200
        assert 'id=test.google.com%2Fperson.111' in self.s.url
        assert 'Possible duplicates' in doc.content
        assert '_first_name_2 _last_name_2' in doc.content
        assert '_first_name_3 _last_name_3' in doc.content

        # Ask for detailed information on the duplicate markings.
        doc = self.s.follow('Show who marked these duplicates')
        assert '_first_name_1' in doc.content
        notes = doc.all('div', class_='view note')
        assert 'Posted by foo' in notes[0].text
        assert 'duplicate test' in notes[0].text
        assert ('This record is a duplicate of test.google.com/person.222' in
                notes[0].text)
        assert 'Posted by foo' in notes[1].text
        assert 'duplicate test' in notes[1].text
        assert ('This record is a duplicate of test.google.com/person.333' in
                notes[1].text)

    def test_reveal(self):
        """Test the hiding and revealing of contact information in the UI."""
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            subdomain='haiti',
            author_name='_reveal_author_name',
            author_email='_reveal_author_email',
            author_phone='_reveal_author_phone',
            entry_date=datetime.datetime.now(),
            first_name='_reveal_first_name',
            last_name='_reveal_last_name',
            sex='male',
            date_of_birth='1970-01-01',
            age='30-40',
        ))
        db.put(Note(
            key_name='haiti:test.google.com/note.456',
            subdomain='haiti',
            author_name='_reveal_note_author_name',
            author_email='_reveal_note_author_email',
            author_phone='_reveal_note_author_phone',
            entry_date=datetime.datetime.now(),
            email_of_found_person='_reveal_email_of_found_person',
            phone_of_found_person='_reveal_phone_of_found_person',
            person_record_id='test.google.com/person.123',
        ))

        # All contact information should be hidden by default.
        doc = self.go('/view?subdomain=haiti&id=test.google.com/person.123')
        assert '_reveal_author_email' not in doc.content
        assert '_reveal_author_phone' not in doc.content
        assert '_reveal_note_author_email' not in doc.content
        assert '_reveal_note_author_phone' not in doc.content
        assert '_reveal_email_of_found_person' not in doc.content
        assert '_reveal_phone_of_found_person' not in doc.content

        # An invalid signature should not work.
        doc = self.go('/view?subdomain=haiti&id=test.google.com/person.123' +
                      '&signature=abc.1999999999')
        assert '_reveal_author_email' not in doc.content
        assert '_reveal_author_phone' not in doc.content
        assert '_reveal_note_author_email' not in doc.content
        assert '_reveal_note_author_phone' not in doc.content
        assert '_reveal_email_of_found_person' not in doc.content
        assert '_reveal_phone_of_found_person' not in doc.content

        # An expired signature should not work.
        signature = reveal.sign(u'view:test.google.com/person.123', -10)
        doc = self.go('/view?subdomain=haiti&id=test.google.com/person.123' +
                      '&signature=' + signature)
        assert '_reveal_author_email' not in doc.content
        assert '_reveal_author_phone' not in doc.content
        assert '_reveal_note_author_email' not in doc.content
        assert '_reveal_note_author_phone' not in doc.content
        assert '_reveal_email_of_found_person' not in doc.content
        assert '_reveal_phone_of_found_person' not in doc.content

        # Now supply a valid revelation signature.
        signature = reveal.sign(u'view:test.google.com/person.123', 10)
        doc = self.go('/view?subdomain=haiti&id=test.google.com/person.123' +
                      '&signature=' + signature)
        assert '_reveal_author_email' in doc.content
        assert '_reveal_author_phone' in doc.content
        assert '_reveal_note_author_email' in doc.content
        assert '_reveal_note_author_phone' in doc.content
        assert '_reveal_email_of_found_person' in doc.content
        assert '_reveal_phone_of_found_person' in doc.content

        # Start over.
        doc = self.go('/view?subdomain=haiti&id=test.google.com/person.123')
        assert '_reveal_author_email' not in doc.content
        assert '_reveal_author_phone' not in doc.content
        assert '_reveal_note_author_email' not in doc.content
        assert '_reveal_note_author_phone' not in doc.content
        assert '_reveal_email_of_found_person' not in doc.content
        assert '_reveal_phone_of_found_person' not in doc.content

        # This time, click through the reveal page flow to get the signature.
        doc = self.s.follow('(click to reveal)')
        doc = self.s.follow('sign in')
        button = doc.firsttag('input', value='Login')
        doc = self.s.submit(button)
        button = doc.firsttag('input', value='Proceed')
        doc = self.s.submit(button)
        assert '_reveal_author_email' in doc.content
        assert '_reveal_author_phone' in doc.content
        assert '_reveal_note_author_email' in doc.content
        assert '_reveal_note_author_phone' in doc.content
        assert '_reveal_email_of_found_person' in doc.content
        assert '_reveal_phone_of_found_person' in doc.content

        # All contact information should be hidden on the multiview page, too.
        doc = self.go('/multiview?subdomain=haiti' +
                      '&id1=test.google.com/person.123')
        assert '_reveal_author_email' not in doc.content
        assert '_reveal_author_phone' not in doc.content
        assert '_reveal_note_author_email' not in doc.content
        assert '_reveal_note_author_phone' not in doc.content
        assert '_reveal_email_of_found_person' not in doc.content
        assert '_reveal_phone_of_found_person' not in doc.content

        # Now supply a valid revelation signature.
        signature = reveal.sign(u'multiview:test.google.com/person.123', 10)
        doc = self.go('/multiview?subdomain=haiti' +
                      '&id1=test.google.com/person.123' +
                      '&signature=' + signature)
        assert '_reveal_author_email' in doc.content
        assert '_reveal_author_phone' in doc.content
        # Notes are not shown on the multiview page.

    def test_note_status(self):
        """Test the posting and viewing of the note status field in the UI."""
        status_class = re.compile(r'\bstatus\b')

        # Check that the right status options appear on the create page.
        doc = self.go('/create?subdomain=haiti&role=provide')
        note = doc.first(**{'class': 'note input'})
        options = note.first('select', name='status').all('option')
        assert len(options) == len(NOTE_STATUS_OPTIONS)
        for option, text in zip(options, NOTE_STATUS_OPTIONS):
            assert text in option.attrs['value']

        # Create a record with no status and get the new record's ID.
        form = doc.first('form')
        doc = self.s.submit(form,
                            first_name='_test_first',
                            last_name='_test_last',
                            author_name='_test_author',
                            text='_test_text')
        view_url = self.s.url

        # Check that the right status options appear on the view page.
        doc = self.s.go(view_url)
        note = doc.first(**{'class': 'note input'})
        options = note.first('select', name='status').all('option')
        assert len(options) == len(NOTE_STATUS_OPTIONS)
        for option, text in zip(options, NOTE_STATUS_OPTIONS):
            assert text in option.attrs['value']

        # Set the status in a note and check that it appears on the view page.
        form = doc.first('form')
        self.s.submit(form, author_name='_test_author2', text='_test_text',
                                    status='believed_alive')
        doc = self.s.go(view_url)
        note = doc.last(**{'class': 'view note'})
        assert 'believed_alive' in note.content
        assert 'believed_dead' not in note.content

        # Set status to is_note_author, but don't check found.
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

    def test_api_write_pfif_1_2(self):
        """Post a single entry as PFIF 1.2 using the upload API."""
        data = get_test_data('test.pfif-1.2.xml')
        self.go('/api/write?subdomain=haiti&key=test_key',
                data=data, type='application/xml')
        person = Person.get('haiti', 'test.google.com/person.21009')
        assert person.first_name == u'_test_first_name'
        assert person.last_name == u'_test_last_name'
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
        assert person.entry_date.year == datetime.datetime.now().year
        assert not person.found

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
        assert note.person_record_id == u'test.google.com/person.21009'
        assert note.text == u'_test_text'
        assert note.source_date == None
        # Current date should replace the provided entry_date.
        assert note.entry_date.year == datetime.datetime.now().year
        assert note.found
        assert note.status == u'believed_alive'
        assert note.linked_person_record_id == u'test.google.com/person.999'

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
        assert note.source_date == datetime.datetime(2010, 1, 17, 11, 13, 17)
        # Current date should replace the provided entry_date.
        assert note.entry_date.year == datetime.datetime.now().year
        assert not note.found
        assert not note.status
        assert not note.linked_person_record_id

    def test_api_write_pfif_1_2_note(self):
        """Post a single note-only entry as PFIF 1.2 using the upload API."""
        # Create person records that the notes will attach to.
        Person(key_name='haiti:test.google.com/person.21009',
               subdomain='haiti',
               first_name='_test_first_name_1',
               last_name='_test_last_name_1',
               entry_date=datetime.datetime(2001, 1, 1, 1, 1, 1)).put()
        Person(key_name='haiti:test.google.com/person.21010',
               subdomain='haiti',
               first_name='_test_first_name_2',
               last_name='_test_last_name_2',
               entry_date=datetime.datetime(2002, 2, 2, 2, 2, 2)).put()

        data = get_test_data('test.pfif-1.2-note.xml')
        self.go('/api/write?subdomain=haiti&key=test_key',
                data=data, type='application/xml')

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
        assert note.source_date == None
        # Current date should replace the provided entry_date.
        assert note.entry_date.year == datetime.datetime.now().year
        assert note.found
        assert note.status == u'believed_alive'
        assert note.linked_person_record_id == u'test.google.com/person.999'

        # Found flag should have propagated to the Person.
        assert person.found

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
        assert note.source_date == datetime.datetime(2010, 1, 17, 11, 13, 17)
        # Current date should replace the provided entry_date.
        assert note.entry_date.year == datetime.datetime.now().year
        assert not note.found
        assert not note.status
        assert not note.linked_person_record_id

        # Found flag should have propagated to the Person.
        assert not person.found

    def test_api_write_pfif_1_1(self):
        """Post a single entry as PFIF 1.1 using the upload API."""
        data = get_test_data('test.pfif-1.1.xml')
        self.go('/api/write?subdomain=haiti&key=test_key',
                data=data, type='application/xml')
        person = Person.get('haiti', 'test.google.com/person.21009')
        assert person.first_name == u'_test_first_name'
        assert person.last_name == u'_test_last_name'
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
        assert person.entry_date.year == datetime.datetime.now().year

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
        assert note.source_date == None
        # Current date should replace the provided entry_date.
        assert note.entry_date.year == datetime.datetime.now().year
        assert note.found

        note = notes[1]
        assert note.author_name == u'inna-testing'
        assert note.author_email == u'inna-testing@gmail.com'
        assert note.author_phone == u'inna-testing-number'
        assert note.email_of_found_person == u''
        assert note.phone_of_found_person == u''
        assert note.last_known_location == u'19.16592425362802 -71.9384765625'
        assert note.record_id == u'test.google.com/note.31095'
        assert note.text == u'new comment - testing'
        assert note.source_date == datetime.datetime(2010, 1, 17, 11, 13, 17)
        # Current date should replace the provided entry_date.
        assert note.entry_date.year == datetime.datetime.now().year
        assert not note.found

    def test_api_write_bad_key(self):
        """Attempt to post an entry with an invalid API key."""
        data = get_test_data('test.pfif-1.2.xml')
        self.go('/api/write?subdomain=haiti&key=bad_key',
                data=data, type='application/xml')
        assert self.s.status == 403

    def test_api_write_empty_record(self):
        """Verify that empty entries are accepted."""
        doc = self.go('/api/write?subdomain=haiti&key=test_key',
                data='''
<pfif xmlns="http://zesty.ca/pfif/1.2">
  <person>
    <person_record_id>test.google.com/person.empty</person_record_id>
  </person>
</pfif>''', type='application/xml')

        # The Person record should have been accepted.
        person_status = doc.first('status:write')
        assert person_status.first('status:written').text == '1'

        # An empty Person entity should be in the datastore.
        person = Person.get('haiti', 'test.google.com/person.empty')

    def test_api_write_wrong_domain(self):
        """Attempt to post an entry with a domain that doesn't match the key."""
        data = get_test_data('test.pfif-1.2.xml')
        doc = self.go('/api/write?subdomain=haiti&key=other_key',
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

    def test_api_read(self):
        """Fetch a single record as PFIF (1.1 and 1.2) using the read API."""
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            subdomain='haiti',
            entry_date=datetime.datetime.now(),
            author_email='_read_author_email',
            author_name='_read_author_name',
            author_phone='_read_author_phone',
            first_name='_read_first_name',
            last_name='_read_last_name',
            sex='female',
            date_of_birth='1970-01-01',
            age='40-50',
            home_city='_read_home_city',
            home_neighborhood='_read_home_neighborhood',
            home_state='_read_home_state',
            home_street='_read_home_street',
            home_postal_code='_read_home_postal_code',
            home_country='_read_home_country',
            other='_read_other & < > "',
            photo_url='_read_photo_url',
            source_name='_read_source_name',
            source_url='_read_source_url',
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6),
        ))
        db.put(Note(
            key_name='haiti:test.google.com/note.456',
            subdomain='haiti',
            author_email='_read_author_email',
            author_name='_read_author_name',
            author_phone='_read_author_phone',
            email_of_found_person='_read_email_of_found_person',
            last_known_location='_read_last_known_location',
            person_record_id='test.google.com/person.123',
            linked_person_record_id='test.google.com/person.888',
            phone_of_found_person='_read_phone_of_found_person',
            text='_read_text',
            source_date=datetime.datetime(2005, 5, 5, 5, 5, 5),
            entry_date=datetime.datetime(2006, 6, 6, 6, 6, 6),
            found=True,
            status='believed_missing'
        ))

        # Fetch a PFIF 1.1 document.
        # Note that author_email, author_phone, email_of_found_person, and
        # phone_of_found_person are omitted intentionally (see
        # utils.filter_sensitive_fields).
        doc = self.go('/api/read?subdomain=haiti' +
                      '&id=test.google.com/person.123&version=1.1')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
    <pfif:author_name>_read_author_name</pfif:author_name>
    <pfif:source_name>_read_source_name</pfif:source_name>
    <pfif:source_date>2001-02-03T04:05:06Z</pfif:source_date>
    <pfif:source_url>_read_source_url</pfif:source_url>
    <pfif:first_name>_read_first_name</pfif:first_name>
    <pfif:last_name>_read_last_name</pfif:last_name>
    <pfif:home_city>_read_home_city</pfif:home_city>
    <pfif:home_state>_read_home_state</pfif:home_state>
    <pfif:home_neighborhood>_read_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_street>_read_home_street</pfif:home_street>
    <pfif:home_zip>_read_home_postal_code</pfif:home_zip>
    <pfif:photo_url>_read_photo_url</pfif:photo_url>
    <pfif:other>_read_other &amp; &lt; &gt; "</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
      <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
      <pfif:author_name>_read_author_name</pfif:author_name>
      <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:last_known_location>_read_last_known_location</pfif:last_known_location>
      <pfif:text>_read_text</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>
''', doc.content)

        # Fetch a PFIF 1.2 document.
        # Note that date_of_birth, author_email, author_phone,
        # email_of_found_person, and phone_of_found_person are omitted
        # intentionally (see utils.filter_sensitive_fields).
        doc = self.go('/api/read?subdomain=haiti' +
                      '&id=test.google.com/person.123&version=1.2')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
    <pfif:author_name>_read_author_name</pfif:author_name>
    <pfif:source_name>_read_source_name</pfif:source_name>
    <pfif:source_date>2001-02-03T04:05:06Z</pfif:source_date>
    <pfif:source_url>_read_source_url</pfif:source_url>
    <pfif:first_name>_read_first_name</pfif:first_name>
    <pfif:last_name>_read_last_name</pfif:last_name>
    <pfif:sex>female</pfif:sex>
    <pfif:age>40-50</pfif:age>
    <pfif:home_street>_read_home_street</pfif:home_street>
    <pfif:home_neighborhood>_read_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_city>_read_home_city</pfif:home_city>
    <pfif:home_state>_read_home_state</pfif:home_state>
    <pfif:home_postal_code>_read_home_postal_code</pfif:home_postal_code>
    <pfif:home_country>_read_home_country</pfif:home_country>
    <pfif:photo_url>_read_photo_url</pfif:photo_url>
    <pfif:other>_read_other &amp; &lt; &gt; "</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
      <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
      <pfif:author_name>_read_author_name</pfif:author_name>
      <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:status>believed_missing</pfif:status>
      <pfif:last_known_location>_read_last_known_location</pfif:last_known_location>
      <pfif:text>_read_text</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>
''', doc.content)

        # Verify that PFIF 1.2 is the default version.
        default_doc = self.go(
            '/api/read?subdomain=haiti&id=test.google.com/person.123')
        assert default_doc.content == doc.content

        # Fetch a PFIF 1.2 document, with full read authorization.
        doc = self.go('/api/read?subdomain=haiti&key=full_read_key' +
                      '&id=test.google.com/person.123&version=1.2')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
    <pfif:author_name>_read_author_name</pfif:author_name>
    <pfif:author_email>_read_author_email</pfif:author_email>
    <pfif:author_phone>_read_author_phone</pfif:author_phone>
    <pfif:source_name>_read_source_name</pfif:source_name>
    <pfif:source_date>2001-02-03T04:05:06Z</pfif:source_date>
    <pfif:source_url>_read_source_url</pfif:source_url>
    <pfif:first_name>_read_first_name</pfif:first_name>
    <pfif:last_name>_read_last_name</pfif:last_name>
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
    <pfif:other>_read_other &amp; &lt; &gt; "</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
      <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
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
''', doc.content)

    def test_read_key(self):
        """Verifies that when read_auth_key_required is set, an authorization
        key is required to read data from the API or feeds."""
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            subdomain='haiti',
            entry_date=datetime.datetime.now(),
            author_email='_read_author_email',
            author_name='_read_author_name',
            author_phone='_read_author_phone',
            first_name='_read_first_name',
            last_name='_read_last_name',
            sex='female',
            date_of_birth='1970-01-01',
            age='40-50',
            home_city='_read_home_city',
            home_neighborhood='_read_home_neighborhood',
            home_state='_read_home_state',
            home_street='_read_home_street',
            home_postal_code='_read_home_postal_code',
            home_country='_read_home_country',
            other='_read_other & < > "',
            photo_url='_read_photo_url',
            source_name='_read_source_name',
            source_url='_read_source_url',
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6),
        ))
        db.put(Note(
            key_name='haiti:test.google.com/note.456',
            subdomain='haiti',
            author_email='_read_author_email',
            author_name='_read_author_name',
            author_phone='_read_author_phone',
            email_of_found_person='_read_email_of_found_person',
            last_known_location='_read_last_known_location',
            person_record_id='test.google.com/person.123',
            linked_person_record_id='test.google.com/person.888',
            phone_of_found_person='_read_phone_of_found_person',
            text='_read_text',
            source_date=datetime.datetime(2005, 5, 5, 5, 5, 5),
            entry_date=datetime.datetime(2006, 6, 6, 6, 6, 6),
            found=True,
            status='believed_missing'
        ))

        config.set_for_subdomain('haiti', read_auth_key_required=True)
        try:
            # Fetch a PFIF 1.2 document from a domain that requires a read key.
            # Without an authorization key, the request should fail.
            doc = self.go('/api/read?subdomain=haiti' +
                          '&id=test.google.com/person.123&version=1.1')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a non-read authorization key, the request should fail.
            doc = self.go('/api/read?subdomain=haiti&key=test_key' +
                          '&id=test.google.com/person.123&version=1.1')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a valid read authorization key, the request should succeed.
            doc = self.go('/api/read?subdomain=haiti&key=read_key' +
                          '&id=test.google.com/person.123&version=1.2')
            assert '_read_first_name' in doc.content

            # Fetch the person feed from a domain that requires a read key.
            # Without an authorization key, the request should fail.
            doc = self.go('/feeds/person?subdomain=haiti')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a non-read authorization key, the request should fail.
            doc = self.go('/feeds/person?subdomain=haiti&key=test_key')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a valid read authorization key, the request should succeed.
            doc = self.go('/feeds/person?subdomain=haiti&key=read_key')
            assert '_read_author_name' in doc.content

            # Fetch the note feed from a domain that requires a read key.
            # Without an authorization key, the request should fail.
            doc = self.go('/feeds/note?subdomain=haiti')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a non-read authorization key, the request should fail.
            doc = self.go('/feeds/note?subdomain=haiti&key=test_key')
            assert self.s.status == 403
            assert 'Missing or invalid authorization key' in doc.content

            # With a valid read authorization key, the request should succeed.
            doc = self.go('/feeds/note?subdomain=haiti&key=read_key')
            assert '_read_text' in doc.content

        finally:
            config.set_for_subdomain('haiti', read_auth_key_required=False)


    def test_api_read_with_non_ascii(self):
        """Fetch a record containing non-ASCII characters using the read API.
        This tests both PFIF 1.1 and 1.2."""
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            subdomain='haiti',
            entry_date=datetime.datetime.now(),
            author_name=u'a with acute = \u00e1',
            source_name=u'c with cedilla = \u00e7',
            source_url=u'e with acute = \u00e9',
            first_name=u'greek alpha = \u03b1',
            last_name=u'hebrew alef = \u05d0'
        ))

        # Fetch a PFIF 1.1 document.
        doc = self.go('/api/read?subdomain=haiti' +
                      '&id=test.google.com/person.123&version=1.1')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
    <pfif:author_name>a with acute = \xc3\xa1</pfif:author_name>
    <pfif:source_name>c with cedilla = \xc3\xa7</pfif:source_name>
    <pfif:source_url>e with acute = \xc3\xa9</pfif:source_url>
    <pfif:first_name>greek alpha = \xce\xb1</pfif:first_name>
    <pfif:last_name>hebrew alef = \xd7\x90</pfif:last_name>
  </pfif:person>
</pfif:pfif>
''', doc.content)

        # Fetch a PFIF 1.2 document.
        doc = self.go('/api/read?subdomain=haiti' +
                      '&id=test.google.com/person.123&version=1.2')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
    <pfif:author_name>a with acute = \xc3\xa1</pfif:author_name>
    <pfif:source_name>c with cedilla = \xc3\xa7</pfif:source_name>
    <pfif:source_url>e with acute = \xc3\xa9</pfif:source_url>
    <pfif:first_name>greek alpha = \xce\xb1</pfif:first_name>
    <pfif:last_name>hebrew alef = \xd7\x90</pfif:last_name>
  </pfif:person>
</pfif:pfif>
''', doc.content)

        # Verify that PFIF 1.2 is the default version.
        default_doc = self.go(
            '/api/read?subdomain=haiti&id=test.google.com/person.123')
        assert default_doc.content == doc.content

    def test_person_feed(self):
        """Fetch a single person using the PFIF Atom feed."""
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            subdomain='haiti',
            entry_date=datetime.datetime.now(),
            author_email='_feed_author_email',
            author_name='_feed_author_name',
            author_phone='_feed_author_phone',
            first_name='_feed_first_name',
            last_name='_feed_last_name',
            sex='male',
            date_of_birth='1975',
            age='30-40',
            home_street='_feed_home_street',
            home_neighborhood='_feed_home_neighborhood',
            home_city='_feed_home_city',
            home_state='_feed_home_state',
            home_postal_code='_feed_home_postal_code',
            home_country='_feed_home_country',
            other='_feed_other & < > "',
            photo_url='_feed_photo_url',
            source_name='_feed_source_name',
            source_url='_feed_source_url',
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6),
        ))
        db.put(Note(
            key_name='haiti:test.google.com/note.456',
            subdomain='haiti',
            author_email='_feed_author_email',
            author_name='_feed_author_name',
            author_phone='_feed_author_phone',
            email_of_found_person='_feed_email_of_found_person',
            last_known_location='_feed_last_known_location',
            person_record_id='test.google.com/person.123',
            linked_person_record_id='test.google.com/person.888',
            phone_of_found_person='_feed_phone_of_found_person',
            text='_feed_text',
            source_date=datetime.datetime(2005, 5, 5, 5, 5, 5),
            entry_date=datetime.datetime(2006, 6, 6, 6, 6, 6),
            found=True,
            status='is_note_author'
        ))

        # Feeds use PFIF 1.2.
        # Note that date_of_birth, author_email, author_phone,
        # email_of_found_person, and phone_of_found_person are omitted
        # intentionally (see utils.filter_sensitive_fields).
        doc = self.go('/feeds/person?subdomain=haiti')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.2">
  <id>http://%s/feeds/person\?subdomain=haiti</id>
  <title>%s</title>
  <updated>....-..-..T..:..:..Z</updated>
  <link rel="self">http://%s/feeds/person\?subdomain=haiti</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
      <pfif:author_name>_feed_author_name</pfif:author_name>
      <pfif:source_name>_feed_source_name</pfif:source_name>
      <pfif:source_date>2001-02-03T04:05:06Z</pfif:source_date>
      <pfif:source_url>_feed_source_url</pfif:source_url>
      <pfif:first_name>_feed_first_name</pfif:first_name>
      <pfif:last_name>_feed_last_name</pfif:last_name>
      <pfif:sex>male</pfif:sex>
      <pfif:age>30-40</pfif:age>
      <pfif:home_street>_feed_home_street</pfif:home_street>
      <pfif:home_neighborhood>_feed_home_neighborhood</pfif:home_neighborhood>
      <pfif:home_city>_feed_home_city</pfif:home_city>
      <pfif:home_state>_feed_home_state</pfif:home_state>
      <pfif:home_postal_code>_feed_home_postal_code</pfif:home_postal_code>
      <pfif:home_country>_feed_home_country</pfif:home_country>
      <pfif:photo_url>_feed_photo_url</pfif:photo_url>
      <pfif:other>_feed_other &amp; &lt; &gt; "</pfif:other>
      <pfif:note>
        <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
        <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
        <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
        <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
        <pfif:author_name>_feed_author_name</pfif:author_name>
        <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
        <pfif:found>true</pfif:found>
        <pfif:status>is_note_author</pfif:status>
        <pfif:last_known_location>_feed_last_known_location</pfif:last_known_location>
        <pfif:text>_feed_text</pfif:text>
      </pfif:note>
    </pfif:person>
    <id>pfif:test.google.com/person.123</id>
    <title>_feed_first_name _feed_last_name</title>
    <author>
      <name>_feed_author_name</name>
    </author>
    <updated>2001-02-03T04:05:06Z</updated>
    <source>
      <title>%s</title>
    </source>
    <content>_feed_first_name _feed_last_name</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport), doc.content)

        # Test the omit_notes parameter.
        doc = self.go('/feeds/person?subdomain=haiti&omit_notes=yes')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.2">
  <id>http://%s/feeds/person\?subdomain=haiti&amp;omit_notes=yes</id>
  <title>%s</title>
  <updated>....-..-..T..:..:..Z</updated>
  <link rel="self">http://%s/feeds/person\?subdomain=haiti&amp;omit_notes=yes</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
      <pfif:author_name>_feed_author_name</pfif:author_name>
      <pfif:source_name>_feed_source_name</pfif:source_name>
      <pfif:source_date>2001-02-03T04:05:06Z</pfif:source_date>
      <pfif:source_url>_feed_source_url</pfif:source_url>
      <pfif:first_name>_feed_first_name</pfif:first_name>
      <pfif:last_name>_feed_last_name</pfif:last_name>
      <pfif:sex>male</pfif:sex>
      <pfif:age>30-40</pfif:age>
      <pfif:home_street>_feed_home_street</pfif:home_street>
      <pfif:home_neighborhood>_feed_home_neighborhood</pfif:home_neighborhood>
      <pfif:home_city>_feed_home_city</pfif:home_city>
      <pfif:home_state>_feed_home_state</pfif:home_state>
      <pfif:home_postal_code>_feed_home_postal_code</pfif:home_postal_code>
      <pfif:home_country>_feed_home_country</pfif:home_country>
      <pfif:photo_url>_feed_photo_url</pfif:photo_url>
      <pfif:other>_feed_other &amp; &lt; &gt; "</pfif:other>
    </pfif:person>
    <id>pfif:test.google.com/person.123</id>
    <title>_feed_first_name _feed_last_name</title>
    <author>
      <name>_feed_author_name</name>
    </author>
    <updated>2001-02-03T04:05:06Z</updated>
    <source>
      <title>%s</title>
    </source>
    <content>_feed_first_name _feed_last_name</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport), doc.content)

        # Fetch the entry, with full read authorization.
        doc = self.go('/feeds/person?subdomain=haiti&key=full_read_key')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.2">
  <id>http://%s/feeds/person\?subdomain=haiti&amp;key=full_read_key</id>
  <title>%s</title>
  <updated>....-..-..T..:..:..Z</updated>
  <link rel="self">http://%s/feeds/person\?subdomain=haiti&amp;key=full_read_key</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
      <pfif:author_name>_feed_author_name</pfif:author_name>
      <pfif:author_email>_feed_author_email</pfif:author_email>
      <pfif:author_phone>_feed_author_phone</pfif:author_phone>
      <pfif:source_name>_feed_source_name</pfif:source_name>
      <pfif:source_date>2001-02-03T04:05:06Z</pfif:source_date>
      <pfif:source_url>_feed_source_url</pfif:source_url>
      <pfif:first_name>_feed_first_name</pfif:first_name>
      <pfif:last_name>_feed_last_name</pfif:last_name>
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
      <pfif:other>_feed_other &amp; &lt; &gt; "</pfif:other>
      <pfif:note>
        <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
        <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
        <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
        <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
        <pfif:author_name>_feed_author_name</pfif:author_name>
        <pfif:author_email>_feed_author_email</pfif:author_email>
        <pfif:author_phone>_feed_author_phone</pfif:author_phone>
        <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
        <pfif:found>true</pfif:found>
        <pfif:status>is_note_author</pfif:status>
        <pfif:email_of_found_person>_feed_email_of_found_person</pfif:email_of_found_person>
        <pfif:phone_of_found_person>_feed_phone_of_found_person</pfif:phone_of_found_person>
        <pfif:last_known_location>_feed_last_known_location</pfif:last_known_location>
        <pfif:text>_feed_text</pfif:text>
      </pfif:note>
    </pfif:person>
    <id>pfif:test.google.com/person.123</id>
    <title>_feed_first_name _feed_last_name</title>
    <author>
      <name>_feed_author_name</name>
      <email>_feed_author_email</email>
    </author>
    <updated>2001-02-03T04:05:06Z</updated>
    <source>
      <title>%s</title>
    </source>
    <content>_feed_first_name _feed_last_name</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport), doc.content)


    def test_note_feed(self):
        """Fetch a single note using the PFIF Atom feed."""
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            subdomain='haiti',
            entry_date=datetime.datetime.now(),
            first_name='_feed_first_name',
            last_name='_feed_last_name',
        ))
        db.put(Note(
            key_name='haiti:test.google.com/note.456',
            subdomain='haiti',
            person_record_id='test.google.com/person.123',
            linked_person_record_id='test.google.com/person.888',
            author_email='_feed_author_email',
            author_name='_feed_author_name',
            author_phone='_feed_author_phone',
            email_of_found_person='_feed_email_of_found_person',
            last_known_location='_feed_last_known_location',
            phone_of_found_person='_feed_phone_of_found_person',
            text='_feed_text',
            source_date=datetime.datetime(2005, 5, 5, 5, 5, 5),
            entry_date=datetime.datetime(2006, 6, 6, 6, 6, 6),
            found=True,
            status='believed_dead'
        ))

        # Feeds use PFIF 1.2.
        # Note that author_email, author_phone, email_of_found_person, and
        # phone_of_found_person are omitted intentionally (see
        # utils.filter_sensitive_fields).
        doc = self.go('/feeds/note?subdomain=haiti')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.2">
  <id>http://%s/feeds/note\?subdomain=haiti</id>
  <title>%s</title>
  <updated>....-..-..T..:..:..Z</updated>
  <link rel="self">http://%s/feeds/note\?subdomain=haiti</link>
  <entry>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.456</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.888</pfif:linked_person_record_id>
      <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
      <pfif:author_name>_feed_author_name</pfif:author_name>
      <pfif:source_date>2005-05-05T05:05:05Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:status>believed_dead</pfif:status>
      <pfif:last_known_location>_feed_last_known_location</pfif:last_known_location>
      <pfif:text>_feed_text</pfif:text>
    </pfif:note>
    <id>pfif:test.google.com/note.456</id>
    <title>_feed_text</title>
    <author>
      <name>_feed_author_name</name>
    </author>
    <updated>2005-05-05T05:05:05Z</updated>
    <content>_feed_text</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport), doc.content)

    def test_person_feed_with_bad_chars(self):
        """Fetch a person whose fields contain characters that are not
        legally representable in XML, using the PFIF Atom feed."""
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            subdomain='haiti',
            entry_date=datetime.datetime.now(),
            author_name=u'illegal character (\x01)',
            first_name=u'illegal character (\x1a)',
            last_name=u'illegal character (\ud800)',
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6)
        ))

        # Note that author_email, author_phone, email_of_found_person, and
        # phone_of_found_person are omitted intentionally (see
        # utils.filter_sensitive_fields).
        doc = self.go('/feeds/person?subdomain=haiti')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.2">
  <id>http://%s/feeds/person\?subdomain=haiti</id>
  <title>%s</title>
  <updated>....-..-..T..:..:..Z</updated>
  <link rel="self">http://%s/feeds/person\?subdomain=haiti</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
      <pfif:author_name>illegal character \(\)</pfif:author_name>
      <pfif:source_date>2001-02-03T04:05:06Z</pfif:source_date>
      <pfif:first_name>illegal character \(\)</pfif:first_name>
      <pfif:last_name>illegal character \(\)</pfif:last_name>
    </pfif:person>
    <id>pfif:test.google.com/person.123</id>
    <title>illegal character \(\) illegal character \(\)</title>
    <author>
      <name>illegal character \(\)</name>
    </author>
    <updated>2001-02-03T04:05:06Z</updated>
    <source>
      <title>%s</title>
    </source>
    <content>illegal character \(\) illegal character \(\)</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport), doc.content)

    def test_person_feed_with_non_ascii(self):
        """Fetch a person whose fields contain non-ASCII characters,
        using the PFIF Atom feed."""
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            subdomain='haiti',
            entry_date=datetime.datetime.now(),
            author_name=u'a with acute = \u00e1',
            source_name=u'c with cedilla = \u00e7',
            source_url=u'e with acute = \u00e9',
            first_name=u'greek alpha = \u03b1',
            last_name=u'hebrew alef = \u05d0',
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6)
        ))

        # Note that author_email, author_phone, email_of_found_person, and
        # phone_of_found_person are omitted intentionally (see
        # utils.filter_sensitive_fields).
        doc = self.go('/feeds/person?subdomain=haiti')
        assert re.match(r'''<\?xml version="1.0" encoding="UTF-8"\?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:pfif="http://zesty.ca/pfif/1.2">
  <id>http://%s/feeds/person\?subdomain=haiti</id>
  <title>%s</title>
  <updated>....-..-..T..:..:..Z</updated>
  <link rel="self">http://%s/feeds/person\?subdomain=haiti</link>
  <entry>
    <pfif:person>
      <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
      <pfif:entry_date>....-..-..T..:..:..Z</pfif:entry_date>
      <pfif:author_name>a with acute = \xc3\xa1</pfif:author_name>
      <pfif:source_name>c with cedilla = \xc3\xa7</pfif:source_name>
      <pfif:source_date>2001-02-03T04:05:06Z</pfif:source_date>
      <pfif:source_url>e with acute = \xc3\xa9</pfif:source_url>
      <pfif:first_name>greek alpha = \xce\xb1</pfif:first_name>
      <pfif:last_name>hebrew alef = \xd7\x90</pfif:last_name>
    </pfif:person>
    <id>pfif:test.google.com/person.123</id>
    <title>greek alpha = \xce\xb1 hebrew alef = \xd7\x90</title>
    <author>
      <name>a with acute = \xc3\xa1</name>
    </author>
    <updated>2001-02-03T04:05:06Z</updated>
    <source>
      <title>%s</title>
    </source>
    <content>greek alpha = \xce\xb1 hebrew alef = \xd7\x90</content>
  </entry>
</feed>
''' % (self.hostport, self.hostport, self.hostport, self.hostport), doc.content)

    def test_person_feed_parameters(self):
        """Test the max_results, skip, and min_entry_date parameters."""
        db.put([Person(
            key_name='haiti:test.google.com/person.%d' % i,
            subdomain='haiti',
            entry_date=datetime.datetime(2000, 1, 1, i, i, i),
            first_name='first.%d' % i,
            last_name='last.%d' % i
        ) for i in range(1, 21)])  # Create 20 persons.

        def assert_ids(*ids):
            person_ids = re.findall(r'record_id>test.google.com/person.(\d+)',
                                    self.s.doc.content)
            assert map(int, person_ids) == list(ids)

        # Should get records in reverse chronological order by default.
        doc = self.go('/feeds/person?subdomain=haiti')
        assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12, 11)

        # Fewer results.
        doc = self.go('/feeds/person?subdomain=haiti&max_results=1')
        assert_ids(20)
        doc = self.go('/feeds/person?subdomain=haiti&max_results=9')
        assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12)

        # More results.
        doc = self.go('/feeds/person?subdomain=haiti&max_results=12')
        assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9)

        # Skip some results.
        doc = self.go('/feeds/person?subdomain=haiti&skip=12&max_results=5')
        assert_ids(8, 7, 6, 5, 4)

        # Should get records in forward chronological order with min_entry_date.
        doc = self.go('/feeds/person?subdomain=haiti' +
                      '&min_entry_date=2000-01-01T18:18:18Z')
        assert_ids(18, 19, 20)

        doc = self.go('/feeds/person?subdomain=haiti' +
                      '&min_entry_date=2000-01-01T03:03:03Z')
        assert_ids(3, 4, 5, 6, 7, 8, 9, 10, 11, 12)

        doc = self.go('/feeds/person?subdomain=haiti' +
                      '&min_entry_date=2000-01-01T03:03:04Z')
        assert_ids(4, 5, 6, 7, 8, 9, 10, 11, 12, 13)

    def test_note_feed_parameters(self):
        """Test the max_results, skip, min_entry_date, and person_record_id
        parameters."""
        Note.entry_date.auto_now = False  # Tests will set entry_date.
        try:
            entities = []
            for i in range(1, 3):  # Create person.1 and person.2.
                entities.append(Person(
                    key_name='haiti:test.google.com/person.%d' % i,
                    subdomain='haiti',
                    entry_date=datetime.datetime(2000, 1, 1, i, i, i),
                    first_name='first',
                    last_name='last'
                ))
            for i in range(1, 6):  # Create notes 1-5 on person.1.
                entities.append(Note(
                    key_name='haiti:test.google.com/note.%d' % i,
                    subdomain='haiti',
                    person_record_id='test.google.com/person.1',
                    entry_date=datetime.datetime(2000, 1, 1, i, i, i)
                ))
            for i in range(6, 18):  # Create notes 6-17 on person.2.
                entities.append(Note(
                    key_name='haiti:test.google.com/note.%d' % i,
                    subdomain='haiti',
                    person_record_id='test.google.com/person.2',
                    entry_date=datetime.datetime(2000, 1, 1, i, i, i)
                ))
            for i in range(18, 21):  # Create notes 18-20 on person.1.
                entities.append(Note(
                    key_name='haiti:test.google.com/note.%d' % i,
                    subdomain='haiti',
                    person_record_id='test.google.com/person.1',
                    entry_date=datetime.datetime(2000, 1, 1, i, i, i)
                ))
            db.put(entities)

            def assert_ids(*ids):
                note_ids = re.findall(r'record_id>test.google.com/note.(\d+)',
                                      self.s.doc.content)
                assert map(int, note_ids) == list(ids)

            # Should get records in reverse chronological order by default.
            doc = self.go('/feeds/note?subdomain=haiti')
            assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12, 11)

            # Fewer results.
            doc = self.go('/feeds/note?subdomain=haiti&max_results=1')
            assert_ids(20)
            doc = self.go('/feeds/note?subdomain=haiti&max_results=9')
            assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12)

            # More results.
            doc = self.go('/feeds/note?subdomain=haiti&max_results=12')
            assert_ids(20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9)

            # Skip some results.
            doc = self.go('/feeds/note?subdomain=haiti&skip=12&max_results=5')
            assert_ids(8, 7, 6, 5, 4)

            # Should get records in forward chronological order.
            doc = self.go('/feeds/note?subdomain=haiti' +
                          '&min_entry_date=2000-01-01T18:18:18Z')
            assert_ids(18, 19, 20)

            doc = self.go('/feeds/note?subdomain=haiti' +
                          '&min_entry_date=2000-01-01T03:03:03Z')
            assert_ids(3, 4, 5, 6, 7, 8, 9, 10, 11, 12)

            doc = self.go('/feeds/note?subdomain=haiti' +
                          '&min_entry_date=2000-01-01T03:03:04Z')
            assert_ids(4, 5, 6, 7, 8, 9, 10, 11, 12, 13)

            # Filter by person_record_id.
            doc = self.go('/feeds/note?subdomain=haiti' +
                          '&person_record_id=test.google.com/person.1')
            assert_ids(20, 19, 18, 5, 4, 3, 2, 1)

            doc = self.go('/feeds/note?subdomain=haiti' +
                          '&person_record_id=test.google.com/person.2')
            assert_ids(17, 16, 15, 14, 13, 12, 11, 10, 9, 8)

            doc = self.go('/feeds/note?subdomain=haiti' +
                          '&person_record_id=test.google.com/person.2' +
                          '&max_results=11')
            assert_ids(17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7)

            doc = self.go('/feeds/note?subdomain=haiti' +
                          '&person_record_id=test.google.com/person.1' +
                          '&min_entry_date=2000-01-01T03:03:03Z')
            assert_ids(3, 4, 5, 18, 19, 20)

            doc = self.go('/feeds/note?subdomain=haiti' +
                          '&person_record_id=test.google.com/person.1' +
                          '&min_entry_date=2000-01-01T03:03:04Z')
            assert_ids(4, 5, 18, 19, 20)

            doc = self.go('/feeds/note?subdomain=haiti' +
                          '&person_record_id=test.google.com/person.2' +
                          '&min_entry_date=2000-01-01T06:06:06Z')
            assert_ids(6, 7, 8, 9, 10, 11, 12, 13, 14, 15)

        finally:
            Note.entry_date.auto_now = True  # Restore Note.entry_date to normal.

    def test_api_read_status(self):
        """Test the reading of the note status field at /api/read and /feeds."""

        # A missing status should not appear as a tag.
        db.put(Person(
            key_name='haiti:test.google.com/person.1001',
            subdomain='haiti',
            entry_date=datetime.datetime.now(),
            first_name='_status_first_name',
            last_name='_status_last_name',
            author_name='_status_author_name'
        ))
        doc = self.go('/api/read?subdomain=haiti' +
                      '&id=test.google.com/person.1001')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/feeds/person?subdomain=haiti')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/feeds/note?subdomain=haiti')
        assert '<pfif:status>' not in doc.content

        # An unspecified status should not appear as a tag.
        db.put(Note(
            key_name='haiti:test.google.com/note.2002',
            subdomain='haiti',
            person_record_id='test.google.com/person.1001'
        ))
        doc = self.go('/api/read?subdomain=haiti' +
                      '&id=test.google.com/person.1001')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/feeds/person?subdomain=haiti')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/feeds/note?subdomain=haiti')
        assert '<pfif:status>' not in doc.content

        # An empty status should not appear as a tag.
        db.put(Note(
            key_name='haiti:test.google.com/note.2002',
            subdomain='haiti',
            person_record_id='test.google.com/person.1001',
            status=''
        ))
        doc = self.go('/api/read?subdomain=haiti' +
                      '&id=test.google.com/person.1001')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/feeds/person?subdomain=haiti')
        assert '<pfif:status>' not in doc.content
        doc = self.go('/feeds/note?subdomain=haiti')
        assert '<pfif:status>' not in doc.content

        # When the status is specified, it should appear in the feed.
        db.put(Note(
            key_name='haiti:test.google.com/note.2002',
            subdomain='haiti',
            person_record_id='test.google.com/person.1001',
            status='believed_alive'
        ))
        doc = self.go('/api/read?subdomain=haiti' +
                      '&id=test.google.com/person.1001')
        assert '<pfif:status>believed_alive</pfif:status>' in doc.content
        doc = self.go('/feeds/person?subdomain=haiti')
        assert '<pfif:status>believed_alive</pfif:status>' in doc.content
        doc = self.go('/feeds/note?subdomain=haiti')
        assert '<pfif:status>believed_alive</pfif:status>' in doc.content

    def test_tasks_count(self):
        """Tests the counting task."""
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            subdomain='haiti',
            author_name='_test1_author_name',
            entry_date=datetime.datetime.now(),
            first_name='_test1_first_name',
            last_name='_test1_last_name',
            sex='male',
            date_of_birth='1970-01-01',
            age='30-40',
        ))
        doc = self.go('/tasks/count?subdomain=haiti&kind_name=Person')
        button = doc.firsttag('input', value='Login')
        doc = self.s.submit(button, admin='True')
        assert 'Person count for haiti: 1' in doc.text
        doc = self.go('/tasks/count?subdomain=pakistan&kind_name=Person')
        assert 'Person count for pakistan: 0' in doc.text

        db.put(Person(
            key_name='haiti:test.google.com/person.456',
            subdomain='haiti',
            author_name='_test2_author_name',
            entry_date=datetime.datetime.now(),
            first_name='_test2_first_name',
            last_name='_test2_last_name',
            sex='female',
            date_of_birth='1970-02-02',
            age='30-40',
        ))
        doc = self.go('/tasks/count?subdomain=haiti&kind_name=Person')
        assert 'Person count for haiti: 2' in doc.text
        doc = self.go('/tasks/count?subdomain=pakistan&kind_name=Person')
        assert 'Person count for pakistan: 0' in doc.text

        db.put(Person(
            key_name='pakistan:test.google.com/person.789',
            subdomain='pakistan',
            author_name='_test3_author_name',
            entry_date=datetime.datetime.now(),
            first_name='_test3_first_name',
            last_name='_test3_last_name',
            sex='male',
            date_of_birth='1970-03-03',
            age='30-40',
        ))
        doc = self.go('/tasks/count?subdomain=haiti&kind_name=Person')
        assert 'Person count for haiti: 2' in doc.text
        doc = self.go('/tasks/count?subdomain=pakistan&kind_name=Person')
        assert 'Person count for pakistan: 1' in doc.text

        db.put(Counter(
            kind_name='Person', subdomain='haiti', last_key='', count=278))
        doc = self.go('/?subdomain=haiti&flush_cache=yes')
        assert 'Currently tracking about 300 records' in doc.text

    def test_admin_dashboard(self):
        """Visits the dashboard page and makes sure it doesn't crash."""
        db.put(Counter(
            kind_name='Person', subdomain='haiti', last_key='', count=278))
        db.put(Counter(
            kind_name='Person', subdomain='pakistan', last_key='', count=127))
        db.put(Counter(
            kind_name='Note', subdomain='haiti', last_key='', count=12))
        db.put(Counter(
            kind_name='Note', subdomain='pakistan', last_key='', count=8))
        assert self.go('/admin/dashboard')
        assert self.s.status == 200

    def test_delete_request(self):
        photo = Photo(bin_data='xyz')
        photo.put()
        photo_id = photo.key().id()
        photo_url = '/photo?id=' + str(photo_id)
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            subdomain='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            first_name='_test_first_name',
            last_name='_test_last_name',
            entry_date=datetime.datetime.now(),
            photo_url=photo_url
        ))
        db.put(Note(
            key_name='haiti:test.google.com/note.456',
            subdomain='haiti',
            author_email='test2@example.com',
            person_record_id='test.google.com/person.123',
            text='Testing'
        ))
        assert Person.get('haiti', 'test.google.com/person.123')
        assert Note.get('haiti', 'test.google.com/note.456')
        assert Photo.get_by_id(photo_id)
        assert self.go(photo_url + '&subdomain=haiti').content == 'xyz'
        assert self.s.status == 200

        MailThread.messages = []

        # Visit the page and click the button to request a deletion code.
        doc = self.go('/view?subdomain=haiti&id=test.google.com/person.123')
        button = doc.firsttag('input', value='Delete this record')
        doc = self.s.submit(button)
        assert 'Really delete the record for _test_first_name _test_last_name' in doc.text
        button = doc.firsttag('input', value='Send a deletion code')
        doc = self.s.submit(button)

        # Check the sent message for a deletion link.
        assert len(MailThread.messages) == 2
        message = MailThread.messages[0]
        assert message['to'] == ['test@example.com']
        assert ('Subject: Deletion request for _test_first_name _test_last_name'
                in message['data'])
        match = re.search(r'(http:.*)', message['data'])
        assert match
        delete_url = match.group(1)
        assert delete_url.startswith(
            'http://%s/delete?id=test.google.com%%2Fperson.123' % self.hostport)

        # Visit the deletion link.
        doc = self.s.go(delete_url)
        button = doc.firsttag('input', value='Yes, delete the record')
        doc = self.s.submit(button)
        assert 'The record has been deleted' in doc.text

        # Check that all associated records were actually deleted.
        assert not Person.get('haiti', 'test.google.com/person.123')
        assert not Note.get('haiti', 'test.google.com/note.456')
        assert not Photo.get_by_id(photo_id)

    def test_config_use_family_name(self):
        # use_family_name=True
        d = self.go('/create?subdomain=haiti')
        assert d.first('label', for_='first_name').text.strip() == 'Given name:'
        assert d.first('label', for_='last_name').text.strip() == 'Family name:'
        assert d.firsttag('input', name='first_name')
        assert d.firsttag('input', name='last_name')

        self.s.submit(d.first('form'),
                      first_name='_test_first',
                      last_name='_test_last',
                      author_name='_test_author')
        person = Person.all().get()
        d = self.go('/view?id=%s&subdomain=haiti' % person.record_id)
        f = d.first('table', class_='fields').all('tr')
        assert f[0].first('td', class_='label').text.strip() == 'Given name:'
        assert f[0].first('td', class_='field').text.strip() == '_test_first'
        assert f[1].first('td', class_='label').text.strip() == 'Family name:'
        assert f[1].first('td', class_='field').text.strip() == '_test_last'
        person.delete()

        # use_family_name=False
        d = self.go('/create?subdomain=pakistan')
        assert d.first('label', for_='first_name').text.strip() == 'Name:'
        assert not d.all('label', for_='last_name')
        assert d.firsttag('input', name='first_name')
        assert not d.alltags('input', name='last_name')
        assert 'Given name' not in d.text
        assert 'Family name' not in d.text

        self.s.submit(d.first('form'),
                      first_name='_test_first',
                      last_name='_test_last',
                      author_name='_test_author')
        person = Person.all().get()
        d = self.go(
            '/view?id=%s&subdomain=pakistan' % person.record_id)
        f = d.first('table', class_='fields').all('tr')
        assert f[0].first('td', class_='label').text.strip() == 'Name:'
        assert f[0].first('td', class_='field').text.strip() == '_test_first'
        assert 'Given name' not in d.text
        assert 'Family name' not in d.text
        assert '_test_last' not in d.first('body').text
        person.delete()

    def test_config_family_name_first(self):
        # family_name_first=True
        doc = self.go('/create?subdomain=china')
        given_label = doc.first('label', for_='first_name')
        family_label = doc.first('label', for_='last_name')
        assert given_label.text.strip() == 'Given name:'
        assert family_label.text.strip() == 'Family name:'
        assert family_label.start < given_label.start

        given_input = doc.firsttag('input', name='first_name')
        family_input = doc.firsttag('input', name='last_name')
        assert family_input.start < given_input.start

        self.s.submit(doc.first('form'),
                      first_name='_test_first',
                      last_name='_test_last',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/view?id=%s&subdomain=china' % person.record_id)
        f = doc.first('table', class_='fields').all('tr')
        assert f[0].first('td', class_='label').text.strip() == 'Family name:'
        assert f[0].first('td', class_='field').text.strip() == '_test_last'
        assert f[1].first('td', class_='label').text.strip() == 'Given name:'
        assert f[1].first('td', class_='field').text.strip() == '_test_first'
        person.delete()

        # family_name_first=False
        doc = self.go('/create?subdomain=haiti')
        given_label = doc.first('label', for_='first_name')
        family_label = doc.first('label', for_='last_name')
        assert given_label.text.strip() == 'Given name:'
        assert family_label.text.strip() == 'Family name:'
        assert family_label.start > given_label.start

        given_input = doc.firsttag('input', name='first_name')
        family_input = doc.firsttag('input', name='last_name')
        assert family_input.start > given_input.start

        self.s.submit(doc.first('form'),
                                    first_name='_test_first',
                                    last_name='_test_last',
                                    author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/view?id=%s&subdomain=haiti' % person.record_id)
        f = doc.first('table', class_='fields').all('tr')
        assert f[0].first('td', class_='label').text.strip() == 'Given name:'
        assert f[0].first('td', class_='field').text.strip() == '_test_first'
        assert f[1].first('td', class_='label').text.strip() == 'Family name:'
        assert f[1].first('td', class_='field').text.strip() == '_test_last'
        person.delete()

    def test_config_use_postal_code(self):
        # use_postal_code=True
        doc = self.go('/create?subdomain=haiti')
        assert doc.first('label', for_='home_postal_code')
        assert doc.firsttag('input', name='home_postal_code')

        self.s.submit(doc.first('form'),
                      first_name='_test_first',
                      last_name='_test_last',
                      home_postal_code='_test_12345',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/view?id=%s&subdomain=haiti' % person.record_id)
        assert 'Postal or zip code' in doc.text
        assert '_test_12345' in doc.text
        person.delete()

        # use_postal_code=False
        doc = self.go('/create?subdomain=pakistan')
        assert not doc.all('label', for_='home_postal_code')
        assert not doc.alltags('input', name='home_postal_code')

        self.s.submit(doc.first('form'),
                      first_name='_test_first',
                      last_name='_test_last',
                      home_postal_code='_test_12345',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/view?id=%s&subdomain=pakistan' % person.record_id)
        assert 'Postal or zip code' not in doc.text
        assert '_test_12345' not in doc.text
        person.delete()


class ConfigTests(TestsBase):
    """Tests that modify ConfigEntry entities in the datastore go here.
    The contents of the datastore will be reset for each test."""

    def tearDown(self):
        reset_data()

    def test_admin_page(self):
        # Load the administration page.
        doc = self.go('/admin?subdomain=haiti')
        button = doc.firsttag('input', value='Login')
        doc = self.s.submit(button, admin='True')
        assert self.s.status == 200 

        # Activate a new subdomain.
        assert not Subdomain.get_by_key_name('xyz')
        create_form = doc.first('form', id='subdomain_create')
        doc = self.s.submit(create_form, subdomain_new='xyz')
        assert Subdomain.get_by_key_name('xyz')

        # Change some settings for the new subdomain.
        settings_form = doc.first('form', id='subdomain_save')
        doc = self.s.submit(settings_form,
            language_menu_options='["no"]',
            subdomain_titles='{"no": "Jordskjelv"}',
            keywords='"foo, bar"',
            use_family_name='false',
            family_name_first='false',
            use_postal_code='false',
            min_query_word_length='1',
            map_default_zoom='6',
            map_default_center='[4, 5]',
            map_size_pixels='[300, 300]',
            read_auth_key_required='false'
        )

        cfg = config.Configuration('xyz')
        assert cfg.language_menu_options == ['no']
        assert cfg.subdomain_titles == {'no': 'Jordskjelv'}
        assert cfg.keywords == 'foo, bar'
        assert not cfg.use_family_name
        assert not cfg.family_name_first
        assert not cfg.use_postal_code
        assert cfg.min_query_word_length == 1
        assert cfg.map_default_zoom == 6
        assert cfg.map_default_center == [4, 5]
        assert cfg.map_size_pixels == [300, 300]
        assert not cfg.read_auth_key_required

        # Change settings again and make sure they took effect.
        settings_form = doc.first('form', id='subdomain_save')
        doc = self.s.submit(settings_form,
            language_menu_options='["nl"]',
            subdomain_titles='{"nl": "Aardbeving"}',
            keywords='"spam, ham"',
            use_family_name='true',
            family_name_first='true',
            use_postal_code='true',
            min_query_word_length='2',
            map_default_zoom='7',
            map_default_center='[-3, -7]',
            map_size_pixels='[123, 456]',
            read_auth_key_required='true'
        )

        cfg = config.Configuration('xyz')
        assert cfg.language_menu_options == ['nl']
        assert cfg.subdomain_titles == {'nl': 'Aardbeving'}
        assert cfg.keywords == 'spam, ham'
        assert cfg.use_family_name
        assert cfg.family_name_first
        assert cfg.use_postal_code
        assert cfg.min_query_word_length == 2
        assert cfg.map_default_zoom == 7
        assert cfg.map_default_center == [-3, -7]
        assert cfg.map_size_pixels == [123, 456]
        assert cfg.read_auth_key_required


class SecretTests(TestsBase):
    """Tests that modify Secret entities in the datastore go here.
    The contents of the datastore will be reset for each test."""
    kinds_written_by_tests = [Secret]

    def test_analytics_id(self):
        """Checks that the analytics_id Secret is used for analytics."""
        doc = self.go('/create?subdomain=haiti')
        assert 'getTracker(' not in doc.content

        db.put(Secret(key_name='analytics_id', secret='analytics_id_xyz'))

        doc = self.go('/create?subdomain=haiti')
        assert "getTracker('analytics_id_xyz')" in doc.content

    def test_maps_api_key(self):
        """Checks that maps don't appear when there is no maps_api_key."""
        db.put(Person(
            key_name='haiti:test.google.com/person.1001',
            subdomain='haiti',
            entry_date=datetime.datetime.now(),
            first_name='_status_first_name',
            last_name='_status_last_name',
            author_name='_status_author_name'
        ))
        doc = self.go('/create?subdomain=haiti&role=provide')
        assert 'map_canvas' not in doc.content
        doc = self.go('/view?subdomain=haiti&id=test.google.com/person.1001')
        assert 'map_canvas' not in doc.content
        assert 'id="map_' not in doc.content

        db.put(Secret(key_name='maps_api_key', secret='maps_api_key_xyz'))

        doc = self.go('/create?subdomain=haiti&role=provide')
        assert 'maps_api_key_xyz' in doc.content
        assert 'map_canvas' in doc.content
        doc = self.go('/view?subdomain=haiti&id=test.google.com/person.1001')
        assert 'maps_api_key_xyz' in doc.content
        assert 'map_canvas' in doc.content
        assert 'id="map_' in doc.content


def main():
    parser = optparse.OptionParser()
    parser.add_option('-a', '--address', default='localhost',
                      help='appserver hostname (default: localhost)')
    parser.add_option('-p', '--port', type='int', default=8081,
                      help='appserver port number (default: 8081)')
    parser.add_option('-m', '--mail_port', type='int', default=8025,
                      help='SMTP server port number (default: 8025)')
    parser.add_option('-v', '--verbose', action='store_true')
    options, args = parser.parse_args()

    try:
        threads = []
        if options.address == 'localhost':
            # We need to start up a clean new appserver for testing.
            threads.append(AppServerRunner(options.port, options.mail_port))
        threads.append(MailThread(options.mail_port))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.wait_until_ready()

        # Connect to the datastore.
        hostport = '%s:%d' % (options.address, options.port)
        remote_api.connect(hostport, remote_api.get_app_id(), 'test', 'test')
        TestsBase.hostport = hostport
        TestsBase.verbose = options.verbose

        # Reset the datastore for the first test.
        reset_data()
        unittest.main()  # You can select tests using command-line arguments.
    except Exception, e:
        # Something went wrong during testing.
        for thread in threads:
            thread.flush_output()
        traceback.print_exc()
        raise SystemExit
    finally:
        for thread in threads:
            thread.stop()
            thread.join()

if __name__ == '__main__':
    main()
