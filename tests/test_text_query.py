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
    
  def test_pasrsing(self):
    q = text_query.TextQuery('abcd  e  fghij')
    self.assertEqual(len(q.words), 3)
    self.assertEqual(len(q.query_words), 3)

if __name__ == '__main__':
  unittest.main()
