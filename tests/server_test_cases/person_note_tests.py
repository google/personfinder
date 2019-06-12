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

"""Test cases for end-to-end testing.  Run with the server_tests script.

See scrape.py for methods available for the document object returned by self.s.go.
"""

import datetime
from parameterized import parameterized
import re
import time
import urlparse

# This has to be imported before const, so that Django will get set up before
# const tries to use Django's translation functions. When the server's actually
# running, main.py will import it, but main.py doesn't get involved here.
import django_setup
from const import ROOT_URL, PERSON_STATUS_TEXT, NOTE_STATUS_TEXT
from model import *
import reveal
import scrape
from scrape import get_all_text, get_all_attrs, get_form_params
from test_pfif import text_diff
from text_query import TextQuery
import utils
from server_tests_base import ServerTestsBase


# Namespaces used for PFIF XML responses.
PFIF_NAMESPACES = {
    'status': 'http://zesty.ca/pfif/1.4/status',
    'pfif': 'http://zesty.ca/pfif/1.4',
    }


class PersonNoteTests(ServerTestsBase):
    """Tests that modify Person and Note entities in the datastore go here.
    The contents of the datastore will be reset for each test."""

    def assert_error_deadend(self, page, *fragments):
        """Assert that the given page is a dead-end.

        Checks to make sure there's an error message that contains the given
        fragments.  On failure, fail assertion.  On success, step back.
        """
        error_message = page.cssselect('.error')[0].text.strip()
        for fragment in fragments:
            assert fragment in error_message, (
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
        result_titles = self.s.doc.cssselect('.resultDataTitle')
        assert len(result_titles) == num_results
        for title in result_titles:
            for text in all_have:
                assert text in title.text.strip(), (
                    '%s must have %s' % (title.text.strip(), text))
        for text in some_have:
            assert any(text in title.text.strip() for title in result_titles), (
                'One of %s must have %s' % (result_titles, text))
        if status:
            result_statuses = self.s.doc.cssselect('.resultDataPersonFound')
            assert len(result_statuses) == len(status)
            for expected_status, result_status in zip(status, result_statuses):
                assert result_status.text.strip() == expected_status, (
                    '"%s" missing expected status: "%s"' % (
                    result_status, expected_status))

    def verify_unsatisfactory_results(self):
        """Verifies the clicking the button at the bottom of the results page.

        Precondition: the current session must be on the results page
        Postcondition: the current session is on the create new record page
        """

        # Click the button to create a new record
        found = False
        for results_form in self.s.doc.cssselect('form'):
            submit_button = results_form.cssselect('input[type="submit"]')
            if (submit_button and
                'Create a new record' in submit_button[0].get('value', '')):
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

        create_form = self.s.doc.cssselect_one('form')
        create_form_params = get_form_params(create_form)
        for key, value in (prefilled_params or {}).iteritems():
            assert create_form_params[key] == value
        for key in unfilled_params or ():
            assert not create_form_params[key]

        # Try to submit without filling in required fields
        self.assert_error_deadend(
            self.s.submit(create_form), 'required', 'try again')

    def verify_note_form(self):
        """Verifies the behavior of the add note form.

        Precondition: the current session is on a page with a note form
            e.g., "create", "add_note" page.
        Postcondition: the current session is still on a page with a note form.
        """

        note_form = self.s.doc.cssselect_one('form')
        assert note_form.cssselect('select[name="status"]')
        assert note_form.cssselect('textarea[name="text"]')
        self.assert_error_deadend(
            self.s.submit(note_form), 'required', 'try again')

    def verify_details_page(self, num_notes=None, full_name=None, details=None):
        """Verifies the content of the details page.

        Verifies that the details contain the given number of notes, given full
        name and the given details.

        Precondition: the current session is on the details page
        Postcondition: the current session is still on the details page
        """

        # Do not assert params.  Upon reaching the details page, you've lost
        # the difference between seekers and providers and the param is gone.
        details = details or {}
        details_page = self.s.doc

        if full_name:
            assert scrape.get_all_text(
                details_page.cssselect_one('.full-name')) == full_name

        # Person info is stored in matching 'label' and 'value' cells.
        fields = dict(zip(
            [label.text.strip() for label in details_page.cssselect('.label')],
            details_page.cssselect('.value')))
        for label, value in details.iteritems():
            assert scrape.get_all_text(fields[label]) == value, (
                'value mismatch for the field named %s' % label)

        if num_notes is not None:
            actual_num_notes = len(details_page
                .cssselect_one('.self-notes').cssselect('.view.note'))
            assert actual_num_notes == num_notes, (
                'expected %s notes, instead was %s'
                    % (num_notes, actual_num_notes))

    def verify_click_search_result(self, n, url_test=lambda u: None):
        """Simulates clicking the nth search result (where n is zero-based).

        Also passes the URL followed to the given url_test function for checking.
        This function should raise an AssertionError on failure.

        Precondition: the current session must be on the results page
        Postcondition: the current session is on the person details page
        """

        # Get the list of links.
        result_link = self.s.doc.cssselect('div.searchResults a.result-link')[n]

        # Verify and then follow the link.
        url_test(result_link.get('href'))
        self.s.follow(result_link)

    def verify_update_notes(self, author_made_contact, note_body, author,
                            status, **kwargs):
        """Verifies the process of adding a new note.

        Posts a new note with the given parameters.

        Precondition: the current session must be on the details page
        Postcondition: the current session is still on the details page
        """

        assert urlparse.urlparse(self.s.url).path.endswith('/view'), (
            'Not currently at "view" page: %s' % self.s.url)

        # Do not assert params.  Upon reaching the details page, you've lost
        # the difference between seekers and providers and the param is gone.
        details_page = self.s.doc
        num_initial_notes = len(details_page.cssselect(
            '.self-notes .view.note'))

        add_note_page = self.go_to_add_note_page()
        note_form = add_note_page.cssselect_one('form')

        # Advance the clock. The new note has a newer source_date by this.
        # This makes sure that the new note appears at the bottom of the view
        # page.
        self.advance_utcnow(seconds=1)

        params = dict(kwargs)
        params['text'] = note_body
        params['author_name'] = author
        expected = params.copy()
        params['author_made_contact'] = (author_made_contact and 'yes') or 'no'
        if status:
            params['status'] = status
            expected['status'] = str(NOTE_STATUS_TEXT.get(status))

        details_page = self.s.submit(note_form, **params)
        notes = details_page.cssselect('.self-notes .view.note')
        assert len(notes) == num_initial_notes + 1
        new_note = notes[-1]
        new_note_text = scrape.get_all_text(new_note)
        for field, text in expected.iteritems():
            if field in ['note_photo_url']:
                url = utils.strip_url_scheme(text)
                assert new_note.cssselect('.photo')[0].get('src') == url, (
                    'Note photo URL mismatch')
            else:
                assert text in new_note_text, (
                    'Note text %r missing %r' % (new_note_text, text))

        # Show this text if and only if the person has been contacted
        assert ('This person has been in contact with someone'
                in new_note_text) == author_made_contact

    def verify_email_sent(self, message_count=1):
        """Verifies email was sent, firing manually from the taskqueue
        if necessary.  """
        # Explicitly fire the send-mail task if necessary
        doc = self.go_as_admin('/_ah/admin/tasks?queue=send-mail')
        try:
            for button in doc.cssselect('button.ae-taskqueues-run-now'):
                doc = self.s.submit(d.first('form', name='queue_run_now'),
                                    run_now=button.get('id'))
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

    def go_to_add_note_page(self):
        """Goes from the "view" page to the "add_note" page.

        Precondition: the current session must be on the "view" page
        Postcondition: the current session is on the "add_note" page
        """
        assert urlparse.urlparse(self.s.url).path.endswith('/view'), (
            'Not currently at "view" page: %s' % self.s.url)
        return self.s.submit(self.s.doc.cssselect_one('input.add-note'))

    def submit_minimal_create_form(self, create_form):
        self.s.submit(create_form,
                      own_info='no',
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      author_name='_test_author_name')

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
        assert not doc.xpath('//meta[@name="robots"]')

        # Robots are not okay on the view page.
        doc = self.go('/haiti/view?id=test.google.com/person.111')
        assert '_test_full_name' in doc.content
        assert doc.xpath('//meta[@name="robots" and @content="noindex"]')

        # Robots are not okay on the results page.
        doc = self.go('/haiti/results?role=seek&query_name=_test_full_name&query_location=')
        assert '_test_full_name' in doc.content
        assert doc.xpath('//meta[@name="robots" and @content="noindex"]')

    def test_have_information_small(self):
        """Follow the I have information flow on the small-sized embed."""

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None, required_params={}, forbidden_params={}):
            required_params.setdefault('role', 'provide')
            required_params.setdefault('ui', 'small')
            self.assert_params_conform(url or self.s.url,
                                  required_params=required_params,
                                  forbidden_params=forbidden_params)

        # Start on the home page and click the "I'm looking for someone" button
        self.go('/haiti?ui=small')
        search_page = self.s.follow('I have information about someone')
        search_form = search_page.cssselect_one('form')
        assert 'I have information about someone' in get_all_text(search_form)

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
        given_name_input = create_page.xpath_one('//input[@name="given_name"]')
        assert '_test_given_name' in given_name_input.get('value')
        family_name_input = create_page.xpath_one(
                '//input[@name="family_name"]')
        assert '_test_family_name' in family_name_input.get('value')

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
            self.assert_params_conform(
                url or self.s.url, {'role': 'seek', 'ui': 'small'})

        # Start on the home page and click the "I'm looking for someone" button
        self.go('/haiti?ui=small')
        search_page = self.s.follow('I\'m looking for someone')
        submit_button = search_page.xpath_one('//input[@type="submit"]')
        assert 'Search for this person' in submit_button.get('value')

        # Try a search, which should yield no results.
        search_form = search_page.cssselect_one('form')
        self.s.submit(search_form, query_name='_test_given_name')
        assert_params()
        self.verify_results_page(0)
        assert_params()
        assert self.s.doc.cssselect('a.create-new-record')

        person = Person(
            key_name='haiti:test.google.com/person.111',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            given_name='alexander',
            family_name='_test_family_name',
            full_name='_test_given_name _test_family_name',
            entry_date=datetime.datetime.utcnow(),
            text='_test A note body')
        person.update_index(['old', 'new'])
        person.put()

        assert_params()

        # Now the search should yield a result.
        self.s.submit(search_form, query_name='alexander')
        assert_params()
        link = self.s.doc.cssselect_one('a.results-found')
        assert 'query_name=alexander' in link.get('href')

    def test_search_page_link(self):
        self.go('/haiti')
        search_page = self.s.follow('I\'m looking for someone')
        submit_button = search_page.xpath_one('//input[@type="submit"]')
        assert 'Search for this person' in submit_button.get('value')

    @parameterized.expand([(True,), (False,)])
    def test_search_with_no_result(self, use_full_text_search):
        config.set(enable_full_text_search = use_full_text_search)
        search_page = self.go('/haiti/query?role=seek')
        submit_button = search_page.xpath_one('//input[@type="submit"]')

        # Try a search, which should yield no results.
        search_form = search_page.cssselect_one('form')
        self.s.submit(search_form, query_name='_test_given_name')
        self.assert_params_conform(
            self.s.url, {'role': 'seek'}, {'ui': 'small'})
        self.verify_results_page(0)
        self.assert_params_conform(
            self.s.url, {'role': 'seek'}, {'ui': 'small'})
        self.verify_unsatisfactory_results()
        self.assert_params_conform(
            self.s.url, {'role': 'seek'}, {'ui': 'small'})

    def test_details_after_create_form_submission(self):
        self.go('/haiti/create?query=&role=seek&given_name=&family_name=')
        self.submit_minimal_create_form(self.s.doc.cssselect_one('form'))

        # For now, the date of birth should be hidden.
        assert 'birth' not in self.s.content.lower()

        self.verify_details_page(
            num_notes=0,
            full_name='_test_given_name _test_family_name',
            details={'Author\'s name:': '_test_author_name'})

    @parameterized.expand([(True,), (False,)])
    def test_search_with_result(self, use_full_text_search):
        config.set(enable_full_text_search = use_full_text_search)
        self.go('/haiti/create?query=&role=seek&given_name=&family_name=')
        self.submit_minimal_create_form(self.s.doc.cssselect_one('form'))
        search_page = self.go('/haiti/query?role=seek')
        search_form = search_page.cssselect_one('form')
        self.s.submit(search_form, query_name='_test_given_name')
        def assert_params(url=None):
            self.assert_params_conform(
                url or self.s.url, {'role': 'seek'}, {'ui': 'small'})
        assert_params()
        self.verify_results_page(1, all_have=(['_test_given_name']),
                                 some_have=(['_test_given_name']),
                                 status=(['Unspecified']))
        self.verify_click_search_result(0, assert_params)

    def test_note_doesnt_update_entry_date(self):
        self.go('/haiti/create?query=&role=seek&given_name=&family_name=')
        self.submit_minimal_create_form(self.s.doc.cssselect_one('form'))
        person = Person.all().filter('given_name =', '_test_given_name').get()
        entry_date = person.entry_date
        self.verify_details_page(num_notes=0)
        self.advance_utcnow(days=5)
        self.verify_update_notes(
            author_made_contact=False, note_body='_test A note body',
            author='_test A note author', status=None)
        person = Person.all().filter('given_name =', '_test_given_name').get()
        self.assertEqual(person.entry_date, entry_date)

    def test_new_note_shown_below_old_note(self):
        self.go('/haiti/create?query=&role=seek&given_name=&family_name=')
        self.submit_minimal_create_form(self.s.doc.cssselect_one('form'))
        self.verify_update_notes(
            False, '_test A note body', '_test A note author', None)
        self.advance_utcnow(seconds=1)
        self.verify_update_notes(
            author_made_contact=True,
            note_body='_test Another note body',
            author='_test Another note author',
            status='believed_alive',
            last_known_location='Port-au-Prince',
            note_photo_url='http://localhost:8081/abc.jpg')

    def test_user_action_log_created(self):
        self.go('/haiti/create?query=&role=seek&given_name=&family_name=')
        self.submit_minimal_create_form(self.s.doc.cssselect_one('form'))
        url_parts = list(urlparse.urlparse(self.s.url))
        record_id = dict(urlparse.parse_qsl(url_parts[4]))['id']
        self.verify_update_notes(
            author_made_contact=True,
            note_body='_test Another note body',
            author='_test Another note author',
            status='believed_alive',
            last_known_location='Port-au-Prince',
            note_photo_url='http://localhost:8081/abc.jpg')

        # Check that a UserActionLog entry was created.
        self.verify_user_action_log('mark_alive', 'Note',
                               repo='haiti',
                               detail=record_id,
                               ip_address='',
                               Note_text='_test Another note body',
                               Note_status='believed_alive')

    def post_and_verify_believed_dead_note(self):
        self.go('/haiti/create?query=&role=seek&given_name=&family_name=')
        self.submit_minimal_create_form(self.s.doc.cssselect_one('form'))
        # By default allow_believed_dead_via_ui = True for repo 'haiti'.
        self.verify_update_notes(
            True, '_test note body', '_test note author', 'believed_dead')

    def test_believed_dead_note(self):
        self.post_and_verify_believed_dead_note()

    @parameterized.expand([(True,), (False,)])
    def test_believed_dead_note_in_results(self, use_full_text_search):
        config.set(enable_full_text_search = use_full_text_search)
        def assert_params(url=None):
            self.assert_params_conform(
                url or self.s.url, {'role': 'seek'}, {'ui': 'small'})
        self.post_and_verify_believed_dead_note()
        search_page = self.go('/haiti/query?role=seek')
        search_form = search_page.cssselect_one('form')
        self.s.submit(search_form, query_name='_test_given_name')
        assert_params()
        self.verify_results_page(
            1, all_have=['_test_given_name'], some_have=['_test_given_name'],
            status=['Someone has received information that this person is dead']
        )

    def test_default_expiry(self):
        config.set_for_repo('haiti', default_expiry_days=10)
        source_datetime = datetime.datetime(2001, 1, 1, 0, 0, 0)
        self.set_utcnow_for_test(source_datetime)
        test_source_date = source_datetime.strftime('%Y-%m-%d')
        # Submit the create form with complete information
        self.go('/haiti/create?query=&role=seek&given_name=&family_name=')
        self.s.submit(self.s.doc.cssselect_one('form'),
                      own_info='no',
                      author_name='_test_author_name',
                      author_email='test_author_email@example.com',
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
        self.verify_details_page(
            num_notes=0,
            full_name='_test_given_name _test_family_name',
            details={
                'Alternate names:':
                    '_test_alternate_given_names _test_alternate_family_names',
                'Sex:': 'female',
                # 'Date of birth:': '1955',  # currently hidden
                'Age:': '50-55',
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
                'Original posting date:': 'Jan 1, 2001 12:00:00 AM UTC',
                'Original site name:': '_test_source_name',
                'Expiry date of this record:': 'Jan 11, 2001 12:00:00 AM UTC'})

    def test_profile_icons_present(self):
        self.go('/haiti/create?query=&role=seek&given_name=&family_name=')
        self.s.submit(self.s.doc.cssselect_one('form'),
                      own_info='no',
                      author_name='_test_author_name',
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      profile_url1='http://www.facebook.com/_test_account1',
                      profile_url2='http://www.twitter.com/_test_account2',
                      profile_url3='http://www.foo.com/_test_account3')
        assert 'facebook-16x16.png' in self.s.doc.content
        assert 'twitter-16x16.png' in self.s.doc.content
        assert 'http://www.facebook.com/_test_account1' in self.s.doc.content
        assert 'http://www.twitter.com/_test_account2' in self.s.doc.content
        assert 'http://www.foo.com/_test_account3' in self.s.doc.content

    def test_seeking_someone_with_query_param(self):
        """Visit the results page with the query (rather than query_name) param.
        """
        person = Person(
            key_name='haiti:test.google.com/person.111',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            given_name='eric',
            family_name='_test_family_name',
            full_name='_test_given_name _test_family_name',
            entry_date=datetime.datetime.utcnow(),
            text='_test A note body')
        person.update_index(['old', 'new'])
        person.put()
        self.go('/haiti/results?role=seek&query=eric')
        link = self.s.doc.cssselect_one('a.result-link')
        assert 'query_name=eric' in link.get('href')

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
        self.verify_details_page(
            num_notes=1,
            details={'Original posting date:': 'Feb 3, 2001 1:05:06 PM JST'})
        assert (
            'Posted by Fred on Feb 3, 2001, 4:08:09 PM JST' in self.s.doc.text)

        self.go('/japan/multiview?id1=test.google.com/person.111'
                '&lang=en')
        assert 'Feb 3, 2001, 1:05:06 PM JST' in self.s.doc.text, \
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
        self.verify_details_page(
            num_notes=1,
            details={'Original posting date:': 'Feb 3, 2001 4:05:06 AM UTC'})
        assert (
            'Posted by Fred on Feb 3, 2001, 7:08:09 AM UTC' in self.s.doc.text)
        self.go('/haiti/multiview?id1=test.google.com/person.111'
                '&lang=en')
        assert 'Feb 3, 2001, 4:05:06 AM UTC' in self.s.doc.text

    def test_new_indexing(self):
        """First create new entry with new_search param then search for it"""

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            self.assert_params_conform(
                url or self.s.url, {'role': 'seek'}, {'ui': 'small'})

        # Start on the home page and click the "I'm looking for someone" button
        self.go('/haiti')
        search_page = self.s.follow('I\'m looking for someone')
        submit_button = search_page.xpath_one('//input[@type="submit"]')
        assert 'Search for this person' in submit_button.get('value')

        # Try a search, which should yield no results.
        search_form = search_page.cssselect_one('form')
        self.s.submit(search_form, query_name='ABCD EFGH IJKL MNOP')
        assert_params()
        self.verify_results_page(0)
        assert_params()
        self.verify_unsatisfactory_results()
        assert_params()

        # Submit the create form with a valid given and family name
        self.s.submit(self.s.doc.cssselect_one('form'),
                      own_info='no',
                      given_name='ABCD EFGH',
                      family_name='IJKL MNOP',
                      alternate_given_names='QRST UVWX',
                      alternate_family_names='YZ01 2345',
                      author_name='author_name')

        # Try a middle-name match.
        self.s.submit(search_form, query_name='EFGH')
        self.verify_results_page(1, all_have=(['ABCD EFGH']))

        # Try a middle-name non-match.
        self.s.submit(search_form, query_name='ABCDEF')
        self.verify_results_page(0)

        # Try a middle-name prefix match.
        self.s.submit(search_form, query_name='MNO')
        self.verify_results_page(1, all_have=(['ABCD EFGH']))

        # Try a multiword match.
        self.s.submit(search_form, query_name='MNOP IJK ABCD EFG')
        self.verify_results_page(1, all_have=(['ABCD EFGH']))

        # Try an alternate-name prefix non-match.
        self.s.submit(search_form, query_name='QRS')
        self.verify_results_page(0)

        # Try a multiword match on an alternate name.
        self.s.submit(search_form, query_name='ABCD EFG QRST UVWX')
        self.verify_results_page(1, all_have=(['ABCD EFGH']))

    def test_indexing_japanese_names(self):
        """Index Japanese person's names and make sure they are searchable."""

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            self.assert_params_conform(
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
        submit_button = search_page.xpath_one('//input[@type="submit"]')
        assert 'Search for this person' in submit_button.get('value')

        # Try a search, which should yield no results.
        search_form = search_page.cssselect_one('form')
        self.s.submit(search_form, query_name='山田 太郎')
        assert_params()
        self.verify_results_page(0)
        assert_params()
        self.verify_unsatisfactory_results()
        assert_params()

        # Submit the create form with a valid given and family name.
        self.s.submit(self.s.doc.cssselect_one('form'),
                      family_name='山田',
                      given_name='太郎',
                      alternate_family_names='やまだ',
                      alternate_given_names='たろう',
                      author_name='author_name')

        # Try a family name match.
        self.s.submit(search_form, query_name='山田')
        self.verify_results_page(1, all_have=([u'山田 太郎',
                                               u'やまだ たろう']))

        # Try a full name prefix match.
        self.s.submit(search_form, query_name='山田太')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try a full name match, where given and family names are not segmented.
        self.s.submit(search_form, query_name='山田太郎')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try an alternate family name match.
        self.s.submit(search_form, query_name='やまだ')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try an alternate name match with given name and family name segmented.
        self.s.submit(search_form, query_name='やまだ たろう')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try an alternate name match without given name and family name
        # segmented.
        self.s.submit(search_form, query_name='やまだたろう')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try an alternate name prefix match, but we don't index prefixes for
        # alternate names.
        self.s.submit(search_form, query_name='やまだたろ')
        self.verify_results_page(0)

        # Try an alternate family name match with katakana variation.
        self.s.submit(search_form, query_name='ヤマダ')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

        # Try an alternate family name match with romaji variation.
        self.s.submit(search_form, query_name='YAMADA')
        self.verify_results_page(1, all_have=([u'山田 太郎']))

    def test_have_information_regular(self):
        """Follow the "I have information" flow on the regular-sized embed."""

        # Set utcnow to match source date
        SOURCE_DATETIME = datetime.datetime(2001, 1, 1, 0, 0, 0)
        self.set_utcnow_for_test(SOURCE_DATETIME)
        test_source_date = SOURCE_DATETIME.strftime('%Y-%m-%d')

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            self.assert_params_conform(
                url or self.s.url, {'role': 'provide'}, {'ui': 'small'})

        self.go('/haiti')
        search_page = self.s.follow('I have information about someone')
        search_form = search_page.cssselect_one('form')
        assert 'I have information about someone' in get_all_text(search_form)

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
        create_form = self.s.doc.cssselect_one('form')
        self.s.submit(create_form,
                      own_info='no',
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      author_name='_test_author_name',
                      text='_test A note body')

        self.verify_details_page(
            num_notes=1,
            full_name='_test_given_name _test_family_name',
            details={'Author\'s name:': '_test_author_name'})

        # Verify that UserActionLog entries are created for 'add' action.
        self.verify_user_action_log('add', 'Person', repo='haiti')
        self.verify_user_action_log('add', 'Note', repo='haiti')

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
        self.verify_details_page(num_notes=1)

        self.go_to_add_note_page()
        self.verify_note_form()
        self.s.back()

        self.verify_update_notes(
            False, '_test A note body', '_test A note author', None)
        self.verify_update_notes(
            True, '_test Another note body', '_test Another note author',
            None, last_known_location='Port-au-Prince',
            note_photo_url='http://localhost:8081/abc.jpg')

        # Submit the create form with complete information
        self.s.submit(create_form,
                      own_info='no',
                      author_name='_test_author_name',
                      author_email='test_author_email@example.com',
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

        self.verify_details_page(
            num_notes=1,
            full_name='_test_given_name _test_family_name',
            details={
                'Alternate names:':
                    '_test_alternate_given_names _test_alternate_family_names',
                'Sex:': 'male',
                # 'Date of birth:': '1970-01',  # currently hidden
                'Age:': '30-40',
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
                'Original posting date:': 'Jan 1, 2001 12:00:00 AM UTC',
                'Original site name:': '_test_source_name',
                'Expiry date of this record:': 'Jan 21, 2001 12:00:02 AM UTC'})

        # Check that UserActionLog entries were created.
        self.verify_user_action_log('add', 'Person', repo='haiti')
        self.verify_user_action_log('add', 'Note', repo='haiti')
        self.verify_user_action_log('mark_dead', 'Note',
                               repo='haiti',
                               detail='_test_given_name _test_family_name',
                               ip_address='127.0.0.1',
                               Note_text='_test A note body',
                               Note_status='believed_dead')

    def test_inputting_own_information(self):
        """Check if some params are set automatically
        when "I want to input my own information" is selected"""
        d = self.go('/haiti/create?role=provide')
        self.s.submit(d.cssselect_one('form'),
                      own_info='yes',
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      your_own_email='test_email@example.com',
                      your_own_phone='_test_phone',
                      text='_test A note body')
        person = Person.all().get()

        # Check if author's information set to
        # person's given name, own email and phone automatically
        self.verify_details_page(
            num_notes=1,
            full_name='_test_given_name _test_family_name',
            details={
                'Author\'s name:': '_test_given_name',
                'Author\'s phone number:': '(click to reveal)',
                'Author\'s e-mail address:': '(click to reveal)'})

        view_url = '/haiti/view?id=' + person.record_id
        doc = self.s.go(view_url)
        note = doc.cssselect('.view.note')[-1]
        note_attrs = get_all_attrs(note)

        # Check if the status set to is_note_author automatically
        assert [v for k, v in note_attrs if 'is_note_author' in v], note_attrs
        assert not [v for k, v in note_attrs if 'believed_dead' in v], \
                note_attrs

    def test_multiview(self):
        """Test the page for marking duplicate records."""
        db.put([Person(
            key_name='haiti:test.google.com/person.111',
            repo='haiti',
            author_name='_author_name_1',
            author_email='_author_email_1',
            author_phone='_author_phone_1',
            entry_date=ServerTestsBase.TEST_DATETIME,
            full_name='_full_name_1',
            alternate_names='_alternate_names_1',
            sex='male',
            date_of_birth='1970-01-01',
            age='31-41',
            photo_url='http://example.com/photo1',
            profile_urls='''http://www.facebook.com/_account_1
http://www.twitter.com/_account_1
http://www.foo.com/_account_1''',
        ), Person(
            key_name='haiti:test.google.com/person.222',
            repo='haiti',
            author_name='_author_name_2',
            author_email='_author_email_2',
            author_phone='_author_phone_2',
            entry_date=ServerTestsBase.TEST_DATETIME,
            full_name='_full_name_2',
            alternate_names='_alternate_names_2',
            sex='male',
            date_of_birth='1970-02-02',
            age='32-42',
            photo_url='http://example.com/photo2',
            profile_urls='http://www.facebook.com/_account_2',
        ), Person(
            key_name='haiti:test.google.com/person.333',
            repo='haiti',
            author_name='_author_name_3',
            author_email='_author_email_3',
            author_phone='_author_phone_3',
            entry_date=ServerTestsBase.TEST_DATETIME,
            full_name='_full_name_3',
            alternate_names='_alternate_names_3',
            sex='male',
            date_of_birth='1970-03-03',
            age='33-43',
            photo_url='http://example.com/photo3',
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
        # The photos should be linked but not inlined.
        assert 'http://example.com/photo1' in doc.content
        assert 'http://example.com/photo2' in doc.content
        assert 'http://example.com/photo3' in doc.content
        assert 'External photo' in doc.content
        assert 'http://www.facebook.com/_account_1' in doc.content
        assert 'http://www.twitter.com/_account_1' in doc.content
        assert 'http://www.foo.com/_account_1' in doc.content
        assert 'http://www.facebook.com/_account_2' in doc.content

        # Mark all three as duplicates.
        button = doc.xpath_one(
                '//input[@value="Yes, these are the same person"]')
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
        notes = doc.cssselect('.self-notes div.view.note.duplicate')
        assert len(notes) == 2, str(doc.content.encode('ascii', 'ignore'))
        # We don't know which note comes first as they are created almost
        # simultaneously.
        note_222_text = get_all_text(notes[0])
        note_333_text = get_all_text(notes[1])
        if 'person.222' in note_333_text:
            note_333_text, note_222_text = note_222_text, note_333_text
        assert 'Posted by foo' in note_222_text
        assert 'duplicate test' in note_222_text
        assert ('This record is a duplicate of test.google.com/person.222' in
                note_222_text)
        assert 'Posted by foo' in note_333_text
        assert 'duplicate test' in note_333_text
        assert ('This record is a duplicate of test.google.com/person.333' in
                note_333_text)

    def test_reveal(self):
        """Test the hiding and revealing of contact information in the UI."""
        db.put([Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            author_name='_reveal_author_name',
            author_email='_reveal_author_email',
            author_phone='_reveal_author_phone',
            entry_date=ServerTestsBase.TEST_DATETIME,
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
            entry_date=ServerTestsBase.TEST_DATETIME,
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
        reveal_region = doc.xpath(
                '//a[normalize-space(text())="(click to reveal)"]')[0]
        url = reveal_region.get('href')
        doc = self.go(url[url.find('/haiti/reveal'):])
        assert 'iframe' in doc.content
        assert 'g-recaptcha-response' in doc.content

        # Try to continue with an invalid captcha response. Get redirected
        # back to the same page.
        button = doc.xpath_one('//input[@value="Proceed"]')
        doc = self.s.submit(button, faked_captcha_response='failure')
        assert 'iframe' in doc.content
        assert 'g-recaptcha-response' in doc.content

        # Continue as if captcha is valid. All information should be viewable.
        doc = self.s.submit(button, faked_captcha_response='success')
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

        data = self.get_test_data('test.pfif-1.2-source.xml')
        self.go('/haiti/api/write?key=domain_test_key',
                data=data, type='application/xml')

        # On Search results page,  we should see Provided by: domain
        doc = self.go('/haiti/results?role=seek&query_name=_test_last_name&query_location=')
        assert get_all_text(doc.cssselect_one('.provider-name')) == (
            'mytestdomain.com')
        assert '_test_last_name' in doc.content

        # On details page, we should see Provided by: domain
        doc = self.go('/haiti/view?lang=en&id=mytestdomain.com/person.21009')
        assert get_all_text(doc.cssselect_one('.provider-name')) == (
            'mytestdomain.com')
        assert '_test_last_name' in doc.content

    def test_referer(self):
        """Follow the "I have information" flow with a referrer set."""
        config.set_for_repo('haiti', referrer_whitelist=['a.org'])

        # Set utcnow to match source date
        SOURCE_DATETIME = datetime.datetime(2001, 1, 1, 0, 0, 0)
        self.set_utcnow_for_test(SOURCE_DATETIME)
        test_source_date = SOURCE_DATETIME.strftime('%Y-%m-%d')

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            self.assert_params_conform(
                url or self.s.url, {'role': 'provide', 'referrer': 'a.org'},
                {'ui': 'small'})

        self.go('/haiti?referrer=a.org')
        search_page = self.s.follow('I have information about someone')
        search_form = search_page.cssselect_one('form')
        assert 'I have information about someone' in get_all_text(search_form)

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
        create_form = self.s.doc.cssselect_one('form')
        self.s.submit(create_form,
                      own_info='no',
                      given_name='_test_given_name',
                      family_name='_test_family_name',
                      author_name='_test_author_name',
                      text='_test A note body')

        netloc = urlparse.urlparse(self.s.url).netloc
        self.verify_details_page(
            num_notes=1,
            details={'Original site name:': '%s (referred by a.org)' % netloc})

    def test_global_domain_key(self):
        """Test that we honor global domain keys."""
        data = self.get_test_data('global-test.pfif-1.2-source.xml')
        self.go('/haiti/api/write?key=global_test_key',
                data=data, type='application/xml')

        # On Search results page,  we should see Provided by: domain
        doc = self.go(
            '/haiti/results?role=seek&query_name=_test_last_name&query_location=')
        assert get_all_text(doc.cssselect_one('.provider-name')) == (
            'globaltestdomain.com')
        assert '_test_last_name' in doc.content

        # On details page, we should see Provided by: domain
        doc = self.go(
            '/haiti/view?lang=en&id=globaltestdomain.com/person.21009'
            )
        assert get_all_text(doc.cssselect_one('.provider-name')) == (
            'globaltestdomain.com')
        assert '_test_last_name' in doc.content

    def test_note_status(self):
        """Test the posting and viewing of the note status field in the UI."""
        status_class = re.compile(r'\bstatus\b')

        # allow_believed_dead_via_ui = True
        config.set_for_repo('haiti', allow_believed_dead_via_ui=True)

        # Check that the right status options appear on the create page.
        doc = self.go('/haiti/create?role=provide')
        note = doc.cssselect_one('.status.card')
        options = note.xpath('descendant::select[@name="status"]/option')
        assert len(options) == len(ServerTestsBase.NOTE_STATUS_OPTIONS)
        for option, text in zip(options, ServerTestsBase.NOTE_STATUS_OPTIONS):
            assert text in option.get('value')

        # Create a record with no status and get the new record's ID.
        form = doc.cssselect_one('form')
        doc = self.s.submit(form,
                            own_info='no',
                            given_name='_test_given',
                            family_name='_test_family',
                            author_name='_test_author',
                            text='_test_text')
        view_url = self.s.url
        url_parts = list(urlparse.urlparse(view_url))
        record_id = dict(urlparse.parse_qsl(url_parts[4]))['id']

        # Check that the right status options appear on the view page.
        self.s.go(view_url)
        doc = self.go_to_add_note_page()
        note = doc.cssselect_one('.create.note')
        options = note.xpath('descendant::select[@name="status"]/option')
        assert len(options) == len(ServerTestsBase.NOTE_STATUS_OPTIONS)
        for option, text in zip(options, ServerTestsBase.NOTE_STATUS_OPTIONS):
            assert text in option.get('value')

        # Advance the clock. The new note has a newer source_date by this.
        # This makes sure that the new note appears at the bottom of the view
        # page.
        self.advance_utcnow(seconds=1)

        # Set the status in a note and check that it appears on the view page.
        form = doc.cssselect_one('form')
        self.s.submit(form, own_info='no', author_name='_test_author2', text='_test_text',
                      status='believed_alive')
        doc = self.s.go(view_url)
        note = doc.cssselect('.view.note')[-1]
        note_attrs = get_all_attrs(note)
        assert [v for k, v in note_attrs if 'believed_alive' in v], note_attrs
        assert not [v for k, v in note_attrs if 'believed_dead' in v], \
                note_attrs
        # Check that a UserActionLog entry was created.
        self.verify_user_action_log('mark_alive', 'Note',
                                    repo='haiti',
                                    detail=record_id,
                                    ip_address='',
                                    Note_text='_test_text',
                                    Note_status='believed_alive')
        db.delete(UserActionLog.all().fetch(10))

        # Set status to is_note_author, but don't check author_made_contact.
        self.s.submit(form,
                      own_info='no',
                      author_name='_test_author',
                      text='_test_text',
                      status='is_note_author')
        self.assert_error_deadend(
            self.s.submit(form,
                          own_info='no',
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
        note = doc.cssselect_one('.status.card')
        options = note.xpath('descendant::select[@name="status"]/option')
        assert len(options) == len(ServerTestsBase.NOTE_STATUS_OPTIONS) - 1
        for option, text in zip(options, ServerTestsBase.NOTE_STATUS_OPTIONS):
            assert text in option.get('value')
            assert option.get('value') != 'believed_dead'

        # Create a record with no status and get the new record's ID.
        form = doc.cssselect_one('form')
        doc = self.s.submit(form,
                            own_info='no',
                            given_name='_test_given',
                            family_name='_test_family',
                            author_name='_test_author',
                            text='_test_text')
        view_url = self.s.url
        url_parts = list(urlparse.urlparse(view_url))
        record_id = dict(urlparse.parse_qsl(url_parts[4]))['id']

        # Check that the believed_dead option does not appear
        # on the view page.
        self.s.go(view_url)
        doc = self.go_to_add_note_page()
        note = doc.cssselect_one('.create.note')
        options = note.xpath('descendant::select[@name="status"]/option')
        assert len(options) == len(ServerTestsBase.NOTE_STATUS_OPTIONS) - 1
        for option, text in zip(options, ServerTestsBase.NOTE_STATUS_OPTIONS):
            assert text in option.get('value')
            assert option.get('value') != 'believed_dead'

        # Advance the clock. Same as above.
        self.advance_utcnow(seconds=1)

        # Set the status in a note and check that it appears on the view page.
        self.s.submit(
            self.s.doc.cssselect_one('form'),
            own_info='no',
            author_name='_test_author2',
            text='_test_text',
            status='believed_alive')
        doc = self.s.go(view_url)
        note = doc.cssselect('.view.note')[-1]
        note_attrs = get_all_attrs(note)
        assert [v for k, v in note_attrs if 'believed_alive' in v], note_attrs
        assert not [v for k, v in note_attrs if 'believed_dead' in v], \
                note_attrs

        # Check that a UserActionLog entry was created.
        self.verify_user_action_log('mark_alive', 'Note',
                                    repo='japan',
                                    detail=record_id,
                                    ip_address='',
                                    Note_text='_test_text',
                                    Note_status='believed_alive')
        db.delete(UserActionLog.all().fetch(10))

        # Advance the clock. Same as above.
        self.advance_utcnow(seconds=1)

        # Set status to believed_dead, but allow_believed_dead_via_ui is false.
        doc = self.go_to_add_note_page()
        self.assert_error_deadend(
            self.s.submit(self.s.doc.cssselect_one('form'),
                          own_info='no',
                          author_name='_test_author',
                          text='_test_text',
                          status='believed_dead'),
            'Not authorized', 'believed_dead')

        # Check that a UserActionLog entry was not created.
        assert not UserActionLog.all().get()

    def test_api_write_pfif_1_4(self):
        """Post a single entry as PFIF 1.4 using the upload API."""
        data = self.get_test_data('test.pfif-1.4.xml')
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

    def test_api_write_pfif_1_2(self):
        """Post a single entry as PFIF 1.2 using the upload API."""
        data = self.get_test_data('test.pfif-1.2.xml')
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
        self.configure_api_logging()
        Person(key_name='haiti:test.google.com/person.21009',
               repo='haiti',
               full_name='_test_full_name_1',
               entry_date=datetime.datetime(2001, 1, 1, 1, 1, 1)).put()
        Person(key_name='haiti:test.google.com/person.21010',
               repo='haiti',
               full_name='_test_full_name_2',
               entry_date=datetime.datetime(2002, 2, 2, 2, 2, 2)).put()

        data = self.get_test_data('test.pfif-1.2-note.xml')
        self.go('/haiti/api/write?key=test_key',
                data=data, type='application/xml')

        self.verify_api_log(ApiActionLog.WRITE)

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
        data = self.get_test_data('test.pfif-1.1.xml')
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
        data = self.get_test_data('test.pfif-1.2.xml')
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
        person_status = doc.xpath(
                '//status:write', namespaces=PFIF_NAMESPACES)[0]
        self.assertEquals(person_status.xpath(
            'status:written', namespaces=PFIF_NAMESPACES)[0].text, '1')

        # An empty Person entity should be in the datastore.
        person = Person.get('haiti', 'test.google.com/person.empty')

    def test_api_write_wrong_domain(self):
        """Attempt to post an entry with a domain that doesn't match the key."""
        data = self.get_test_data('test.pfif-1.2.xml')
        doc = self.go('/haiti/api/write?key=other_key',
                      data=data, type='application/xml')

        # The Person record should have been rejected.
        person_status = doc.xpath(
                '//status:write', namespaces=PFIF_NAMESPACES)[0]
        assert person_status.xpath(
                'status:written', namespaces=PFIF_NAMESPACES)[0].text == '0'
        assert ('Not in authorized domain' in
                person_status.xpath(
                    '*/status:error', namespaces=PFIF_NAMESPACES)[0].text)

        # Both of the Note records should have been rejected.
        note_status = doc.xpath('//status:write', namespaces=PFIF_NAMESPACES)[1]
        assert note_status.xpath(
                'status:written', namespaces=PFIF_NAMESPACES)[0].text == '0'
        first_error = note_status.xpath(
                '*/status:error', namespaces=PFIF_NAMESPACES)[0]
        second_error = note_status.xpath(
                '*/status:error', namespaces=PFIF_NAMESPACES)[1]
        assert 'Not in authorized domain' in first_error.text
        assert 'Not in authorized domain' in second_error.text

    def test_api_write_log_skipping(self):
        """Test skipping bad note entries."""
        self.configure_api_logging()
        data = self.get_test_data('test.pfif-1.2-badrecord.xml')
        self.go('/haiti/api/write?key=test_key',
                data=data, type='application/xml')
        assert self.s.status == 200, \
            'status = %s, content=%s' % (self.s.status, self.s.content)
        # verify we logged the write.
        self.verify_api_log(ApiActionLog.WRITE, person_records=1, people_skipped=1)

    def test_api_write_reviewed_note(self):
        """Post reviewed note entries."""
        data = self.get_test_data('test.pfif-1.2.xml')
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
        data = self.get_test_data('test.pfif-1.2.xml')
        self.go('/haiti/api/write?key=test_key',
                data=data, type='application/xml')

        # Test authorized key.
        data = self.get_test_data('test.pfif-1.2-believed-dead.xml')
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
        person_status = doc.xpath(
                'status:write', namespaces=PFIF_NAMESPACES)[0]
        assert person_status.xpath(
                'status:written', namespaces=PFIF_NAMESPACES)[0].text == '0'
        # The Note record should be rejected with error message
        note_status = doc.xpath('//status:write', namespaces=PFIF_NAMESPACES)[1]
        assert note_status.xpath(
                'status:parsed', namespaces=PFIF_NAMESPACES)[0].text == '1'
        assert note_status.xpath(
                'status:written', namespaces=PFIF_NAMESPACES)[0].text == '0'
        assert ('Not authorized to post notes with the status \"believed_dead\"'
                in note_status.xpath('*/status:error',
                    namespaces=PFIF_NAMESPACES)[0].text)

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
        self.configure_api_logging()
        self.go('/haiti/api/subscribe?key=subscribe_key', data=data)
        # verify we logged the subscribe.
        self.verify_api_log(ApiActionLog.SUBSCRIBE, api_key='subscribe_key')

        subscriptions = person.get_subscriptions()
        assert 'Success' in self.s.content
        assert len(subscriptions) == 1
        assert subscriptions[0].email == SUBSCRIBE_EMAIL
        assert subscriptions[0].language == 'en'
        self.verify_email_sent()
        message = self.mail_server.messages[0]
        payload = self.get_email_payload(message)

        assert message['to'] == [SUBSCRIBE_EMAIL]
        assert 'do-not-reply@' in message['from']
        assert '_test_full_name' in payload
        assert 'view?id=test.google.com%2Fperson.111' in payload

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
        self.configure_api_logging()
        self.go('/haiti/api/unsubscribe?key=subscribe_key', data=data)
        assert 'Success' in self.s.content
        assert len(person.get_subscriptions()) == 0

        # verify we logged the unsub.
        self.verify_api_log(ApiActionLog.UNSUBSCRIBE, api_key='subscribe_key')

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
        self.configure_api_logging()

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
            assert 'xmlns:gpf' in doc.content

        finally:
            config.set_for_repo('haiti', read_auth_key_required=False)


    def test_api_read_with_non_ascii(self):
        """Fetch a record containing non-ASCII characters using the read API.
        This tests PFIF 1.1 - 1.4."""
        expiry_date = ServerTestsBase.TEST_DATETIME + datetime.timedelta(days=1)
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            entry_date=ServerTestsBase.TEST_DATETIME,
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
                      '&version=1.1')
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
'''.decode('utf-8')
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # Fetch a PFIF 1.2 document.
        self.configure_api_logging()
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
''', doc.content.encode('utf-8'))
        # verify the self.log was written.
        self.verify_api_log(ApiActionLog.READ, api_key='')

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
'''.decode('utf-8')
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
'''.decode('utf-8')
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
        self.s.submit(self.s.doc.cssselect_one('form'),
                      own_info='no',
                      given_name='_search_given_name',
                      family_name='_search_1st_family_name',
                      author_name='_search_1st_author_name')
        # Add a note for this person.
        self.go_to_add_note_page()
        self.s.submit(self.s.doc.cssselect_one('form'),
                      own_info='no',
                      author_made_contact='yes',
                      text='this is text for first person',
                      author_name='_search_1st_note_author_name')
        # Add a 2nd person with same given name but different family name.
        self.go('/haiti/create')
        self.s.submit(self.s.doc.cssselect_one('form'),
                      own_info='no',
                      given_name='_search_given_name',
                      family_name='_search_2nd_family_name',
                      author_name='_search_2nd_author_name')
        form_params = get_form_params(self.s.doc.cssselect_one('form'))
        record_id_2 = form_params['id']
        # Add a note for this 2nd person.
        self.go_to_add_note_page()
        self.s.submit(self.s.doc.cssselect_one('form'),
                      own_info='no',
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
            self.configure_api_logging()
            doc = self.go('/haiti/api/search?key=search_key' +
                          '&q=_search_1st_family_name')
            assert self.s.status not in [403, 404]
            # verify we logged the search.
            self.verify_api_log(ApiActionLog.SEARCH, api_key='search_key')

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
            assert self.s.status not in [403, 404]
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


    def verify_sms_response(
            self, message_text, phone_number, path, expected_response_code,
            expected_response):
        request_data = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<request>'
            '    <message_text>%(message_text)s</message_text>'
            '    <receiver_phone_number>%(phone_number)s</receiver_phone_number>'
            '</request>' % {
                'message_text': message_text, 'phone_number': phone_number})
        doc = self.go(path, data=request_data, type='application/xml')
        assert self.s.status == expected_response_code
        if expected_response_code == 200:
            expected_data = (
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<response>\n'
                '  <message_text>%s</message_text>\n'
                '</response>\n') % expected_response
            assert doc.content == expected_data
        else:
            assert expected_response in doc.content


    def test_sms_api_search(self):
        """Tests the search function of the SMS API."""
        self.setup_person_and_note()

        config.set(sms_number_to_repo={'+12345678901': 'haiti'})
        config.set(enable_sms_record_input=False)

        self.verify_sms_response(
            message_text='Search _test_family_name',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=200,
            expected_response='_test_given_name _test_family_name / '
                 'Someone has received information that this person is alive / '
                 'female / 52 / From: _test_home_city _test_home_state ## '
                 'More at: google.org/personfinder/haiti?ui=light ## '
                 'All data entered in Person Finder is available to the public '
                 'and usable by anyone. Google does not review or verify the '
                 'accuracy of this data google.org/personfinder/global/tos')
        self.verify_sms_response(
            message_text='Search _non_existent_family_name',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=200,
            expected_response='No results found for: _non_existent_family_name '
                 '## More at: google.org/personfinder/haiti?ui=light ## '
                 'All data entered in Person Finder is available to the public '
                 'and usable by anyone. Google does not review or verify the '
                 'accuracy of this data google.org/personfinder/global/tos')
        self.verify_sms_response(
            message_text='Hello',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=200,
            expected_response='Usage: &quot;Search John&quot;')


    def test_sms_api_add(self):
        """Tests the add function of the SMS API."""
        self.setup_person_and_note()

        config.set(sms_number_to_repo={'+12345678901': 'haiti'})
        config.set(enable_sms_record_input=True)

        self.verify_sms_response(
            message_text='I am Gilbert Smith',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=200,
            expected_response='Added a record for: Gilbert Smith')
        self.verify_sms_response(
            message_text='Hello',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=200,
            expected_response='Usage: &quot;Search John&quot; OR &quot;I am '
                'John&quot;')
        db_res = indexing.search('haiti', TextQuery('Gilbert Smith'), 1)
        assert len(db_res) == 1


    def test_sms_non_english(self):
        """Tests the SMS API in languages other than English."""
        self.setup_person_and_note()

        config.set(sms_number_to_repo={'+12345678901': 'haiti'})
        config.set(enable_sms_record_input=True)

        self.verify_sms_response(
            message_text='buscar _test_family_name',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=200,
            expected_response='_test_given_name _test_family_name / Alguien '
                 'tiene informacion de que esta persona esta viva / mujer / 52 '
                 '/ De: _test_home_city _test_home_state ## Mas en: '
                 'google.org/personfinder/haiti?ui=light ## Toda la '
                 'informacion ingresada en Person Finder esta disponible de '
                 'forma publica y puede ser usada por cualquier persona. '
                 'Google no revisa o verifica la veracidad de la informacion '
                 'google.org/personfinder/global/tos')
        self.verify_sms_response(
            message_text='Yo soy Arturo Gutierrez',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=200,
            expected_response='Se ha anadido un registro para Arturo Gutierrez')
        self.verify_sms_response(
            message_text='chache _test_family_name',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=200,
            expected_response='_test_given_name _test_family_name / Gen yon '
                 'moun ki resevwa enfomasyon moun sa an vi / fi / 52 / Soti '
                 'nan: _test_home_city _test_home_state ## Plis nan: '
                 'google.org/personfinder/haiti?ui=light ## Tout done yo te '
                 'antre nan Cheche Moun la disponib ak piblik la ak nenpot '
                 'moun ka itilize. Google pa revize oswa verifye presizyon nan '
                 'done sa a google.org/personfinder/global/tos')
        self.verify_sms_response(
            message_text='mwen se Rene Martin',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=200,
            expected_response='Nou ajoute nan list la: Rene Martin')
        self.verify_sms_response(
            message_text='chercher _test_family_name',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=200,
            expected_response='_test_given_name _test_family_name / '
                 'Quelqu&#39;un a recu des informations indiquant que cette '
                 'personne est en vie. / femme / 52 / De : _test_home_city '
                 '_test_home_state ## Plus d&#39;informations a l&#39;adresse '
                 'google.org/personfinder/haiti?ui=light ## Toutes les donnees '
                 'saisies dans l&#39;outil Recherche de personnes sont '
                 'accessibles au public et utilisables par tous. Google ne '
                 'revise pas ces donnees et ne verifie pas leur exactitude '
                 '(google.org/personfinder/global/tos).')
        self.verify_sms_response(
            message_text='je suis Christophe Macron',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=200,
            expected_response='Une fiche sur Christophe Macron a ete ajoutee')
        db_res = indexing.search('haiti', TextQuery('Arturo Gutierrez'), 1)
        assert len(db_res) == 1
        db_res = indexing.search('haiti', TextQuery('Rene Martin'), 1)
        assert len(db_res) == 1
        db_res = indexing.search('haiti', TextQuery('Christophe Macron'), 1)
        assert len(db_res) == 1


    def test_sms_altogether_invalid(self):
        """Tests SMS API requests that are completely invalid."""
        self.setup_person_and_note()

        config.set(sms_number_to_repo={'+12345678901': 'haiti'})
        config.set(enable_sms_record_input=False)

        self.verify_sms_response(
            message_text='Hello',
            phone_number='+10987654321',
            path='/global/api/handle_sms?key=sms_key&lang=en',
            expected_response_code=400,
            expected_response= 'You&#39;ve reached Person Finder, but '
                'there&#39;s not a repository assigned for +10987654321.')
        self.verify_sms_response(
            message_text='Search _test_family_name',
            phone_number='+12345678901',
            path='/global/api/handle_sms?lang=en',
            expected_response_code=403,
            expected_response='&#39;key&#39; URL parameter is either missing, '
                'invalid or lacks required permissions. The key&#39;s repo '
                'must be &#39;*&#39;, search_permission must be True, and it '
                'must have write permission with domain name &#39;*&#39;.')
        self.verify_sms_response(
            message_text='Search _test_family_name',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=global_test_key&lang=en',
            expected_response_code=403,
            expected_response='&#39;key&#39; URL parameter is either missing, '
                'invalid or lacks required permissions. The key&#39;s repo '
                'must be &#39;*&#39;, search_permission must be True, and it '
                'must have write permission with domain name &#39;*&#39;.')
        self.verify_sms_response(
            message_text='Search _test_family_name',
            phone_number='+12345678901',
            path='/global/api/handle_sms?key=search_key&lang=en',
            expected_response_code=403,
            expected_response='&#39;key&#39; URL parameter is either missing, '
                'invalid or lacks required permissions. The key&#39;s repo '
                'must be &#39;*&#39;, search_permission must be True, and it '
                'must have write permission with domain name &#39;*&#39;.')


    def test_person_feed(self):
        """Fetch a single person using the PFIF Atom feed."""
        self.configure_api_logging()
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
        self.verify_api_log(ApiActionLog.READ, api_key='')

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
        # See: https://www.w3.org/TR/REC-xml/#charsets
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
'''.decode('utf-8') % (self.hostport, self.hostport, self.hostport,
        self.hostport, self.hostport)
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
        url, status, message, headers, content = scrape.fetch(
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
            entry_date=ServerTestsBase.TEST_DATETIME,
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
            entry_date=ServerTestsBase.TEST_DATETIME
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
            entry_date=ServerTestsBase.TEST_DATETIME
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
            entry_date=ServerTestsBase.TEST_DATETIME,
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
        # verify no extend button for clone record
        assert not doc.cssselect('#extend-btn')

        # Check that the deletion confirmation page shows the right message.
        doc = self.s.follow(doc.cssselect_one('#delete-btn'))
        assert 'we might later receive another copy' in doc.text

        # Click the button to delete a record.
        button = doc.xpath_one('//input[@value="Yes, delete the record"]')
        doc = self.s.submit(button, faked_captcha_response='failure')

        # Check to make sure that the user was redirected to the same page due
        # to an invalid captcha.
        assert 'delete the record for "_test_given_name ' + \
               '_test_family_name"' in doc.text

        # Continue with a valid captcha (faked, for purpose of test). Check the
        # sent messages for proper notification of related e-mail accounts.
        doc = self.go(
            '/haiti/delete',
            data='id=test.google.com/person.123&' +
                 'reason_for_deletion=spam_received&' +
                 'faked_captcha_response=success')

        # Both entities should be gone.
        assert not db.get(person.key())
        assert not db.get(note.key())

        # Clone deletion cannot be undone, so no e-mail should have been sent.
        assert len(self.mail_server.messages) == 0

    def test_expire_clone(self):
        """Confirms that an expiring delete clone record behaves properly."""
        person, note = self.setup_person_and_note('test.google.com')
        person.original_creation_date = person.source_date
        person.put()

        # Check that they exist
        p123_id = 'test.google.com/person.123'
        self.advance_utcnow(days=40)
        # Both entities should be there.
        assert db.get(person.key())
        assert db.get(note.key())

        doc = self.go('/haiti/view?id=' + p123_id)
        self.advance_utcnow(days=1)  # past the default 40-day expiry period
        # run the process_expirations task
        doc = self.run_task('/haiti/tasks/process_expirations')
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
        assert person.original_creation_date == ServerTestsBase.TEST_DATETIME, '%s != %s' % (
            person.original_creation_date, ServerTestsBase.TEST_DATETIME)

        self.advance_utcnow(days=11)  # past the configured 10-day expiry period
        # run the process_expirations task
        doc = self.run_task('/haiti/tasks/process_expirations')
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
            assert doc.content_bytes == 'xyz'
            # Should not be available in a different repo.
            self.go('/pakistan/photo?id=%s' % id)
            assert self.s.status == 404

    def test_extend_expiry(self):
        """Verify that extension of the expiry date works as expected."""
        person, note = self.setup_person_and_note()
        expiry_date = ServerTestsBase.TEST_DATETIME + datetime.timedelta(days=18)
        person.expiry_date = expiry_date
        db.put([person])

        # Advance time to within one day of expiry.
        self.advance_utcnow(days=17, seconds=1)
        # There should be an expiration warning.
        doc = self.go('/haiti/view?id=' + person.record_id)
        assert 'Warning: this record will expire' in doc.text
        # Click the extend button.
        doc = self.s.follow(doc.cssselect_one('#extend-btn'))
        assert 'extend the expiration' in doc.text
        # Click the button on the confirmation page.
        button = doc.xpath_one('//input[@value="Yes, extend the record"]')
        doc = self.s.submit(button, faked_captcha_response='failure')
        # Verify that we failed the captcha.
        assert 'extend the expiration' in doc.text
        # Simulate passing the captcha.
        doc = self.go('/haiti/extend',
                      data='id=' + str(person.record_id) +
                           '&faked_captcha_response=success')
        # Verify that the expiry date was extended.
        person = Person.get('haiti', person.record_id)
        self.assertEquals(expiry_date + datetime.timedelta(days=60),
                          person.expiry_date)
        # Verify that the expiration warning is gone.
        doc = self.go('/haiti/view?id=' + person.record_id)
        assert 'Warning: this record will expire' not in doc.text

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

        create_form = doc.cssselect_one('form')
        # Submit the create form with complete information.
        # Note contains bad words
        self.s.submit(create_form,
                      own_info='no',
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
        author_email = self.s.doc.cssselect_one('input#author_email')
        button = self.s.doc.xpath_one('//input[@value="Send email"]')
        doc = self.s.submit(button,
                            own_info='no',
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
        self.verify_user_action_log('add', 'NoteWithBadWords', repo='haiti')

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
        self.verify_user_action_log('mark_dead', 'Note', repo='haiti',
                                    entity_key_name=keyname)

        # Add a note with bad words to the existing person record.
        doc = self.s.go(view_url)
        doc = self.go_to_add_note_page()

        self.s.submit(doc.cssselect_one('form'),
                      own_info='no',
                      author_name='_test_author2',
                      text='_test add note with bad words.',
                      status='believed_alive')

        # Ask for author's email address.
        assert 'enter your e-mail address below' in self.s.doc.text
        assert 'author_email' in self.s.doc.content
        author_email = self.s.doc.cssselect_one('input#author_email')
        button = self.s.doc.xpath_one('//input[@value="Send email"]')
        doc = self.s.submit(button,
                            own_info='no',
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
        self.verify_user_action_log('add', 'NoteWithBadWords', repo='haiti')

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
        self.verify_user_action_log('mark_alive', 'Note', repo='haiti',
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
        doc = self.s.follow(doc.cssselect_one('#delete-btn'))
        assert 'delete the record for "_test_given_name ' + \
               '_test_family_name"' in doc.text, utils.encode(doc.text)
        button = doc.xpath_one('//input[@value="Yes, delete the record"]')
        doc = self.s.submit(button, faked_captcha_response='failure')

        # Check to make sure that the user was redirected to the same page due
        # to an invalid captcha.
        assert 'delete the record for "_test_given_name ' + \
               '_test_family_name"' in doc.text
        assert 'The record has been deleted' not in doc.text

        # Continue with a valid captcha (faked, for purpose of test). Check the
        # sent messages for proper notification of related e-mail accounts.
        doc = self.go(
            '/haiti/delete',
            data='id=haiti.personfinder.google.org/person.123&' +
                 'reason_for_deletion=spam_received&' +
                 'faked_captcha_response=success')
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
        self.verify_user_action_log('delete', 'Person', repo='haiti',
            entity_key_name='haiti:haiti.personfinder.google.org/person.123',
            detail='spam_received')

        assert db.get(photo.key())
        assert db.get(note_photo.key())

        # Search for the record. Make sure it does not show up.
        doc = self.go('/haiti/results?role=seek&' +
                      'query_name=_test_given_name+_test_family_name&query_location=')
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
        form = [f for f in doc.cssselect('form') if
                f.get('action').endswith('/restore')][0]
        doc = self.s.submit(
            form, own_info='no', faked_captcha_response='success')
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
                      'query_name=_test_given_name+_test_family_name&query_location=')
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
      <pfif:sex>female</pfif:sex>
      <pfif:age>52</pfif:age>
      <pfif:home_city>_test_home_city</pfif:home_city>
      <pfif:home_state>_test_home_state</pfif:home_state>
      <pfif:photo_url>_test_photo_url</pfif:photo_url>
      <pfif:note>
        <pfif:note_record_id>haiti.personfinder.google.org/note.456</pfif:note_record_id>
        <pfif:person_record_id>haiti.personfinder.google.org/person.123</pfif:person_record_id>
        <pfif:entry_date>2010-01-01T00:00:00Z</pfif:entry_date>
        <pfif:author_name></pfif:author_name>
        <pfif:source_date>2010-01-01T00:00:00Z</pfif:source_date>
        <pfif:status>believed_alive</pfif:status>
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
                           'reason_for_deletion=spam_received&' +
                           'faked_captcha_response=success')

        # Run the expirations processing task.
        doc = self.run_task('/haiti/tasks/process_expirations')

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
                      'query_name=_test_given_name+_test_family_name&query_location=')
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
        doc = self.run_task('/haiti/tasks/process_expirations')

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
                      'query_name=_test_given_name+_test_family_name&query_location=')
        assert 'No results found' in doc.text

    def test_add_note_for_deleted_person(self):
        """Tries to add a note to a person record which has been deleted.
        It should fail.
        """
        person, note = self.setup_person_and_note()
        view_doc = self.go('/haiti/view?id=%s' % person.person_record_id)

        # Delete the record with a faked captcha.
        doc = self.go(
            '/haiti/delete',
            data=('id=%s&reason_for_deletion=spam_received&' +
                  'faked_captcha_response=success')
                    % person.person_record_id)
        assert 'The record has been deleted' in doc.text

        # Try to add a note to the deleted person. It should fail.
        note_form = view_doc.cssselect_one('form')
        doc = self.s.submit(
            note_form,
            own_info='no',
            text='test text',
            author_name= 'test author',
            author_made_contact= 'no')
        assert self.s.status == 404
        self.assert_error_deadend(
            doc, "This person's entry does not exist or has been deleted.")

    def test_add_note_invalid_email(self):
        """Tries to add a note with an invalid email. It should fail."""
        person = Person(
            key_name='haiti:test.google.com/person.112',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name',
            entry_date=datetime.datetime.utcnow())
        person.update_index(['old', 'new'])
        person.put()

        doc = self.go('/haiti/view?id=test.google.com/person.112')
        add_note_page = self.go_to_add_note_page()
        note_form = add_note_page.cssselect_one('form')
        params = {'own_info': 'no',
                  'given_name': '_test_given',
                  'family_name': '_test_family',
                  'author_name': '_test_author',
                  'text': 'here is some text',
                  'author_email': 'NotAValidEmailAdddress'}
        doc = self.s.submit(note_form, params)
        self.assertEqual(self.s.status, 400)
        expected_err_msg = (
            'The email address you entered appears to be invalid.')
        assert expected_err_msg in doc.content

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

        # Run the expirations processing task.
        self.run_task('/haiti/tasks/process_expirations').content

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
            entry_date=ServerTestsBase.TEST_DATETIME,
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

        button = doc.xpath_one('//input[@value="Yes, update the note"]')
        doc = self.s.submit(button)
        assert 'Notes for this person' in doc.text
        assert 'This note has been marked as spam.' in doc.text
        assert 'Not spam' in doc.text
        assert 'Reveal note' in doc.text

        # When a note is flagged, these new links appear.
        assert doc.cssselect('a#reveal-note')
        assert doc.cssselect('a#hide-note')
        # When a note is flagged, the contents of the note are hidden.
        assert doc.cssselect_one('div.contents').get('style') == \
                'display: none;'

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
        doc_feed_note = self.go(
            '/haiti/feeds/note?person_record_id=test.google.com/person.123')
        assert not doc_feed_note.xpath(
                '//pfif:text', namespaces=PFIF_NAMESPACES)[0].text
        doc_feed_person = self.go( \
            '/haiti/feeds/person?person_record_id=test.google.com/person.123')
        assert not doc_feed_person.xpath(
                '//pfif:note/pfif:text',
                namespaces=PFIF_NAMESPACES)[0].text

        # Unmark the note as spam.
        doc = self.go('/haiti/view?id=test.google.com/person.123')
        doc = self.s.follow('Not spam')
        assert 'Are you sure' in doc.text
        assert 'TestingSpam' in doc.text
        assert 'captcha' in doc.content

        # Make sure it redirects to the same page with error
        doc = self.s.submit(button)
        assert 'Are you sure' in doc.text
        assert 'TestingSpam' in doc.text

        # Simulate successful completion of the Turing test.
        doc = self.s.submit(button, faked_captcha_response='success')
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
            entry_date=utils.get_utcnow(),
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6),
        ), Person(
            key_name='haiti:test.google.com/person.2',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name2',
            entry_date=utils.get_utcnow(),
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6),
        ), Person(
            key_name='haiti:test.google.com/person.3',
            repo='haiti',
            author_name='_test_author_name',
            author_email='test@example.com',
            full_name='_test_full_name3',
            entry_date=utils.get_utcnow(),
            source_date=datetime.datetime(2001, 2, 3, 4, 5, 6),
        ), Note(
            key_name='haiti:test.google.com/note.1',
            repo='haiti',
            person_record_id='test.google.com/person.1',
            text='Testing',
            entry_date=utils.get_utcnow(),
        ), Note(
            key_name='haiti:test.google.com/note.2',
            repo='haiti',
            person_record_id='test.google.com/person.2',
            linked_person_record_id='test.google.com/person.3',
            text='Testing',
            entry_date=utils.get_utcnow(),
        ), Note(
            key_name='haiti:test.google.com/note.3',
            repo='haiti',
            person_record_id='test.google.com/person.3',
            linked_person_record_id='test.google.com/person.2',
            text='Testing',
            entry_date=utils.get_utcnow(),
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
        # Advances the clock so that the new note is shown below the old notes.
        self.advance_utcnow(seconds=1)
        doc = self.go('/haiti/view?id=test.google.com/person.1')
        self.verify_details_page(num_notes=1)
        self.verify_update_notes(False, '_test A note body',
                                 '_test A note author',
                                 status='information_sought')
        self.verify_details_page(num_notes=2)
        self.verify_email_sent()

        # Verify email data
        message = self.mail_server.messages[0]
        payload = self.get_email_payload(message)
        assert message['to'] == [SUBSCRIBER_1]
        assert 'do-not-reply@' in message['from']
        assert '_test_full_name1' in payload
        # Subscription is French, email should be, too
        assert 'recherche des informations' in payload
        assert '_test A note body' in payload
        assert 'view?id=test.google.com%2Fperson.1' in payload

        # Reset the MailThread queue
        self.mail_server.messages = []

        # Visit the multiview page and link Persons 1 and 2
        doc = self.go('/haiti/multiview' +
                      '?id1=test.google.com/person.1' +
                      '&id2=test.google.com/person.2')
        button = doc.xpath_one(
                '//input[@value="Yes, these are the same person"]')
        doc = self.s.submit(button, own_info='no', text='duplicate test', author_name='foo')

        # Verify subscribers were notified
        self.verify_email_sent(2)

        # Verify email details
        messages_by_to = {}
        for message in self.mail_server.messages:
            assert len(message['to']) == 1
            messages_by_to[message['to'][0]] = message
        message_1 = messages_by_to[SUBSCRIBER_1]
        assert 'do-not-reply@' in message_1['from']
        assert '_test_full_name1' in self.get_email_payload(message_1)
        message_2 = messages_by_to[SUBSCRIBER_2]
        assert 'do-not-reply@' in message_2['from']
        assert '_test_full_name2' in self.get_email_payload(message_2)

        # Reset the MailThread queue
        self.mail_server.messages = []

        # Post a note on the person.3 details page and verify that
        # subscribers to Persons 1 and 2 are each notified once.
        doc = self.go('/haiti/view?id=test.google.com/person.3')
        self.verify_update_notes(False, '_test A note body',
                                 '_test A note author',
                                 status='information_sought')
        self.verify_details_page(num_notes=1)
        self.verify_email_sent(2)
        tos = set()
        for message in self.mail_server.messages:
            assert len(message['to']) == 1
            tos.add(message['to'][0])
        assert tos == set([SUBSCRIBER_1, SUBSCRIBER_2])

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
        data = self.get_test_data('test.pfif-1.2-notification.xml')
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
        doc = self.s.follow(doc.cssselect_one('#subscribe-btn'))

        # Empty email is an error.
        button = doc.xpath_one('//input[@value="Subscribe"]')
        doc = self.s.submit(button)
        assert 'Invalid e-mail address. Please try again.' in doc.text
        assert len(person.get_subscriptions()) == 0

        # Invalid captcha response is an error
        self.s.back()
        button = doc.xpath_one('//input[@value="Subscribe"]')
        doc = self.s.submit(
            button,
            own_info='no',
            subscribe_email=SUBSCRIBE_EMAIL,
            faked_captcha_response='failure')
        assert 'iframe' in doc.content
        assert 'g-recaptcha-response' in doc.content
        assert len(person.get_subscriptions()) == 0

        # Invalid email is an error (even with valid captcha)
        INVALID_EMAIL = 'test@example'
        doc = self.s.submit(
            button,
            own_info='no',
            subscribe_email=INVALID_EMAIL,
            faked_captcha_response='success')
        assert 'Invalid e-mail address. Please try again.' in doc.text
        assert len(person.get_subscriptions()) == 0

        # Valid email and captcha is success
        self.s.back()
        doc = self.s.submit(
            button,
            own_info='no',
            subscribe_email=SUBSCRIBE_EMAIL,
            faked_captcha_response='success')
        assert 'successfully subscribed. ' in doc.text
        assert '_test_full_name' in doc.text
        subscriptions = person.get_subscriptions()
        assert len(subscriptions) == 1
        assert subscriptions[0].email == SUBSCRIBE_EMAIL
        assert subscriptions[0].language == 'en'

        self.verify_email_sent()
        message = self.mail_server.messages[0]
        payload = self.get_email_payload(message)

        assert message['to'] == [SUBSCRIBE_EMAIL]
        assert 'do-not-reply@' in message['from']
        assert '_test_full_name' in payload
        assert 'view?id=test.google.com%2Fperson.111' in payload

        # Already subscribed person is shown info page
        self.s.back()
        doc = self.s.submit(
            button,
            own_info='no',
            subscribe_email=SUBSCRIBE_EMAIL,
            faked_captcha_response='success')
        assert 'already subscribed. ' in doc.text
        assert 'for _test_full_name' in doc.text
        assert len(person.get_subscriptions()) == 1

        # Already subscribed person with new language is success
        self.s.back()
        doc = self.s.submit(
            button,
            own_info='no',
            subscribe_email=SUBSCRIBE_EMAIL,
            faked_captcha_response='success',
            lang='fr')
        assert u'maintenant abonn\u00E9' in doc.text
        assert '_test_full_name' in doc.text
        subscriptions = person.get_subscriptions()
        assert len(subscriptions) == 1
        assert subscriptions[0].email == SUBSCRIBE_EMAIL
        assert subscriptions[0].language == 'fr'

        # Test the unsubscribe link in the email
        unsub_url = re.search('(/haiti/unsubscribe.*)', payload).group(1)
        doc = self.go(unsub_url)
        # "You have successfully unsubscribed." in French.
        assert u'Vous vous \u00eates bien d\u00e9sabonn\u00e9.' in doc.content
        assert len(person.get_subscriptions()) == 0

    def test_config_use_family_name(self):
        # use_family_name=True
        d = self.go('/haiti/create')
        assert d.xpath_one('//label[@for="given_name"]').text.strip() == (
            'Given name (First name) (required):')
        assert d.xpath_one('//label[@for="family_name"]').text.strip() == (
            'Family name (Surname) (required):')
        assert d.xpath('//input[@name="given_name"]')
        assert d.xpath('//input[@name="family_name"]')
        assert d.xpath_one('//label[@for="alternate_given_names"]').text.strip() == \
            'Alternate given names:'
        assert d.xpath_one('//label[@for="alternate_family_names"]').text.strip() == \
            'Alternate family names:'
        assert d.xpath('//input[@name="alternate_given_names"]')
        assert d.xpath('//input[@name="alternate_family_names"]')

        self.s.submit(d.cssselect_one('form'),
                      own_info='no',
                      given_name='_test_given',
                      family_name='_test_family',
                      alternate_given_names='_test_alternate_given',
                      alternate_family_names='_test_alternate_family',
                      author_name='_test_author')
        person = Person.all().get()
        d = self.go('/haiti/view?id=%s' % person.record_id)
        self.verify_details_page(
            full_name='_test_given _test_family',
            details={
                'Alternate names:':
                    '_test_alternate_given _test_alternate_family'})

        self.go('/haiti/results?role=seek&'
                'query_name=_test_given+_test_family&query_location=')
        self.verify_results_page(1, all_have=([
            '_test_given _test_family',
            '(_test_alternate_given _test_alternate_family)']))
        person.delete()

        # use_family_name=False
        d = self.go('/pakistan/create')
        assert d.xpath_one('//label[@for="given_name"]').text.strip() == 'Name:'
        assert not d.xpath('//label[@for="family_name"]')
        assert d.xpath('//input[@name="given_name"]')
        assert not d.xpath('//input[@name="family_name"]')
        assert 'Given name' not in d.text
        assert 'Family name' not in d.text

        self.s.submit(d.cssselect_one('form'),
                      own_info='no',
                      given_name='_test_given',
                      family_name='_test_family',
                      author_name='_test_author')
        person = Person.all().get()
        d = self.go(
            '/pakistan/view?id=%s' % person.record_id)
        assert scrape.get_all_text(d.cssselect_one('.full-name')) == (
            '_test_given')
        assert '_test_family' not in d.content

        self.go('/pakistan/results?role=seek&'
                'query_name=_test_given+_test_family&query_location')
        self.verify_results_page(1)
        first_title = get_all_text(self.s.doc.cssselect('.resultDataTitle')[0])
        assert '_test_given' in first_title
        assert '_test_family' not in first_title
        person.delete()


    def test_config_family_name_first(self):
        # family_name_first=True
        doc = self.go('/japan/create?lang=en')
        given_label = doc.xpath_one('//label[@for="given_name"]')
        family_label = doc.xpath_one('//label[@for="family_name"]')
        assert given_label.text.strip() == 'Given name (First name) (required):'
        assert family_label.text.strip() == 'Family name (Surname) (required):'
        assert family_label.sourceline < given_label.sourceline

        given_input = doc.xpath_one('//input[@name="given_name"]')
        family_input = doc.xpath_one('//input[@name="family_name"]')
        assert family_input.sourceline < given_input.sourceline

        alternate_given_label = doc.xpath_one(
                '//label[@for="alternate_given_names"]')
        alternate_family_label = doc.xpath_one(
                '//label[@for="alternate_family_names"]')
        assert alternate_given_label.text.strip() == 'Alternate given names:'
        assert alternate_family_label.text.strip() == 'Alternate family names:'
        assert (alternate_family_label.sourceline <
                alternate_given_label.sourceline)

        alternate_given_input = doc.xpath_one(
            '//input[@name="alternate_given_names"]')
        alternate_family_input = doc.xpath_one(
            '//input[@name="alternate_family_names"]')
        assert (alternate_family_input.sourceline <
                alternate_given_input.sourceline)

        self.s.submit(doc.cssselect_one('form'),
                      own_info='no',
                      given_name='_test_given',
                      family_name='_test_family',
                      alternate_given_names='_test_alternate_given',
                      alternate_family_names='_test_alternate_family',
                      author_name='_test_author')
        person = Person.all().get()

        doc = self.go('/japan/view?id=%s&lang=en' % person.record_id)
        self.verify_details_page(
            full_name='_test_family _test_given',
            details={
                'Alternate names:':
                    '_test_alternate_family _test_alternate_given'})

        self.go('/japan/results?role=seek&'
                'query_name=_test_family+_test_given&lang=en&query_location=')
        self.verify_results_page(1, all_have=([
            '_test_family _test_given',
            '(_test_alternate_family _test_alternate_given)']))
        person.delete()

        # family_name_first=False
        doc = self.go('/haiti/create')
        given_label = doc.xpath_one('//label[@for="given_name"]')
        family_label = doc.xpath_one('//label[@for="family_name"]')
        assert given_label.text.strip() == 'Given name (First name) (required):'
        assert family_label.text.strip() == 'Family name (Surname) (required):'
        assert family_label.sourceline > given_label.sourceline

        given_input = doc.xpath_one('//input[@name="given_name"]')
        family_input = doc.xpath_one('//input[@name="family_name"]')
        assert family_input.sourceline > given_input.sourceline

        alternate_given_label = doc.xpath_one(
                '//label[@for="alternate_given_names"]')
        alternate_family_label = doc.xpath_one(
                '//label[@for="alternate_family_names"]')
        assert alternate_given_label.text.strip() == 'Alternate given names:'
        assert alternate_family_label.text.strip() == 'Alternate family names:'
        assert (alternate_family_label.sourceline >
                alternate_given_label.sourceline)

        alternate_given_input = doc.xpath_one(
            '//input[@name="alternate_given_names"]')
        alternate_family_input = doc.xpath_one(
            '//input[@name="alternate_family_names"]')
        assert (alternate_family_input.sourceline >
                alternate_given_input.sourceline)

        self.s.submit(doc.cssselect_one('form'),
                      own_info='no',
                      given_name='_test_given',
                      family_name='_test_family',
                      alternate_given_names='_test_alternate_given',
                      alternate_family_names='_test_alternate_family',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/haiti/view?id=%s' % person.record_id)
        self.verify_details_page(
            full_name='_test_given _test_family',
            details={
                'Alternate names:':
                    '_test_alternate_given _test_alternate_family'})

        self.go('/haiti/results?role=seek&'
                'query_name=_test_given+_test_family&query_location')
        self.verify_results_page(1, all_have=([
            '_test_given _test_family',
            '(_test_alternate_given _test_alternate_family)']))
        person.delete()

    def test_config_use_alternate_names(self):
        # use_alternate_names=True
        config.set_for_repo('haiti', use_alternate_names=True)
        d = self.go('/haiti/create')
        assert d.xpath_one(
                '//label[@for="alternate_given_names"]').text.strip() == \
                        'Alternate given names:'
        assert d.xpath_one(
                '//label[@for="alternate_family_names"]').text.strip() == \
                        'Alternate family names:'
        assert d.xpath('//input[@name="alternate_given_names"]')
        assert d.xpath('//input[@name="alternate_family_names"]')

        self.s.submit(d.cssselect_one('form'),
                      own_info='no',
                      given_name='_test_given',
                      family_name='_test_family',
                      alternate_given_names='_test_alternate_given',
                      alternate_family_names='_test_alternate_family',
                      author_name='_test_author')
        person = Person.all().get()
        d = self.go('/haiti/view?id=%s' % person.record_id)
        self.verify_details_page(
            details={
                'Alternate names:':
                    '_test_alternate_given _test_alternate_family'})

        self.go('/haiti/results?role=seek&'
                'query_name=_test_given+_test_family&query_location=')
        self.verify_results_page(1, all_have=([
            '_test_given _test_family',
            '(_test_alternate_given _test_alternate_family)']))
        person.delete()

        # use_alternate_names=False
        config.set_for_repo('pakistan', use_alternate_names=False)
        d = self.go('/pakistan/create')
        assert not d.xpath('//label[@for="alternate_given_names"]')
        assert not d.xpath('//label[@for="alternate_family_names"]')
        assert not d.xpath('//input[@name="alternate_given_names"]')
        assert not d.xpath('//input[@name="alternate_family_names"]')
        assert 'Alternate given names' not in d.text
        assert 'Alternate family names' not in d.text

        self.s.submit(d.cssselect_one('form'),
                      own_info='no',
                      given_name='_test_given',
                      family_name='_test_family',
                      alternate_given_names='_test_alternate_given',
                      alternate_family_names='_test_alternate_family',
                      author_name='_test_author')
        person = Person.all().get()
        d = self.go(
            '/pakistan/view?id=%s' % person.record_id)
        assert all(
            scrape.get_all_text(e) != 'Alternate names:'
            for e in d.cssselect('.label'))
        assert '_test_alternate_given' not in d.text
        assert '_test_alternate_family' not in d.text

        self.go('/pakistan/results?role=seek&query_name=_test_given+_test_family&query_location=')
        self.verify_results_page(1)
        first_title = get_all_text(self.s.doc.cssselect('.resultDataTitle')[0])
        assert '_test_given' in first_title
        assert '_test_alternate_given' not in first_title
        assert '_test_alternate_family' not in first_title
        person.delete()


    def test_search_name_and_location(self):
        # enable_fulltext_search=True
        config.set(enable_fulltext_search=True)
        d = self.go('/haiti/create')
        assert d.xpath('//input[@name="given_name"]')
        assert d.xpath('//input[@name="family_name"]')
        assert d.xpath('//label[@for="home_neighborhood"]')
        assert d.xpath('//input[@name="home_neighborhood"]')
        assert d.xpath('//label[@for="home_city"]')
        assert d.xpath('//input[@name="home_city"]')
        assert d.xpath('//label[@for="home_state"]')
        assert d.xpath('//input[@name="home_state"]')
        assert d.xpath('//label[@for="home_country"]')
        assert d.xpath('//input[@name="home_country"]')
        # Submit a person record.
        self.s.submit(d.cssselect_one('form'),
                      given_name='_test_given',
                      family_name='_test_family',
                      home_neighborhood='_test_home_neighborhood',
                      home_city='_test_home_city',
                      home_state='_test_home_state',
                      home_country='_test_home_country',
                      author_name='_test_author')
        person = Person.all().get()
        self.go('/haiti/results?role=seek&'
                'query_name=_test_given+_test_family&'
                'query_location=_test_home_neighborhood+_test_home_city+'
                '_test_home_state+_test_home_country')
        self.verify_results_page(1)
        person.delete()


    def test_config_allow_believed_dead_via_ui(self):
        # allow_believed_dead_via_ui=True
        config.set_for_repo('haiti', allow_believed_dead_via_ui=True)
        doc = self.go('/haiti/create')
        self.s.submit(doc.cssselect_one('form'),
                      own_info='no',
                      given_name='_test_given',
                      family_name='_test_family',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/haiti/add_note?id=%s' % person.record_id)
        assert doc.cssselect('option[value="believed_dead"]')

        # allow_believed_dead_via_ui=False
        config.set_for_repo('japan', allow_believed_dead_via_ui=False)
        doc = self.go('/japan/create')
        self.s.submit(doc.cssselect_one('form'),
                      own_info='no',
                      given_name='_test_given',
                      family_name='_test_family',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/japan/add_note?id=%s' % person.record_id)
        assert not doc.cssselect('option[value="believed_dead"]')


    def test_config_use_postal_code(self):
        # use_postal_code=True
        doc = self.go('/haiti/create')
        assert doc.xpath('//label[@for="home_postal_code"]')
        assert doc.xpath('//input[@name="home_postal_code"]')

        self.s.submit(doc.cssselect_one('form'),
                      own_info='no',
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
        assert not doc.xpath('//label[@for="home_postal_code"]')
        assert not doc.xpath('//input[@name="home_postal_code"]')

        self.s.submit(doc.cssselect_one('form'),
                      own_info='no',
                      given_name='_test_given',
                      family_name='_test_family',
                      home_postal_code='_test_12345',
                      author_name='_test_author')
        person = Person.all().get()
        doc = self.go('/pakistan/view?id=%s' % person.record_id)
        assert 'Postal or zip code' not in doc.text
        assert '_test_12345' not in doc.text
        person.delete()

    def test_repo_alias(self):
        config.set(repo_aliases={'jp': 'japan'})

        self.go('/jp/', redirects=0)
        self.assertEqual(self.s.status, 302)
        self.assertEqual(self.s.headers['location'], self.path_to_url('/japan/'))

        # With an action and query parameters.
        self.go('/jp/view?id=123&ui=light', redirects=0)
        self.assertEqual(self.s.status, 302)
        self.assertEqual(
            self.s.headers['location'],
            self.path_to_url('/japan/view?id=123&ui=light'))

        # No redirect.
        self.go('/japan/', redirects=0)
        self.assertEqual(self.s.status, 200)

    def test_create_with_invalid_email(self):
        doc = self.go('/haiti/create')
        doc = self.s.submit(
            doc.cssselect_one('form'),
            own_info='no',
            given_name='_test_given',
            family_name='_test_family',
            home_postal_code='_test_12345',
            author_name='_test_author',
            author_email='NotAValidEmailAddress')
        self.assertEqual(self.s.status, 400)
        expected_err_msg = (
            'The email address you entered appears to be invalid.')
        assert expected_err_msg in doc.content

    def test_create_and_seek_with_nondefault_charset(self):
        """Follow the basic create/seek flow with non-default charset
        (Shift_JIS).

        Verify:
        - "charsets" query parameter is passed around
        - Query parameters (encoded in Shift_JIS) are handled correctly
        """

        # Japanese translation of "I have information about someone"
        ja_i_have_info = (
            u'\u5b89\u5426\u60c5\u5831\u3092\u63d0\u4f9b\u3059\u308b')
        # Japanese translation of "I'm looking for someone"
        ja_looking_for_someone = (
            u'\u4eba\u3092\u63a2\u3057\u3066\u3044\u308b')
        test_given_name = u'\u592a\u90ce'
        test_family_name = u'\u30b0\u30fc\u30b0\u30eb'

        # Shorthand to assert the correctness of our URL
        def assert_params(url=None):
            self.assert_params_conform(
                url or self.s.url, {'charsets': 'shift_jis'})

        # Start on the home page and click the
        # "I have information about someone" button
        self.go('/haiti?lang=ja&charsets=shift_jis')
        query_page = self.s.follow(ja_i_have_info)
        assert_params()
        query_form = query_page.cssselect_one('form')

        # Input a given name and a family name.
        create_page = self.s.submit(
                query_form,
                given_name=test_given_name,
                family_name=test_family_name)
        assert_params()
        create_form = create_page.cssselect_one('form')

        # Submit a person record.
        self.s.submit(create_form,
                      own_info='no',
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
        search_form = search_page.cssselect_one('form')

        # Search for the record just submitted.
        self.s.submit(
            search_form, query_name=u'%s %s' % (test_given_name, test_family_name))
        assert_params()
        self.verify_results_page(1, all_have=([test_given_name]),
                                 some_have=([test_given_name]))

        self.verify_click_search_result(0, assert_params)

    def test_http_get_for_api_write(self):
        """Test that sending HTTP GET request to api/write results in an error
        with HTTP status code 405. api/write only supports HTTP POST.

        It returns 405 because api.Write.get() doesn't exist, so
        utils.BaseHandler.get() is called.
        """

        doc = self.go('/haiti/api/write?key=domain_test_key')
        assert self.s.status == 405

    def test_cssselect(self):
        """Test that Document.cssselect works. May delete later.
        """
        doc = self.go('/haiti/')
        assert doc.cssselect_one('div.subtitle-bar').text.strip() == 'Haiti Earthquake'

    def test_xpath(self):
        """Test that Document.xpath works. May delete later.
        """
        doc = self.go('/haiti/')
        assert doc.cssselect_one('div.subtitle-bar').text.strip() == 'Haiti Earthquake'
