# coding:utf-8

"""Tests for script_variant.py"""

import script_variant
import unittest


class ScriptVariantTests(unittest.TestCase):
    def test_romanize_japanese_word(self):
        assert script_variant.romanize_japanese_word(
            u'雪歩') == [u'YUKIHO']
        assert script_variant.romanize_japanese_word(
            u'東京') == [u'TOKYO']
        assert script_variant.romanize_japanese_word(
            u'偶像大师') == [u'偶像大师']
        assert script_variant.romanize_japanese_word(
            u'天海') == [u'TENKAI', u'AMAMI', u'AMAGAI', u'AMAUMI']
        assert script_variant.romanize_japanese_word(
            u'') == [u'']

    def test_romanize_word(self):
        assert script_variant.romanize_word_by_unidecode(u'Cœur') == [u'Coeur']
        assert script_variant.romanize_word_by_unidecode(u'貴音') == [u'Gui Yin']
        assert script_variant.romanize_word_by_unidecode(u'きくちまこと') == [u'KIKUCHIMAKOTO']
        assert script_variant.romanize_word_by_unidecode(u'') == [u'']
