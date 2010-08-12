#!/usr/bin/python2.5
#
# Copyright 2010 Google Inc. All Rights Reserved.

"""Unittest for indexing.py module."""

__author__ = 'eyalf@google.com (Eyal Fink)'

from google.appengine.ext import db
import indexing
import unittest
import logging
import sys

from text_query import TextQuery

class TestPerson(db.Model):
  first_name = db.StringProperty()
  last_name = db.StringProperty()
  names_prefixes = db.StringListProperty()
  _fields_to_index_properties = ['first_name', 'last_name']
  _fields_to_index_by_prefix_properties = ['first_name', 'last_name']

class IndexingTests(unittest.TestCase):

  def setUp(self):
    db.delete(TestPerson.all())

  def add_persons(self, *persons):
    for p in persons:
      indexing.update_index_properties(p)
      db.put(p)

  def get_matches(self, query, limit=100):
    results = indexing.search(TestPerson, TextQuery(query), limit)
    return [(p.first_name, p.last_name) for p in results]

  def get_ranked(self, results, query, limit=100):
    ranked = indexing.rank_and_order(results, TextQuery(query), limit)
    return [(p.first_name, p.last_name) for p in results]

  def test_rank_and_order(self):
    res= [TestPerson(first_name='Bryan', last_name='abc'),
          TestPerson(first_name='Bryan', last_name='abcef'),
          TestPerson(first_name='abc', last_name='Bryan'),
          TestPerson(first_name='Bryan abc', last_name='efg')]

    sorted = indexing.rank_and_order(res, TextQuery('Bryan abc'), 100)
    self.assertEqual(['%s %s'%(p.first_name, p.last_name) for p in sorted],
                     ['Bryan abc', 'abc Bryan', 'Bryan abc efg', 'Bryan abcef'])

    sorted = indexing.rank_and_order(res, TextQuery('Bryan abc'), 2)
    self.assertEqual(['%s %s'%(p.first_name, p.last_name) for p in sorted],
                     ['Bryan abc', 'abc Bryan'])

    sorted = indexing.rank_and_order(res, TextQuery('abc Bryan'), 100)
    self.assertEqual(['%s %s'%(p.first_name, p.last_name) for p in sorted],
                     ['abc Bryan', 'Bryan abc', 'Bryan abc efg', 'Bryan abcef'])


    res= [TestPerson(first_name='abc', last_name='efg'),
          TestPerson(first_name='ABC', last_name='EFG'),
          TestPerson(first_name='ABC', last_name='efghij')]

    sorted = indexing.rank_and_order(res, TextQuery('abc'), 100)
    self.assertEqual(['%s %s'%(p.first_name, p.last_name) for p in sorted],
                     ['abc efg', 'ABC EFG', 'ABC efghij'])

  def test_cjk_ranking_1(self):
    # This is Jackie Chan's Chinese name.  His family name is CHAN and his
    # given name is KONG + SANG; the usual Chinese order is CHAN + KONG + SANG.
    CHAN, KONG, SANG = u'\u9673', u'\u6e2f', u'\u751f'

    # This is I. M. Pei's Chinese name.  His family name is BEI and his
    # given name is YU + MING; the usual Chinese order is BEI + YU + MING.
    BEI, YU, MING = u'\u8c9d', u'\u807f', u'\u9298'
    persons = [
      TestPerson(first_name=CHAN + KONG + SANG, last_name='foo'),
      TestPerson(first_name=SANG, last_name=CHAN + KONG),
      TestPerson(first_name=CHAN, last_name=KONG + SANG),
      TestPerson(first_name=KONG + SANG, last_name=CHAN),
      TestPerson(first_name=KONG + CHAN, last_name=SANG),
      TestPerson(first_name=KONG, last_name=SANG),
      TestPerson(first_name=YU + MING, last_name=BEI),
    ]

    self.assertEqual([
      (KONG + SANG, CHAN),  # surname + given name is best
      (SANG, CHAN + KONG),  # then multi-char surname + given name
      (CHAN, KONG + SANG),  # then surname/given switched
      (KONG + CHAN, SANG),  # then out-of-order match
      (CHAN + KONG + SANG, 'foo'),  # then exact given name match
      (KONG, SANG),  # then partial match
      (YU + MING, BEI),  # then nothing match
    ], self.get_ranked(persons, CHAN + KONG + SANG))

    self.assertEqual([
      (KONG + SANG, CHAN),  # surname + given name is best
      (CHAN, KONG + SANG),  # then surname/given switched
      (KONG + CHAN, SANG),  # then multi-char surname / given switched
      (SANG, CHAN + KONG),  # then out-of-order match
      (CHAN + KONG + SANG, 'foo'),  # then exact given name match
      (KONG, SANG),  # then partial match
      (YU + MING, BEI),  # then nothing match
    ], self.get_ranked(persons, CHAN + ' ' + KONG + SANG))

  def test_cjk_ranking_2(self):
    # This is Steven Chu's Chinese name.  His family name is ZHU and his
    # given name is DI + WEN; the usual Chinese order is ZHU + DI + WEN.
    ZHU, DI, WEN = u'\u6731', u'\u68e3', u'\u6587'

    # A test database of three records with various permutations of the name.
    persons = [
      TestPerson(first_name=WEN, last_name=ZHU + DI),
      TestPerson(first_name=DI + WEN, last_name=ZHU),
      TestPerson(first_name=ZHU, last_name=DI + WEN),
    ]

    # When the search query is ZHU + DI + WEN:
    self.assertEqual([
      (DI + WEN, ZHU),  # best: treat query as 1-char surname + given name
      (WEN, ZHU + DI),  # then: treat query as multi-char surname + given name
      (ZHU, DI + WEN),  # then: treat query as given name + surname
    ], self.get_ranked(persons, ZHU + DI + WEN))

    # When the search query is ZHU + ' ' + DI + WEN (no multi-char surname):
    self.assertEqual([
      (DI + WEN, ZHU),  # best: treat query as surname + ' ' + given name
      (ZHU, DI + WEN),  # then: treat query as given name + ' ' + surname
      (WEN, ZHU + DI),  # then: match query characters out of order
    ], self.get_ranked(persons, ZHU + ' ' + DI + WEN))

  def test_search(self):
    persons = [TestPerson(first_name='Bryan', last_name='abc'),
               TestPerson(first_name='Bryan', last_name='abcef'),
               TestPerson(first_name='abc', last_name='Bryan'),
               TestPerson(first_name='Bryan abc', last_name='efg'),
               TestPerson(first_name='AAAA BBBB', last_name='CCC DDD')]
    for p in persons:
      indexing.update_index_properties(p)
      db.put(p)

    res = indexing.search(TestPerson, TextQuery('Bryan abc'), 1)
    self.assertEqual(['%s %s'%(p.first_name, p.last_name) for p in res],
                     ['Bryan abc'])

    res = indexing.search(TestPerson, TextQuery('CC AAAA'), 100)
    self.assertEqual(['%s %s'%(p.first_name, p.last_name) for p in res],
                     ['AAAA BBBB CCC DDD'])

  def test_cjk_first_only(self):
    self.add_persons(
      TestPerson(first_name=u'\u4f59\u5609\u5e73', last_name='foo'),
      TestPerson(first_name=u'\u80e1\u6d9b\u5e73', last_name='foo'),
    )

    # Any single character should give a hit.
    self.assertEqual([(u'\u4f59\u5609\u5e73', 'foo')],
                     self.get_matches(u'\u4f59'))
    self.assertEqual([(u'\u4f59\u5609\u5e73', 'foo')],
                     self.get_matches(u'\u5609'))
    self.assertEqual([(u'\u4f59\u5609\u5e73', 'foo'),
                      (u'\u80e1\u6d9b\u5e73', 'foo')],
                     self.get_matches(u'\u5e73'))

    # Order of characters in the query should not matter.
    self.assertEqual([(u'\u4f59\u5609\u5e73', 'foo')],
                     self.get_matches(u'\u5609\u5e73'))
    self.assertEqual([(u'\u4f59\u5609\u5e73', 'foo')],
                     self.get_matches(u'\u5e73\u5609'))
    self.assertEqual([(u'\u4f59\u5609\u5e73', 'foo')],
                     self.get_matches(u'\u4f59\u5609\u5e73'))


  def test_cjk_last_only(self):
    self.add_persons(
      TestPerson(first_name='foo', last_name=u'\u4f59\u5609\u5e73'),
      TestPerson(first_name='foo', last_name=u'\u80e1\u6d9b\u5e73'),
    )

    # Any single character should give a hit.
    self.assertEqual([('foo', u'\u4f59\u5609\u5e73')],
                     self.get_matches(u'\u4f59'))
    self.assertEqual([('foo', u'\u4f59\u5609\u5e73')],
                     self.get_matches(u'\u5609'))
    self.assertEqual([('foo', u'\u4f59\u5609\u5e73'),
                      ('foo', u'\u80e1\u6d9b\u5e73')],
                     self.get_matches(u'\u5e73'))

    # Order of characters in the query should not matter.
    self.assertEqual([('foo', u'\u4f59\u5609\u5e73')],
                     self.get_matches(u'\u5609\u5e73'))
    self.assertEqual([('foo', u'\u4f59\u5609\u5e73')],
                     self.get_matches(u'\u5e73\u5609'))
    self.assertEqual([('foo', u'\u4f59\u5609\u5e73')],
                     self.get_matches(u'\u4f59\u5609\u5e73'))


  def test_cjk_first_last(self):
    self.add_persons(
      TestPerson(first_name=u'\u5609\u5e73', last_name=u'\u4f59'),
      TestPerson(first_name=u'\u6d9b\u5e73', last_name=u'\u80e1'),
    )

    # Any single character should give a hit.
    self.assertEqual([(u'\u5609\u5e73', u'\u4f59')],
                     self.get_matches(u'\u4f59'))
    self.assertEqual([(u'\u5609\u5e73', u'\u4f59')],
                     self.get_matches(u'\u5609'))
    self.assertEqual([(u'\u5609\u5e73', u'\u4f59'),
                      (u'\u6d9b\u5e73', u'\u80e1')],
                     self.get_matches(u'\u5e73'))

    # Order of characters in the query should not matter.
    self.assertEqual([(u'\u5609\u5e73', u'\u4f59')],
                     self.get_matches(u'\u5609\u5e73'))
    self.assertEqual([(u'\u5609\u5e73', u'\u4f59')],
                     self.get_matches(u'\u5e73\u5609'))
    self.assertEqual([(u'\u5609\u5e73', u'\u4f59')],
                     self.get_matches(u'\u4f59\u5609\u5e73'))


if __name__ == '__main__':
  logging.basicConfig( stream=sys.stderr )
  unittest.main()
