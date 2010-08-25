#!/usr/bin/python2.5
# Copyright 2010 Google Inc.
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

from datetime import datetime
import sys

from model import *
from utils import *
import reveal


class Admin(Handler):
    def get(self):
        user = users.get_current_user()
        self.render('templates/admin.html', user=user,
                    login_url=users.create_login_url(self.request.url),
                    logout_url=users.create_logout_url(self.request.url),
                    id=self.env.domain + '/person.')

    def post(self):
        if self.params.operation == 'delete':
            # Redirect to the deletion handler with a valid signature.
            action = ('delete', str(self.params.id))
            self.redirect('/delete', id=self.params.id,
                          signature=reveal.sign(action))


if __name__ == '__main__':
    run(('/admin', Admin))
