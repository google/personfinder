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

"""Tests for utils."""

import datetime
import os
import tempfile
import unittest

import django.utils.translation
from google.appengine.ext import db
from google.appengine.ext import webapp
from pytest import raises

import config
import pfif
import main
import model
import utils


class UtilsTests(unittest.TestCase):
    """Test the loose odds and ends."""

    def test_get_app_name(self):
        app_id = 'test'
        os.environ['APPLICATION_ID'] = app_id
        assert utils.get_app_name() == app_id
        os.environ['APPLICATION_ID'] = 's~' + app_id
        assert utils.get_app_name() == app_id

    def test_get_host(self):
        host = 'foo.appspot.com'
        os.environ['HTTP_HOST'] = host
        assert utils.get_host() == host
        os.environ['HTTP_HOST'] = 'foo.' + host
        assert utils.get_host() == host

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
        raises(Exception, utils.strip, None)

    def test_validate_yes(self):
        assert utils.validate_yes('yes') == 'yes'
        assert utils.validate_yes('YES') == 'yes'
        assert utils.validate_yes('no') == ''
        assert utils.validate_yes('y') == ''
        raises(Exception, utils.validate_yes, None)

    def test_validate_role(self):
        assert utils.validate_role('provide') == 'provide'
        assert utils.validate_role('PROVIDE') == 'provide'
        assert utils.validate_role('seek') == 'seek'
        assert utils.validate_role('pro') == 'seek'
        assert utils.validate_role('provider') == 'seek'
        raises(Exception, utils.validate_role, None)

    def test_validate_expiry(self):
        assert utils.validate_expiry(100) == 100
        assert utils.validate_expiry('abc') == None
        assert utils.validate_expiry(-100) == None

    def test_validate_version(self):
        for version in pfif.PFIF_VERSIONS:
            assert utils.validate_version(version) == pfif.PFIF_VERSIONS[
                version]
        assert utils.validate_version('') == pfif.PFIF_VERSIONS[
            pfif.PFIF_DEFAULT_VERSION]
        raises(Exception, utils.validate_version, '1.0')

    def test_validate_age(self):
        assert utils.validate_age('20') == '20'
        assert utils.validate_age(' 20 ') == '20'
        assert utils.validate_age(u'２０') == '20'
        assert utils.validate_age('20-30') == '20-30'
        assert utils.validate_age('20 - 30') == '20-30'
        assert utils.validate_age(u'２０〜３０') == '20-30'
        assert utils.validate_age(u'２０　ー　３０') == '20-30'
        assert utils.validate_age('20 !') == ''
        assert utils.validate_age('2 0') == ''

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
        model.Repo(key_name='haiti').put()
        config.set_for_repo(
            'haiti',
            repo_titles={'en': 'Haiti Earthquake'},
            language_menu_options=['en', 'ht', 'fr', 'es'])

    def tearDown(self):
        db.delete(config.ConfigEntry.all())

    def handler_for_url(self, url):
        request = webapp.Request(webapp.Request.blank(url).environ)
        response = webapp.Response()
        handler = utils.BaseHandler()
        handler.initialize(request, response, main.setup_env(request))
        return (request, response, handler)

    def test_parameter_validation(self):
        _, _, handler = self.handler_for_url(
            '/haiti/start?'
            'given_name=++John++&'
            'family_name=Doe&'
            'author_made_contact=YES&'
            'role=PROVIDE&')

        assert handler.params.given_name == 'John'
        assert handler.params.family_name == 'Doe'
        assert handler.params.author_made_contact == 'yes'
        assert handler.params.role == 'provide'

    def test_nonexistent_repo(self):
        request, response, handler = self.handler_for_url('/x/start')
        assert response.status == 404
        assert 'No such repository' in response.out.getvalue()
        assert 'class="error"' in response.out.getvalue()  # error template

    def test_set_allow_believed_dead_via_ui(self):
        """Verify the configuration of allow_believed_dead_via_ui."""
        # Set allow_believed_dead_via_ui to be True
        config.set_for_repo('haiti', allow_believed_dead_via_ui=True)
        _, response, handler = self.handler_for_url('/haiti/start')
        assert handler.config.allow_believed_dead_via_ui == True

        # Set allow_believed_dead_via_ui to be False
        config.set_for_repo('haiti', allow_believed_dead_via_ui=False)
        _, response, handler = self.handler_for_url('/haiti/start')
        assert handler.config.allow_believed_dead_via_ui == False


if __name__ == '__main__':
    unittest.main()
