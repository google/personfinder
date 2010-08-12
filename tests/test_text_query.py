#!/usr/bin/python2.5
#
# Copyright 2010 Google Inc. All Rights Reserved.

"""Unittest for text_query.py module."""

__author__ = 'eyalf@google.com (Eyal Fink)'

from google.appengine.ext import db
import text_query
import unittest


class TextQueryTests(unittest.TestCase):
  def test_normalize(self):
    self.assertEqual(text_query.normalize(u'hi there'), u'HI THERE')
    self.assertEqual(text_query.normalize(u'salut l\xe0'), u'SALUT LA')
    self.assertEqual(
        text_query.normalize(
            u'L\xf2ng Str\xefng w\xedth l\xf4ts \xf6f \xc3cc\xebnts'),
        u'LONG STRING WITH LOTS OF ACCENTS')

  def test_cjk_separation(self):
    q = text_query.TextQuery(u'\u4f59\u5609\u5e73')
    self.assertEqual([u'\u4f59', u'\u5609', u'\u5e73'], q.words)
    self.assertEqual(q.words, q.query_words)
    q = text_query.TextQuery(u'foo\u4f59\u5609bar\u5e73')
    self.assertEqual(['FOO', u'\u4f59', u'\u5609', 'BAR', u'\u5e73'], q.words)
    self.assertEqual(q.words, q.query_words)
    
  def test_pasrsing(self):
    q = text_query.TextQuery('abcd  e  fghij')
    self.assertEqual(['ABCD', 'E', 'FGHIJ'], q.words)
    self.assertEqual(q.words, q.query_words)

if __name__ == '__main__':
  unittest.main()
