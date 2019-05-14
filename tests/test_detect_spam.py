# Copyright 2019 Google Inc.
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
