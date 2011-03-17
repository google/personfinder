#!/usr/bin/python2.5
#
# Copyright 2011 Google Inc. All Rights Reserved.
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

"""Unittest for jp_mobile_carriers.py module."""

__author__ = 'tomohiko@google.com (Tomohiko Kimura)'

import jp_mobile_carriers
import unittest


class JpMobileCarriersTests(unittest.TestCase):
    def test_clean_phone_number(self):
        assert (jp_mobile_carriers.clean_phone_number(
            u'(03)1234-5678') == u'0312345678')
        assert (jp_mobile_carriers.clean_phone_number(
            u'(\uff10\uff13)\uff11\uff12\uff13\uff14-\uff15\uff16\uff17\uff18')
            == u'0312345678')
        assert (jp_mobile_carriers.clean_phone_number(
            u'  (080)1234-5678  ') == u'08012345678')
        assert (jp_mobile_carriers.clean_phone_number(
            u'080 1234 5678') == u'08012345678')
        assert (jp_mobile_carriers.clean_phone_number(
            u'\uff08\uff10\uff18\uff10\uff09\uff11\uff12\uff13\uff14\u30fc' +
            u'\uff15\uff16\uff17\uff18') == u'08012345678')
        assert (jp_mobile_carriers.clean_phone_number(
            u'\uff08\uff10\uff18\uff10\uff09\uff11\uff12\uff13\uff14\u2015' +
            u'\uff15\uff16\uff17\uff18') == u'08012345678')
        assert (jp_mobile_carriers.clean_phone_number(
            u'080.1234.5678') == u'08012345678')

    def test_is_phone_number(self):
        assert jp_mobile_carriers.is_phone_number('0312345678')
        assert jp_mobile_carriers.is_phone_number('08011112222')
        assert not jp_mobile_carriers.is_phone_number('(03)1234-5678')
        assert not jp_mobile_carriers.is_phone_number('031234')
        assert not jp_mobile_carriers.is_phone_number('031234567890')
        assert not jp_mobile_carriers.is_phone_number('John Doe')

    def test_carrier_url_res(self):
        au_links = jp_mobile_carriers.AU_URL_RE.findall(
            '<a href="http://dengon.ezweb.ne.jp/service.do?' +
            'p1=dmb222&t1=1&p2=08065422684&' +
            'rt=d559531edacd9240e437211465300941">')
        assert (au_links[0] == 'http://dengon.ezweb.ne.jp/service.do?' +
            'p1=dmb222&t1=1&p2=08065422684&' +
            'rt=d559531edacd9240e437211465300941')
        docomo_links = jp_mobile_carriers.DOCOMO_URL_RE.findall(
            '<a href="http://dengon.docomo.ne.jp/inoticelist.cgi?' +
            'bi1=1&si=1&ep=0URiwwQpJTpIoYv&sm=09051246550&es=0">')
        assert (docomo_links[0] == 'http://dengon.docomo.ne.jp/inoticelist.cgi?'
            + 'bi1=1&si=1&ep=0URiwwQpJTpIoYv&sm=09051246550&es=0')
        assert jp_mobile_carriers.WILLCOM_URL_RE.findall(
            '<a href="http://dengon.willcom-inc.com/service.do?' +
            'p1=dmb222&t1=1&p2=08065422684&rt=916c35cbcca01d8a9d">')
        emobile_links = jp_mobile_carriers.EMOBILE_URL_RE.findall(
            '<a href="http://dengon.emnet.ne.jp/action/safety/list.do?' +
            'arg1=S17E&cs=true&arg2=08070036335&' +
            'tlimit=292f7ec9aa7cfb03f0edaf3120454892">')
        assert (emobile_links[0] == 'http://dengon.emnet.ne.jp/action/' +
            'safety/list.do?arg1=S17E&cs=true&arg2=08070036335&' +
            'tlimit=292f7ec9aa7cfb03f0edaf3120454892')

if __name__ == '__main__':
    unittest.main()
