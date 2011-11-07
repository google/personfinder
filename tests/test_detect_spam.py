#!/usr/bin/python2.5
#
# Copyright 2010 Google Inc. All Rights Reserved.

"""Unittest for detect_spam.py module."""

__author__ = 'shaomei@google.com (Shaomei Wu)'

from google.appengine.ext import db
from detect_spam import SpamDetector
import unittest


class SpamDetectorTests(unittest.TestCase):
    def test_init(self):
        d = SpamDetector('foo, BAR')
        assert set(['foo', 'bar']) == d.bad_words_set

    def test_estimate_spam_score(self):
        d = SpamDetector('foo, BAR')
        assert d.estimate_spam_score('a sentence with foo, bar') == 0.4
        assert d.estimate_spam_score("It's a Foo day.") == 0.25 
        assert d.estimate_spam_score('x') == 0
        assert d.estimate_spam_score('123') == 0
        assert d.estimate_spam_score('  ,') == None
        assert d.estimate_spam_score('') == None 

if __name__ == '__main__':
    unittest.main()
