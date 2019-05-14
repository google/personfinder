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
import unittest

from google.appengine.ext import db
from google.appengine.ext import testbed
from google.appengine.api import search
import sys
import logging
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
            'haiti/0522',
            given_name='Ami',
            family_name='Futami',
            full_name='Ami Futami',
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
            'haiti/1224',
            given_name=u'雪歩',
            family_name=u'萩原',
            entry_date=TEST_DATETIME)
        self.p13 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0523',
            given_name=u'Zhen Mei',
            family_name=u'Shuang Hai',
            entry_date=TEST_DATETIME)
        self.p14 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0829',
            given_name=u'真',
            family_name=u'菊地',
            entry_date=TEST_DATETIME)
        self.p15 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/1829',
            given_name=u'眞',
            family_name=u'菊地',
            entry_date=TEST_DATETIME)
        self.p16 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0909',
            full_name=u'音無小鳥',
            entry_date=TEST_DATETIME)
        self.p17 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0910',
            full_name=u'曾诚',
            family_name = u'曾',
            given_name = u'诚',
            entry_date=TEST_DATETIME)

        self.p18 = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0911',
            full_name=u'Shan Yu',
            family_name=u'Shan',
            given_name=u'Yu',
            entry_date=TEST_DATETIME)


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
        db.put(self.p13)
        db.put(self.p14)
        db.put(self.p15)
        db.put(self.p16)
        db.put(self.p17)
        db.put(self.p18)
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
        full_text_search.add_record_to_index(self.p13)
        full_text_search.add_record_to_index(self.p14)
        full_text_search.add_record_to_index(self.p15)
        full_text_search.add_record_to_index(self.p16)
        full_text_search.add_record_to_index(self.p17)
        full_text_search.add_record_to_index(self.p18)

        # Search by alternate name
        results = full_text_search.search('haiti', {'name': 'Iorin'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0505'])

        # Search by family name
        results = full_text_search.search('haiti', {'name': 'Minase'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0505'])

        # Search by given name
        results = full_text_search.search('haiti', {'name': 'Iori'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0505'])

        # Search by given name + family name
        results = full_text_search.search('haiti', {'name': 'Minase Iori'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0505'])

        # Search by full name
        resutls = full_text_search.search('haiti', {'name': 'Iori Minase'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0505'])

        # Search by a name contains location
        results = full_text_search.search('haiti', {'name': 'Chihaya Arao'}, 5)
        assert not results

        # Search by name & location
        results = full_text_search.search('haiti', {'name':'Chihaya',
                                                    'location': 'Arao'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0225'])

        # Search Cyrillic record by name & location
        results = full_text_search.search('haiti', {'name': 'Ritsuko',
                                                    'location': 'Tottori'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0623'])

        # Search by home_street only ( input inside the name box)
        results = full_text_search.search('haiti', {'name': 'Kunaideme72'}, 5)
        assert not results

        # Search by home_city only ( input inside the location box)
        results = full_text_search.search('haiti', {'location': 'Arao'}, 5)
        assert not results

        # Search by home_state only ( input inside the location box)
        results = full_text_search.search('haiti', {'location': 'Kumamoto'}, 5)
        assert not results

        # Search by home_postal_code only ( input inside the name box)
        results = full_text_search.search('haiti', {'name': '864-0003'}, 5)
        assert not results

        # Search by home_neighborhood only ( input inside the location box)
        results = full_text_search.search(
                                    'haiti', {'location': 'Araokeibajou'}, 5)
        assert not results

        # Search by home_country only ( input inside the name box)
        results = full_text_search.search('haiti', {'name': 'Japan'}, 5)
        assert not results

        # Search in a different repository
        results = full_text_search.search('japan', {'name': 'Iori'}, 5)
        assert not results

        # Check no results
        results = full_text_search.search('haiti', {'name': 'Producer san'}, 5)
        assert not results

        # Search with no query text
        results = full_text_search.search(
                                    'haiti', {'name': '', 'location': ''}, 5)
        assert not results

        # Search deleted record
        delete.delete_person(self, self.p5)
        results = full_text_search.search('haiti', {'name': 'Ami'}, 5)
        assert not results

        # Search with empty dict
        results = full_text_search.search('haiti', {}, 5)

        # Search by full name
        results = full_text_search.search('haiti', {'name': 'Rin Shibuya'}, 5)
        assert set([r.record_id for r in results]) == \
               set(['haiti:0810'])

        # Search romaji record by kanji name
        results = full_text_search.search('haiti', {'name': u'千早'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0225'])

        # Search romaji record by kanji name and location
        results = full_text_search.search('haiti', {'name': u'千早',
                                                    'location': u'荒尾'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0225'])

        # Check rank order
        # (same kanji higher than different kanji with the same reading)

        results = full_text_search.search('haiti', {'name': u'菊地 真'}, 5)
        assert [r.record_id for r in results] == \
            ['haiti/0829', 'haiti/1829']
        results = full_text_search.search('haiti', {'name': u'菊地 眞'}, 5)
        assert [r.record_id for r in results] == \
            ['haiti/1829', 'haiti/0829']

        # Search kanji record by multi reading
        results = full_text_search.search('haiti', {'name': u'hagiwara'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/1224'])
        results = full_text_search.search('haiti', {'name': 'ogiwara'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/1224'])

        # Search romaji record by hiragana name and location
        results = full_text_search.search('haiti', {'name': u'ちはや',
                                                    'location': u'あらお'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0225'])

        # Search by full name without space
        results = full_text_search.search('haiti', {'name': 'HibikiGanaha'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/1010'])

        # Search kanji record by full name without space
        results = full_text_search.search('haiti', {'name': u'AzusaMiura'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0719'])

        # Search Cyrillic record by full name without space
        results = full_text_search.search('haiti', {'name': u'RitsukoAkiduki'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0623'])

        # Search full name without space record by given name and family name
        results = full_text_search.search('haiti', {'name': u'Kotori Otonashi'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0909'])

        # Search Cyrillic record by full name without space
        results = full_text_search.search('haiti', {'name': u'OtonashiKotori'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0909'])

        # Search Chinese record by kanji
        results = full_text_search.search('haiti', {'name': u'真美'}, 5)
        assert set([r.record_id for r in results]) == \
            set(['haiti/0523'])

        # Search Name with Location part contain a part of person's name
        results = full_text_search.search('haiti',
                                          {'name': 'Rin Shibuya',
                                           'location': 'Shinjuku Rin'}, 5)
        assert not results

        # Input the name and location in the wrong box
        results = full_text_search.search('haiti',
                                          {'name': 'Shinjuku',
                                           'location': 'Rin Shibuya'}, 5)
        assert not results

        # Search by Special Chinese Family Name
        # while records are written in English
        results = full_text_search.search('haiti', {'name': u'单鱼'}, 5)
        assert set([r.record_id for r in results]) == \
               set(['haiti/0911'])

        # Search by Pinyin(Chinese Romaji)
        # while records are written in Chinese
        results = full_text_search.search('haiti', {'name': u'Zeng Cheng'}, 5)
        assert set([r.record_id for r in results]) == \
               set(['haiti/0910'])

        # Search by Chinese
        # while records are written in Chinese
        results = full_text_search.search('haiti', {'name': u'曾诚'}, 5)
        assert set([r.record_id for r in results]) == \
               set(['haiti/0910'])


    def test_delete_record_from_index(self):
        db.put(self.p4)
        full_text_search.add_record_to_index(self.p4)
        full_text_search.delete_record_from_index(self.p4)
        results = full_text_search.search('haiti',  {'name': 'Miki'}, 5)
        assert not results
