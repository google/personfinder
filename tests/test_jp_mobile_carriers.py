#!/usr/bin/python2.5
#
# Copyright 2011 Google Inc. All Rights Reserved.

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

    def test_is_phone_number(self):
        assert jp_mobile_carriers.is_phone_number('0312345678')
        assert jp_mobile_carriers.is_phone_number('08011112222')
        assert not jp_mobile_carriers.is_phone_number('(03)1234-5678')
        assert not jp_mobile_carriers.is_phone_number('031234')
        assert not jp_mobile_carriers.is_phone_number('031234567890')
        assert not jp_mobile_carriers.is_phone_number('John Doe')

    def test_carrier_url_res(self):
        assert jp_mobile_carriers.AU_URL_RE.findall(
            '<a href="http://dengon.ezweb.ne.jp/service.do?' +
            'p1=dmb222&t1=1&p2=08065422684&rt=916c35cbcca01d8a9d">')
        anchors = jp_mobile_carriers.DOCOMO_URL_RE.findall(
            '<a href="http://dengon.docomo.ne.jp/inoticelist.cgi?' +
            'bi1=1&si=1&ep=0URiwwQpJTpIoYv&sm=09051246550&es=0">')
        assert (anchors[0] == 'http://dengon.docomo.ne.jp/inoticelist.cgi?' +
            'bi1=1&si=1&ep=0URiwwQpJTpIoYv&sm=09051246550&es=0')
        assert jp_mobile_carriers.WILLCOM_URL_RE.findall(
            '<a href="http://dengon.willcom-inc.com/service.do?' +
            'p1=dmb222&t1=1&p2=08065422684&rt=916c35cbcca01d8a9d">')

    def test_scrape_redirect_url(self):
        assert (jp_mobile_carriers.scrape_redirect_url('08065422684') ==
            'http://dengon.ezweb.ne.jp/service.do?p1=dmb222&p2=08065422684')

    def test_get_mobile_carrier_redirect_url(self):
        assert (jp_mobile_carriers.get_mobile_carrier_redirect_url(
            '(080)6542-2684') ==
            'http://dengon.ezweb.ne.jp/service.do?p1=dmb222&p2=08065422684')
        assert not jp_mobile_carriers.get_mobile_carrier_redirect_url(
            'John Doe')

if __name__ == '__main__':
    unittest.main()
