import jautils

from unidecode import unidecode

import os.path
import re

def read_dictionary(file_name):
    """
    Reads dictionary file.
    Args:
        file_name: file name.
                   format: kanji + '\t' + yomigana
    Return:
        {kanj: yomigana, ...}
    """
    dictionary = {}
    try:
        if os.path.exists(file_name):
            with open(file_name, 'r') as f:
                for line in f:
                    kanji, hiragana = line.rstrip('\n').split('\t')
                    kanji = kanji.decode('utf-8')
                    hiragana = hiragana.decode('utf-8')
                    if kanji in dictionary:
                        dictionary[kanji].add(hiragana)
                    else:
                        dictionary[kanji] = set([hiragana])

    except IOError:
        return None
    return dictionary

JAPANESE_NAME_DICTIONARY = read_dictionary('japanese_name_dict.txt')
JAPANESE_LOCATION_DICTIONARY = read_dictionary('jp_location_dict.txt')


def has_kanji(word):
    """
    Returns whether word contains kanji or not.
    """
    # [\u3400-\u9fff]: kanji
    # TODO: update this range (some of kanji characters out of this range.)
    return re.match(ur'([\u3400-\u9fff])', word)


def romanize_japanese_name_by_name_dict(word):
    """
    This method romanizes japanese name by using name dictionary.
    If word isn't found in dictionary, this method doesn't
    apply romanize.
    This method can return multiple romanizations.
    Returns:
        [romanized_jp_name, ...]
    """
    if not word:
        return ['']

    if word in JAPANESE_NAME_DICTIONARY:
        yomigana_list = JAPANESE_NAME_DICTIONARY[word]
        return [jautils.hiragana_to_romaji(yomigana)
                for yomigana in yomigana_list]

    return [word]


def romanize_japanese_location(word):
    """
    This method romanizes japanese location by using name dictionary.
    If word isn't found in dictionary, this method doesn't
    apply romanize.
    This method can return multiple romanizations.
    Returns:
        [romanized_jp_location, ...]
    """
    if not word:
        return ['']

    if word in JAPANESE_LOCATION_DICTIONARY:
        yomigana_list = JAPANESE_LOCATION_DICTIONARY[word]
        return [jautils.hiragana_to_romaji(yomigana)
                for yomigana in yomigana_list]

    return [word]


def romanize_word_by_unidecode(word):
    """
    This method romanizes all languages by unidecode.
    If word is hiragana or katakana, it is romanized by jautils.
    kanji is romanized in Chinese way.
    Args:
        word: should be script varianted
    Returns:
        arrays of romanzied_word by unidecode [romanized_word]
    """
    if not word:
        return ['']

    if jautils.should_normalize(word):
        hiragana_word = jautils.normalize(word)
        return [jautils.hiragana_to_romaji(hiragana_word)]
    romanized_word = unidecode(word)
    return [romanized_word.strip()]


def romanize_word(word):
    """
    This method romanizes all languages.
    If word is hiragana or katakana, it is romanized by jautils.
    Args:
        word: should be script varianted
    Returns:
        script varianted word
    """
    if not word:
        return []

    romanized_words = []
    if has_kanji(word):
        romanized_words = romanize_japanese_name_by_name_dict(word)
        romanized_words.extend(romanize_japanese_location(word))

    if jautils.should_normalize(word):
        hiragana_word = jautils.normalize(word)
        romanized_words.append(jautils.hiragana_to_romaji(hiragana_word))

    romanized_word = unidecode(word)
    romanized_words.append(romanized_word.strip())
    return romanized_words
