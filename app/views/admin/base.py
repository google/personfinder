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

    def setup(self, request, *args, **kwargs):
        """See docs on BaseView.setup."""
        # pylint: disable=attribute-defined-outside-init
        super(AdminBaseView, self).setup(request, *args, **kwargs)
        self.env.show_logo = True
        self.env.enable_javascript = True
        self.env.user = users.get_current_user()
        self.env.logout_url = users.create_logout_url(self.build_absolute_uri())
        self.env.all_repo_options = [
            utils.Struct(
                repo=repo, url=self.build_absolute_path('/%s/admin' % repo))
            for repo in sorted(model.Repo.list())
        ]
        self.xsrf_tool = utils.XsrfTool()

    def get_params(self):
        return views.base.read_params(
            super(AdminBaseView, self).get_params(),
            self.request,
            post_params={'xsrf_token': utils.strip})

    def dispatch(self, request, *args, **kwargs):
        """See docs on django.views.View.dispatch."""
        # All the admin pages, and only the admin pages, require the user to be
        # logged in as an admin.
        # If we start requiring login for other pages, we should consider
        # refactoring this into a decorator or something like that.
        if not self.env.user:
            return django.shortcuts.redirect(
                users.create_login_url(self.build_absolute_uri()))
        if not users.is_current_user_admin():
            logout_url = users.create_logout_url(self.build_absolute_uri())
            return self.render(
                'not_admin_error.html',
                status_code=403,
                logout_url=logout_url,
                user=self.env.user)
        return super(AdminBaseView, self).dispatch(request, args, kwargs)
