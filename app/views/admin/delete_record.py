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
"""The admin delete-record page.

No deleting is done from this page itself; it's just a way to skip the captcha
on the user-facing deletion page.
"""

import django.shortcuts

import const
import reveal
import utils
import views.admin.base


class AdminDeleteRecordView(views.admin.base.AdminBaseView):
    """The admin delete-record view."""

    ACTION_ID = 'admin/delete_record'

    def setup(self, request, *args, **kwargs):
        super(AdminDeleteRecordView, self).setup(request, *args, **kwargs)
        self.params.read_values(post_params={'id': utils.strip})

    @views.admin.base.enforce_moderator_admin_level
    def get(self, request, *args, **kwargs):
        """Serves GET requests with the deletion form."""
        del request, args, kwargs  # unused
        return self.render(
            'admin_delete_record.html',
            id='%s/person.' % const.HOME_DOMAIN,
            xsrf_token=self.xsrf_tool.generate_token(self.env.user.user_id(),
                                                     self.ACTION_ID))

    @views.admin.base.enforce_moderator_admin_level
    def post(self, request, *args, **kwargs):
        """Sends the user to the deletion page with a valid signature."""
        del request, args, kwargs  # unused
        self.enforce_xsrf(self.ACTION_ID)
        action = ('delete', self.params.id)
        path = '/delete?' + utils.urlencode({
            'id': self.params.id,
            'signature': reveal.sign(action),
        })
        return django.shortcuts.redirect(
            self.build_absolute_uri(path, self.env.repo))
