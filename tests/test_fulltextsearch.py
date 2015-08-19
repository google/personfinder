"""Tests for full_text_search.py"""

import unittest
import logging
import datetime

from google.appengine.ext import db
from google.appengine.ext import testbed
from google.appengine.api import search

import full_text_search
import model

TEST_DATETIME = datetime.datetime(2010, 1, 1, 0, 0, 0)

def create_index(person):
    full_text_search.create_index(
        record_id=person.record_id,
        repo=person.repo,
        given_name=person.given_name,
        family_name=person.family_name,
        full_name=person.full_name,
        alternate_names=person.alternate_names
    )

class FullTextSearchTests(unittest.TestCase):
    def setUp(self):
        self.tb = testbed.Testbed()
        self.tb.activate()
        self.tb.init_search_stub()
        self.p1 = model.Person(
            key_name='%s:%s' % ('haiti', 'haiti/0505'),
            repo='haiti',
            given_name='Iori',
            family_name='Minase',
            full_name='Iori Minase',
            alternate_names='Iorin',
            entry_date=TEST_DATETIME
        )
        self.p2 = model.Person(
            key_name='%s:%s' % ('haiti', 'haiti/0325'),
            repo='haiti',
            given_name='Yayoi',
            family_name='Takatsuki',
            full_name='Yayoi Takatsuki',
            alternate_names='Yayotan',
            entry_date=TEST_DATETIME
        )
        self.p3 = model.Person(
            key_name='%s:%s' % ('haiti', 'haiti/1202'),
            repo='haiti',
            given_name='Yayoi',
            full_name='Yayoi san',
            alternate_names='Nigochan',
            entry_date=TEST_DATETIME
        )
        self.p4 = model.Person(
            key_name='%s:%s' % ('haiti', 'haiti/1123'),
            repo='haiti',
            given_name='Miki',
            family_name='Hoshii',
            full_name='Miki Hoshii',
            entry_date=TEST_DATETIME
        )

    def tearDown(self):
        db.delete(self.p1)
        self.tb.deactivate()

    def test_create_index_name_only(self):
        db.put(self.p1)
        full_text_search.create_index(
            record_id='haiti/0505',
            repo='haiti',
            given_name='Iori',
            family_name='Minase',
            full_name='Iori Minase',
            alternate_names='Iorin'
        )
        results = full_text_search.search_with_index('haiti', 'Iorin', 100)
        assert results[0].record_id == 'haiti/0505'

    def test_search_index_name_only(self):
        db.put(self.p2)
        db.put(self.p3)
        db.put(self.p4)
        create_index(self.p2)
        create_index(self.p3)
        create_index(self.p4)
        results = full_text_search.search_with_index('haiti', 'Yayoi', 100)
        assert len(results) == 2
        record_ids = ['haiti/0325', 'haiti/1202']
        for result in results:
            assert result.record_id in record_ids

    def test_delete_index(self):
        db.put(self.p4)
        create_index(self.p4)
        full_text_search.delete_index(self.p4)
        results = full_text_search.search_with_index('haiti', 'Miki', 100)
        assert results == []
