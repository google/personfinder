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

"""Tests for the Main handler."""

import unittest
from google.appengine.ext import testbed
from google.appengine.ext import webapp
from mock import patch
import webob

import config
import django.utils
import main
import test_handler

def setup_request(path):
    """Constructs a webapp.Request object for a given request path."""
    return webapp.Request(webob.Request.blank(path).environ)

class MainTests(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_get_repo_and_action(self):
        def check(path, repo, action):
            request = setup_request(path)
            assert main.get_repo_and_action(request) == (repo, action)
        check('/personfinder/foo', 'foo', '')
        check('/personfinder/foo/query', 'foo', 'query')
        check('/personfinder', None, '')
        check('/personfinder/global', None, '')
        check('/personfinder/global/faq', None, 'faq')
        check('/foo', 'foo', '')
        check('/foo/view', 'foo', 'view')

    def test_lang_vulnerability(self):
        """Regression test for bad characters in the lang parameter."""
        request = setup_request('/haiti/start&lang=abc%0adef:ghi')
        env = main.setup_env(request)
        assert '\n' not in env.lang, env.lang
        assert ':' not in env.lang, env.lang

    def test_default_language(self):
        """Verify that language_menu_options[0] is used as the default."""
        request = setup_request('/haiti/start')
        handler = main.Main(request, webapp.Response())
        assert handler.env.lang == 'en'  # first language in the options list
        assert django.utils.translation.get_language() == 'en'

        config.set_for_repo('haiti', language_menu_options=['fr', 'ht', 'es'])

        request = setup_request('/haiti/start')
        handler = main.Main(request, webapp.Response())
        assert handler.env.lang == 'fr'  # first language in the options list
        assert django.utils.translation.get_language() == 'fr'

    def test_content_security_policy_for_react(self):
        """Verify CSP is set when the React UI is enabled."""
        config.set(enable_react_ui=True)
        request = setup_request('/')
        response = webapp.Response()
        handler = main.Main(request, response)
        with patch('utils.generate_random_key') as generate_random_key_mock:
            generate_random_key_mock.return_value = 'totallyrandomkey'
            handler.get()
            assert 'Content-Security-Policy' in response.headers
            assert ('nonce-totallyrandomkey' in
                    response.headers['Content-Security-Policy'])
            assert 'nonce="totallyrandomkey"' in response.body


if __name__ == '__main__':
    unittest.main()
