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
import datetime

import config
import model
import utils

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
        'map_default_zoom': 5,
        'map_default_center': '[-43.8, 152.5]',
        'map_size_pixels': '[200, 400]',
        'keywords': '',
        'use_family_name': False,
        'family_name_first': False,
        'use_alternate_names': False,
        'use_postal_code': False,
        'allow_believed_dead_via_ui': False,
        'min_query_word_length': 1,
        'show_profile_entry': False,
        'profile_websites': '[]',
        'time_zone_offset': 0,
        'time_zone_abbreviation': 'UTC',
        'search_auth_key_required': False,
        'read_auth_key_required': False,
        'zero_rating_mode': False,
        'bad_words': '',
        'updated_date': utils.get_timestamp(
            datetime.datetime(2019, 5, 10, 11, 15, 0)),
    }

    _BASE_POST_PARAMS = {
        'langlist__0': 'en',
        'langlist__1': 'fr',
        'repotitle__en': 'en title',
        'repotitle__fr': 'fr title',
        'custommsg__start_page_custom_htmls__en': 'en start msg',
        'custommsg__start_page_custom_htmls__fr': 'fr start msg',
        'custommsg__results_page_custom_htmls__en': 'en results msg',
        'custommsg__results_page_custom_htmls__fr': 'fr results msg',
        'custommsg__view_page_custom_htmls__en': 'en view msg',
        'custommsg__view_page_custom_htmls__fr': 'fr view msg',
        'custommsg__seek_query_form_custom_htmls__en': 'en seek msg',
        'custommsg__seek_query_form_custom_htmls__fr': 'fr seek msg',
        'custommsg__footer_custom_htmls__en': 'en footer msg',
        'custommsg__footer_custom_htmls__fr': 'fr footer msg',
        'map_default_center': '[-43.8, 152.5]',
        'map_default_zoom': '5',
        'map_size_pixels': '[200, 400]',
        'keywords': '',
        'use_family_name': 'false',
        'family_name_first': 'false',
        'use_alternate_names': 'false',
        'use_postal_code': 'false',
        'allow_believed_dead_via_ui': 'false',
        'min_query_word_length': '1',
        'show_profile_entry': 'false',
        'profile_websites': '[]',
        'time_zone_offset': '0',
        'time_zone_abbreviation': 'UTC',
        'search_auth_key_required': 'false',
        'read_auth_key_required': 'false',
        'zero_rating_mode': 'false',
        'bad_words': '',
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
            # These can be either None or an empty dictionary.
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

    def test_edit_lang_list(self):
        self.login_as_superadmin()
        self._post_with_params(
            langlist__0='en', langlist__1='fr', langlist__2='es')
        repo_conf = config.Configuration('haiti')
        self.assertEqual(repo_conf.language_menu_options, ['en', 'fr', 'es'])

    def test_edit_repo_titles(self):
        self.login_as_superadmin()
        self._post_with_params(
            repotitle__en='en title', repotitle__fr='new and improved fr title')
        repo_conf = config.Configuration('haiti')
        self.assertEqual(
            repo_conf.repo_titles['fr'], 'new and improved fr title')

    def test_edit_custom_messages(self):
        """Tests POST requests to edit custom messages."""
        self.login_as_manager()
        self._post_with_params(
            custommsg__start_page_custom_htmls__en='new en msg')
        repo_conf = config.Configuration('haiti')
        self.assertEqual(repo_conf.start_page_custom_htmls['en'], 'new en msg')

    def test_edit_activation_status_config(self):
        # Set the time to an hour past the original update_date.
        utils.set_utcnow_for_test(datetime.datetime(2019, 5, 10, 12, 15, 0))
        self.login_as_superadmin()
        self._post_with_params(
            activation_status=str(model.Repo.ActivationStatus.DEACTIVATED),
            deactivation_message_html='it is deactivated')
        repo = model.Repo.get_by_key_name('haiti')
        self.assertEqual(
            repo.activation_status, model.Repo.ActivationStatus.DEACTIVATED)
        repo_conf = config.Configuration('haiti')
        self.assertEqual(
            repo_conf.deactivation_message_html, 'it is deactivated')
        self.assertEqual(
            repo_conf.updated_date,
            utils.get_timestamp(datetime.datetime(2019, 5, 10, 12, 15, 0)))

    def test_edit_data_retention_mode_config(self):
        # Set the time to an hour past the original update_date.
        utils.set_utcnow_for_test(datetime.datetime(2019, 5, 10, 12, 15, 0))
        self.login_as_superadmin()
        self._post_with_params(test_mode=True)
        repo = model.Repo.get_by_key_name('haiti')
        self.assertTrue(repo.test_mode)
        repo_conf = config.Configuration('haiti')
        self.assertIs(repo_conf.test_mode, True)
        self.assertEqual(
            repo_conf.updated_date,
            utils.get_timestamp(datetime.datetime(2019, 5, 10, 12, 15, 0)))

    def test_edit_keywords_config(self):
        self.login_as_superadmin()
        self._post_with_params(keywords='haiti,earthquake')
        repo_conf = config.Configuration('haiti')
        self.assertEqual(repo_conf.keywords, 'haiti,earthquake')

    def test_edit_forms_config(self):
        self.login_as_superadmin()
        self._post_with_params(
            use_family_name='true',
            family_name_first='true',
            use_alternate_names='true',
            use_postal_code='true',
            allow_believed_dead_via_ui='true',
            min_query_word_length='2',
            show_profile_entry='true',
            # The value for this doesn't really matter.
            profile_websites='{"arbitrary": "json"}')
        repo_conf = config.Configuration('haiti')
        self.assertIs(repo_conf.use_family_name, True)
        self.assertIs(repo_conf.family_name_first, True)
        self.assertIs(repo_conf.use_alternate_names, True)
        self.assertIs(repo_conf.use_postal_code, True)
        self.assertIs(repo_conf.allow_believed_dead_via_ui, True)
        self.assertEqual(repo_conf.min_query_word_length, 2)
        self.assertIs(repo_conf.show_profile_entry, True)
        self.assertEqual(repo_conf.profile_websites, {'arbitrary': 'json'})

    def test_edit_map_config(self):
        self.login_as_superadmin()
        self._post_with_params(
            map_default_zoom='8',
            map_default_center='[32.7, 85.6]',
            map_size_pixels='[300, 450]')
        repo_conf = config.Configuration('haiti')
        self.assertEqual(repo_conf.map_default_zoom, 8)
        self.assertEqual(repo_conf.map_default_center, [32.7, 85.6])
        self.assertEqual(repo_conf.map_size_pixels, [300, 450])

    def test_edit_timezone_config(self):
        self.login_as_superadmin()
        self._post_with_params(
            time_zone_offset='5.75',
            time_zone_abbreviation='NPT')
        repo_conf = config.Configuration('haiti')
        self.assertEqual(repo_conf.time_zone_offset, 5.75)
        self.assertEqual(repo_conf.time_zone_abbreviation, 'NPT')

    def test_api_access_control_config(self):
        self.login_as_superadmin()
        self._post_with_params(
            search_auth_key_required='true',
            read_auth_key_required='true')
        repo_conf = config.Configuration('haiti')
        self.assertIs(repo_conf.search_auth_key_required, True)
        self.assertIs(repo_conf.read_auth_key_required, True)

    def test_edit_zero_rating_config(self):
        self.login_as_superadmin()
        self._post_with_params(zero_rating_mode='true')
        repo_conf = config.Configuration('haiti')
        self.assertIs(repo_conf.zero_rating_mode, True)

    def test_edit_spam_config(self):
        self.login_as_superadmin()
        self._post_with_params(bad_words='voldemort')
        repo_conf = config.Configuration('haiti')
        self.assertEqual(repo_conf.bad_words, 'voldemort')

    def test_manager_edit_restrictions(self):
        self.login_as_manager()
        self._post_with_params(
            use_family_name='true',
            family_name_first='true',
            use_alternate_names='true',
            use_postal_code='true',
            allow_believed_dead_via_ui='true',
            min_query_word_length='2',
            show_profile_entry='true',
            map_default_zoom='8',
            map_default_center='[32.7, 85.6]',
            map_size_pixels='[300, 450]',
            time_zone_offset='5.75',
            time_zone_abbreviation='NPT',
            search_auth_key_required='true',
            read_auth_key_required='true',
            zero_rating_mode='true',
            bad_words='voldemort')
        repo_conf = config.Configuration('haiti')
        for key, value in AdminRepoIndexViewTests._PRIOR_CONFIG.items():
            self.assertEqual(repo_conf.get(key), value)

    def _post_with_params(self, **kwargs):
        get_doc = self.to_doc(self.client.get('/haiti/admin', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_params = copy.deepcopy(AdminRepoIndexViewTests._BASE_POST_PARAMS)
        post_params['activation_status'] = str(
            model.Repo.ActivationStatus.ACTIVE)
        post_params['test_mode'] = 'false'
        post_params['xsrf_token'] = xsrf_token
        post_params.update(kwargs)
        return self.client.post('/haiti/admin/', post_params, secure=True)
