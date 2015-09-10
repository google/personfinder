# coding:utf-8
import jautils

from unidecode import unidecode
from google.appengine.api import memcache

import logging
import re

def change_word_to_alphabet(word):
    """
    Changes word to alphabet.
    This method should be called in translate_languages_to_roman().
    Args:
        word: should be script varianted
    Returns:
        script varianted word
    """
    if jautils.should_normalize(word):
        hiragana_word = jautils.normalize(word)
        return jautils.hiragana_to_romaji(hiragana_word)
    script_varianted_word = unidecode(word)
    return script_varianted_word


def romanize_japanese_name_by_name_dict(word):
    if not word:
        return word

    hiragana = memcache.get(unicode(word, 'utf-8'))
    logging.info(hiragana)
    return jautils.hiragana_to_romaji(hiragana)


def translate_all_languages_to_roman(word):
    """
    Translates all languages to Roman.
    Args:
        word: should be script_varianted
    Returns:
        script varianted word
    """
    if not word:
        return word

    return change_word_to_alphabet(word)


def apply_script_variant(query_txt):
    """
    Applies to script variant to query_txt.
    Args:
        query_txt: Search query
    Returns:
        script varianted query_txt (except kanji)
    """
    query_words = query_txt.split(' ')
    return ' '.join([translate_all_languages_to_roman(word) for word in query_words])
