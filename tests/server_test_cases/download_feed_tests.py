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


class DownloadFeedTests(ServerTestsBase):
    """Tests for the tools/download_feed.py script."""
    def setUp(self):
        ServerTestsBase.setUp(self)
        self.setup_person_and_note()
        fd, self.filename = tempfile.mkstemp()
        os.close(fd)

    def tearDown(self):
        os.remove(self.filename)
        ServerTestsBase.tearDown(self)

    def test_download_xml(self):
        url = 'http://%s/personfinder/haiti/feeds/person' % self.hostport
        download_feed.main('-q', '-o', self.filename, url)
        output = open(self.filename).read()
        assert '<pfif:pfif ' in output
        assert '<pfif:person>' in output
        assert '<pfif:given_name>_test_given_name</pfif:given_name>' in output

    def test_download_csv(self):
        url = 'http://%s/personfinder/haiti/feeds/person' % self.hostport
        download_feed.main('-q', '-o', self.filename, '-f', 'csv',
                           '-F', 'family_name,given_name,age', url)
        lines = open(self.filename).readlines()
        assert len(lines) == 2
        assert lines[0].strip() == 'family_name,given_name,age'
        assert lines[1].strip() == '_test_family_name,_test_given_name,52'

    def test_download_notes(self):
        url = 'http://%s/personfinder/haiti/feeds/note' % self.hostport
        download_feed.main('-q', '-o', self.filename, '-n', url)
        output = open(self.filename).read()
        assert '<pfif:pfif ' in output
        assert '<pfif:note>' in output
        assert '<pfif:text>Testing</pfif:text>' in output
