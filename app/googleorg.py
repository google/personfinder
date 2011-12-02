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
from google.appengine.ext import webapp

class Handler(utils.Handler):
    repo_name_required = False
    ignore_repo_name = True

    def get(self, path):
        path = path.strip('/')
        if path == 'howitworks':
            self.render('templates/googleorg-howitworks.html')

        elif path == 'faq':
            self.render('templates/googleorg-faq.html')

        elif path == 'responders':
            self.render('templates/googleorg-responders.html')

        else:
            return self.redirect('/personfinder/howitworks')


if __name__ == '__main__':
    # we can't use utils.run here because we need our path to be at the root.
    webapp.util.run_wsgi_app(webapp.WSGIApplication([(r'/personfinder(.*)', Handler)]))
