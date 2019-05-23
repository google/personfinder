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


"""Tests for the main global admin page."""

import copy

import config

import view_tests_base


class AdminGlobalIndexViewTests(view_tests_base.ViewTestsBase):
    """Tests the global admin index view."""

    _PRIOR_CONFIG = {
        'sms_number_to_repo': '{"+15551234567": "haiti"}',
        'repo_aliases': '{"h": "haiti"}',
        'brand': 'none',
        'privacy_policy_url': 'www.example.com/privacy',
        'tos_url': 'www.example.com/tos',
        'feedback_url': 'www.example.com/feedback',
        'captcha_site_key': 'captcha-key',
        'captcha_secret_key': 'captcha-secret-key',
        'analytics_id': 'analytics-id',
        'amp_gtm_id': 'amp-gtm-id',
        'maps_api_key': 'maps-api-key',
        'translate_api_key': 'translate-api-key',
        'notification_email': 'notifications@example.com',
        'unreviewed_notes_threshold': 12,
    }

    _BASE_POST_PARAMS = {
        'sms_number_to_repo': '{"+15551234567": "haiti"}',
        'repo_aliases': '{"h": "haiti"}',
        'brand': 'none',
        'privacy_policy_url': 'www.example.com/privacy',
        'tos_url': 'www.example.com/tos',
        'feedback_url': 'www.example.com/feedback',
        'captcha_site_key': 'captcha-key',
        'captcha_secret_key': 'captcha-secret-key',
        'analytics_id': 'analytics-id',
        'amp_gtm_id': 'amp-gtm-id',
        'maps_api_key': 'maps-api-key',
        'translate_api_key': 'translate-api-key',
        'notification_email': 'notifications@example.com',
        'unreviewed_notes_threshold': '12',
    }

    def setUp(self):
        super(AdminGlobalIndexViewTests, self).setUp()
        self.data_generator.repo()
        config.set_for_repo('*', **AdminGlobalIndexViewTests._PRIOR_CONFIG)
        self.login_as_superadmin()

    def test_get(self):
        """Tests GET requests."""
        resp = self.client.get('/global/admin/', secure=True)
        self.assertEqual(
            resp.context.get('sms_config'), {
                'sms_number_to_repo': '"{\\"+15551234567\\": \\"haiti\\"}"',
            })
        self.assertEqual(
            resp.context.get('repo_alias_config'), {
                'repo_aliases': '"{\\"h\\": \\"haiti\\"}"',
            })
        self.assertEqual(
            resp.context.get('site_info_config'), {
                'brand': 'none',
                'privacy_policy_url': 'www.example.com/privacy',
                'tos_url': 'www.example.com/tos',
                'feedback_url': 'www.example.com/feedback',
            })
        self.assertEqual(
            resp.context.get('recaptcha_config'), {
                'captcha_site_key': 'captcha-key',
                'captcha_secret_key': 'captcha-secret-key',
            })
        self.assertEqual(
            resp.context.get('ganalytics_config'), {
                'analytics_id': 'analytics-id',
                'amp_gtm_id': 'amp-gtm-id',
            })
        self.assertEqual(
            resp.context.get('gmaps_config'), {
                'maps_api_key': 'maps-api-key',
            })
        self.assertEqual(
            resp.context.get('gtranslate_config'), {
                'translate_api_key': 'translate-api-key',
            })
        self.assertEqual(
            resp.context.get('notification_config'), {
                'notification_email': 'notifications@example.com',
                'unreviewed_notes_threshold': '12',
            })

    def test_edit_sms_config(self):
        self._post_with_params(sms_number_to_repo='{"+1800pfhaiti": "haiti"}')
        conf = config.Configuration('*')
        self.assertEqual(conf.sms_number_to_repo, {'+1800pfhaiti': 'haiti'})

    def test_edit_repo_alias_config(self):
        self._post_with_params(repo_aliases='{"e": "ecuador"}')
        conf = config.Configuration('*')
        self.assertEqual(conf.repo_aliases, {'e': 'ecuador'})

    def test_edit_site_info_config(self):
        self._post_with_params(
            brand='google',
            privacy_policy_url='othersite.org/privacy',
            tos_url='othersite.org/tos',
            feedback_url='othersite.org/feedback')
        conf = config.Configuration('*')
        self.assertEqual(conf.brand, 'google')
        self.assertEqual(conf.privacy_policy_url, 'othersite.org/privacy')
        self.assertEqual(conf.tos_url, 'othersite.org/tos')
        self.assertEqual(conf.feedback_url, 'othersite.org/feedback')

    def test_edit_recaptcha_config(self):
        self._post_with_params(
            captcha_site_key='NEW-captcha-key',
            captcha_secret_key='NEW-captcha-secret-key')
        conf = config.Configuration('*')
        self.assertEqual(conf.captcha_site_key, 'NEW-captcha-key')
        self.assertEqual(conf.captcha_secret_key, 'NEW-captcha-secret-key')

    def test_edit_ganalytics_config(self):
        self._post_with_params(
            analytics_id='NEW-analytics-id',
            amp_gtm_id='NEW-amp-gtm-id')
        conf = config.Configuration('*')
        self.assertEqual(conf.analytics_id, 'NEW-analytics-id')
        self.assertEqual(conf.amp_gtm_id, 'NEW-amp-gtm-id')

    def test_edit_gmaps_config(self):
        self._post_with_params(maps_api_key='NEW-maps-api-key')
        conf = config.Configuration('*')
        self.assertEqual(conf.maps_api_key, 'NEW-maps-api-key')

    def test_edit_gtranslate_config(self):
        self._post_with_params(translate_api_key='NEW-translate-api-key')
        conf = config.Configuration('*')
        self.assertEqual(conf.translate_api_key, 'NEW-translate-api-key')

    def test_edit_notification_config(self):
        self._post_with_params(
            notification_email='notifications@othersite.org',
            unreviewed_notes_threshold='86')
        conf = config.Configuration('*')
        self.assertEqual(conf.notification_email, 'notifications@othersite.org')
        self.assertEqual(conf.unreviewed_notes_threshold, 86)

    def _post_with_params(self, **kwargs):
        get_doc = self.to_doc(self.client.get('/global/admin', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_params = copy.deepcopy(AdminGlobalIndexViewTests._BASE_POST_PARAMS)
        post_params['xsrf_token'] = xsrf_token
        post_params.update(kwargs)
        return self.client.post('/global/admin/', post_params, secure=True)
