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


"""Tests for the admin create-repo page."""

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


class AdminCreateRepoViewTests(view_tests_base.ViewTestsBase):
    """Tests the admin create-repo view."""

    def setUp(self):
        super(AdminCreateRepoViewTests, self).setUp()
        self.data_generator.repo()
        self.login_as_superadmin()

    def test_get(self):
        """Tests GET requests."""
        doc = self.to_doc(self.client.get(
            '/global/admin/create_repo/', secure=True))
        self.assertIsNotNone(doc.cssselect_one('input[name="new_repo"]'))

    def test_create_repo(self):
        """Tests POST requests to create a new repo."""
        get_doc = self.to_doc(self.client.get(
            '/global/admin/create_repo/', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_resp = self.client.post('/global/admin/create_repo/', {
            'xsrf_token': xsrf_token,
            'new_repo': 'idaho'
        }, secure=True)
        # Check that the user's redirected to the repo's main admin page.
        self.assertIsInstance(post_resp, django.http.HttpResponseRedirect)
        self.assertEqual(post_resp.url, '/idaho/admin')
        # Check that the repo object is put in datastore.
        repo = model.Repo.get_by_key_name('idaho')
        self.assertIsNotNone(repo)
        self.assertEqual(
            repo.activation_status, model.Repo.ActivationStatus.STAGING)
        self.assertIs(repo.test_mode, False)
        # Check a couple of the config fields that are set by default.
        repo_conf = config.Configuration('idaho')
        self.assertEqual(repo_conf.language_menu_options, ['en', 'fr'])
        self.assertIs(repo_conf.launched, False)
        self.assertEqual(repo_conf.time_zone_abbreviation, 'UTC')
