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


import jautils

from unidecode import unidecode

import os.path
import re
import logging

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
                    if not line.strip() or line.strip()[0] == "#":
                        continue
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

JAPANESE_NAME_LOCATION_DICTIONARY = read_dictionary('japanese_name_location_dict.txt')
CHINESE_FAMILY_NAME_DICTIONARY = read_dictionary('chinese_family_name_dict.txt')

def has_kanji(word):
    """
    Returns whether word contains kanji or not.
    """
    # [\u3400-\u9fff]: kanji
    # TODO: update this range (some of kanji characters out of this range.)
    return re.match(ur'([\u3400-\u9fff])', word)


def romanize_single_japanese_word(word):
    """
    This method romanizes a single Japanese word using a dictionary.
    If the word isn't found in the dictionary, this method returns the word as is.
    This method can return multiple romanizations
    (because there are multiple ways to read the same kanji name in Japanese).
    This method doesn't support romanizing full names using first/last
    names in the dictionary.

    Returns:
        [romanized_jp_word, ...]
    """
    if not word:
        return ['']

    if word in JAPANESE_NAME_LOCATION_DICTIONARY:
        yomigana_list = JAPANESE_NAME_LOCATION_DICTIONARY[word]
        return [jautils.hiragana_to_romaji(yomigana)
                for yomigana in yomigana_list]

    return [word]


def romanize_japanese_word(word, for_index=True):
    """
    This method romanizes a Japanese text chunk using a dictionary.
    If the word isn't found in the dictionary, this method returns the word as is.
    This method can return multiple romanizations
    (because there are multiple ways to read the same kanji name in Japanese).

    This method can romanize full names without a white space (e.g., "山田太郎")
    if the first/last names are in the dictionary.

    Args:
        for_index: Set this to True for indexing purpose.
                   Set this to False when you want to romanize query text.
    Returns:
        [romanized_jp_word, ...]
    """
    if not word:
        return ['']

    words = set()
    for index in xrange(1, len(word)):
        # Splits the word to support romanizing fullname without space.
        # If the query is a full name without white space(e.g., "山田太郎"),
        # and the first/last name is in the dictionary,
        # but the full name is not in the dictionary,
        # it can still return romanization "yamadataro".
        first_part = word[:index]
        last_part = word[index:]
        romanized_first_parts = romanize_single_japanese_word(
            first_part)
        romanized_last_parts = romanize_single_japanese_word(
            last_part)
        for romanized_first_part in romanized_first_parts:
            for romanized_last_part in romanized_last_parts:
                if (romanized_first_part != first_part and
                        romanized_last_part != last_part):
                    words.add(romanized_first_part + romanized_last_part)
                    # For indexing purpose, if the input is "山田太郎", we need
                    # to add "yamada" and "taro" in addition to "yamadataro"
                    # because it must match queries e.g., "山田" or "太郎".
                    #
                    # But, when we apply this method for search queries, we
                    # must not do this. If the search query is [山田太郎] and
                    # we return ["yamadataro", "yamada", "taro"], the query
                    # will be "yamadataro OR yamada OR taro". Then it will
                    # also match records with name "yamada hanako" etc., which
                    # is bad.
                    #
                    # TODO(ichikawa) Consider applying this for search queries,
                    #     but construct a query 'yamadataro OR "yamada taro"'
                    #     instead. Then it will also match a record with name
                    #     "yamada taro".
                    if for_index:
                        words.add(romanized_first_part)
                        words.add(romanized_last_part)
    words.update(romanize_single_japanese_word(word))
    return list(words)


def romanize_word_by_unidecode(word):
    """
    This method romanizes all languages by unidecode.
    If word is hiragana or katakana, it is romanized by jautils.
    kanji is romanized in Chinese way.
    Args:
        word: should be script varianted
    Returns:
        an array of romanzied_word by unidecode [romanized_word]
    """
    if not word:
        return ['']

    if jautils.should_normalize(word):
        hiragana_word = jautils.normalize(word)
        return [jautils.hiragana_to_romaji(hiragana_word)]
    romanized_word = unidecode(word)
    return [romanized_word.strip()]


def split_chinese_name(word):
    """
    This method tries to split a chinese name into two parts: family_name and given_name
    Args:
        word: a chinese name string
    Returns:
        family_name and given_name if it is a valid chinese name
        else None, None
    """
    if not word:
        return None, None

    word = word.replace(" ", "")
    if not re.search(ur'^[\u3400-\u9fff]+$', word):
        return None, None

    for i in range(1,3):
        if word[:i] in CHINESE_FAMILY_NAME_DICTIONARY:
            return word[:i], word[i:]

    return None, None


def romanize_chinese_name(word):
    """
    This method romanizes a chinese person name including family_name and given_name

    Returns:
        Romanized Chinese name
    """
    family_name, given_name = split_chinese_name(word)

    if not family_name:
        return []

    romanized_surname_list = list(CHINESE_FAMILY_NAME_DICTIONARY[family_name])
    return [romanized_surname_list[0] + unidecode(given_name).strip()]


def romanize_search_query(word):
    """
    This method romanizes all languages for search query.
    If word is hiragana or katakana, it is romanized by jautils.
    Args:
        word: should be script varianted
    Returns:
        [romanized_word, ... ]   
        (if word can be romanized by unidecode and jp_dictionary,
        returns multiple romanizations.)
    """
    if not word:
        return []

    romanized_words = []
    if has_kanji(word):
        romanized_words = romanize_japanese_word(word, for_index=False)

    if jautils.should_normalize(word):
        hiragana_word = jautils.normalize(word)
        romanized_words.append(jautils.hiragana_to_romaji(hiragana_word))

    # if the name is a Chinese name and the chinese_romanize can produce
    # a different result, append the result to the romanzied_words with
    # unidecode results together
    unidecode_romanize_word = unidecode(word).strip()
    chinese_romanize_list = romanize_chinese_name(word)
    chinese_romanize_word = chinese_romanize_list[0] if chinese_romanize_list else ''
    if chinese_romanize_word and chinese_romanize_word != unidecode_romanize_word:
        romanized_words.append(chinese_romanize_word)
    romanized_words.append(unidecode_romanize_word)

    return romanized_words
