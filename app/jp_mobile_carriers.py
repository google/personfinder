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

DOCOMO_URL = 'http://dengon.docomo.ne.jp/inoticelist.cgi'
DOCOMO_HIDDEN_RE = re.compile(
    r'\<INPUT TYPE\=\"HIDDEN\" NAME\=\"ep\" VALUE\=\"(\w+)\"\>', re.I)

NUMBER_SEPARATOR_RE = re.compile(
    ur'[\(\)\.\-\s\u2010-\u2015\u2212\u301c\u30fc\ufe58\ufe63\uff0d]')
#PHONE_NUMBER_RE = re.compile(r'^\d{11}$')
#INTERNATIONAL_PHONE_NUMBER_RE = re.compile(r'^\+?81(\d{10})')
PHONE_NUMBER_RE = re.compile(r'^\+?(01181|81)?(\d{9,11})$')
MOBILE_NUMBER_RE = re.compile(r'^0(7|8|9)0\d{8}$')
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


def get_phone_number(string):
    """Normalize the given string, which may be a phone number, and returns
    a normalized phone number if the string is a phone number, or None
    otherwise. Gets rid of separator characters, converts unicode characters to
    ascii chars, and if the phone number contains the country code for Japan
    (81), strips of the code and prepend '0'.
    Args:
        string: unicode string to normalize.
    Returns:
        A normalized phone number if the input string is phone number, or
        None otherwise.
    """
    normalized = NUMBER_SEPARATOR_RE.sub(
        '', unicodedata.normalize('NFKC', string))
    number_match = PHONE_NUMBER_RE.match(normalized)
    if number_match:
        if number_match.groups()[0]:
            return '0' + number_match.groups()[1]
        else:
            return number_match.groups()[1]

def is_mobile_number(string):
    """Tests the given string matches the pattern for the Japanese mobile phone
    number.
    Args:
        string: unicode string that is stripped of phone number separators such
        as '(', ')', and '-' and converted into ascii numeric characters.
    Returns:
        True if the string is a Jp mobile phone number, and False otherwise.
    """
    return bool(MOBILE_NUMBER_RE.match(string))

def extract_redirect_url(scrape):
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
    """Returns a mapping for POST data to Docomo's url to inquire for messages
    for the given number.
    Args:
        number: a normalized mobile number.
    Returns:
        a mapping for the POST data.
    """
    return {'es': 0,
            'si': 1,
            'bi1': 1,
            'ep': hidden_param,
            'sm': number}

def look_up_number(number):
    """Look up messages for the number, registered in the Japanese mobile
    carriers-provided emergency message board services. The five Japanese mobile
    carriers maintain separate message indices, but their systems can talk to
    one another when they don't find messages for the given number in their own
    indices. This function first talks to Docomo's system as a main entry point.
    Docomo returns urls of registered messages if it finds ones in its system.
    If it doesn't, Docomo's system talks to the other 4 carriers' and returns an
    url for an appropriate carrier if messages are found. If no messages are
    found registered for the number, Docomo's system simply indicates so.
    Args:
        number: A mobile phone number.
    Returns:
        A url for messages found registered to some carrier (including Docomo)
        or otherwise an url for Docomo's response telling no results found.
    Throws:
        Exception when failed to scrape.
    """
    # Scrape Docomo's gateway page and get a hidden time stamp param.
    scrape = urllib2.urlopen(DOCOMO_URL).read()
    hidden_param = DOCOMO_HIDDEN_RE.findall(scrape)[0]

    # Encode the number and the above param as POST data
    data = get_docomo_post_data(number, hidden_param)
    encoded_data = urllib.urlencode(data)
    # Scrape Docomo's answer on the number
    scrape = urllib2.urlopen(DOCOMO_URL, encoded_data).read()

    # Extract a further redirect url, if any.
    url = extract_redirect_url(scrape)
    if url:
        return url
    # If no further redirect is extracted, that is, messages are found in
    # Docomo's system or no messages are found, return an url for a GET request
    # to the scraped Docomo page 
    return DOCOMO_URL + '?' + encoded_data

def handle_phone_number(handler, query):
    """Handles a phone number query. If the query is a mobile phone number,
    looks up the number for registered messages in the mobile carriers-provided
    message board services and redirects to the results page. If the query is a
    non-mobile phone number, shows a 171 suggestion.
    Args:
        handler: a request handler for this request.
        query: a query string to the Person Finder query page.
    Returns:
        True if the query string is a phone number and has been properly
        handled, and False otherwise.
    """
    phone_number = get_phone_number(unicode(query))
    if phone_number:
        if is_mobile_number(phone_number):
            handler.redirect(look_up_number(phone_number))
        else:
            handler.render('templates/query.html',
                           role=handler.params.role,
                           query=handler.params.query,
                           show_jp_171_suggestion=True)
        return True
    else:
        return False

