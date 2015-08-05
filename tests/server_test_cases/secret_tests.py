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


class SecretTests(ServerTestsBase):
    """Tests that manipulate Secret entities."""

    def test_analytics_id(self):
        """Checks that the analytics_id Secret is used for analytics."""
        doc = self.go('/haiti/create')
        assert 'getTracker(' not in doc.content

        db.put(Secret(key_name='analytics_id', secret='analytics_id_xyz'))

        doc = self.go('/haiti/create')
        assert "getTracker('analytics_id_xyz')" in doc.content

    def test_maps_api_key(self):
        """Checks that maps don't appear when there is no maps_api_key."""
        db.put(Person(
            key_name='haiti:test.google.com/person.1001',
            repo='haiti',
            entry_date=ServerTestsBase.TEST_DATETIME,
            full_name='_status_full_name',
            author_name='_status_author_name'
        ))
        doc = self.go('/haiti/create?role=provide')
        assert 'id="clickable_map"' not in doc.content
        doc = self.go('/haiti/view?id=test.google.com/person.1001')
        assert 'id="clickable_map"' not in doc.content

        db.put(Secret(key_name='maps_api_key', secret='maps_api_key_xyz'))

        doc = self.go('/haiti/create?role=provide')
        assert 'maps_api_key_xyz' in doc.content
        assert 'id="clickable_map"' in doc.content
        doc = self.go('/haiti/view?id=test.google.com/person.1001')
        assert 'maps_api_key_xyz' in doc.content
        assert 'id="clickable_map"' in doc.content
