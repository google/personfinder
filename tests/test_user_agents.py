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

"""Tests for user_agents."""

import unittest

from google.appengine.ext import webapp

import user_agents


def make_request_with_user_agent(agent):
    url = '/main?subdomain=haiti'
    request = webapp.Request(webapp.Request.blank(url).environ)
    request.headers['user-agent'] = agent
    return request


class UserAgentsTests(unittest.TestCase):
    def test_is_jp_tier2_mobile_phone(self):
        # Japanese Tier-2 phones
        request = make_request_with_user_agent('DoCoMo/1.0/D502i/c10')
        assert user_agents.is_jp_tier2_mobile_phone(request)
        request = make_request_with_user_agent(
            'DoCoMo/2.0 P906i(c100;TB;W24H15)')
        assert user_agents.is_jp_tier2_mobile_phone(request)
        request = make_request_with_user_agent(
            'KDDI-HI31 UP.Browser/6.2.0.5 (GUI) MMP/2.0')
        assert user_agents.is_jp_tier2_mobile_phone(request)
        request = make_request_with_user_agent(
            'SoftBank/1.0/805SC/SCJ001 Browser/NetFront/3.3 Profile/MIDP-2.0 '
            'Configuration/CLDC-1.1')
        assert user_agents.is_jp_tier2_mobile_phone(request)

        # iPhone, iPad, and Android
        request = make_request_with_user_agent(
            'Mozilla/5.0 (iPhone; U; CPU iPhone OS 2_1 like Mac OS X; ja-jp) '
            'AppleWebKit/525.18.1 (KHTML, like Gecko) Version/3.1.1 '
            'Mobile/5F136 Safari/525.20')
        assert not user_agents.is_jp_tier2_mobile_phone(request)
        request = make_request_with_user_agent(
            'Mozilla/5.0 (iPad; U; CPU OS 3_2_2 like Mac OS X; en-us) '
            'AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 '
            'Mobile/7B500 Safari/531.21.10')
        assert not user_agents.is_jp_tier2_mobile_phone(request)
        request = make_request_with_user_agent(
            'Mozilla/5.0 (Linux; U; Android 2.2; en-us; Nexus One Build/FRF91) '
            'AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 '
            'Mobile Safari/533.1')
        assert not user_agents.is_jp_tier2_mobile_phone(request)

        # Desktop browsers
        request = make_request_with_user_agent(
            'Mozilla/4.0 (compatible; MSIE 4.01; Windows 98)')
        assert not user_agents.is_jp_tier2_mobile_phone(request)
        request = make_request_with_user_agent(
            'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-US) '
            'AppleWebKit/533.4 (KHTML, like Gecko) '
            'Chrome/5.0.375.55 Safari/533.4')
        assert not user_agents.is_jp_tier2_mobile_phone(request)
        request = make_request_with_user_agent(
            'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; ja-JP-mac; '
            'rv:1.9.0.6) Gecko/2009011912 Firefox/3.0.6 GTB5')
        assert not user_agents.is_jp_tier2_mobile_phone(request)
        request = make_request_with_user_agent(
            'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; ja-jp) '
            'AppleWebKit/533.16 (KHTML, like Gecko) Version/5.0 Safari/533.16')
        assert not user_agents.is_jp_tier2_mobile_phone(request)

