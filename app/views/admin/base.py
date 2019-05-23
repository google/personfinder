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
"""Code shared by admin view modules."""

import django.shortcuts
from google.appengine.api import users

import model
import modelmodule.admin_acls as admin_acls_model
import utils
import views.base


class AdminBaseView(views.base.BaseView):
    """Base view for admin views."""

    class Env(views.base.BaseView.Env):
        """Class to store environment information used by views and templates.
        """
        # pylint: disable=attribute-defined-outside-init

        @property
        def all_repo_options(self):
            """Gets a list of Structs with repo IDs and URLs.

            Each Struct is expected to have two values:
            - repo: the repo ID
            - url: the URL to the repo's admin page
            """
            return self._all_repo_options

        @all_repo_options.setter
        def all_repo_options(self, value):
            self._all_repo_options = value

        @property
        def logout_url(self):
            """Gets a logout URL for the user."""
            return self._logout_url

        @logout_url.setter
        def logout_url(self, value):
            self._logout_url = value

        @property
        def user(self):
            """Gets a users.User object for the current user, if any."""
            return self._user

        @user.setter
        def user(self, value):
            self._user = value

    def _get_user_admin_permission(self):
        if not self.env.user:
            return None
        user_repo_admin_object = admin_acls_model.AdminPermission.get(
            self.env.repo, self.env.user.email())
        if (user_repo_admin_object and
                user_repo_admin_object.expiration_date < utils.get_utcnow()):
            user_repo_admin_object = None
        user_global_admin_object = admin_acls_model.AdminPermission.get(
            'global', self.env.user.email())
        if (user_global_admin_object and
                user_global_admin_object.expiration_date < utils.get_utcnow()):
            user_global_admin_object = None
        if user_repo_admin_object is None:
            return user_global_admin_object
        if user_global_admin_object is None:
            return user_repo_admin_object
        if user_repo_admin_object.compare_level_to(
                user_global_admin_object.access_level) > 0:
            return user_repo_admin_object
        return user_global_admin_object

    def setup(self, request, *args, **kwargs):
        """See docs on BaseView.setup."""
        # pylint: disable=attribute-defined-outside-init
        super(AdminBaseView, self).setup(request, *args, **kwargs)
        self.params.read_values(post_params={'xsrf_token': utils.strip})
        self.env.show_logo = True
        self.env.enable_javascript = True
        self.env.user = users.get_current_user()
        self.env.user_admin_permission = self._get_user_admin_permission()
        self.env.logout_url = users.create_logout_url(self.build_absolute_uri())
        self.env.all_repo_options = [
            utils.Struct(
                repo=repo, url=self.build_absolute_path('/%s/admin' % repo))
            for repo in sorted(model.Repo.list())
        ]
        self.xsrf_tool = utils.XsrfTool()

    def enforce_xsrf(self, action_id):
        """Verifies the request's XSRF token.

        Checks the request's XSRF token and raises Django's PermissionDenied
        exception if the request didn't have a token or the token is invalid.
        As long as it's not caught, this will cause Django to return a 403.

        Args:
            action_id (str): The action ID used for creating the page's tokens.

        Raises:
            PermissionDenied: If the request's token is missing or invalid.
        """
        if not (self.params.xsrf_token and
                self.xsrf_tool.verify_token(
                    self.params.xsrf_token,
                    self.env.user.user_id(),
                    action_id)):
            raise django.core.exceptions.PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        """See docs on django.views.View.dispatch."""
        # All the admin pages, and only the admin pages, require the user to be
        # logged in as an admin.
        # If we start requiring login for other pages, we should consider
        # refactoring this into a decorator or something like that.
        if not self.env.user:
            return django.shortcuts.redirect(
                users.create_login_url(self.build_absolute_uri()))
        return super(AdminBaseView, self).dispatch(request, args, kwargs)


def _enforce_admin_level(user_admin_permission, min_level):
    if user_admin_permission is None:
        raise django.core.exceptions.PermissionDenied
    if user_admin_permission.compare_level_to(min_level) < 0:
        raise django.core.exceptions.PermissionDenied


def enforce_moderator_admin_level(func):
    """Require that the user be a moderator (or return a 403)."""
    def inner(self, *args, **kwargs):
        """Implementation of the enforce_moderator_admin_level decorator."""
        _enforce_admin_level(
            self.env.user_admin_permission,
            admin_acls_model.AdminPermission.AccessLevel.MODERATOR)
        return func(self, *args, **kwargs)
    return inner


def enforce_manager_admin_level(func):
    """Require that the user be a manager (or return a 403)."""
    def inner(self, *args, **kwargs):
        """Implementation of the enforce_manager_admin_level decorator."""
        _enforce_admin_level(
            self.env.user_admin_permission,
            admin_acls_model.AdminPermission.AccessLevel.MANAGER)
        return func(self, *args, **kwargs)
    return inner


def enforce_superadmin_admin_level(func):
    """Require that the user be a superadmin (or return a 403)."""
    def inner(self, *args, **kwargs):
        """Implementation of the enforce_superadmin_admin_level decorator."""
        _enforce_admin_level(
            self.env.user_admin_permission,
            admin_acls_model.AdminPermission.AccessLevel.SUPERADMIN)
        return func(self, *args, **kwargs)
    return inner
