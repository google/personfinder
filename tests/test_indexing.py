#!/usr/bin/python2.5
#
# Copyright 2010 Google Inc. All Rights Reserved.

"""Unittest for indexing.py module."""

__author__ = 'eyalf@google.com (Eyal Fink)'

from google.appengine.ext import db
import datetime
import indexing
import logging
import model
import sys
import unittest

from text_query import TextQuery

def create_person(first_name, last_name):
    return model.Person.create_original(
        'test', first_name=first_name, last_name=last_name,
        entry_date=datetime.datetime.utcnow())


class IndexingTests(unittest.TestCase):
    def setUp(self):
        db.delete(model.Person.all())

    def add_persons(self, *persons):
        for p in persons:
            indexing.update_index_properties(p)
            db.put(p)

    def get_matches(self, query, limit=100):
        results = indexing.search('test', TextQuery(query), limit)
        return [(p.first_name, p.last_name) for p in results]

    def get_ranked(self, results, query, limit=100):
        ranked = indexing.rank_and_order(results, TextQuery(query), limit)
        return [(p.first_name, p.last_name) for p in results]

    def test_rank_and_order(self):
        res= [create_person(first_name='Bryan', last_name='abc', ),
              create_person(first_name='Bryan', last_name='abcef'),
              create_person(first_name='abc', last_name='Bryan'),
              create_person(first_name='Bryan abc', last_name='efg')]

        sorted = indexing.rank_and_order(res, TextQuery('Bryan abc'), 100)
        assert ['%s %s'%(p.first_name, p.last_name) for p in sorted] == \
            ['Bryan abc', 'abc Bryan', 'Bryan abc efg', 'Bryan abcef']

        sorted = indexing.rank_and_order(res, TextQuery('Bryan abc'), 2)
        assert ['%s %s'%(p.first_name, p.last_name) for p in sorted] == \
            ['Bryan abc', 'abc Bryan']

        sorted = indexing.rank_and_order(res, TextQuery('abc Bryan'), 100)
        assert ['%s %s'%(p.first_name, p.last_name) for p in sorted] == \
            ['abc Bryan', 'Bryan abc', 'Bryan abc efg', 'Bryan abcef']


        res= [create_person(first_name='abc', last_name='efg'),
              create_person(first_name='ABC', last_name='EFG'),
              create_person(first_name='ABC', last_name='efghij')]

        sorted = indexing.rank_and_order(res, TextQuery('abc'), 100)
        assert ['%s %s'%(p.first_name, p.last_name) for p in sorted] == \
            ['abc efg', 'ABC EFG', 'ABC efghij']

    def test_cjk_ranking_1(self):
        # This is Jackie Chan's Chinese name.  His family name is CHAN and given
        # name is KONG + SANG; the usual Chinese order is CHAN + KONG + SANG.
        CHAN, KONG, SANG = u'\u9673', u'\u6e2f', u'\u751f'

        # This is I. M. Pei's Chinese name.  His family name is BEI and his
        # given name is YU + MING; the usual Chinese order is BEI + YU + MING.
        BEI, YU, MING = u'\u8c9d', u'\u807f', u'\u9298'
        persons = [
            create_person(first_name=CHAN + KONG + SANG, last_name='foo'),
            create_person(first_name=SANG, last_name=CHAN + KONG),
            create_person(first_name=CHAN, last_name=KONG + SANG),
            create_person(first_name=KONG + SANG, last_name=CHAN),
            create_person(first_name=KONG + CHAN, last_name=SANG),
            create_person(first_name=KONG, last_name=SANG),
            create_person(first_name=YU + MING, last_name=BEI),
        ]

        assert self.get_ranked(persons, CHAN + KONG + SANG) == [
            (KONG + SANG, CHAN),  # surname + given name is best
            (SANG, CHAN + KONG),  # then multi-char surname + given name
            (CHAN, KONG + SANG),  # then surname/given switched
            (KONG + CHAN, SANG),  # then out-of-order match
            (CHAN + KONG + SANG, 'foo'),  # then exact given name match
            (KONG, SANG),  # then partial match
            (YU + MING, BEI),  # then nothing match
        ]

        assert self.get_ranked(persons, CHAN + ' ' + KONG + SANG) == [
            (KONG + SANG, CHAN),  # surname + given name is best
            (CHAN, KONG + SANG),  # then surname/given switched
            (KONG + CHAN, SANG),  # then multi-char surname / given switched
            (SANG, CHAN + KONG),  # then out-of-order match
            (CHAN + KONG + SANG, 'foo'),  # then exact given name match
            (KONG, SANG),  # then partial match
            (YU + MING, BEI),  # then nothing match
        ]

    def test_cjk_ranking_2(self):
        # This is Steven Chu's Chinese name.  His family name is ZHU and his
        # given name is DI + WEN; the usual Chinese order is ZHU + DI + WEN.
        ZHU, DI, WEN = u'\u6731', u'\u68e3', u'\u6587'

        # A test database of 3 records with various permutations of the name.
        persons = [
            create_person(first_name=WEN, last_name=ZHU + DI),
            create_person(first_name=DI + WEN, last_name=ZHU),
            create_person(first_name=ZHU, last_name=DI + WEN),
        ]

        # When the search query is ZHU + DI + WEN:
        assert self.get_ranked(persons, ZHU + DI + WEN) == [
            (DI + WEN, ZHU),  # best: treat query as 1-char surname + given name
            (WEN, ZHU + DI),  # then: treat as multi-char surname + given name
            (ZHU, DI + WEN),  # then: treat query as given name + surname
        ]

        # When the search query is ZHU + ' ' + DI + WEN (no multi-char surname):
        assert self.get_ranked(persons, ZHU + ' ' + DI + WEN) == [
            (DI + WEN, ZHU),  # best: treat query as surname + ' ' + given name
            (ZHU, DI + WEN),  # then: treat query as given name + ' ' + surname
            (WEN, ZHU + DI),  # then: match query characters out of order
        ]

    def test_search(self):
        persons = [create_person(first_name='Bryan', last_name='abc'),
                   create_person(first_name='Bryan', last_name='abcef'),
                   create_person(first_name='abc', last_name='Bryan'),
                   create_person(first_name='Bryan abc', last_name='efg'),
                   create_person(first_name='AAAA BBBB', last_name='CCC DDD')]
        for p in persons:
            indexing.update_index_properties(p)
            db.put(p)

        res = indexing.search('test', TextQuery('Bryan abc'), 1)
        assert [(p.first_name, p.last_name) for p in res] == [('Bryan', 'abc')]

        res = indexing.search('test', TextQuery('CC AAAA'), 100)
        assert [(p.first_name, p.last_name) for p in res] == \
            [('AAAA BBBB', 'CCC DDD')]

    def test_cjk_first_only(self):
        self.add_persons(
            create_person(first_name=u'\u4f59\u5609\u5e73', last_name='foo'),
            create_person(first_name=u'\u80e1\u6d9b\u5e73', last_name='foo'),
        )

        # Any single character should give a hit.
        assert self.get_matches(u'\u4f59') == [(u'\u4f59\u5609\u5e73', 'foo')]
        assert self.get_matches(u'\u5609') == [(u'\u4f59\u5609\u5e73', 'foo')]
        assert self.get_matches(u'\u5e73') == [
            (u'\u4f59\u5609\u5e73', 'foo'),
            (u'\u80e1\u6d9b\u5e73', 'foo')
        ]

        # Order of characters in the query should not matter.
        assert self.get_matches(u'\u5609\u5e73') == \
            [(u'\u4f59\u5609\u5e73', 'foo')]
        assert self.get_matches(u'\u5e73\u5609') == \
            [(u'\u4f59\u5609\u5e73', 'foo')]
        assert self.get_matches(u'\u4f59\u5609\u5e73') == \
            [(u'\u4f59\u5609\u5e73', 'foo')]


    def test_cjk_last_only(self):
        self.add_persons(
            create_person(first_name='foo', last_name=u'\u4f59\u5609\u5e73'),
            create_person(first_name='foo', last_name=u'\u80e1\u6d9b\u5e73'),
        )

        # Any single character should give a hit.
        assert self.get_matches(u'\u4f59') == \
            [('foo', u'\u4f59\u5609\u5e73')]
        assert self.get_matches(u'\u5609') == \
            [('foo', u'\u4f59\u5609\u5e73')]
        assert self.get_matches(u'\u5e73') == [
            ('foo', u'\u4f59\u5609\u5e73'),
            ('foo', u'\u80e1\u6d9b\u5e73')
        ]

        # Order of characters in the query should not matter.
        assert self.get_matches(u'\u5609\u5e73') == \
            [('foo', u'\u4f59\u5609\u5e73')]
        assert self.get_matches(u'\u5e73\u5609') == \
            [('foo', u'\u4f59\u5609\u5e73')]
        assert self.get_matches(u'\u4f59\u5609\u5e73') == \
            [('foo', u'\u4f59\u5609\u5e73')]


    def test_cjk_first_last(self):
        self.add_persons(
            create_person(first_name=u'\u5609\u5e73', last_name=u'\u4f59'),
            create_person(first_name=u'\u6d9b\u5e73', last_name=u'\u80e1'),
        )

        # Any single character should give a hit.
        assert self.get_matches(u'\u4f59') == \
            [(u'\u5609\u5e73', u'\u4f59')]
        assert self.get_matches(u'\u5609') == \
            [(u'\u5609\u5e73', u'\u4f59')]
        assert self.get_matches(u'\u5e73') == [
            (u'\u5609\u5e73', u'\u4f59'),
            (u'\u6d9b\u5e73', u'\u80e1')
        ]

        # Order of characters in the query should not matter.
        assert self.get_matches(u'\u5609\u5e73') == \
            [(u'\u5609\u5e73', u'\u4f59')]
        assert self.get_matches(u'\u5e73\u5609') == \
            [(u'\u5609\u5e73', u'\u4f59')]
        assert self.get_matches(u'\u4f59\u5609\u5e73') == \
            [(u'\u5609\u5e73', u'\u4f59')]


if __name__ == '__main__':
    logging.basicConfig( stream=sys.stderr )
    unittest.main()
