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
"""Tests for the main repo admin page."""

import copy

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


class AdminRepoIndexViewTests(view_tests_base.ViewTestsBase):
    """Tests the admin repo index view."""

    _PRIOR_CONFIG = {
        'language_menu_options': ['en', 'fr'],
        'repo_titles': {'en': 'en title', 'fr': 'fr title'},
        'start_page_custom_htmls': {
            'en': 'en start msg', 'fr': 'fr start msg'},
        'results_page_custom_htmls': {
            'en': 'en results msg', 'fr': 'fr results msg'},
        'view_page_custom_htmls': {
            'en': 'en view msg', 'fr': 'fr view msg'},
        'seek_query_form_custom_htmls': {
            'en': 'en seek msg', 'fr': 'fr seek msg'},
        'footer_custom_htmls': {
            'en': 'en footer msg', 'fr': 'fr footer msg'},
        'time_zone_abbreviation': 'UTC',
    }

    _SUPERADMIN_ONLY_CONTEXT_KEYS = [
        'activation_config',
        'api_access_control_config',
        'data_retention_config',
        'forms_config',
        'keywords_config',
        'map_config',
        'spam_config',
        'timezone_config',
        'zero_rating_config',
    ]

    def setUp(self):
        super(AdminRepoIndexViewTests, self).setUp()
        self.data_generator.repo()
        config.set_for_repo('haiti', **AdminRepoIndexViewTests._PRIOR_CONFIG)

    def test_get_as_manager(self):
        """Tests GET requests as a manager-level admin."""
        self.login_as_manager()
        resp = self.client.get('/haiti/admin/', secure=True)
        doc = self.to_doc(resp)
        # Check that a couple of the custom messages appear in the doc content.
        self.assertTrue('en start msg' in doc.content)
        self.assertTrue('fr view msg' in doc.content)
        # I tried doing this test the other way around -- checking that every
        # key in the context was among the set of keys we expect manager-level
        # admins to have access to -- but that didn't work out well, because
        # Django seems to include basic stuff (e.g., "True", "None", etc.) as
        # part of the context (in other words, there's stuff in the context dict
        # that didn't come from us, and I don't want to have to keep a list of
        # them).
        for key in AdminRepoIndexViewTests._SUPERADMIN_ONLY_CONTEXT_KEYS:
            self.assertFalse(
                resp.context.get(key),
                'Non-empty superadmin-only key: %s' % key)

    def test_get_as_superadmin(self):
        """Tests GET requests as a superadmin."""
        self.login_as_superadmin()
        resp = self.client.get('/haiti/admin/', secure=True)
        doc = self.to_doc(resp)
        # Check that a couple of the custom messages appear in the doc content.
        self.assertTrue('en start msg' in doc.content)
        self.assertTrue('fr view msg' in doc.content)
        for key in AdminRepoIndexViewTests._SUPERADMIN_ONLY_CONTEXT_KEYS:
            self.assertTrue(
                resp.context[key],
                'Empty superadmin key for superadmin: %s' % key)

    def test_edit_custom_messages(self):
        """Tests POST requests to edit custom messages."""
        self.login_as_manager()
        get_doc = self.to_doc(self.client.get('/haiti/admin', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_params = copy.deepcopy(AdminRepoIndexViewTests._PRIOR_CONFIG)
        post_params['activation_status'] = str(
            model.Repo.ActivationStatus.ACTIVE)
        post_params['test_mode'] = 'false'
        post_params['custommsg__start_page_custom_htmls__en'] = 'new en msg'
        post_params['xsrf_token'] = xsrf_token
        post_resp = self.client.post('/haiti/admin/', post_params, secure=True)
        # Check that the repo object wasn't changed.
        repo = model.Repo.get_by_key_name('haiti')
        self.assertEqual(
            repo.activation_status, model.Repo.ActivationStatus.ACTIVE)
        self.assertIs(repo.test_mode, False)
        # Check a couple of the config fields that are set by default.
        repo_conf = config.Configuration('haiti')
        self.assertEqual(repo_conf.language_menu_options, ['en', 'fr'])
        self.assertEqual(repo_conf.time_zone_abbreviation, 'UTC')
        # Check that the custom message was updated.
        self.assertEqual(repo_conf.start_page_custom_htmls['en'], 'new en msg')

    def test_edit_activation_status(self):
        self.login_as_superadmin()
        get_doc = self.to_doc(self.client.get('/haiti/admin', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_params = copy.deepcopy(AdminRepoIndexViewTests._PRIOR_CONFIG)
        post_params['activation_status'] = str(
            model.Repo.ActivationStatus.DEACTIVATED)
        post_params['test_mode'] = 'false'
        post_params['xsrf_token'] = xsrf_token
        post_resp = self.client.post('/haiti/admin/', post_params, secure=True)
        repo = model.Repo.get_by_key_name('haiti')
        self.assertEqual(
            repo.activation_status, model.Repo.ActivationStatus.DEACTIVATED)
