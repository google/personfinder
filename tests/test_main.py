#!/usr/bin/python2.7
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
from google.appengine.ext import webapp
import webob

import config
import django.utils
import main
import test_handler

def setup_request(path):
    """Constructs a webapp.Request object for a given request path."""
    return webapp.Request(webob.Request.blank(path).environ)

class MainTests(unittest.TestCase):
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

    def test_shiftjis_get(self):
        """Tests Shift-JIS encoding of GET query parameters."""
        request = setup_request(
            '/japan/results?charsets=shift_jis&query=%8D%B2%93%A1&role=seek&')
        handler = main.Main(request, webapp.Response())
        assert handler.env.charset == 'shift_jis'
        assert request.charset == 'shift_jis'
        assert request.get('query') == u'\u4F50\u85E4'

    def test_shiftjis_post(self):
        """Tests Shift-JIS encoding of POST query parameters."""
        request = setup_request('/japan/post?')
        request.body = 'charsets=shift_jis&given_name=%8D%B2%93%A1'
        request.method = 'POST'
        handler = main.Main(request, webapp.Response())
        assert handler.env.charset == 'shift_jis'
        assert request.charset == 'shift_jis'
        assert request.get('given_name') == u'\u4F50\u85E4'

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


if __name__ == '__main__':
    unittest.main()
