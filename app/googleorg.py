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

import utils


class Handler(utils.Handler):
    subdomain_required = False
    ignore_subdomain = True

    def get(self, path):
        path = path.strip('/')
        if path == 'global/howitworks':
            self.render('templates/googleorg-howitworks.html')

        elif path == 'global/faq':
            self.render('templates/googleorg-faq.html')

        elif path == 'global/responders':
            self.render('templates/googleorg-responders.html')

        else:
            return self.redirect('/personfinder/global/howitworks')


if __name__ == '__main__':
    utils.run(('/personfinder(.*)', Handler))
