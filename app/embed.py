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

from utils import *


class Handler(BaseHandler):
    def get(self):
        env = self.env
        self.render('embed.html', close_button=self.params.ui == 'small',
                    gadget_link_html=anchor_start(
                        '%s/gadget?lang=%s' % (env.repo_url, env.lang)),
                    apache_link_html=anchor_start(
                        'http://www.apache.org/licenses/LICENSE-2.0.html'),
                    developers_link_html=anchor_start(
                        'http://code.google.com/p/googlepersonfinder'),
                    link_end_html='</a>'
)
