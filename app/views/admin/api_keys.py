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

"""The admin API key pages.

The way navigation is handled for these pages is a little unintuitive so let me
explain:
 - The main entry point to these pages is the list view, which accepts GET
   requests and returns a view with a) a link to create a new API key (which
   makes a GET request to the management page) and b) a list of existing pages,
   each with an "edit" button.
 - The list view's "edit" buttons make a _POST_ request to send the user to the
   management page for that key, with the key in a CGI parameter. I'm not
   exactly sure why that's a POST instead of a GET request, but I would guess
   it's to keep API keys out of URLs (which would end up in browser histories).
 - When a key is created or edited through the management page, it makes a POST
   request to itself, which returns a redirect to itself (which becomes a GET
   request). Consequently, the POST/GET handlers are the opposite of what you
   might expect: the POST handler handles the initial display of the form, while
   the GET handler handles what you see afterwards. The GET handler takes the
   Datastore key for a log entry (via a CGI param), which it uses to get the API
   key itself by way of the log entry.
"""

import django.core.exceptions
import django.shortcuts
import django.utils.translation as t
from google.appengine.ext import db

import model
import utils
import views.admin.base


_API_KEY_LENGTH = 16


class ApiKeyListView(views.admin.base.AdminBaseView):
    """The admin API key list view."""

    ACTION_ID = 'admin/api_keys/list'

    @views.admin.base.enforce_superadmin_admin_level
    def get(self, request, *args, **kwargs):
        """Serves a view with a list of API keys."""
        del request, args, kwargs  # unused
        auths = model.Authorization.all().filter(
            'repo = ', self.env.repo or '*')
        return self.render(
            'admin_api_keys_list.html',
            admin_api_keys_url=self.build_absolute_path(
                '/admin/api_keys', self.env.repo or 'global'),
            user=self.env.user,
            user_email=self.env.user.email(),
            authorizations=auths,
            xsrf_token=self.xsrf_tool.generate_token(
               self.env.user.user_id(), 'admin_api_keys'))


class ApiKeyManagementView(views.admin.base.AdminBaseView):
    """The API key management view, for creating or editing keys."""

    ACTION_ID = 'admin/api_keys'

    def setup(self, request, *args, **kwargs):
        super(ApiKeyManagementView, self).setup(request, *args, **kwargs)
        self.params.read_values(
            get_params={
                'log_key': utils.strip,
            },
            post_params={
                'authorization_key': utils.strip,
                'believed_dead_permission': utils.validate_checkbox_as_bool,
                'contact_name': utils.strip,
                'contact_email': utils.strip,
                'domain_write_permission': utils.strip,
                'edit_form': utils.strip,
                'full_read_permission': utils.validate_checkbox_as_bool,
                'is_valid': utils.validate_checkbox_as_bool,
                'key': utils.strip,
                'mark_notes_reviewed': utils.validate_checkbox_as_bool,
                'organization_name': utils.strip,
                'read_permission': utils.validate_checkbox_as_bool,
                'search_permission': utils.validate_checkbox_as_bool,
                'stats_permission': utils.validate_checkbox_as_bool,
                'subscribe_permission': utils.validate_checkbox_as_bool,
            })

    @views.admin.base.enforce_superadmin_admin_level
    def get(self, request, *args, **kwargs):
        if self.params.log_key:
            management_log_key = self.params.log_key
            management_log = db.get(management_log_key)
            message = ''
            if management_log.action == model.ApiKeyManagementLog.CREATE:
                message = t.ugettext(
                    'A new API key has been created successfully.')
            elif management_log.action == model.ApiKeyManagementLog.UPDATE:
                message = t.ugettext(
                    'The API key has been updated successfully.')
            return self._render_form(management_log.authorization, message)
        else:
            return self._render_form()

    def _make_authorization(self, repo, key_str):
        """Creates and stores an Authorization entity with the request's params.

        Args:
            repo (str): The ID of a repository, or '*' for a global key.
            key_str (str): The key itself.

        Returns:
            Authorization: An Authorization entity, already put in Datastore.
        """
        authorization = model.Authorization.create(
            repo,
            key_str,
            contact_name=self.params.contact_name,
            contact_email=self.params.contact_email,
            organization_name=self.params.organization_name,
            domain_write_permission=self.params.domain_write_permission,
            read_permission=self.params.read_permission,
            full_read_permission=self.params.full_read_permission,
            search_permission=self.params.search_permission,
            subscribe_permission=self.params.subscribe_permission,
            mark_notes_reviewed=self.params.mark_notes_reviewed,
            believed_dead_permission=self.params.believed_dead_permission,
            stats_permission=self.params.stats_permission,
            is_valid=self.params.is_valid)
        authorization.put()
        return authorization

    @views.admin.base.enforce_superadmin_admin_level
    def post(self, request, *args, **kwargs):
        self.enforce_xsrf('admin_api_keys')

        # Navigation to an individual key's management page is handled by making
        # a POST request to this view. When it's such a request, the edit_form
        # param will be set.
        if self.params.edit_form:
            authorization = db.get(self.params.authorization_key)
            if not authorization:
                return self.error(404, t.ugettext(
                    'No such Authorization entity.'))
            return self._render_form(authorization)

        if not (self.params.contact_name and
                self.params.contact_email and
                self.params.organization_name):
            return self.error(400, t.ugettext(
                'Please fill in all the required fields.'))

        repo = self.env.repo
        if repo == 'global':
            repo = '*'
        if self.params.key:
            # Just override the existing one.
            existing_authorization = db.get(self.params.key)
            if not existing_authorization:
                return self.error(404, t.ugettext(
                    'No such Authorization entity.'))
            # This shouldn't happen unless an admin does something funny with
            # URLs, but check just to be safe.
            if existing_authorization.repo != repo:
                return self.error(400, t.ugettext(
                    'Authorization already exists for another repo! '
                    'That\'s not expected.'))
            key_str = existing_authorization.api_key
            action = model.ApiKeyManagementLog.UPDATE
        else:
            key_str = utils.generate_random_key(_API_KEY_LENGTH)
            action = model.ApiKeyManagementLog.CREATE

        authorization = self._make_authorization(repo, key_str)

        management_log = model.ApiKeyManagementLog(
            repo=repo,
            api_key=authorization.api_key,
            action=action,
            ip_address=request.META.get('REMOTE_ADDR'),
            key_state=authorization.summary_str())
        management_log.put()

        return django.shortcuts.redirect(
            self.build_absolute_uri(
                '/%s/admin/api_keys?repo=%s&log_key=%s' % (
                    self.env.repo or 'global',
                    self.env.repo or 'global',
                    management_log.key())))

    def _render_form(self, authorization=None, message=None):
        """Produces a response with the API key management form.

        Args:
            authorization (Authorization, optional): An Authorization object. If
                present, an edit form will be produced; if None, a create form
                will be produced.
            message (str, optional): A message to display along with the form.

        Returns:
            HttpResponse: An HTTP response with the form.
        """
        if authorization:
            operation_type = 'update'
        else:
            authorization = model.Authorization.DEFAULT_SETTINGS
            operation_type = 'create'
        list_url = self.build_absolute_path(
            '/%s/admin/api_keys/list' % (self.env.repo or 'global'))
        return self.render(
            'admin_api_keys.html',
            user=self.env.user,
            target_key=authorization,
            user_email=self.env.user.email(),
            operation_type=operation_type,
            message=message,
            list_url=list_url,
            xsrf_token=self.xsrf_tool.generate_token(
                self.env.user.user_id(), 'admin_api_keys'),
        )
