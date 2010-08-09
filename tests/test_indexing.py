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

  
if __name__ == '__main__':
  logging.basicConfig( stream=sys.stderr )
  unittest.main()
