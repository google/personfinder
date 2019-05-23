# coding=utf-8
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
    def test_get_phone_number(self):
        assert (jp_mobile_carriers.get_phone_number(
            u'(03)1234-5678') == u'0312345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'(\uff10\uff13)\uff11\uff12\uff13\uff14-\uff15\uff16\uff17\uff18')
            == u'0312345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'  (080)1234-5678  ') == u'08012345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'080 1234 5678') == u'08012345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'\uff08\uff10\uff18\uff10\uff09\uff11\uff12\uff13\uff14\u30fc' +
            u'\uff15\uff16\uff17\uff18') == u'08012345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'\uff08\uff10\uff18\uff10\uff09\uff11\uff12\uff13\uff14\u2015' +
            u'\uff15\uff16\uff17\uff18') == u'08012345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'080.1234.5678') == u'08012345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'818012345678') == u'08012345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'+81.80.1234.5678') == u'08012345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'+81.3.1234.5678') == u'0312345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'+81.44.1234.5678') == u'04412345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'011818012345678') == u'08012345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'+011.81.80.1234.5678') == u'08012345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'011.81.3.1234.5678') == u'0312345678')
        assert (jp_mobile_carriers.get_phone_number(
            u'+011.81.44.1234.5678') == u'04412345678')
        assert (jp_mobile_carriers.get_phone_number(u'+81.5555.1234.5678')
            is None)
        assert jp_mobile_carriers.get_phone_number(u'John Doe') is None

    def test_is_mobile_number(self):
        assert not jp_mobile_carriers.is_mobile_number('0312345678')
        assert jp_mobile_carriers.is_mobile_number('09044445555')
        assert jp_mobile_carriers.is_mobile_number('08011112222')
        assert jp_mobile_carriers.is_mobile_number('07001010101')
        # 060 numbers are not targetted.
        assert not jp_mobile_carriers.is_mobile_number('06001010101')
        assert not jp_mobile_carriers.is_mobile_number('09188558585')
        assert not jp_mobile_carriers.is_mobile_number('(03)1234-5678')
        assert not jp_mobile_carriers.is_mobile_number('031234')
        assert not jp_mobile_carriers.is_mobile_number('031234567890')
        assert not jp_mobile_carriers.is_mobile_number('John Doe')

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
        soft_bank_links = jp_mobile_carriers.SOFT_BANK_URL_RE.findall(
            '<A HREF="http://dengon.softbank.ne.jp/J?n=HaCr05">')
        assert (soft_bank_links[0] ==
            'http://dengon.softbank.ne.jp/J?n=HaCr05')
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
        docomo_messages = jp_mobile_carriers.DOCOMO_MESSAGE_RE.findall(
            '<DIV ALIGN="LEFT">' +
            '09051246550<BR>' +
            '<A HREF="http://dengon.docomo.ne.jp/inoticelist.cgi?' +
            'mi=111PybHG001&ix=1&si=2&sm=0SXPP6CbnSukofp&es=0" ACCESSKEY="1">' +
            '[1]2011/03/13<BR>' +
            '&nbsp;11:43</A><BR></DIV>')
        assert (docomo_messages[0] == 'http://dengon.docomo.ne.jp/' +
            'inoticelist.cgi?mi=111PybHG001&ix=1&si=2&sm=0SXPP6CbnSukofp&es=0')
        web171_links = jp_mobile_carriers.WEB171_URL_RE.findall(
            '<A HREF="https://www.web171.jp/web171app/messageBoardList.do?' +
            'lang=jp&msn=08070036335">NTT東西伝言板(web171)へ</A><BR>')
        assert (web171_links[0] == 'https://www.web171.jp/web171app/' +
            'messageBoardList.do?lang=jp&msn=08070036335')

    def test_extract_redirect_url(self):
        scrape = ('<html><head></head><body><br>' +
                  '<A HREF="http://dengon.softbank.ne.jp/J?n=HaCr05">' +
                  'To Soft Bank BBS</A><BR>' +
                  '</body></html>')
        scraped_url = jp_mobile_carriers.extract_redirect_url(scrape)
        assert (scraped_url == 'http://dengon.softbank.ne.jp/J?n=HaCr05')
        scrape2 = ('<html><head></head><body>' +
                   '08011112222<br>No messages for this number.' +
                   '</body></html>')
        scraped_url2 = jp_mobile_carriers.extract_redirect_url(scrape2)
        assert scraped_url2 == None

    def test_docomo_has_messages(self):
        scrape_no_messages = (
            '<html><head>Error</head><body><br>' +
            'No messages are registerd for the number.<br>' +
            '<A HREF="http://dengon.docomo.ne.jp/top.cgi?es=0">To the Top' +
            '</A><BR></body></html>')
        scrape_with_messages = (
            '<html><head>Message Board System</head><body><br>' +
            'Found messages:<br>' +
            '<DIV ALIGN="LEFT">09051246550<BR>' +
            '<A HREF="http://dengon.docomo.ne.jp/inoticelist.cgi?' +
            'mi=111PybHG001&ix=1&si=2&sm=0SXPP6CbnSukofp&es=0" ACCESSKEY="1">' +
            '[1]2011/03/13<BR>' +
            '&nbsp;11:43</A><BR></DIV></body></html>')
        assert not jp_mobile_carriers.docomo_has_messages(scrape_no_messages)
        assert jp_mobile_carriers.docomo_has_messages(scrape_with_messages)

    def test_get_docomo_post_data(self):
        number = '08065422684'
        hidden = 'xyz'
        data = jp_mobile_carriers.get_docomo_post_data(number, hidden)
        assert data['es'] == 1
        assert data['si'] == 1
        assert data['bi1'] == 1
        assert data['ep'] == hidden
        assert data['sm'] == number

if __name__ == '__main__':
    unittest.main()
