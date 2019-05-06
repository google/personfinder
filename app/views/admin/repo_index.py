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

import django.shortcuts
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

    def _get_category_permissions(self):
        return {
            key: self.env.user_admin_permission.compare_level_to(min_level) >= 0
            for key, min_level in
            AdminRepoIndexView._CATEGORY_PERMISSION_LEVELS.items()
        }

    @views.admin.base.enforce_manager_admin_level
    def get(self, request, *args, **kwargs):
        """Serves GET requests."""
        del request, args, kwargs  # Unused.
        language_exonyms = sorted(list(const.LANGUAGE_EXONYMS.items()),
                                  key= lambda lang: lang[1])
        category_permissions = self._get_category_permissions()
        language_config = self._get_language_config(category_permissions)
        encoder = simplejson.encoder.JSONEncoder(ensure_ascii=False)
        return self.render(
            'admin_repo_index.html',
            category_permissions=category_permissions,
            language_exonyms_json=encoder.encode(language_exonyms),
            language_config_json=encoder.encode(language_config),
            xsrf_token=self.xsrf_tool.generate_token(
                self.env.user.user_id(), self.ACTION_ID))

    def _get_language_config(self, category_permissions):
        language_config = {}
        language_config['lang_list'] = self.env.config.get(
            'language_menu_options', [])
        if category_permissions['everything_else']:
            language_config['repo_titles'] = self.env.config.get(
                'repo_titles', {})
        if category_permissions['custom_messages']:
            custom_messages = {}
            for config_key in AdminRepoIndexView._CUSTOM_MESSAGES_CONFIG_KEYS:
                custom_messages[config_key] = self.env.config.get(
                    config_key, {})
            language_config['custom_messages'] = custom_messages
        return language_config

    @views.admin.base.enforce_manager_admin_level
    def post(self, request, *args, **kwargs):
        """Serves POST requests, updating the repo's configuration."""
        del request, args, kwargs  # Unused.
        self.enforce_xsrf(self.ACTION_ID)
        category_permissions = self._get_category_permissions()
