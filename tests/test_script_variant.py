# coding:utf-8

"""Tests for script_variant.py"""

import script_variant
import unittest


class ScriptVariantTests(unittest.TestCase):
    def test_romanize_japanese_name_by_name_dict(self):
        assert script_variant.romanize_japanese_name_by_name_dict(
            u'雪歩') == [u'YUKIHO']
        assert script_variant.romanize_japanese_name_by_name_dict(
            u'偶像大师') == [u'偶像大师']
        assert script_variant.romanize_japanese_name_by_name_dict(
            u'') == u''

    def test_romanize_japanese_location(self):
        assert script_variant.romanize_japanese_location(u'中野') == [u'NAKANO']
        assert script_variant.romanize_japanese_location(u'海门') == [u'海门']
        assert script_variant.romanize_japanese_location(u'') == u''

    def test_romanize_word(self):
        assert script_variant.romanize_word_by_unidecode(u'Cœur') == [u'Coeur']
        assert script_variant.romanize_word_by_unidecode(u'貴音') == [u'Gui Yin']
        assert script_variant.romanize_word_by_unidecode(u'きくちまこと') == [u'KIKUCHIMAKOTO']
        assert script_variant.romanize_word_by_unidecode(u'') == u''

    def test_romanize_text(self):
        assert script_variant.romanize_text(u'あまみ はるか') == u'AMAMI HARUKA'
        assert script_variant.romanize_text(u'新宿 響') == u'SHINJUKU HIBIKI'
        assert script_variant.romanize_text(u'') == u''
