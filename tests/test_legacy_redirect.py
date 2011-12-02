#!/usr/bin/python2.5
# encoding: utf-8
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

"""Tests for legacy_redirect."""

import unittest
import utils
import webob

import legacy_redirect
from google.appengine.ext import webapp

class LegacyRedirectTests(unittest.TestCase):
    """Test that old-style subdomain requests get redirected properly."""

    def init(self, path, host):
        env = webob.Request.blank(path).environ
        env['HTTP_HOST'] = host
        request = webapp.Request(env)
        response = webapp.Response()
        self.handler = utils.Handler()
        self.handler.initialize(request, response)

    def test_get_subdomain_host(self):
        self.init('/', 'japan.personfinder.appspot.com')
        assert 'japan' == legacy_redirect.get_subdomain(self.handler)

    def test_subdomain_redirect(self):
        """Verify that we redirect a host-based subdomain properly."""
        self.init('/', 'japan.personfinder.appspot.com')
        legacy_redirect.redirect(self.handler)
        self.assertEquals(self.handler.response.status, 302)
        self.assertEquals(self.handler.response.headers['Location'],
                          'http://personfinder.appspot.com/japan/')


    def test_subdomain_action(self):
        """Verify that a random action gets redirected properly."""
        self.init('/view?first_name=&id=turkey-2011.person-finder.appspot.com'
                  '%2Fperson.1141073&last_name=&query=ahmet&role=seek',
                  host='turkey-2011.googlepersonfinder.appspot.com')
        legacy_redirect.redirect(self.handler)
        self.assertEquals(self.handler.response.status, 302)
        self.assertEquals(self.handler.response.headers['Location'],
                          'http://googlepersonfinder.appspot.com/turkey-2011'
                          '/view?first_name='
                          '&id=turkey-2011.person-finder.appspot.com'
                          '%2Fperson.1141073&last_name=&query=ahmet&role=seek')

    def test_dotorg_redirect(self):
        """Verify that personfinder.google.org redirects work."""
        self.init('/view?first_name=&id=turkey-2011.person-finder.appspot.com'
                  '%2Fperson.1141073&last_name=&query=ahmet&role=seek',
                  host='turkey-2011.personfinder.google.org')
        legacy_redirect.redirect(self.handler)
        self.assertEquals(self.handler.response.status, 302)
        self.assertEquals(self.handler.response.headers['Location'],
                          'http://personfinder.google.org/turkey-2011/view?'
                          'first_name=&id=turkey-2011.person-finder.appspot.com'
                          '%2Fperson.1141073&last_name=&query=ahmet&role=seek')
