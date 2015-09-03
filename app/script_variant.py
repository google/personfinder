from unidecode import unidecode
import jautils
import logging
import re

def word_to_alphabet(word):
    if jautils.should_normalize(word):
        hiragana_word = jautils.normalize(word)
        romaji_word = jautils.hiragana_to_romaji(hiragana_word)
    script_varianted_word = unidecode(word)
    return script_varianted_word

def script_variant_western(query_word):
    if not query_word:
        return query_word
    cjk_separated = re.sub(ur'([\u3400-\u9fff])', r' \1 ', query_word)
    splited_query_word = cjk_separated.split()
    words = [word_to_alphabet(word)
             if not re.match(ur'([\u3400-\u9fff])', word) else word
             for word in splited_query_word]
    return ''.join([word for word in words])

def language_to_roman(query_txt):
    query_words = query_txt.split(' ')
    return ' '.join([script_variant_western(word) for word in query_words])
