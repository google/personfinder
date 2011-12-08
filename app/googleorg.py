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
    repo_required = False
    ignore_repo = True

    def get(self, path):
        if path:
            path = path.strip('/')
        repo_menu_html = self.get_repo_menu_html()
        if path == 'howitworks':
            self.render('templates/googleorg-howitworks.html',
                        repo_menu_html=repo_menu_html)

        elif path == 'faq':
            self.render('templates/googleorg-faq.html',
                        repo_menu_html=repo_menu_html)

        elif path == 'responders':
            self.render('templates/googleorg-responders.html',
                        repo_menu_html=repo_menu_html)

        else:
            return self.redirect('/personfinder/global/howitworks')


if __name__ == '__main__':
    # we can't use utils.run here because we need our path to be at the root.
    webapp.util.run_wsgi_app(webapp.WSGIApplication(
        [(r'/personfinder/?(faq|responders|howitworks)?', Handler),
         (r'/personfinder/global/?(faq|responders|howitworks)?', Handler)]))
