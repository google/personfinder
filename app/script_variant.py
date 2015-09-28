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
                    kanji, hiragana = line[:-1].split('\t')
                    dictionary[kanji.decode('utf-8')] = hiragana.decode('utf-8')
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
    if not word:
        return False
    return re.match(ur'([\u3400-\u9fff])', word)


def romanize_japanese_name_by_name_dict(word):
    """
    This method romanizes japanese name by using name dictionary.
    If word isn't found in dictionary, this method doesn't
    apply romanize.
    """
    if not word:
        return word

    if word in JAPANESE_NAME_DICTIONARY:
        yomigana = JAPANESE_NAME_DICTIONARY[word]
        return jautils.hiragana_to_romaji(yomigana)

    return word


def romanize_japanese_location(word):
    """
    This method romanizes japanese name by using name dictionary.
    If word isn't found in dictionary, this method doesn't
    apply romanize.
    """
    if not word:
        return word

    if word in JAPANESE_LOCATION_DICTIONARY:
        yomigana = JAPANESE_LOCATION_DICTIONARY[word]
        return jautils.hiragana_to_romaji(yomigana)

    return word


def romanize_word_by_unidecode(word):
    """
    This method romanizes all languages by unidecode.
    If word is hiragana or katakana, it is romanized by jautils.
    kanji is romanized in Chinese way.
    Args:
        word: should be script varianted
    Returns:
        script varianted word
    """
    if not word:
        return word

    if jautils.should_normalize(word):
        hiragana_word = jautils.normalize(word)
        return jautils.hiragana_to_romaji(hiragana_word)
    romanized_word = unidecode(word)
    return romanized_word.strip()


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
        return word

    if has_kanji(word):
        word = romanize_japanese_name_by_name_dict(word)
        word = romanize_japanese_location(word)

    if jautils.should_normalize(word):
        hiragana_word = jautils.normalize(word)
        return jautils.hiragana_to_romaji(hiragana_word)
    romanized_word = unidecode(word)
    return romanized_word.strip()


def romanize_text(query_txt):
    """
    Applies romanization to each word in query_txt.
    This method uses unidecode and jautils for script variant.
    Args:
        query_txt: Search query
    Returns:
        script varianted query_txt (except kanji)
    """
    query_words = query_txt.split(' ')
    return ' '.join([romanize_word(word) for word in query_words])


def find_kanji_word(query_txt):
    """
    Finds kanji word from query_txt.
    Args:
        query_txt: Search query
    Returns:
        '"kanji1" "kanji2" ...'
    """
    query_words = query_txt.split(' ')
    kanji_list_in_query_words = []
    for word in query_words:
        if re.match(ur'([\u3400-\u9fff])', word):
            kanji_list_in_query_words.append(word)
    return ' '.join([word for word in kanji_list_in_query_words])
