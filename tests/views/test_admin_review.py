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


"""Tests for the admin review page."""

import django
import django.http
import django.test

import model

import view_tests_base


class AdminReviewViewTests(view_tests_base.ViewTestsBase):
    """Tests the admin review view."""

    def setUp(self):
        super(AdminReviewViewTests, self).setUp()
        self.data_generator.repo()
        self.person = self.data_generator.person()
        self.login_as_moderator()

    def test_get_no_notes(self):
        """Tests GET requests when there are no notes."""
        resp = self.client.get('/haiti/admin/review', secure=True)
        self.assertEqual(len(resp.context['notes']), 0)
        self.assertEqual(resp.context['next_url'], None)
        self.assertEqual(resp.context['source_options_nav'][0][0], 'all')
        self.assertEqual(resp.context['source_options_nav'][0][1], None)
        self.assertEqual(
            resp.context['source_options_nav'][1][0],
            'haiti.personfinder.google.org')
        self.assertEqual(
            resp.context['source_options_nav'][1][1],
            '/haiti/admin/review?source=haiti.personfinder.google.org&'
            'status=all')
        self.assertEqual(
            resp.context['status_options_nav'][1][0], 'unspecified')
        self.assertEqual(
            resp.context['status_options_nav'][1][1],
            '/haiti/admin/review?source=all&status=unspecified')

    def test_get(self):
        """Tests GET requests when there are notes."""
        for i in range(5):
            self.data_generator.note(person_id=self.person.record_id)
        resp = self.client.get('/haiti/admin/review', secure=True)
        self.assertEqual(len(resp.context['notes']), 5)
        self.assertEqual(resp.context['next_url'], None)
        self.assertEqual(resp.context['source_options_nav'][0][0], 'all')
        self.assertEqual(resp.context['source_options_nav'][0][1], None)
        self.assertEqual(
            resp.context['source_options_nav'][1][0],
            'haiti.personfinder.google.org')
        self.assertEqual(
            resp.context['source_options_nav'][1][1],
            '/haiti/admin/review?source=haiti.personfinder.google.org&'
            'status=all')
        self.assertEqual(
            resp.context['status_options_nav'][1][0], 'unspecified')
        self.assertEqual(
            resp.context['status_options_nav'][1][1],
            '/haiti/admin/review?source=all&status=unspecified')

    def test_get_specified_status(self):
        for i in range(5):
            self.data_generator.note(person_id=self.person.record_id)
        for i in range(5):
            self.data_generator.note(
                person_id=self.person.record_id,
                status='is_note_author')
        resp = self.client.get(
            '/haiti/admin/review?status=is_note_author', secure=True)
        self.assertEqual(len(resp.context['notes']), 5)
        self.assertEqual(resp.context['next_url'], None)
        self.assertEqual(resp.context['source_options_nav'][0][0], 'all')
        self.assertEqual(resp.context['source_options_nav'][0][1], None)
        self.assertEqual(
            resp.context['source_options_nav'][1][0],
            'haiti.personfinder.google.org')
        self.assertEqual(
            resp.context['source_options_nav'][1][1],
            '/haiti/admin/review?source=haiti.personfinder.google.org&'
            'status=is_note_author')
        self.assertEqual(
            resp.context['status_options_nav'][1][0], 'unspecified')
        self.assertEqual(
            resp.context['status_options_nav'][1][1],
            '/haiti/admin/review?source=all&status=unspecified')

    def test_get_specified_source(self):
        other_source_person = self.data_generator.person(
            record_id='haiti.example.org/Person.1')
        for i in range(5):
            self.data_generator.note(person_id=self.person.record_id)
        for i in range(5):
            self.data_generator.note(
                person_id=other_source_person.record_id)
        resp = self.client.get(
            '/haiti/admin/review?source=haiti.example.org', secure=True)
        self.assertEqual(len(resp.context['notes']), 5)
        self.assertEqual(resp.context['next_url'], None)
        self.assertEqual(resp.context['source_options_nav'][0][0], 'all')
        self.assertEqual(
            resp.context['source_options_nav'][0][1],
            '/haiti/admin/review?source=all&status=all')
        self.assertEqual(
            resp.context['source_options_nav'][1][0],
            'haiti.personfinder.google.org')
        self.assertEqual(
            resp.context['source_options_nav'][1][1],
            '/haiti/admin/review?source=haiti.personfinder.google.org&'
            'status=all')
        self.assertEqual(
            resp.context['status_options_nav'][1][0], 'unspecified')
        self.assertEqual(
            resp.context['status_options_nav'][1][1],
            '/haiti/admin/review?source=haiti.example.org&status=unspecified')

    def test_accept_note(self):
        """Tests POST requests to accept a note."""
        note = self.data_generator.note(person_id=self.person.record_id)
        get_doc = self.to_doc(self.client.get(
            '/haiti/admin/review/', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_resp = self.client.post('/haiti/admin/review/', {
            'note.%s' % note.record_id: 'accept',
            'xsrf_token': xsrf_token,
        }, secure=True)
        # Check that the user's redirected to the repo's main admin page.
        self.assertIsInstance(post_resp, django.http.HttpResponseRedirect)
        self.assertEqual(post_resp.url, '/haiti/admin/review/')
        # Reload the Note from Datastore.
        note = model.Note.get('haiti', note.record_id)
        self.assertIs(note.reviewed, True)
        self.assertIs(note.hidden, False)

    def test_flag_note(self):
        """Tests POST requests to flag a note."""
        note = self.data_generator.note(person_id=self.person.record_id)
        get_doc = self.to_doc(self.client.get(
            '/haiti/admin/review/', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_resp = self.client.post('/haiti/admin/review/', {
            'note.%s' % note.record_id: 'flag',
            'xsrf_token': xsrf_token,
        }, secure=True)
        # Check that the user's redirected to the repo's main admin page.
        self.assertIsInstance(post_resp, django.http.HttpResponseRedirect)
        self.assertEqual(post_resp.url, '/haiti/admin/review/')
        # Reload the Note from Datastore.
        note = model.Note.get('haiti', note.record_id)
        self.assertIs(note.reviewed, True)
        self.assertIs(note.hidden, True)
