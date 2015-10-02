# coding:utf-8

"""Tests for script_variant.py"""

import script_variant
import unittest
import sys

class ScriptVariantTests(unittest.TestCase):
    def test_romanize_japanese_name_by_name_dict(self):
        results = script_variant.romanize_japanese_name_by_name_dict(u'天海春香')
        assert set(results) == set([u"AMAMIHARUKA", u"TENKAI", u"TENKAIHARUKA",
                                    u"AMAGAIHARUKA", u"AMAMI", u"HARUKA",
                                    u"AMAGAI", u"AMAUMIHARUKA", u"AMAUMI",
                                    u"天海春香", ])
        assert script_variant.romanize_japanese_name_by_name_dict(
            u'偶像大师') == [u'偶像大师']
        assert script_variant.romanize_japanese_name_by_name_dict(
            u'響') == ['HIBIKI']
        assert script_variant.romanize_japanese_name_by_name_dict(
            u'') == [u'']

    def test_romanize_japanese_location(self):
        assert script_variant.romanize_japanese_location(u'中野') == [u'NAKANO']
        assert script_variant.romanize_japanese_location(u'海门') == [u'海门']
        assert script_variant.romanize_japanese_location(u'') == [u'']

    def test_romanize_word_by_unidecode(self):
        assert script_variant.romanize_word_by_unidecode(u'Cœur') == [u'Coeur']
        assert script_variant.romanize_word_by_unidecode(u'貴音') == [u'Gui Yin']
        assert script_variant.romanize_word_by_unidecode(u'きくちまこと') ==\
            [u'KIKUCHIMAKOTO']
        assert script_variant.romanize_word_by_unidecode(u'') == [u'']

    def test_romanize_word(word):
        results = script_variant.romanize_word(u'天海')
        assert set(results) == set([u'TAKASHIWATARU', u'TAKASHIHIROSHI',
                                    u'HIROSHIKAI', u'TAKASHIHAI', u'TENKAI',
                                    u'HIROSHIWATARU', u'HIROSHIMARIN',
                                    u'TAKASHIKAI', u'TAKASHIUMI', u'TAKASHIMARIN',
                                    u'AMAMI', u'HIROSHIHIROSHI', u'HIROSHIUMI',
                                    u'HIROSHIHAI', u'AMAGAI', u'AMAUMI', u'天海',
                                    u'Tian Hai',])
