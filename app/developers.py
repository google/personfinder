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


class Developers(Handler):
    def get(self):
        self.render('templates/developers.html', close_button=self.params.small,
                    apache_link=anchor_start(
                        'http://www.apache.org/licenses/LICENSE-2.0.html'),
                    cc_link=anchor_start(
                        'http://creativecommons.org/licenses/by/3.0/legalcode'),
                    googlegroup_email=anchor(
                        'http://groups.google.com/group/personfinder',
                        'personfinder@googlegroups.com'),
                    authkey_email=anchor('mailto:pf-authkey@google.com',
                                         'pf-authkey@google.com'),
                    pfif_link=anchor_start(
                        'http://zesty.ca/pfif/1.2/pfif-1.2-example.html'),
                    codesite_link=anchor_start(
                        'http://code.google.com/p/googlepersonfinder'),
                    end_link='</a>')

if __name__ == '__main__':
    run(('/developers', Developers))
