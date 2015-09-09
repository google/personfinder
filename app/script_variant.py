import jautils

from unidecode import unidecode

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

def translate_languages_to_roman(word):
    """
    Translates languages(except kanji) to Roman.
    This method is for ignore Japanese kanji.
    Args:
        word: should be script_varianted
    Returns:
        script varianted word
    """
    if not word:
        return word

    cjk_separated = re.sub(ur'([\u3400-\u9fff])', r' \1 ', word)
    splited_word = cjk_separated.split()
    translated_words = [change_word_to_alphabet(word)
                        if not re.match(ur'([\u3400-\u9fff])', word) else word
                        for word in splited_word]
    return ''.join([word for word in translated_words])

def translate__all_languages_to_roman(word):
    """
    Translates all languages to Roman.
    Args:
        word: should be script_varianted
    Returns:
        script varianted word
    """
    if not word:
        return word

    translated_words = [change_word_to_alphabet(word) for word in splited_word]
    return ''.join([word for word in translated_words])

def apply_script_variant(query_txt, ignore_kanji=True):
    """
    Applies to script variant to query_txt.
    Args:
        query_txt: Search query
    Returns:
        script varianted query_txt (except kanji)
    """
    query_words = query_txt.split(' ')
    return ' '.join([translate_languages_to_roman(word) for word in query_words])
