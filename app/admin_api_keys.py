#!/usr/bin/python2.5
# Copyright 2011 Google Inc.
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

import urllib

from google.appengine.ext import db
from google.appengine.api import users

from model import (
    Authorization, ApiKeyManagementLog
)
import utils

from django.utils.translation import ugettext as _

"""
The string representation for a key of an Authorization entity should
not be in any URL because the representation of db.Key can be
de-serialized, thus it can reveal the raw api key, so we use an
encrypted key of an Authorization entity for the url params.
"""

API_KEY_LENGTH = 16
KEYS_PER_PAGE = 50

def to_authorization_params(param):
    param_list = [
        'contact_name',
        'contact_email',
        'organization_name',
        'domain_write_permission',
        'read_permission',
        'full_read_permission',
        'search_permission',
        'subscribe_permission',
        'mark_notes_reviewed',
        'is_valid',
    ]
    ret = {}
    for param_name in param_list:
        ret[param_name] = getattr(param, param_name)
    return ret


class ListApiKeys(utils.Handler):
    """
    A handler for listing API keys for a particular domain.
    TODO(tmatsuo) implement a search/filter and pagination feature.
    """
    @utils.require_api_key_management_permission
    def get(self):
        user = users.get_current_user()
        q = Authorization.all().filter('subdomain =', self.subdomain)
        authorizations = q.fetch(KEYS_PER_PAGE)
        nav_html = ('<a href="/admin/api_keys?subdomain=%s">%s</a> '
                    % (self.subdomain, _('Create a new API key')))
        return self.render('admin_api_keys_list.html',
                           nav_html=nav_html,
                           user=user, authorizations=authorizations)


class CreateOrUpdateApiKey(utils.Handler):
    """A handler for create/update API keys."""

    def render_form(self, authorization=None, message=''):
        """Display a form for create/update Authorization"""
        user = users.get_current_user()
        if authorization:
            nav_html = ('<a href="/admin/api_keys?subdomain=%s">%s</a> '
                        % (self.subdomain, _('Create a new API key')))
            operation_name = 'Update an existing key'
        else:
            authorization = Authorization.DEFAULT_SETTINGS
            operation_name = _('Create a new API key')
            nav_html = ''

        nav_html += ('<a href="/admin/api_keys/list?subdomain=%s">%s</a>'
                     % (self.subdomain, _('List API keys')))
        return self.render(
            'admin_api_keys.html',
            user=user, target_key=authorization,
            login_url=users.create_login_url(self.request.url),
            logout_url=users.create_logout_url(self.request.url),
            operation_name=operation_name, message=message,
            nav_html=nav_html,
        )

    @utils.require_api_key_management_permission
    def get(self):
        """
        It can be called with a key of ApiKeyManagementLog entity. In
        such a case, it will show a detailed information of the key in
        a form for updating the key, otherwise, it will show a form
        for creating a new API key.
        """
        management_log_key = self.request.get('log_key')
        if management_log_key:
            management_log = db.get(management_log_key)
            message = ''
            if management_log.action == ApiKeyManagementLog.CREATE:
                message = _('A new API key has been created successfully.')
            elif management_log.action == ApiKeyManagementLog.UPDATE:
                message = _('The API key has been updated successfully.')
            return self.render_form(management_log.authorization, message)
        else:
            # display a creation form
            return self.render_form()

    @utils.require_api_key_management_permission
    def post(self):
        """Handle a post request from the create/update/edit form"""

        # Handle a form submission from list page
        if self.request.get('edit_form'):
            try:
                authorization = db.get(self.request.get('authorization_key'))
            except Exception:
                return self.error(404, _('No such Authorization entity.'))
            return self.render_form(authorization)

        # Handle authorization form submission
        if not (self.params.contact_name and 
                self.params.contact_email and
                self.params.organization_name):
            return self.error(400,
                              _('Please fill in all the required fields.'))

        original_key = self.request.get('key')
        if original_key:
            # just override the existing one
            existing_authorization = db.get(original_key)
            key_str = existing_authorization.key().name().split(':')[1]
            action = ApiKeyManagementLog.UPDATE
        else:
            key_str = utils.get_random_string(API_KEY_LENGTH)
            action = ApiKeyManagementLog.CREATE

        authorization = Authorization.create(
            self.subdomain, key_str,
            **to_authorization_params(self.params))
        authorization.put()

        management_log = ApiKeyManagementLog(subdomain=self.subdomain,
                                             api_key=authorization.api_key,
                                             action=action)
        management_log.put()

        self.redirect('/admin/api_keys?repo=%s&log_key=%s'
                      % (self.subdomain, management_log.key()))


if __name__ == '__main__':
    utils.run(('/admin/api_keys', CreateOrUpdateApiKey),
              ('/admin/api_keys/list', ListApiKeys),
    )
