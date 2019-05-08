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
              value for _, value in sorted(lang_list, key=lambda kv : kv[0])]
          self.params.read_values(
              post_params={
                  'activation_status': utils.validate_int,
                  'deactivation_message_html': utils.strip,
              })

    def setup(self, request, *args, **kwargs):
        """See docs on BaseView.setup."""
        # pylint: disable=attribute-defined-outside-init
        super(AdminRepoIndexView, self).setup(request, *args, **kwargs)
        self._repo_obj = model.Repo.get(self.env.repo)
        self._read_params(request)
        self._category_permissions = self._get_category_permissions()

    def _get_category_permissions(self):
        return {
            key: self.env.user_admin_permission.compare_level_to(min_level) >= 0
            for key, min_level in
            AdminRepoIndexView._CATEGORY_PERMISSION_LEVELS.items()
        }

    def _render_form(self):
        language_exonyms = sorted(list(const.LANGUAGE_EXONYMS.items()),
                                  key= lambda lang: lang[1])
        encoder = simplejson.encoder.JSONEncoder(ensure_ascii=False)
        return self.render(
            'admin_repo_index.html',
            category_permissions=self._category_permissions,
            # Language-specific fields are handled by a React component, so we
            # encode that into JSON for it.
            # TODO(nworden): once we upgrade to Django 2.1+, use the new
            # built-in json_script filter instead of encoding it ourselves.
            language_exonyms_json=encoder.encode(language_exonyms),
            language_config_json=encoder.encode(self._get_language_config()),
            activation_config=self._get_activation_config(),
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

    @views.admin.base.enforce_manager_admin_level
    def post(self, request, *args, **kwargs):
        """Serves POST requests, updating the repo's configuration."""
        del request, args, kwargs  # Unused.
        self.enforce_xsrf(self.ACTION_ID)
        self._set_language_config()
        self._set_activation_config()
        # Reload the config since we just changed it.
        self.env.config = config.Configuration(self.env.repo)
        return self._render_form()

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
            self._repo_obj.activation_status = self.params.activation_status
            self._repo_obj.put()
            config.set_for_repo(
                self.env.repo,
                deactivation_message_html=self.params.deactivation_message_html)
