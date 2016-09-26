#!/usr/bin/python2.7
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

"""Test cases for end-to-end testing.  Run with the server_tests script."""

import calendar
import datetime
import email
import email.header
import optparse
import os
import pytest
import re
import simplejson
import sys
import tempfile
import time
import unittest
import urlparse

from google.appengine.api import images

import config
from const import ROOT_URL, PERSON_STATUS_TEXT, NOTE_STATUS_TEXT
import download_feed
from model import *
from photo import MAX_IMAGE_DIMENSION
import remote_api
from resources import Resource, ResourceBundle
import reveal
import scrape
import setup_pf as setup
from test_pfif import text_diff
from text_query import TextQuery
import utils
from server_tests_base import ServerTestsBase


class ReadOnlyTests(ServerTestsBase):
    """Tests that don't modify data go here."""

    def setUp(self):
        """Sets up a scrape Session for each test."""
        self.s = scrape.Session(verbose=1)
        # These tests don't rely on utcnow, so don't bother to set it.

    def tearDown(self):
        # These tests don't write anything, so no need to reset the datastore.
        pass

    def test_noconfig(self):
        """Check the home page with no config (generic welcome page)."""
        doc = self.go('/')
        assert 'You are now running Person Finder.' in doc.text

    def test_home(self):
        """Check the generic home page."""
        doc = self.go('/global/home.html')
        assert 'You are now running Person Finder.' in doc.text

    def test_tos(self):
        """Check the generic TOS page."""
        doc = self.go('/global/tos.html')
        assert 'Terms of Service' in doc.text

    def test_start(self):
        """Check the start page with no language specified."""
        doc = self.go('/haiti')
        assert 'I\'m looking for someone' in doc.text

    def test_start_english(self):
        """Check the start page with English language specified."""
        doc = self.go('/haiti?lang=en')
        assert 'I\'m looking for someone' in doc.text

    def test_start_french(self):
        """Check the French start page."""
        doc = self.go('/haiti?lang=fr')
        assert 'Je recherche une personne' in doc.text

    def test_start_creole(self):
        """Check the Creole start page."""
        doc = self.go('/haiti?lang=ht')
        assert u'Mwen ap ch\u00e8che yon moun' in doc.text

    def test_language_xss(self):
        """Regression test for an XSS vulnerability in the 'lang' parameter."""
        doc = self.go('/haiti?lang="<script>alert(1)</script>')
        assert '<script>' not in doc.content

    def test_language_cookie_caching(self):
        """Regression test for caching the wrong language."""

        # Run a session where the default language is English
        en_session = self.s = scrape.Session(verbose=1)

        doc = self.go('/haiti?lang=en')  # sets cookie
        assert 'I\'m looking for someone' in doc.text

        doc = self.go('/haiti')
        assert 'I\'m looking for someone' in doc.text

        # Run a separate session where the default language is French
        fr_session = self.s = scrape.Session(verbose=1)

        doc = self.go('/haiti?lang=fr')  # sets cookie
        assert 'Je recherche une personne' in doc.text

        doc = self.go('/haiti')
        assert 'Je recherche une personne' in doc.text

        # Check that this didn't screw up the language for the other session
        self.s = en_session

        doc = self.go('/haiti')
        assert 'I\'m looking for someone' in doc.text

    def test_charsets(self):
        """Checks that pages are delivered in the requested charset."""

        # Try with no specified charset.
        doc = self.go('/haiti?lang=ja')
        assert self.s.headers['content-type'] == 'text/html; charset=utf-8'
        assert 'content="text/html; charset=utf-8"' in doc.content
        # UTF-8 encoding of text (U+5B89 U+5426 U+60C5 U+5831) in title
        assert ('\xe5\xae\x89\xe5\x90\xa6\xe6\x83\x85\xe5\xa0\xb1' in
                doc.content_bytes)

        # Try with a specific requested charset.
        doc = self.go('/haiti?lang=ja&charsets=shift_jis')
        assert self.s.headers['content-type'] == 'text/html; charset=shift_jis'
        assert 'content="text/html; charset=shift_jis"' in doc.content
        # Shift_JIS encoding of title text
        assert '\x88\xc0\x94\xdb\x8f\xee\x95\xf1' in doc.content_bytes

        # Confirm that spelling of charset is preserved.
        doc = self.go('/haiti?lang=ja&charsets=Shift-JIS')
        assert self.s.headers['content-type'] == 'text/html; charset=Shift-JIS'
        assert 'content="text/html; charset=Shift-JIS"' in doc.content
        # Shift_JIS encoding of title text
        assert '\x88\xc0\x94\xdb\x8f\xee\x95\xf1' in doc.content_bytes

        # Confirm that UTF-8 takes precedence.
        doc = self.go('/haiti?lang=ja&charsets=Shift-JIS,utf8')
        assert self.s.headers['content-type'] == 'text/html; charset=utf-8'
        assert 'content="text/html; charset=utf-8"' in doc.content
        # UTF-8 encoding of title text
        assert ('\xe5\xae\x89\xe5\x90\xa6\xe6\x83\x85\xe5\xa0\xb1' in
                doc.content_bytes)

    def test_kddi_charsets(self):
        """Checks that pages are delivered in Shift_JIS if the user agent is a
        feature phone by KDDI."""
        self.s.agent = 'KDDI-HI31 UP.Browser/6.2.0.5 (GUI) MMP/2.0'
        doc = self.go('/haiti?lang=ja')
        assert self.s.headers['content-type'] == 'text/html; charset=Shift_JIS'
        assert 'content="text/html; charset=Shift_JIS"' in doc.content
        # Shift_JIS encoding of title text
        assert '\x88\xc0\x94\xdb\x8f\xee\x95\xf1' in doc.content_bytes

    def test_query(self):
        """Check the query page."""
        doc = self.go('/haiti/query')
        button = doc.xpath_one('//input[@type="submit"]')
        assert button.get('value') == 'Search for this person'

        doc = self.go('/haiti/query?role=provide')
        button = doc.xpath_one('//input[@type="submit"]')
        assert button.get('value') == 'Provide information about this person'

    def test_results(self):
        """Check the results page."""
        doc = self.go('/haiti/results?query_name=xy')
        assert 'We have nothing' in doc.text

    def test_create(self):
        """Check the create page."""
        doc = self.go('/haiti/create')
        assert 'Who you are looking for' in doc.text

        doc = self.go('/haiti/create?role=provide')
        assert 'Who you have information about' in doc.text

        params = [
            'role=provide',
            'family_name=__FAMILY_NAME__',
            'given_name=__GIVEN_NAME__',
            'home_street=__HOME_STREET__',
            'home_neighborhood=__HOME_NEIGHBORHOOD__',
            'home_city=__HOME_CITY__',
            'home_state=__HOME_STATE__',
            'home_postal_code=__HOME_POSTAL_CODE__',
            'description=__DESCRIPTION__',
            'photo_url=__PHOTO_URL__',
            'clone=yes',
            'author_name=__AUTHOR_NAME__',
            'author_phone=__AUTHOR_PHONE__',
            'author_email=__AUTHOR_EMAIL__',
            'source_url=__SOURCE_URL__',
            'source_date=__SOURCE_DATE__',
            'source_name=__SOURCE_NAME__',
            'status=believed_alive',
            'text=__TEXT__',
            'last_known_location=__LAST_KNOWN_LOCATION__',
            'author_made_contact=yes',
            'phone_of_found_person=__PHONE_OF_FOUND_PERSON__',
            'email_of_found_person=__EMAIL_OF_FOUND_PERSON__'
        ]
        doc = self.go('/haiti/create?' + '&'.join(params))
        tag = doc.xpath_one('//input[@name="family_name"]')
        assert tag.get('value') == '__FAMILY_NAME__'

        tag = doc.xpath_one('//input[@name="given_name"]')
        assert tag.get('value') == '__GIVEN_NAME__'

        tag = doc.xpath_one('//input[@name="home_street"]')
        assert tag.get('value') == '__HOME_STREET__'

        tag = doc.xpath_one('//input[@name="home_neighborhood"]')
        assert tag.get('value') == '__HOME_NEIGHBORHOOD__'

        tag = doc.xpath_one('//input[@name="home_city"]')
        assert tag.get('value') == '__HOME_CITY__'

        tag = doc.xpath_one('//input[@name="home_state"]')
        assert tag.get('value') == '__HOME_STATE__'

        tag = doc.xpath_one('//input[@name="home_postal_code"]')
        assert tag.get('value') == '__HOME_POSTAL_CODE__'

        tag = doc.xpath_one('//textarea[@name="description"]')
        assert tag.text == '__DESCRIPTION__'

        tag = doc.xpath_one('//input[@name="photo_url"]')
        assert tag.get('value') == '__PHOTO_URL__'

        tag = doc.cssselect_one('input#clone_yes')
        assert tag.get('checked') == 'checked'

        tag = doc.xpath_one('//input[@name="author_name"]')
        assert tag.get('value') == '__AUTHOR_NAME__'

        tag = doc.xpath_one('//input[@name="author_phone"]')
        assert tag.get('value') == '__AUTHOR_PHONE__'

        tag = doc.xpath_one('//input[@name="author_email"]')
        assert tag.get('value') == '__AUTHOR_EMAIL__'

        tag = doc.xpath_one('//input[@name="source_url"]')
        assert tag.get('value') == '__SOURCE_URL__'

        tag = doc.xpath_one('//input[@name="source_date"]')
        assert tag.get('value') == '__SOURCE_DATE__'

        tag = doc.xpath_one('//input[@name="source_name"]')
        assert tag.get('value') == '__SOURCE_NAME__'

        tag = doc.xpath_one('//option[@value="believed_alive"]')
        assert tag.get('selected') == 'selected'

        tag = doc.xpath_one('//textarea[@name="text"]')
        assert tag.text == '__TEXT__'

        tag = doc.xpath_one('//textarea[@name="last_known_location"]')
        assert tag.text == '__LAST_KNOWN_LOCATION__'

        tag = doc.cssselect_one('input#author_made_contact_yes')
        assert tag.get('checked') == 'checked'

        tag = doc.xpath_one('//input[@name="phone_of_found_person"]')
        assert tag.get('value') == '__PHONE_OF_FOUND_PERSON__'

        tag = doc.xpath_one('//input[@name="email_of_found_person"]')
        assert tag.get('value') == '__EMAIL_OF_FOUND_PERSON__'

    def test_view(self):
        """Check the view page."""
        doc = self.go('/haiti/view')
        assert 'No person id was specified' in doc.text

    def test_multiview(self):
        """Check the multiview page."""
        doc = self.go('/haiti/multiview')
        assert 'Compare these records' in doc.text

    def test_photo(self):
        """Check the photo page."""
        doc = self.go('/haiti/photo')
        assert 'Photo id is unspecified or invalid' in doc.text

    def test_static(self):
        """Check that the static files are accessible."""
        doc = self.go('/static/no-photo.gif')
        self.assertEqual(self.s.status, 200)
        assert doc.content_bytes.startswith('GIF89a')

    def test_embed(self):
        """Check the embed page."""
        doc = self.go('/haiti/embed')
        assert 'Embedding' in doc.text

    def test_gadget(self):
        """Check the gadget page."""
        doc = self.go('/haiti/gadget')
        assert '<Module>' in doc.content
        assert 'application/xml' in self.s.headers['content-type']

    def test_sitemap(self):
        """Check the sitemap generator."""
        doc = self.go('/haiti/sitemap')
        assert '</sitemapindex>' in doc.content

        doc = self.go('/haiti/sitemap?shard_index=1')
        assert '</urlset>' in doc.content

    def test_config_repo_titles(self):
        doc = self.go('/haiti')
        assert 'Haiti Earthquake' in scrape.get_all_text(
            doc.cssselect_one('div.subtitle-bar'))

        doc = self.go('/pakistan')
        assert 'Pakistan Floods' in scrape.get_all_text(doc.cssselect_one('div.subtitle-bar'))

    def test_config_language_menu_options(self):
        doc = self.go('/haiti')
        select = doc.cssselect_one('select#language_picker')
        options = select.cssselect('option')

        # It first lists languages in the repository config.
        # These are set in setup_configs() in setup_pf.py.
        assert options[0].text.strip() == u'English'  # en
        assert options[1].text.strip() == u'Krey\xf2l'  # ht
        assert options[2].text.strip() == u'Fran\xe7ais'  # fr
        assert options[3].text.strip() == u'espa\u00F1ol'  # es

        # All other languages follow.
        assert select.xpath('//option[normalize-space(.)="%s"]' %
                            u'\u0627\u0631\u062F\u0648')  # ur

        doc = self.go('/pakistan')
        select = doc.cssselect_one('select#language_picker')
        options = select.cssselect('option')

        # It first lists languages in the repository config.
        # These are set in setup_configs() in setup_pf.py.
        assert options[0].text.strip() == u'English'  # en
        assert options[1].text.strip() == u'\u0627\u0631\u062F\u0648'  # ur

        # All other languages follow.
        assert select.xpath('//option[normalize-space(.)="%s"]' %
                            u'Fran\xe7ais')  # fr

    def test_config_keywords(self):
        doc = self.go('/haiti')
        meta = doc.xpath_one('//meta[@name="keywords"]')
        assert 'tremblement' in meta.get('content')

        doc = self.go('/pakistan')
        meta = doc.xpath_one('//meta[@name="keywords"]')
        assert 'pakistan flood' in meta.get('content')

    def test_css(self):
        """Check that the CSS files are accessible."""
        doc = self.go('/global/css?lang=en&ui=default')
        assert 'body {' in doc.content
        doc = self.go('/global/css?lang=en&ui=small')
        assert 'body {' in doc.content
        doc = self.go('/global/css?lang=en&ui=light')
        assert 'Apache License' in doc.content
        doc = self.go('/global/css?lang=ar&ui=default')
        assert 'body {' in doc.content
