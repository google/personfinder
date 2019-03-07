#!/usr/bin/python2.7
# Copyright 2016 Google Inc.
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


from const import *
from model import *
from utils import *
import reveal


class Handler(BaseHandler):
    """An admin page to delete person records."""

    # After a repository is deactivated, we still need the admin page to be
    # accessible so we can edit its settings.
    ignore_deactivation = True

    repo_required = False
    admin_required = True

    def get(self):
        xsrf_tool = XsrfTool()
        user = users.get_current_user()
        self.render(
            'admin_delete_record.html',
            id=self.env.domain + '/person.',
            xsrf_token=xsrf_tool.generate_token(
                user.user_id(), 'admin_delete_record'))

    def post(self):
        xsrf_tool = XsrfTool()
        user = users.get_current_user()
        if not (self.params.xsrf_token and xsrf_tool.verify_token(
                    self.params.xsrf_token, user.user_id(),
                    'admin_delete_record')):
            self.error(403)
            return False
        # Redirect to the deletion handler with a valid signature.
        action = ('delete', str(self.params.id))
        self.redirect('/delete', id=self.params.id,
                      signature=reveal.sign(action))
