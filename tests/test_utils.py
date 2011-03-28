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

import datetime
import os
import tempfile
import unittest

from google.appengine.ext import webapp
from nose.tools import assert_raises

import config
import model
import utils


class UtilsTests(unittest.TestCase):
    """Test the loose odds and ends."""

    def test_encode(self):
        assert utils.encode('abc') == 'abc'
        assert utils.encode(u'abc') == 'abc'
        assert utils.encode(u'\u4f60\u597d') == '\xe4\xbd\xa0\xe5\xa5\xbd'
        assert utils.encode('\xe4\xbd\xa0\xe5\xa5\xbd') == \
            '\xe4\xbd\xa0\xe5\xa5\xbd'
        assert utils.encode('abc', 'shift_jis') == 'abc'
        assert utils.encode(u'abc', 'shift_jis') == 'abc'
        assert utils.encode(u'\uffe3\u2015', 'shift_jis') == '\x81P\x81\\'

    def test_urlencode(self):
        assert utils.urlencode({'foo': 'bar',
                                'skipped': (),
                                'a param with space': 'value',
                                'x': 'a value with space'}) == \
            'a+param+with+space=value&foo=bar&x=a+value+with+space'
        assert utils.urlencode({'a': u'foo',
                                'b': u'\u4f60\u597d',
                                'c': '\xe4\xbd\xa0\xe5\xa5\xbd',
                                u'\u4f60\u597d': 'd'}) == \
            'a=foo&b=%E4%BD%A0%E5%A5%BD' + \
            '&c=%E4%BD%A0%E5%A5%BD&%E4%BD%A0%E5%A5%BD=d'

    def test_set_url_param(self):
        assert utils.set_url_param(
            'http://example.com/server/', 'foo', 'bar') == \
            'http://example.com/server/?foo=bar'
        assert utils.set_url_param(
            'http://example.com/server', 'foo', 'bar') == \
            'http://example.com/server?foo=bar'
        assert utils.set_url_param(
            'http://example.com/server?foo=baz', 'foo', 'bar') == \
            'http://example.com/server?foo=bar'
        assert utils.set_url_param(
            'http://example.com/server?foo=baz', 'foo', 'bar') == \
            'http://example.com/server?foo=bar'

        # Collapses multiple parameters
        assert utils.set_url_param(
            'http://example.com/server?foo=baz&foo=baq', 'foo', 'bar') == \
            'http://example.com/server?foo=bar'
        assert utils.set_url_param(
            'http://example.com/server?foo=baz&foo=baq', 'x', 'y') == \
            'http://example.com/server?foo=baq&x=y'

        # Unicode is properly converted
        assert utils.set_url_param(
            'http://example.com/server?foo=bar',
            u'\u4f60\u597d', '\xe4\xbd\xa0\xe5\xa5\xbd') == \
            'http://example.com/server?foo=bar&' + \
            '%E4%BD%A0%E5%A5%BD=%E4%BD%A0%E5%A5%BD'

    def test_strip(self):
        assert utils.strip('    ') == ''
        assert utils.strip(u'    ') == u''
        assert utils.strip('  x  ') == 'x'
        assert utils.strip(u'  x  ') == u'x'
        assert_raises(Exception, utils.strip, None)

    def test_validate_yes(self):
        assert utils.validate_yes('yes') == 'yes'
        assert utils.validate_yes('YES') == 'yes'
        assert utils.validate_yes('no') == ''
        assert utils.validate_yes('y') == ''
        assert_raises(Exception, utils.validate_yes, None)

    def test_validate_role(self):
        assert utils.validate_role('provide') == 'provide'
        assert utils.validate_role('PROVIDE') == 'provide'
        assert utils.validate_role('seek') == 'seek'
        assert utils.validate_role('pro') == 'seek'
        assert utils.validate_role('provider') == 'seek'
        assert_raises(Exception, utils.validate_role, None)

    def test_validate_age(self):
        assert utils.validate_age('20') == '20'
        assert utils.validate_age(' 20 ') == '20'
        assert utils.validate_age('20-30') == '20-30'
        assert utils.validate_age('20 !') == ''

    # TODO: test_validate_image

    def test_set_utcnow_for_test(self):
        max_delta = datetime.timedelta(0,0,100)
        utcnow = datetime.datetime.utcnow()
        utilsnow = utils.get_utcnow()
        # max sure we're getting the current time.
        assert (utilsnow - utcnow) < max_delta
        # now set the utils time.
        test_time = datetime.datetime(2011, 1, 1, 0, 0)
        utils.set_utcnow_for_test(test_time)
        assert utils.get_utcnow() == test_time
        # now unset.
        utils.set_utcnow_for_test(None)
        assert utils.get_utcnow()
        assert utils.get_utcnow() != test_time


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

        model.Subdomain(key_name='haiti').put()

        config.set_for_subdomain(
            'haiti',
            subdomain_titles={'en': 'Haiti Earthquake'},
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

    def handler_for_useragent(self, useragent):
        url = '/main?subdomain=haiti'
        request = webapp.Request(webapp.Request.blank(url).environ)
        request.headers['user-agent'] = useragent
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

        assert handler.params.first_name == 'John'
        assert handler.params.last_name == 'Doe'
        assert handler.params.found == 'yes'
        assert handler.params.role == 'provide'

    def test_caches(self):
        self.reset_global_cache()
        self.set_template_content('hello')

        _, response, handler = self.handler_for_url('/main?subdomain=haiti')
        handler.render(self._template_name, cache_time=3600)
        assert response.out.getvalue() == 'hello'

        self.set_template_content('goodbye')

        _, response, handler = self.handler_for_url('/main?subdomain=haiti')
        handler.render(self._template_name, cache_time=3600)
        assert response.out.getvalue() == 'hello'

        self.reset_global_cache()

        _, response, handler = self.handler_for_url('/main?subdomain=haiti')
        handler.render(self._template_name, cache_time=3600)
        assert response.out.getvalue() == 'goodbye'

    def test_nonexistent_subdomain(self):
        request, response, handler = self.handler_for_url('/main?subdomain=x')
        assert 'No such domain' in response.out.getvalue()

    def test_shiftjis_get(self):
        req, resp, handler = self.handler_for_url(
            '/results?'
            'subdomain=japan\0&'
            'charsets=shift_jis&'
            'query=%8D%B2%93%A1\0&'
            'role=seek&')
        assert handler.params.query == u'\u4F50\u85E4'
        assert req.charset == 'shift_jis'
        assert handler.charset == 'shift_jis'

    def test_shiftjis_post(self):
        request = webapp.Request(webapp.Request.blank('/post?').environ)
        request.body = \
            'subdomain=japan\0&charsets=shift_jis&first_name=%8D%B2%93%A1\0'
        request.method = 'POST'
        response = webapp.Response()
        handler = utils.Handler()
        handler.initialize(request, response)

        assert handler.params.first_name == u'\u4F50\u85E4'
        assert request.charset == 'shift_jis'
        assert handler.charset == 'shift_jis'

    def test_get_mobile_spec(self):
        # Japanese Tier-2 phones
        _, _, handler = self.handler_for_useragent('DoCoMo/1.0/D502i/c10')
        assert handler.get_mobile_spec() == 'tier2'
        _, _, handler = self.handler_for_useragent(
            'DoCoMo/2.0 P906i(c100;TB;W24H15)')
        assert handler.get_mobile_spec() == 'tier2'
        _, _, handler = self.handler_for_useragent(
            'KDDI-HI31 UP.Browser/6.2.0.5 (GUI) MMP/2.0')
        assert handler.get_mobile_spec() == 'tier2'
        _, _, handler = self.handler_for_useragent(
            'SoftBank/1.0/805SC/SCJ001 Browser/NetFront/3.3 Profile/MIDP-2.0 '
            'Configuration/CLDC-1.1')
        assert handler.get_mobile_spec() == 'tier2'

        # iPhone, iPad, and Android
        _, _, handler = self.handler_for_useragent(
            'Mozilla/5.0 (iPhone; U; CPU iPhone OS 2_1 like Mac OS X; ja-jp) '
            'AppleWebKit/525.18.1 (KHTML, like Gecko) Version/3.1.1 '
            'Mobile/5F136 Safari/525.20')
        assert handler.get_mobile_spec() == ''
        _, _, handler = self.handler_for_useragent(
            'Mozilla/5.0 (iPad; U; CPU OS 3_2_2 like Mac OS X; en-us) '
            'AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 '
            'Mobile/7B500 Safari/531.21.10')
        assert handler.get_mobile_spec() == ''
        _, _, handler = self.handler_for_useragent(
            'Mozilla/5.0 (Linux; U; Android 2.2; en-us; Nexus One Build/FRF91) '
            'AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 '
            'Mobile Safari/533.1')
        assert handler.get_mobile_spec() == ''

        # Desktop browsers
        _, _, handler = self.handler_for_useragent(
            'Mozilla/4.0 (compatible; MSIE 4.01; Windows 98)')
        assert handler.get_mobile_spec() == ''
        _, _, handler = self.handler_for_useragent(
            'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-US) '
            'AppleWebKit/533.4 (KHTML, like Gecko) '
            'Chrome/5.0.375.55 Safari/533.4')
        assert handler.get_mobile_spec() == ''
        _, _, handler = self.handler_for_useragent(
            'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; ja-JP-mac; '
            'rv:1.9.0.6) Gecko/2009011912 Firefox/3.0.6 GTB5')
        assert handler.get_mobile_spec() == ''
        _, _, handler = self.handler_for_useragent(
            'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; ja-jp) '
            'AppleWebKit/533.16 (KHTML, like Gecko) Version/5.0 Safari/533.16')
        assert handler.get_mobile_spec() == ''

if __name__ == '__main__':
    unittest.main()
