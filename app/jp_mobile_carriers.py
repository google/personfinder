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
import urllib
import urllib2

SOFT_BANK_MOBILE_URL = 'http://dengon.softbank.ne.jp/pc-2.jsp?m=%s'
DOCOMO_URL = 'http://dengon.docomo.ne.jp/inoticelist.cgi'
DOCOMO_HIDDEN_RE = re.compile(
    r'\<INPUT TYPE\=\"HIDDEN\" NAME\=\"ep\" VALUE\=\"(\w+)\"\>')
DOCOMO_ENCODING = 'Shift_JIS'

NUMBER_SEPARATOR_RE = re.compile(
    ur'[\(\)\.\-\s\u2010-\u2015\u2212\u301c\u30fc\ufe58\ufe63\uff0d]')
PHONE_NUMBER_RE = re.compile(r'^\d{11}$')
INTERNATIONAL_PHONE_NUMBER_RE = re.compile(r'^\+?81(\d{10})')
AU_URL_RE = re.compile(
    r'\<a href\=\"(http:\/\/dengon\.ezweb\.ne\.jp\/[^\"]+)"\>', re.I)
DOCOMO_URL_RE = re.compile(
    r'\<a href\=\"(http:\/\/dengon\.docomo\.ne\.jp\/[^\"]+)"\>', re.I)
SOFT_BANK_URL_RE = re.compile(
    r'\<a href\=\"(http:\/\/dengon\.softbank\.ne\.jp\/[^\"]+)"\>', re.I)
WILLCOM_URL_RE = re.compile(
    r'\<a href\=\"(http:\/\/dengon\.willcom\-inc\.com\/[^\"]+)"\>', re.I)
EMOBILE_URL_RE = re.compile(
    r'\<a href\=\"(http:\/\/dengon\.emnet\.ne\.jp\/[^\"]+)"\>', re.I)


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

def scrape_redirect_url(scrape):
    """Tries to extract a further redirect URL for the correct mobile carrier
    page from the given page scraped from Docomo. If finds a further redirect
    url to other carrier's page, returns that final destination url, otherwise
    returns None.
    Args:
        scrape: the scraped content from the url.
    Returns:
        url for further redirect to an appropriate mobile carrier's message
        board page if it's found, otherwise None.
    """
    au_urls = AU_URL_RE.findall(scrape)
    if au_urls:
        return au_urls[0]
    soft_bank_urls = SOFT_BANK_URL_RE.findall(scrape)
    if soft_bank_urls:
        return soft_bank_urls[0]
    willcom_urls = WILLCOM_URL_RE.findall(scrape)
    if willcom_urls:
        return willcom_urls[0]
    emobile_urls = EMOBILE_URL_RE.findall(scrape)
    if emobile_urls:
        return emobile_urls[0]

def get_docomo_post_data(number, hidden_param):
    """Returns a mapping for POST data to the Docomo's url to inquire for
    the messages for the given number.
    Args:
        number: a normalized mobile number.
    Returns
        a mapping for the POST data.
    """
    return {'es': 0,
            'si': 1,
            'bi1': 1,
            'ep': hidden_param,
            'sm': number}

def scrape_docomo(number):
    """Scrape from the Docomo-provided message board system.
    Args:
        number: A mobile phone number.
    Returns:
        Scraped contents from Docomo's system.
    Throws:
        Exception when failed to scrape.
    """
    # Scrape Docomo's gateway page and get a hidden time stamp param.
    scrape = urllib2.urlopen(DOCOMO_URL).read()
    hidden_param = DOCOMO_HIDDEN_RE.findall(scrape)[0]

    # Encode the number and the above param as POST data
    data = get_docomo_post_data(number, hidden_param)
    encoded_data = urllib.urlencode(data)
    return unicode(urllib2.urlopen(DOCOMO_URL, encoded_data).read(),
                   DOCOMO_ENCODING)

def access_mobile_carrier(query):
    """Checks if a given query is a phone number, and if so, returns
    a scraped content of the mobile carrier provided message board service
    or a redirect url to an appropriate mobile carrier's page.
    Args:
        query: a query string to the Person Finder query page, possibly
        a mobile phone number.
    Returns:
        A pair of the scaped content of the carrier's service, and a
        redirect url found in it (if any).
    """
    maybe_phone_number = clean_phone_number(unicode(query))
    if is_phone_number(maybe_phone_number):
        scrape = scrape_docomo(maybe_phone_number)
        url = scrape_redirect_url(scrape)
        return (scrape, url)

def has_redirect_url(carrier_response):
    """Checks if the carrier response includes a redirect url.
    Args:
        carrier_response: carrier response returned by access_mobile_carrier.
    Returns:
        True if the response has a redirect url, and False otherwise.
    """
    return carrier_response != None and carrier_response[1] != None 

def get_redirect_url(carrier_response):
    """Returns a redirect url found in the carrier response.
    Args:
        carrier_response: carrier response returned by access_mobile_carrier.
    Returns:
        The redirect url.
    """
    return carrier_response[1]

def has_content(carrier_response):
    """Checks if the carrier response has a content.
    Args:
        carrier_response: carrier response returned by access_mobile_carrier.
    Returns:
        True if the response has a content, and False otherwise.
    """
    return carrier_response != None and carrier_response[0] != None 

def get_content(carrier_response):
    """Returns a content given in the carrier response.
    Args:
        carrier_response: carrier response returned by access_mobile_carrier.
    Returns:
        The response HTML content.
    """
    return carrier_response[0] 

