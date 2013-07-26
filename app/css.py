#!/usr/bin/python2.5
# Copyright 2013 Google Inc.
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

from model import *
from utils import *

class Handler(BaseHandler):

    repo_required = False
    ignore_deactivation = True

    def get(self):
        self.response.headers['Content-Type'] = 'text/css'
        if self.env.ui in ['small', 'light']:
            template_name = 'css-%s' % self.env.ui
        else:
            template_name = 'css-default'
        self.render(
            template_name,
            start='right' if self.env.rtl else 'left',
            end='left' if self.env.rtl else 'right')
