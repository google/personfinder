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
WILLCOM_URL = ('http://dengon.willcom-inc.com/dengon/MessageListForward.do?' +
               'language=J&searchTelephoneNumber=%s')

NUMBER_SEPARATOR_RE = re.compile(
    ur'[\(\)\.\-\s\u2010-\u2015\u2212\u301c\u30fc\ufe58\ufe63\uff0d]')
PHONE_NUMBER_RE = re.compile(r'^\d{11}$')
INTERNATIONAL_PHONE_NUMBER_RE = re.compile(r'^\+?81(\d{10})')
AU_URL_RE = re.compile(
    r'\<a href\=\"(http:\/\/dengon\.ezweb\.ne\.jp\/[^\"]+)"\>')
DOCOMO_URL_RE = re.compile(
    r'\<a href\=\"(http:\/\/dengon\.docomo\.ne\.jp\/[^\"]+)"\>')
WILLCOM_URL_RE = re.compile(
    r'\<a href\=\"(http:\/\/dengon\.willcom\-inc\.com\/[^\"]+)"\>')
EMOBILE_URL_RE = re.compile(
    r'\<a href\=\"(http:\/\/dengon\.emnet\.ne\.jp\/[^\"]+)"\>')


def clean_phone_number(string):
    """Cleans up a given string which is possibly a phone number by
    getting rid of separator characters and converting unicode
    characters to ascii chars
    Args:
        string: unicode string to normalize.
    Returns:
        unicode string that is stripped of number separators and converted
        to ascii number characters if needed. It also removes international
        country code for Japan (81) and converts it into a domestic format.
    """
    cleaned_num = NUMBER_SEPARATOR_RE.sub(
        '', unicodedata.normalize('NFKC', string))
    international_num = INTERNATIONAL_PHONE_NUMBER_RE.findall(cleaned_num)
    if international_num:
        return '0' + international_num[0]
    else:
        return cleaned_num

def is_phone_number(string):
    """Tests the given string matches the pattern for the Japanese mobile phone
    number.
    Args:
        string: unicode string that is stripped of phone number separators such
        as '(', ')', and '-' and converted into ascii numeric characters.
    Returns:
        True if the string is a Jp mobile phone number, and False otherwise.
    """
    return PHONE_NUMBER_RE.match(string)

def scrape_redirect_url(url, scrape):
    """Tries to extract a further redirect URL for the correct mobile carrier
    page from the given scraped page, accessed at the given url. If finds a
    further redirect url to other carrier's page, returns that final
    destination url, otherwise returns the given original url.
    Args:
        url: the url of the scraped page.
        scrape: the scraped content from the url.
    Returns:
        url for further redirect to an appropriate mobile carrier's message
        board page if it's found, otherwise just returns the given url.
    """
    au_urls = AU_URL_RE.findall(scrape)
    if au_urls:
        return au_urls[0]
    docomo_urls = DOCOMO_URL_RE.findall(scrape)
    if docomo_urls:
        return docomo_urls[0]
    willcom_urls = WILLCOM_URL_RE.findall(scrape)
    if willcom_urls:
        return willcom_urls[0]
    emobile_urls = EMOBILE_URL_RE.findall(scrape)
    if emobile_urls:
        return emobile_urls[0]
    return url

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
        sbm_url = SOFT_BANK_MOBILE_URL % maybe_phone_number
        try:
            sbm_scrape = urllib2.urlopen(sbm_url).read()
        except:
            return None
        return scrape_redirect_url(sbm_url, sbm_scrape)


