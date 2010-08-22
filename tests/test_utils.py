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

"""Tests for utils."""

from google.appengine.ext import webapp
import datetime
import os
import tempfile
import unittest

import config
import utils


class UtilsTests(unittest.TestCase):
  """Test the loose odds and ends."""

  def test_to_utf8(self):
    self.assertEqual('abc', utils.to_utf8('abc'))
    self.assertEqual('abc', utils.to_utf8(u'abc'))
    self.assertEqual('\xe4\xbd\xa0\xe5\xa5\xbd', utils.to_utf8(u'\u4f60\u597d'))
    self.assertEqual('\xe4\xbd\xa0\xe5\xa5\xbd',
                     utils.to_utf8('\xe4\xbd\xa0\xe5\xa5\xbd'))

  def test_urlencode(self):
    self.assertEqual(
        'a+param+with+space=value&foo=bar&x=a+value+with+space',
        utils.urlencode({'foo': 'bar',
                         'skipped': (),
                         'a param with space': 'value',
                         'x': 'a value with space'}))
    self.assertEqual(
        'a=foo&b=%E4%BD%A0%E5%A5%BD&c=%E4%BD%A0%E5%A5%BD&%E4%BD%A0%E5%A5%BD=d',
        utils.urlencode({'a': u'foo',
                         'b': u'\u4f60\u597d',
                         'c': '\xe4\xbd\xa0\xe5\xa5\xbd',
                         u'\u4f60\u597d': 'd'}))

  def test_set_url_param(self):
    self.assertEqual(
        'http://example.com/server/?foo=bar',
        utils.set_url_param('http://example.com/server/', 'foo', 'bar'))
    self.assertEqual(
        'http://example.com/server?foo=bar',
        utils.set_url_param('http://example.com/server', 'foo', 'bar'))
    self.assertEqual(
        'http://example.com/server?foo=bar',
        utils.set_url_param('http://example.com/server?foo=baz', 'foo', 'bar'))
    self.assertEqual(
        'http://example.com/server?foo=bar',
        utils.set_url_param('http://example.com/server?foo=baz', 'foo', 'bar'))

    # Collapses multiple parameters
    self.assertEqual(
        'http://example.com/server?foo=bar',
        utils.set_url_param('http://example.com/server?foo=baz&foo=baq',
                            'foo', 'bar'))
    self.assertEqual(
        'http://example.com/server?foo=baq&x=y',
        utils.set_url_param('http://example.com/server?foo=baz&foo=baq',
                            'x', 'y'))

    # Unicode is properly converted
    self.assertEqual(
        'http://example.com/server?foo=bar&'
        '%E4%BD%A0%E5%A5%BD=%E4%BD%A0%E5%A5%BD',
        utils.set_url_param('http://example.com/server?foo=bar',
                            u'\u4f60\u597d', '\xe4\xbd\xa0\xe5\xa5\xbd'))

  def test_strip(self):
    self.assertEqual('', utils.strip('    '))
    self.assertEqual(u'', utils.strip(u'    '))
    self.assertEqual('x', utils.strip('  x  '))
    self.assertEqual(u'x', utils.strip(u'  x  '))
    self.assertRaises(Exception, utils.strip, None)

  def test_validate_yes(self):
    self.assertEqual('yes', utils.validate_yes('yes'))
    self.assertEqual('yes', utils.validate_yes('YES'))
    self.assertEqual('', utils.validate_yes('no'))
    self.assertEqual('', utils.validate_yes('y'))
    self.assertRaises(Exception, utils.validate_yes, None)

  def test_validate_role(self):
    self.assertEqual('provide', utils.validate_role('provide'))
    self.assertEqual('provide', utils.validate_role('PROVIDE'))
    self.assertEqual('seek', utils.validate_role('seek'))
    self.assertEqual('seek', utils.validate_role('pro'))
    self.assertEqual('seek', utils.validate_role('provider'))
    self.assertRaises(Exception, utils.validate_role, None)

  # TODO: test_validate_image


class HandlerTests(unittest.TestCase):
  """Tests for the base handler implementation."""

  def setUp(self):
    # Set up temp file to contain a template whose content we can change
    fd, self._template_path = tempfile.mkstemp()
    os.close(fd)

    # Stash the template ROOT hardwired into the module and install our own
    self._stored_root = utils.ROOT
    utils.ROOT = os.path.dirname(self._template_path)
    self._template_name = os.path.basename(self._template_path)

    config.set_for_subdomain(
      'haiti',
      subdomain_title={'en': 'Haiti Earthquake'},
      language_menu_options=['en', 'ht', 'fr', 'es'])

  def tearDown(self):
    # Cleanup the template file
    os.unlink(self._template_path)

    # Restore the original template ROOT
    utils.ROOT = self._stored_root

  def reset_global_cache(self):
    """Resets the cache that the handler classes."""
    utils.global_cache = {}
    utils.global_cache_insert_time = {}

  def set_template_content(self, content):
    template = None
    try:
      template = open(self._template_path, mode='w')
      template.write(content)
    finally:
      if template:
        template.close()
      # Reset the internal template cache used by appengine to ensure our
      # content is re-read
      webapp.template.template_cache = {}

  def handler_for_url(self, url):
    request = webapp.Request(webapp.Request.blank(url).environ)
    response = webapp.Response()
    handler = utils.Handler()
    handler.initialize(request, response)
    return (request, response, handler)

  def test_parameter_validation(self):
    _, _, handler = self.handler_for_url(
        '/main?'
        'subdomain=haiti&'
        'first_name=++John++&'
        'last_name=Doe&'
        'found=YES&'
        'role=PROVIDE&')

    self.assertEqual('John', handler.params.first_name)
    self.assertEqual('Doe', handler.params.last_name)
    self.assertEqual('yes', handler.params.found)
    self.assertEqual('provide', handler.params.role)

  def test_caches(self):
    self.reset_global_cache()
    self.set_template_content('hello')

    _, response, handler = self.handler_for_url('/main?subdomain=haiti')
    handler.render(self._template_name, cache_time=3600)
    self.assertEqual('hello', response.out.getvalue())

    self.set_template_content('goodbye')

    _, response, handler = self.handler_for_url('/main?subdomain=haiti')
    handler.render(self._template_name, cache_time=3600)
    self.assertEqual('hello', response.out.getvalue())

    self.reset_global_cache()

    _, response, handler = self.handler_for_url('/main?subdomain=haiti')
    handler.render(self._template_name, cache_time=3600)
    self.assertEqual('goodbye', response.out.getvalue())


if __name__ == '__main__':
  unittest.main()
