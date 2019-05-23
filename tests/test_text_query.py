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


"""Unittest for text_query.py module."""

from __future__ import absolute_import
__author__ = 'eyalf@google.com (Eyal Fink)'

import text_query
import unittest


class TextQueryTests(unittest.TestCase):
    def test_normalize(self):
        assert text_query.normalize(u'hi there') == u'HI THERE'
        assert text_query.normalize(u'salut l\xe0') == u'SALUT LA'
        assert text_query.normalize(
            u'L\xf2ng Str\xefng w\xedth l\xf4ts \xf6f \xc3cc\xebnts') == \
            u'LONG STRING WITH LOTS OF ACCENTS'

    def test_cjk_separation(self):
        q = text_query.TextQuery(u'\u4f59\u5609\u5e73')
        assert [u'\u4f59', u'\u5609', u'\u5e73'] == q.words
        assert q.words == q.query_words
        q = text_query.TextQuery(u'foo\u4f59\u5609bar\u5e73')
        assert q.words == ['FOO', u'\u4f59', u'\u5609', 'BAR', u'\u5e73']
        assert q.words == q.query_words

    def test_parsing(self):
        q = text_query.TextQuery('abcd  e  fghij')
        assert ['ABCD', 'E', 'FGHIJ'] == q.words
        assert q.words == q.query_words

if __name__ == '__main__':
    unittest.main()
