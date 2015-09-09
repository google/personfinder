#!/usr/bin/python2.7
# encoding: utf-8
"""Tests for script_variant.py"""
import unittest

import script_variant

class ScriptVariantTests(unittest.TestCase):
    def test_apply_script_variant(self):
        assert script_variant.apply_script_variant(u'四条 貴音') == u'四条 貴音'
        assert script_variant.apply_script_variant(u'三浦あずさ king') == u'三浦AZUSA king'
    
    def test_translate_languages_to_roman(self):
        assert script_variant.translate_languages_to_roman(u'吉澤') == u'吉澤'
        assert script_variant.translate_languages_to_roman(u'Reporter') == u'Reporter'
