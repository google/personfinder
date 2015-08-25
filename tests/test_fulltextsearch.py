#!/usr/bin/python2.7
# Copyright 2015 Google Inc.
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

"""Tests for full_text_search.py"""

import datetime
import logging
import unittest

from google.appengine.ext import db
from google.appengine.ext import testbed
from google.appengine.api import search

import full_text_search
import model

TEST_DATETIME = datetime.datetime(2010, 1, 1, 0, 0, 0)

class FullTextSearchTests(unittest.TestCase):
    def setUp(self):
        self.tb = testbed.Testbed()
        self.tb.activate()
        self.tb.init_search_stub()
        self.p1 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0505',
            given_name='Iori',
            family_name='Minase',
            full_name='Iori Minase',
            alternate_names='Iorin',
            entry_date=TEST_DATETIME
        )
        self.p2 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0325',
            given_name='Yayoi',
            family_name='Takatsuki',
            full_name='Yayoi Takatsuki',
            alternate_names='Yayotan',
            entry_date=TEST_DATETIME
        )
        self.p3 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/1202',
            given_name='Yayoi',
            full_name='Yayoi san',
            alternate_names='Nigochan',
            entry_date=TEST_DATETIME
        )
        self.p4 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/1123',
            given_name='Miki',
            family_name='Hoshii',
            full_name='Miki Hoshii',
            entry_date=TEST_DATETIME
        )

    def tearDown(self):
        db.delete(model.Person.all())
        self.tb.deactivate()

    def test_search_by_name_only(self):
        db.put(self.p1)
        db.put(self.p2)
        db.put(self.p3)
        db.put(self.p4)
        full_text_search.add_record_to_index(self.p1)
        full_text_search.add_record_to_index(self.p2)
        full_text_search.add_record_to_index(self.p3)
        full_text_search.add_record_to_index(self.p4)

        # Search by alternate name
        results = full_text_search.search('haiti', 'Iorin', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0505'])

        # Search by family name
        results = full_text_search.search('haiti', 'Minase', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0505'])

        # Search by given name
        results = full_text_search.search('haiti', 'Iori', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0505'])

        # Search by given name + family name
        results = full_text_search.search('haiti', 'Minase Iori', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0505'])

        # Search by full name
        resutls = full_text_search.search('haiti', 'Iori Minase', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0505'])

        # Search in a different repository
        results = full_text_search.search('japan', 'Iori', 5)
        assert not results

        # Check no results
        results = full_text_search.search('haiti', 'Producer san', 5)
        assert not results

        # Search with no query text
        results = full_text_search.search('haiti', '', 5)
        assert not results

    def test_delete_index(self):
        db.put(self.p4)
        full_text_search.add_record_to_index(self.p4)
        full_text_search.delete_record_from_index(self.p4)
        results = full_text_search.search('haiti', 'Miki', 5)
        assert not results
