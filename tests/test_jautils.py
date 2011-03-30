#!/usr/bin/python2.5
# encoding: utf-8
#
# Copyright 2011 Google Inc. All Rights Reserved.

"""Unittest for jautils.py module."""

__author__ = 'ryok@google.com (Ryo Kawaguchi)'

import jautils
import unittest


class JaUtilsTests(unittest.TestCase):
    def test_should_normalize(self):
        assert jautils.should_normalize(u'abc') == False
        assert jautils.should_normalize(u' ABC ') == False
        assert jautils.should_normalize(u'ABC 012') == False
        assert jautils.should_normalize(u'漢字') == False
        assert jautils.should_normalize(u'ひらがな') == True
        assert jautils.should_normalize(u'カタカナ') == True
        assert jautils.should_normalize(u'ｶﾀｶﾅ') == True
        assert jautils.should_normalize(u'ａｂｃ') == True
        assert jautils.should_normalize(u'　ＡＢＣ　') == True
        assert jautils.should_normalize(u'ひらがな カタカナ') == True

    def test_normalize(self):
        assert jautils.normalize(u'abc') == u'ABC'
        assert jautils.normalize(u' ABC ') == u'ABC'
        assert jautils.normalize(u'ABC 012') == u'ABC'
        assert jautils.normalize(u'漢字') == u'漢字'
        assert jautils.normalize(u'ひらがな') == u'ひらがな'
        assert jautils.normalize(u'カタカナ') == u'かたかな'
        assert jautils.normalize(u'ｶﾀｶﾅ') == u'かたかな'
        assert jautils.normalize(u'ａｂｃ') == u'ABC'
        assert jautils.normalize(u'　ＡＢＣ　') == u'ABC'
        assert jautils.normalize(u'ひらがな カタカナ') == u'ひらがな かたかな'
        assert jautils.normalize(u"(abc) O'Hearn") == u'ABC  OHEARN'

    def test_katakana_to_hiragana(self):
        assert jautils.katakana_to_hiragana(u'abc') == u'abc'
        assert jautils.katakana_to_hiragana(u'漢字') == u'漢字'
        assert jautils.katakana_to_hiragana(u'ひらがな') == u'ひらがな'
        assert jautils.katakana_to_hiragana(u'カタカナ') == u'かたかな'
        assert jautils.katakana_to_hiragana(u'ｶﾀｶﾅ') == u'ｶﾀｶﾅ'
        assert jautils.katakana_to_hiragana(u'ａｂｃ') == u'ａｂｃ'
        assert jautils.katakana_to_hiragana(u'キャラメル') == u'きゃらめる'
        assert jautils.katakana_to_hiragana(u'ハードル') == u'はーどる'
        assert jautils.katakana_to_hiragana(
            u'カンダショウタロウ') == u'かんだしょうたろう'
        assert jautils.katakana_to_hiragana(
            u'エンドウイチオ') == u'えんどういちお'
        assert jautils.katakana_to_hiragana(
            u'ひらがな カタカナ') == u'ひらがな かたかな'

    def test_hiragana_to_romaji(self):
        assert jautils.hiragana_to_romaji(u'abc') == u'abc'
        assert jautils.hiragana_to_romaji(u'漢字') == u'漢字'
        assert jautils.hiragana_to_romaji(u'ひらがな') == u'HIRAGANA'
        assert jautils.hiragana_to_romaji(u'カタカナ') == u'カタカナ'
        assert jautils.hiragana_to_romaji(u'ｶﾀｶﾅ') == u'ｶﾀｶﾅ'
        assert jautils.hiragana_to_romaji(u'ａｂｃ') == u'ａｂｃ'
        assert jautils.hiragana_to_romaji(u'きゃらめる') == u'KYARAMERU'
        assert jautils.hiragana_to_romaji(u'はーどる') == u'HA-DORU'
        assert jautils.hiragana_to_romaji(
            u'かんだしょうたろう') == u'KANDASHOTARO'
        assert jautils.hiragana_to_romaji(
            u'えんどういちお') == u'ENDOICHIO'
        assert jautils.hiragana_to_romaji(
            u'ひらがな カタカナ') == u'HIRAGANA カタカナ'

    def test_get_additional_tokens(self):
        assert jautils.get_additional_tokens([u'ABC']) == set()
        assert jautils.get_additional_tokens(set([u'ABC'])) == set()
        assert jautils.get_additional_tokens([u'ABC', u'ひらがな']) == \
            set([u'HIRAGANA'])
        assert jautils.get_additional_tokens([u'やまだ', u'たろう']) == \
            set([u'YAMADA', u'TARO', u'やまだたろう', u'たろうやまだ'])
        assert jautils.get_additional_tokens([u'はい', u'やまだ', u'たろう']) == \
            set([u'HAI', u'YAMADA', u'TARO'])

    def test_sorted_by_popularity(self):
        assert jautils.sorted_by_popularity(
            [u'山', u'田', u'xxx', u'yyy', u'zzz']) == \
            [u'xxx', u'yyy', u'zzz', u'山', u'田']
        assert jautils.sorted_by_popularity(
            [u'山', u'田', u'はなこ']) == \
            [u'はなこ', u'山', u'田']
        assert jautils.sorted_by_popularity(
            [u'山', u'田', u'龍', u'太', u'郎']) == \
            [u'龍', u'太', u'郎', u'山', u'田']


if __name__ == '__main__':
    unittest.main()
