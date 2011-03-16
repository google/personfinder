#!/usr/bin/python2.5
# Copyright 2011 Google Inc.
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

import re
import unicodedata
import urllib2

SOFT_BANK_MOBILE_URL = 'http://dengon.softbank.ne.jp/pc-2.jsp?m=%s'
AU_URL = 'http://dengon.ezweb.ne.jp/service.do?p1=dmb222&p2=%s'
WILLCOM_URL = ('http://dengon.willcom-inc.com/dengon/MessageList.do?' +
               'searchTelephoneNumber=%s')

NUMBER_SEPARATOR_RE = re.compile(r'[\(\)\.\-\s]')
PHONE_NUMBER_RE = re.compile(r'^\d{7,11}$')
AU_URL_RE = re.compile(r'dengon\.ezweb\.ne\.jp')
DOCOMO_URL_RE = re.compile(
    r'\<a href\=\"(http:\/\/dengon\.docomo\.ne\.jp\/[^\"]+)"\>')
WILLCOM_URL_RE = re.compile(r'dengon\.willcom\-inc\.com')


def clean_phone_number(string):
    """Cleans up a given string which is possibly a phone number by
    getting rid of separator characters and converting unicode
    characters to ascii chars
    Args:
        string: unicode string to normalize.
    Returns:
        unicode string that is stripped of number separators and converted
        to ascii number characters where needed.
    """
    cleaned_num = unicodedata.normalize('NFKC', string)
    return NUMBER_SEPARATOR_RE.sub('', cleaned_num)

def is_phone_number(string):
    """Tests the given string matches the pattern for the phone number.
    Args:
        string: unicode string that is stripped of phone number separators such
        as '(', ')', and '-' and converted into ascii numeric characters.
    Returns:
        True if the string is a phone number, and False otherwise.
    """
    return PHONE_NUMBER_RE.match(string)

def scrape_redirect_url(phone_number):
    """Tries to scrape a redirect URL for the mobile carrier page for the
    given phone number. First scrapes Soft Bank Mobile's page, and if
    finds a further redirect url to other carrier's page, returns that
    final destination url.
    Args:
        phone_number: a mobile phone number string.
    Returns:
        redirect url to an appropriate mobile carrier's message board page
        for the phone number if succeeds in scraping one, and None otherwise.
    """
    sbm_url = SOFT_BANK_MOBILE_URL % phone_number
    try:
        sbm_scrape = urllib2.urlopen(sbm_url).read()
    except:
        return None
    if AU_URL_RE.findall(sbm_scrape):
        return AU_URL % phone_number
    docomo_urls = DOCOMO_URL_RE.findall(sbm_scrape)
    if docomo_urls:
        return docomo_urls[0]
    return sbm_url

def get_mobile_carrier_redirect_url(query):
    """Checks if a given query is a phone number, and if so, returns
    a redirect url to an appropriate mobile carrier's page.
    Args:
        query: a query string to the Person Finder query page, possibly
        a mobile phone number.
    Returns:
        redirect url to an appropriate mobile carrier's message board page
        if the query is a mobile phone number and succeeds in scraping the
        url, and None otherwise.
    """
    maybe_phone_number = clean_phone_number(unicode(query))
    if is_phone_number(maybe_phone_number):
        return scrape_redirect_url(maybe_phone_number)

