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
"""The admin custom messages page."""

import simplejson

import config
import utils
import views.admin.base


class AdminGlobalIndexView(views.admin.base.AdminBaseView):
    """The admin global index view."""

    ACTION_ID = 'admin/global-index'

    _JSON_FIELDS = [
        'sms_number_to_repo',
        'repo_aliases',
    ]

    def setup(self, request, *args, **kwargs):
        super(AdminGlobalIndexView, self).setup(request, *args, **kwargs)
        self.params.read_values(
            post_params={
                'sms_number_to_repo': utils.strip,
                'repo_aliases': utils.strip,
                'brand': utils.strip,
                'privacy_policy_url': utils.strip,
                'tos_url': utils.strip,
                'feedback_url': utils.strip,
                'captcha_site_key': utils.strip,
                'captcha_secret_key': utils.strip,
                'analytics_id': utils.strip,
                'amp_gtm_id': utils.strip,
                'maps_api_key': utils.strip,
                'translate_api_key': utils.strip,
                'notification_email': utils.strip,
                'unreviewed_notes_threshold': utils.validate_int,
            })
        self._json_encoder = simplejson.encoder.JSONEncoder(ensure_ascii=False)

    def _render_form(self):
        return self.render(
            'admin_global_index.html',
            sms_config=self._get_sms_config(),
            repo_alias_config=self._get_repo_alias_config(),
            site_info_config=self._get_site_info_config(),
            recaptcha_config=self._get_recaptcha_config(),
            ganalytics_config=self._get_ganalytics_config(),
            gmaps_config=self._get_gmaps_config(),
            gtranslate_config=self._get_gtranslate_config(),
            notification_config=self._get_notification_config(),
            xsrf_token=self.xsrf_tool.generate_token(
                self.env.user.user_id(), self.ACTION_ID))

    @views.admin.base.enforce_superadmin_admin_level
    def get(self, request, *args, **kwargs):
        """Serves GET requests."""
        del request, args, kwargs  # Unused.
        return self._render_form()

    def _get_sms_config(self):
        return {
            'sms_number_to_repo': self._json_encoder.encode(
                self.env.config.get('sms_number_to_repo')),
        }

    def _get_repo_alias_config(self):
        return {
            'repo_aliases': self._json_encoder.encode(
                self.env.config.get('repo_aliases')),
        }

    def _get_site_info_config(self):
        return {
            'brand': self.env.config.get('brand', 'none'),
            'privacy_policy_url': self.env.config.get('privacy_policy_url', ''),
            'tos_url': self.env.config.get('tos_url', ''),
            'feedback_url': self.env.config.get('feedback_url', ''),
        }

    def _get_recaptcha_config(self):
        return {
            'captcha_site_key': self.env.config.get('captcha_site_key', ''),
            'captcha_secret_key': self.env.config.get('captcha_secret_key', ''),
        }

    def _get_ganalytics_config(self):
        return {
            'analytics_id': self.env.config.get('analytics_id', ''),
            'amp_gtm_id': self.env.config.get('amp_gtm_id', ''),
        }

    def _get_gmaps_config(self):
        return {
            'maps_api_key': self.env.config.get('maps_api_key', ''),
        }

    def _get_gtranslate_config(self):
        return {
            'translate_api_key': self.env.config.get('translate_api_key', ''),
        }

    def _get_notification_config(self):
        return {
            'notification_email': self.env.config.get('notification_email', ''),
            'unreviewed_notes_threshold': str(self.env.config.get(
                'unreviewed_notes_threshold', 100)),
        }

    @views.admin.base.enforce_superadmin_admin_level
    def post(self, request, *args, **kwargs):
        """Serves POST requests, updating the repo's configuration."""
        del request, args, kwargs  # Unused.
        self.enforce_xsrf(self.ACTION_ID)
        validation_response = self._validate_input()
        if validation_response:
            return validation_response
        self._set_sms_config()
        self._set_repo_alias_config()
        self._set_site_info_config()
        self._set_recaptcha_config()
        self._set_ganalytics_config()
        self._set_gmaps_config()
        self._set_gtranslate_config()
        self._set_notification_config()
        # Reload the config since we just changed it.
        self.env.config = config.Configuration('*')
        return self._render_form()

    def _validate_input(self):
        try:
            for field_name in AdminGlobalIndexView._JSON_FIELDS:
                if not self.params.get(field_name):
                    return self.error(400, 'Missing JSON value.')
                simplejson.loads(self.params.get(field_name))
        except simplejson.JSONDecodeError:
            return self.error(400, 'Invalid JSON value.')

    def _set_sms_config(self):
        config.set_for_repo(
            '*',
            sms_number_to_repo=simplejson.loads(self.params.sms_number_to_repo))

    def _set_repo_alias_config(self):
        config.set_for_repo(
            '*',
            repo_aliases=simplejson.loads(self.params.repo_aliases))

    def _set_site_info_config(self):
        config.set_for_repo(
            '*',
            brand=self.params.brand,
            privacy_policy_url=self.params.privacy_policy_url,
            tos_url=self.params.tos_url,
            feedback_url=self.params.feedback_url)

    def _set_recaptcha_config(self):
        config.set_for_repo(
            '*',
            captcha_site_key=self.params.captcha_site_key,
            captcha_secret_key=self.params.captcha_secret_key)

    def _set_ganalytics_config(self):
        config.set_for_repo(
            '*',
            analytics_id=self.params.analytics_id,
            amp_gtm_id=self.params.amp_gtm_id)

    def _set_gmaps_config(self):
        config.set_for_repo('*', maps_api_key=self.params.maps_api_key)

    def _set_gtranslate_config(self):
        config.set_for_repo(
            '*', translate_api_key=self.params.translate_api_key)

    def _set_notification_config(self):
        config.set_for_repo(
            '*',
            notification_email=self.params.notification_email,
            unreviewed_notes_threshold=self.params.unreviewed_notes_threshold)
