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

    _POST_PARAMETERS = {
        'xsrf_token': utils.strip,
    }

    def setup(self, request, *args, **kwargs):
        super(AdminBaseView, self).setup(request, *args, **kwargs)
        self.read_params(post_params=AdminBaseView._POST_PARAMETERS)
        self.env.show_logo = True
        self.env.enable_javascript = True
        self.env.user = users.get_current_user()
        self.env.logout_url = users.create_logout_url(self.build_absolute_uri())
        self.env.all_repo_options = [
            utils.Struct(
                repo=repo, url=self.build_absolute_path('/%s/admin' % repo))
            for repo in sorted(model.Repo.list())
        ]

    def dispatch(self, request, *args, **kwargs):
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
