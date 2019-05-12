# coding:utf-8
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

"""Tests for script_variant.py"""

import script_variant
import unittest

class ScriptVariantTests(unittest.TestCase):

    def test_romanize_japanese_word(self):
        # Person name.
        assert u'YUKIHO' in script_variant.romanize_japanese_word(u'雪歩')
        # Location name.
        assert u'TOKYO' in script_variant.romanize_japanese_word(u'東京')
        # Full name with for_index=True.
        results = script_variant.romanize_japanese_word(
            u'天海春香', for_index=True)
        assert u'AMAMIHARUKA' in results
        assert u'AMAMI' in results
        assert u'HARUKA' in results
        # Full name with for_index=False.
        results = script_variant.romanize_japanese_word(
            u'天海春香', for_index=False)
        assert u'AMAMIHARUKA' in results
        assert u'AMAMI' not in results
        assert u'HARUKA' not in results
        # Not in the dictionary.
        assert script_variant.romanize_japanese_word(
            u'偶像大师') == [u'偶像大师']
        # Empty string.
        assert script_variant.romanize_japanese_word(u'') == [u'']

    def test_romanize_word_by_unidecode(self):
        assert script_variant.romanize_word_by_unidecode(u'Cœur') == [u'Coeur']
        assert script_variant.romanize_word_by_unidecode(u'貴音') == [u'Gui Yin']
        assert script_variant.romanize_word_by_unidecode(u'きくちまこと') == (
            [u'KIKUCHIMAKOTO'])
        assert script_variant.romanize_word_by_unidecode(u'') == [u'']

    def test_romanize_search_query(word):
        results = script_variant.romanize_search_query(u'天海')
        # Two possible Japanese romanizations.
        assert u'AMAMI' in results
        assert u'TENKAI' in results
        # Chinese romanization.
        assert u'Tian Hai' in results
