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

# pylint: disable=wrong-import-order
# pylint sometimes thinks config is a standard import that belongs before the
# django import. It's mistaken; config is our own module (if you run
# python -c "import config", it produces an error saying config doesn't exist).
# Filed issue #626 to move us out of the global namespace someday, which would
# prevent stuff like this.
import config
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
        """Tests GET requests."""
        resp = self.client.get('/haiti/admin/review', secure=True)
        self.assertEqual(len(resp.context['notes']), 0)
        self.assertEqual(resp.context['next_url'], None)
        self.assertEqual(resp.context['source_options_nav'][0][0], 'all')
        self.assertEqual(resp.context['source_options_nav'][0][1], None)
        self.assertEqual(
            resp.context['status_options_nav'][1][0], 'unspecified')
        self.assertEqual(
            resp.context['status_options_nav'][1][1],
            '/haiti/admin/review?source=all&status=unspecified')

    def test_create_repo(self):
        """Tests POST requests to create a new repo."""
        note = self.data_generator.note(person_id=self.person.record_id)
        get_doc = self.to_doc(self.client.get(
            '/global/admin/review/', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_resp = self.client.post('/global/admin/review/', {
            'note.%s' % note.record_id: 'accept',
        }, secure=True)
        # Check that the user's redirected to the repo's main admin page.
        self.assertIsInstance(post_resp, django.http.HttpResponseRedirect)
        self.assertEqual(post_resp.url, '/haiti/admin/review')
