#!/usr/bin/python2.7
# coding:utf-8
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

import delete
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
        self.p5 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0829',
            given_name='Makoto',
            family_name='Kikuchi',
            full_name='Makoto Kikuchi',
            entry_date=TEST_DATETIME
        )
        self.p6 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0225',
            given_name='Chihaya',
            family_name='Kisaragi',
            full_name='Chihaya Kisaragi',
            home_street='Kunaideme72',
            home_city='Arao',
            home_state='Kumamoto',
            home_postal_code='864-0003',
            home_neighborhood='Araokeibajou',
            home_country='Japan',
            entry_date=TEST_DATETIME
        )
        self.p7 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/1010',
            given_name='Hibiki',
            family_name='Ganaha',
            full_name='Hibiki Ganaha',
            entry_date=TEST_DATETIME
        )
        self.p8 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0719',
            given_name=u'あずさ',
            family_name=u'三浦',
            home_city=u'横浜',
            entry_date=TEST_DATETIME
        )
        self.p9 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0623',
            given_name=u'рицуко',
            family_name=u'акидуки',
            home_city=u'тоттори',
            entry_date=TEST_DATETIME
        )
        self.p10 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti:0810',
            given_name='Rin',
            family_name='Shibuya',
            full_name='Rin Shibuya',
            home_city='shinjuku',
            entry_date=TEST_DATETIME
        )
        self.p11 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti:0203',
            given_name='Rin',
            family_name='Tosaka',
            full_name='Rin Tosaka',
            home_city='Shibuya',
            entry_date=TEST_DATETIME
        )
        self.p12 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0523',
            given_name=u'Zhen Mei',
            family_name=u'Shuang Hai',
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
        db.put(self.p5)
        db.put(self.p6)
        db.put(self.p7)
        db.put(self.p8)
        db.put(self.p9)
        db.put(self.p10)
        db.put(self.p11)
        db.put(self.p12)
        full_text_search.add_record_to_index(self.p1)
        full_text_search.add_record_to_index(self.p2)
        full_text_search.add_record_to_index(self.p3)
        full_text_search.add_record_to_index(self.p4)
        full_text_search.add_record_to_index(self.p5)
        full_text_search.add_record_to_index(self.p6)
        full_text_search.add_record_to_index(self.p7)
        full_text_search.add_record_to_index(self.p8)
        full_text_search.add_record_to_index(self.p9)
        full_text_search.add_record_to_index(self.p10)
        full_text_search.add_record_to_index(self.p11)
        full_text_search.add_record_to_index(self.p12)

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

        # Search by name & location
        results = full_text_search.search('haiti', 'Chihaya Arao', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0225'])

        # Search Cyrillic record by name & location
        results = full_text_search.search('haiti', 'Ritsuko Tottori', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0623'])

        # Search by home_street only
        results = full_text_search.search('haiti', 'Kunaideme72', 5)
        assert not results

        # Search by home_city only
        results = full_text_search.search('haiti', 'Arao', 5)
        assert not results

        # Search by home_state only
        results = full_text_search.search('haiti', 'Kumamoto', 5)
        assert not results

        # Search by home_postal_code only
        results = full_text_search.search('haiti', '864-0003', 5)
        assert not results

        # Search by home_neighborhood only
        results = full_text_search.search('haiti', 'Araokeibajou', 5)
        assert not results

        # Search by home_country only
        results = full_text_search.search('haiti', 'Japan', 5)
        assert not results

        # Search in a different repository
        results = full_text_search.search('japan', 'Iori', 5)
        assert not results

        # Check no results
        results = full_text_search.search('haiti', 'Producer san', 5)
        assert not results

        # Search with no query text
        results = full_text_search.search('haiti', '', 5)
        assert not results

        # Search deleted record
        delete.delete_person(self, self.p5)
        results = full_text_search.search('haiti', 'Makoto', 5)
        assert not results

        # Check rank order (name match heigher than location match)
        results = full_text_search.search('haiti', 'Rin Shibuya', 5)
        assert [r.record_id for r in results] == \
               ['haiti:0810', 'haiti:0203']

        # Search romaji record by kanji name
        results = full_text_search.search('haiti', u'千早', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0225'])

        # Search romaji record by kanji name and location
        results = full_text_search.search('haiti', u'千早 荒尾', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0225'])

        # Search romaji record by hiragana name and location
        results = full_text_search.search('haiti', u'ちはや あらお', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0225'])

        # Search by full name without space
        results = full_text_search.search('haiti', 'HibikiGanaha', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/1010'])

        # Search kanji record by full name without space
        results = full_text_search.search('haiti', u'AzusaMiura', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0719'])

        # Search Cyrillic record by full name without space
        results = full_text_search.search('haiti', u'RitsukoAkiduki', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0623'])

        # Search Chinese record by kanji
        results = full_text_search.search('haiti', u'真美', 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0523'])


    def test_delete_record_from_index(self):
        db.put(self.p4)
        full_text_search.add_record_to_index(self.p4)
        full_text_search.delete_record_from_index(self.p4)
        results = full_text_search.search('haiti', 'Miki', 5)
        assert not results
