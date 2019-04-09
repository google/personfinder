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

"""The admin API key pages."""

import model
import views.admin.base


class ApiKeyListView(views.admin.base.AdminBaseView):
    """The admin API key list view."""

    ACTION_ID = 'admin/api_keys/list'

    def get(self, request, *args, **kwargs):
        """Serves get requests.

        Args:
            request: Unused.
            *args: Unused.
            **kwargs: Unused.

        Returns:
            HttpResponse: A HTTP response with the API key list.
        """
        del request, args, kwargs  # unused
        auths = model.Authorization.all().filter(
            'repo = ', self.env.repo or '*')
        return self.render(
            'admin_api_keys_list.html',
            admin_api_keys_url=self.build_absolute_path('/admin/api_keys'),
            user=self.env.user, user_email=self.env.user.email(),
            authorizations=auths,
            xsrf_token=self.xsrf_tool.generate_token(
               self.env.user.user_id(), 'admin_api_keys'))
