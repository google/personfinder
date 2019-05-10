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
import const
import model
import modelmodule.admin_acls as admin_acls_model
import utils
import views.admin.base


class AdminRepoIndexView(views.admin.base.AdminBaseView):
    """The admin repo index view."""

    ACTION_ID = 'admin/repo-index'

    _CATEGORY_PERMISSION_LEVELS = {
        'custom_messages':
        admin_acls_model.AdminPermission.AccessLevel.MANAGER,
        'everything_else':
        admin_acls_model.AdminPermission.AccessLevel.SUPERADMIN,
    }

    _CUSTOM_MESSAGES_CONFIG_KEYS = [
        'start_page_custom_htmls',
        'results_page_custom_htmls',
        'view_page_custom_htmls',
        'seek_query_form_custom_htmls',
        'footer_custom_htmls',
    ]

    _JSON_FIELDS = [
        'map_default_center',
        'map_size_pixels',
        'profile_websites',
    ]

    def _read_params(self, request):
        if request.method == 'POST':
            lang_list = []
            self.params.repo_titles = {}
            self.params.custom_messages = {}
            for key, value in request.POST.items():
                key_parts = key.split('__')
                if key_parts[0] == 'langlist':
                    lang_list.append((int(key_parts[1]), value))
                elif key_parts[0] == 'repotitle':
                    self.params.repo_titles[key_parts[1]] = value
                elif key_parts[0] == 'custommsg':
                    messages = self.params.custom_messages.setdefault(
                        key_parts[1], {})
                    messages[key_parts[2]] = value
            self.params.lang_list = [
                value for _, value in sorted(lang_list, key=lambda kv: kv[0])]
            self.params.read_values(
                post_params={
                    'activation_status': utils.validate_int,
                    'allow_believed_dead_via_ui':
                    utils.validate_checkbox_as_bool,
                    'bad_words': utils.strip,
                    'deactivation_message_html': utils.strip,
                    'family_name_first': utils.validate_checkbox_as_bool,
                    'keywords': utils.strip,
                    'map_default_center': utils.strip,
                    'map_default_zoom': utils.validate_int,
                    'map_size_pixels': utils.strip,
                    'min_query_word_length': utils.validate_int,
                    'profile_websites': utils.strip,
                    'read_auth_key_required': utils.validate_checkbox_as_bool,
                    'search_auth_key_required': utils.validate_checkbox_as_bool,
                    'show_profile_entry': utils.validate_checkbox_as_bool,
                    'test_mode': utils.validate_checkbox_as_bool,
                    'time_zone_offset': utils.validate_float,
                    'time_zone_abbreviation': utils.strip,
                    'use_alternate_names': utils.validate_checkbox_as_bool,
                    'use_family_name': utils.validate_checkbox_as_bool,
                    'use_postal_code': utils.validate_checkbox_as_bool,
                    'zero_rating_mode': utils.validate_checkbox_as_bool,
                })

    def setup(self, request, *args, **kwargs):
        """See docs on BaseView.setup."""
        # pylint: disable=attribute-defined-outside-init
        super(AdminRepoIndexView, self).setup(request, *args, **kwargs)
        self._repo_obj = model.Repo.get(self.env.repo)
        self._read_params(request)
        self._category_permissions = self._get_category_permissions()
        self._json_encoder = simplejson.encoder.JSONEncoder(ensure_ascii=False)

    def _get_category_permissions(self):
        if not self.env.user_admin_permission:
            return {}
        return {
            key: self.env.user_admin_permission.compare_level_to(min_level) >= 0
            for key, min_level in
            AdminRepoIndexView._CATEGORY_PERMISSION_LEVELS.items()
        }

    def _render_form(self):
        language_exonyms = sorted(list(const.LANGUAGE_EXONYMS.items()),
                                  key=lambda lang: lang[1])
        return self.render(
            'admin_repo_index.html',
            category_permissions=self._category_permissions,
            # Language-specific fields are handled by a React component, so we
            # encode that into JSON for it.
            # TODO(nworden): once we upgrade to Django 2.1+, use the new
            # built-in json_script filter instead of encoding it ourselves.
            language_exonyms_json=self._json_encoder.encode(language_exonyms),
            language_config_json=self._json_encoder.encode(
                self._get_language_config()),
            activation_config=self._get_activation_config(),
            data_retention_config=self._get_data_retention_config(),
            keywords_config=self._get_keywords_config(),
            forms_config=self._get_forms_config(),
            map_config=self._get_map_config(),
            timezone_config=self._get_timezone_config(),
            api_access_control_config=self._get_api_access_control_config(),
            zero_rating_config=self._get_zero_rating_config(),
            spam_config=self._get_spam_config(),
            xsrf_token=self.xsrf_tool.generate_token(
                self.env.user.user_id(), self.ACTION_ID))

    @views.admin.base.enforce_manager_admin_level
    def get(self, request, *args, **kwargs):
        """Serves GET requests."""
        del request, args, kwargs  # Unused.
        return self._render_form()

    def _get_language_config(self):
        language_config = {}
        language_config['lang_list'] = self.env.config.get(
            'language_menu_options', [])
        if self._category_permissions['everything_else']:
            language_config['repo_titles'] = self.env.config.get(
                'repo_titles', {})
        if self._category_permissions['custom_messages']:
            custom_messages = {}
            for config_key in AdminRepoIndexView._CUSTOM_MESSAGES_CONFIG_KEYS:
                custom_messages[config_key] = self.env.config.get(
                    config_key, {})
            language_config['custom_messages'] = custom_messages
        return language_config

    def _get_activation_config(self):
        activation_config = {}
        if self._category_permissions['everything_else']:
            activation_config['activation_status'] = (
                self._repo_obj.activation_status)
            activation_config['deactivation_message_html'] = (
                self.env.config.get('deactivation_message_html'))
        return activation_config

    def _get_data_retention_config(self):
        data_retention_config = {}
        if self._category_permissions['everything_else']:
            data_retention_config['test_mode'] = self._repo_obj.test_mode
        return data_retention_config

    def _get_keywords_config(self):
        keywords_config = {}
        if self._category_permissions['everything_else']:
            keywords_config['keywords'] = self.env.config.get('keywords')
        return keywords_config

    def _get_forms_config(self):
        forms_config = {}
        if self._category_permissions['everything_else']:
            forms_config['use_family_name'] = self.env.config.get(
                'use_family_name')
            forms_config['family_name_first'] = self.env.config.get(
                'family_name_first')
            forms_config['use_alternate_names'] = self.env.config.get(
                'use_alternate_names')
            forms_config['use_postal_code'] = self.env.config.get(
                'use_postal_code')
            forms_config['allow_believed_dead_via_ui'] = self.env.config.get(
                'allow_believed_dead_via_ui')
            forms_config['min_query_word_length'] = self.env.config.get(
                'min_query_word_length')
            forms_config['show_profile_entry'] = self.env.config.get(
                'show_profile_entry')
            forms_config['profile_websites'] = self._json_encoder.encode(
                self.env.config.get('profile_websites'))
        return forms_config

    def _get_map_config(self):
        map_config = {}
        if self._category_permissions['everything_else']:
            map_config['map_default_zoom'] = self.env.config.get(
                'map_default_zoom')
            map_config['map_default_center'] = self._json_encoder.encode(
                self.env.config.get('map_default_center'))
            map_config['map_size_pixels'] = self._json_encoder.encode(
                self.env.config.get('map_size_pixels'))
        return map_config

    def _get_timezone_config(self):
        timezone_config = {}
        if self._category_permissions['everything_else']:
            timezone_config['time_zone_offset'] = self.env.config.get(
                'time_zone_offset')
            timezone_config['time_zone_abbreviation'] = self.env.config.get(
                'time_zone_abbreviation')
        return timezone_config

    def _get_api_access_control_config(self):
        api_access_control_config = {}
        if self._category_permissions['everything_else']:
            api_access_control_config['search_auth_key_required'] = (
                self.env.config.get('search_auth_key_required'))
            api_access_control_config['read_auth_key_required'] = (
                self.env.config.get('read_auth_key_required'))
        return api_access_control_config

    def _get_zero_rating_config(self):
        zero_rating_config = {}
        if self._category_permissions['everything_else']:
            zero_rating_config['zero_rating_mode'] = self.env.config.get(
                'zero_rating_mode')
        return zero_rating_config

    def _get_spam_config(self):
        spam_config = {}
        if self._category_permissions['everything_else']:
            spam_config['bad_words'] = self.env.config.get('bad_words')
        return spam_config

    @views.admin.base.enforce_manager_admin_level
    def post(self, request, *args, **kwargs):
        """Serves POST requests, updating the repo's configuration."""
        del request, args, kwargs  # Unused.
        self.enforce_xsrf(self.ACTION_ID)
        validation_response = self._validate_input()
        if validation_response:
            return validation_response
        self._set_language_config()
        self._set_activation_config()
        self._set_data_retention_config()
        self._set_keywords_config()
        self._set_forms_config()
        self._set_map_config()
        self._set_timezone_config()
        self._set_api_access_control_config()
        self._set_zero_rating_config()
        self._set_spam_config()
        # Reload the config since we just changed it.
        self.env.config = config.Configuration(self.env.repo)
        return self._render_form()

    def _validate_input(self):
        if self._category_permissions['everything_else']:
            # It happens that all of the JSON fields fall into this permission
            # category.
            try:
                for field_name in AdminRepoIndexView._JSON_FIELDS:
                    if not self.params.get(field_name):
                        return self.error(400, 'Missing JSON value.')
                    simplejson.loads(self.params.get(field_name))
            except simplejson.JSONDecodeError:
                return self.error(400, 'Invalid JSON value.')

    def _set_language_config(self):
        values = {}
        if self._category_permissions['everything_else']:
            values['language_menu_options'] = self.params.lang_list
            values['repo_titles'] = self.params.repo_titles
        if self._category_permissions['custom_messages']:
            for config_key, value in self.params.custom_messages.items():
                values[config_key] = value
        config.set_for_repo(self.env.repo, **values)

    def _set_activation_config(self):
        if self._category_permissions['everything_else']:
            if (self._repo_obj.activation_status !=
                    self.params.activation_status):
                self._repo_obj.activation_status = self.params.activation_status
                self._repo_obj.put()
                config.set_for_repo(
                    self.env.repo,
                    updated_date=utils.get_utcnow_timestamp())
            config.set_for_repo(
                self.env.repo,
                deactivation_message_html=self.params.deactivation_message_html)

    def _set_data_retention_config(self):
        if self._category_permissions['everything_else']:
            if self._repo_obj.test_mode != self.params.test_mode:
                # TODO(nworden): stop setting test_mode in the config once we've
                # switched to using the field on the Repo object exclusively.
                self._repo_obj.test_mode = self.params.test_mode
                self._repo_obj.put()
                config.set_for_repo(
                    self.env.repo,
                    test_mode=self.params.test_mode,
                    updated_date=utils.get_utcnow_timestamp())

    def _set_keywords_config(self):
        if self._category_permissions['everything_else']:
            config.set_for_repo(self.env.repo, keywords=self.params.keywords)

    def _set_forms_config(self):
        if self._category_permissions['everything_else']:
            values = {}
            values['use_family_name'] = self.params.use_family_name
            values['family_name_first'] = self.params.family_name_first
            values['use_alternate_names'] = self.params.use_alternate_names
            values['use_postal_code'] = self.params.use_postal_code
            values['allow_believed_dead_via_ui'] = (
                self.params.allow_believed_dead_via_ui)
            values['min_query_word_length'] = self.params.min_query_word_length
            values['show_profile_entry'] = self.params.show_profile_entry
            values['profile_websites'] = simplejson.loads(
                self.params.profile_websites)
            config.set_for_repo(self.env.repo, **values)

    def _set_map_config(self):
        if self._category_permissions['everything_else']:
            values = {}
            values['map_default_center'] = simplejson.loads(
                self.params.map_default_center)
            values['map_default_zoom'] = self.params.map_default_zoom
            values['map_size_pixels'] = simplejson.loads(
                self.params.map_size_pixels)
            config.set_for_repo(self.env.repo, **values)

    def _set_timezone_config(self):
        if self._category_permissions['everything_else']:
            values = {}
            values['time_zone_offset'] = self.params.time_zone_offset
            values['time_zone_abbreviation'] = (
                self.params.time_zone_abbreviation)
            config.set_for_repo(self.env.repo, **values)

    def _set_api_access_control_config(self):
        if self._category_permissions['everything_else']:
            values = {}
            values['search_auth_key_required'] = (
                self.params.search_auth_key_required)
            values['read_auth_key_required'] = (
                self.params.read_auth_key_required)
            config.set_for_repo(self.env.repo, **values)

    def _set_zero_rating_config(self):
        if self._category_permissions['everything_else']:
            config.set_for_repo(
                self.env.repo, zero_rating_mode=self.params.zero_rating_mode)

    def _set_spam_config(self):
        if self._category_permissions['everything_else']:
            config.set_for_repo(self.env.repo, bad_words=self.params.bad_words)
