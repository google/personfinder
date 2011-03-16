#!/usr/bin/python2.5
# coding: utf-8
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions specific for Japanese language."""

import re
import unicodedata


# Hiragana to romaji.
# This table is copied from: http://code.google.com/p/mozc/source/browse/trunk/src/data/preedit/hiragana-romanji.tsv 
HIRAGANA_TO_ROMAJI = [
    [u"う゛ぁ", u"VA", u""],
    [u"う゛ぃ", u"VI", u""],
    [u"う゛", u"VU", u""],
    [u"う゛ぇ", u"VE", u""],
    [u"う゛ぉ", u"VO", u""],
    [u"う゛ゃ", u"VYA", u""],
    [u"う゛ゅ", u"VYU", u""],
    [u"う゛ょ", u"VYO", u""],
    [u"っう゛", u"V", u"ゔ"],
    [u"ゔぁ", u"VA", u""],
    [u"ゔぃ", u"VI", u""],
    [u"ゔ", u"VU", u""],
    [u"ゔぇ", u"VE", u""],
    [u"ゔぉ", u"VO", u""],
    [u"ゔゃ", u"VYA", u""],
    [u"ゔゅ", u"VYU", u""],
    [u"ゔょ", u"VYO", u""],
    [u"っゔ", u"V", u"ゔ"],
    [u"っうぁ", u"WWA", u""],
    [u"っうぃ", u"WWI", u""],
    [u"っう", u"WWU", u""],
    [u"っうぇ", u"WWE", u""],
    [u"っうぉ", u"WWO", u""],
    [u"っぁ", u"XXA", u""],
    [u"っぃ", u"XXI", u""],
    [u"っぅ", u"XXU", u""],
    [u"っぇ", u"XXE", u""],
    [u"っぉ", u"XXO", u""],
    [u"っか", u"KKA", u""],
    [u"っき", u"K", u"き"],
    [u"っく", u"KKU", u""],
    [u"っけ", u"KKE", u""],
    [u"っこ", u"KKO", u""],
    [u"っが", u"GGA", u""],
    [u"っぎ", u"G", u"ぎ"],
    [u"っぐ", u"GGU", u""],
    [u"っげ", u"GGE", u""],
    [u"っご", u"GGO", u""],
    [u"っさ", u"SSA", u""],
    [u"っし", u"S", u"し"],
    [u"っす", u"SSU", u""],
    [u"っせ", u"SSE", u""],
    [u"っそ", u"SSO", u""],
    [u"っざ", u"ZZA", u""],
    [u"っじ", u"Z", u"じ"],
    [u"っず", u"ZZU", u""],
    [u"っぜ", u"ZZE", u""],
    [u"っぞ", u"ZZO", u""],
    [u"った", u"TTA", u""],
    [u"っち", u"C", u"ち"],
    [u"っつ", u"TTU", u""],
    [u"って", u"TTE", u""],
    [u"っと", u"TTO", u""],
    [u"っだ", u"DDA", u""],
    [u"っぢ", u"D", u"ぢ"],
    [u"っづ", u"DDU", u""],
    [u"っで", u"DDE", u""],
    [u"っど", u"DDO", u""],
    [u"っは", u"HHA", u""],
    [u"っひ", u"H", u"ひ"],
    [u"っふ", u"HHU", u""],
    [u"っへ", u"HHE", u""],
    [u"っほ", u"HHO", u""],
    [u"っば", u"BBA", u""],
    [u"っび", u"B", u"び"],
    [u"っぶ", u"BBU", u""],
    [u"っべ", u"BBE", u""],
    [u"っぼ", u"BBO", u""],
    [u"っぱ", u"PPA", u""],
    [u"っぴ", u"P", u"ぴ"],
    [u"っぷ", u"PPU", u""],
    [u"っぺ", u"PPE", u""],
    [u"っぽ", u"PPO", u""],
    [u"っま", u"MMA", u""],
    [u"っみ", u"M", u"み"],
    [u"っむ", u"MMU", u""],
    [u"っめ", u"MME", u""],
    [u"っも", u"MMO", u""],
    [u"っや", u"YYA", u""],
    [u"っゆ", u"YYU", u""],
    [u"っよ", u"YYO", u""],
    [u"っゃ", u"XXYA", u""],
    [u"っゅ", u"XXYU", u""],
    [u"っょ", u"XXYO", u""],
    [u"っら", u"RRA", u""],
    [u"っり", u"R", u"り"],
    [u"っる", u"RRU", u""],
    [u"っれ", u"RRE", u""],
    [u"っろ", u"RRO", u""],
    [u"っゎ", u"XXWA", u""],
    [u"っわ", u"WWA", u""],
    [u"っゐ", u"WWI", u""],
    [u"っゑ", u"WWE", u""],
    [u"っを", u"WWO", u""],
    [u"いぇ", u"YE", u""],
    [u"うぁ", u"WA", u""],
    [u"きゃ", u"KYA", u""],
    [u"きぃ", u"KYI", u""],
    [u"きゅ", u"KYU", u""],
    [u"きぇ", u"KYE", u""],
    [u"きょ", u"KYO", u""],
    [u"ぎゃ", u"GYA", u""],
    [u"ぎぃ", u"GYI", u""],
    [u"ぎゅ", u"GYU", u""],
    [u"ぎぇ", u"GYE", u""],
    [u"ぎょ", u"GYO", u""],
    [u"くぁ", u"QA", u""],
    [u"くぃ", u"QI", u""],
    [u"くぇ", u"QE", u""],
    [u"くぉ", u"QO", u""],
    [u"しゃ", u"SHA", u""],
    [u"しぃ", u"SHI", u""],
    [u"しゅ", u"SHU", u""],
    [u"しぇ", u"SHE", u""],
    [u"しょ", u"SHO", u""],
    [u"じゃ", u"JA", u""],
    [u"じぃ", u"ZYI", u""],
    [u"じゅ", u"JU", u""],
    [u"じぇ", u"JE", u""],
    [u"じょ", u"JO", u""],
    [u"ちゃ", u"CHA", u""],
    [u"ちゅ", u"CHU", u""],
    [u"ちぇ", u"CHE", u""],
    [u"ちょ", u"CYO", u""],
    [u"ぢゃ", u"DYA", u""],
    [u"ぢぃ", u"DYI", u""],
    [u"ぢゅ", u"DYU", u""],
    [u"ぢぇ", u"DYE", u""],
    [u"ぢょ", u"DYO", u""],
    [u"つぁ", u"TSA", u""],
    [u"つぃ", u"TSI", u""],
    [u"つぇ", u"TSE", u""],
    [u"つぉ", u"TSO", u""],
    [u"てゃ", u"THA", u""],
    [u"てぃ", u"THI", u""],
    [u"てゅ", u"THU", u""],
    [u"てぇ", u"THE", u""],
    [u"てょ", u"THO", u""],
    [u"でゃ", u"DHA", u""],
    [u"でぃ", u"DHI", u""],
    [u"でゅ", u"DHU", u""],
    [u"でぇ", u"DHE", u""],
    [u"でょ", u"DHO", u""],
    [u"とぁ", u"TWA", u""],
    [u"とぃ", u"TWI", u""],
    [u"とぅ", u"TWU", u""],
    [u"とぇ", u"TWE", u""],
    [u"とぉ", u"TWO", u""],
    [u"どぁ", u"DWA", u""],
    [u"どぃ", u"DWI", u""],
    [u"どぅ", u"DWU", u""],
    [u"どぇ", u"DWE", u""],
    [u"どぉ", u"DWO", u""],
    [u"にゃ", u"NYA", u""],
    [u"にぃ", u"NYI", u""],
    [u"にゅ", u"NYU", u""],
    [u"にぇ", u"NYE", u""],
    [u"にょ", u"NYO", u""],
    [u"ひゃ", u"HYA", u""],
    [u"ひぃ", u"HYI", u""],
    [u"ひゅ", u"HYU", u""],
    [u"ひぇ", u"HYE", u""],
    [u"ひょ", u"HYO", u""],
    [u"びゃ", u"BYA", u""],
    [u"びぃ", u"BYI", u""],
    [u"びゅ", u"BYU", u""],
    [u"びぇ", u"BYE", u""],
    [u"びょ", u"BYO", u""],
    [u"ぴゃ", u"PYA", u""],
    [u"ぴぃ", u"PYI", u""],
    [u"ぴゅ", u"PYU", u""],
    [u"ぴぇ", u"PYE", u""],
    [u"ぴょ", u"PYO", u""],
    [u"ふゃ", u"FYA", u""],
    [u"ふゅ", u"FYU", u""],
    [u"ふょ", u"FYO", u""],
    [u"みゃ", u"MYA", u""],
    [u"みぃ", u"MYI", u""],
    [u"みゅ", u"MYU", u""],
    [u"みぇ", u"MYE", u""],
    [u"みょ", u"MYO", u""],
    [u"りゃ", u"RYA", u""],
    [u"りぃ", u"RYI", u""],
    [u"りゅ", u"RYU", u""],
    [u"りぇ", u"RYE", u""],
    [u"りょ", u"RYO", u""],
    [u"んあ", u"NNA", u""],
    [u"んい", u"NNI", u""],
    [u"んう", u"NNU", u""],
    [u"んえ", u"NNE", u""],
    [u"んお", u"NNO", u""],
    [u"んな", u"NNNA", u""],
    [u"んに", u"NNNI", u""],
    [u"んぬ", u"NNNU", u""],
    [u"んね", u"NNNE", u""],
    [u"んの", u"NNNO", u""],
    [u"あ", u"A", u""],
    [u"い", u"I", u""],
    [u"う", u"U", u""],
    [u"え", u"E", u""],
    [u"お", u"O", u""],
    [u"ぁ", u"XA", u""],
    [u"ぃ", u"XI", u""],
    [u"ぅ", u"XU", u""],
    [u"ぇ", u"XE", u""],
    [u"ぉ", u"XO", u""],
    [u"か", u"KA", u""],
    [u"き", u"KI", u""],
    [u"く", u"KU", u""],
    [u"け", u"KE", u""],
    [u"こ", u"KO", u""],
    [u"ヵ", u"XKA", u""],
    [u"ヶ", u"XKE", u""],
    [u"が", u"GA", u""],
    [u"ぎ", u"GI", u""],
    [u"ぐ", u"GU", u""],
    [u"げ", u"GE", u""],
    [u"ご", u"GO", u""],
    [u"さ", u"SA", u""],
    [u"し", u"SHI", u""],
    [u"す", u"SU", u""],
    [u"せ", u"SE", u""],
    [u"そ", u"SO", u""],
    [u"ざ", u"ZA", u""],
    [u"じ", u"JI", u""],
    [u"ず", u"ZU", u""],
    [u"ぜ", u"ZE", u""],
    [u"ぞ", u"ZO", u""],
    [u"た", u"TA", u""],
    [u"ち", u"CHI", u""],
    [u"つ", u"TSU", u""],
    [u"て", u"TE", u""],
    [u"と", u"TO", u""],
    [u"だ", u"DA", u""],
    [u"ぢ", u"DI", u""],
    [u"づ", u"DU", u""],
    [u"で", u"DE", u""],
    [u"ど", u"DO", u""],
    [u"っ", u"XTU", u""],
    [u"な", u"NA", u""],
    [u"に", u"NI", u""],
    [u"ぬ", u"NU", u""],
    [u"ね", u"NE", u""],
    [u"の", u"NO", u""],
    [u"は", u"HA", u""],
    [u"ひ", u"HI", u""],
    [u"ふ", u"HU", u""],
    [u"へ", u"HE", u""],
    [u"ほ", u"HO", u""],
    [u"ば", u"BA", u""],
    [u"び", u"BI", u""],
    [u"ぶ", u"BU", u""],
    [u"べ", u"BE", u""],
    [u"ぼ", u"BO", u""],
    [u"ぱ", u"PA", u""],
    [u"ぴ", u"PI", u""],
    [u"ぷ", u"PU", u""],
    [u"ぺ", u"PE", u""],
    [u"ぽ", u"PO", u""],
    [u"ま", u"MA", u""],
    [u"み", u"MI", u""],
    [u"む", u"MU", u""],
    [u"め", u"ME", u""],
    [u"も", u"MO", u""],
    [u"ゃ", u"XYA", u""],
    [u"や", u"YA", u""],
    [u"ゅ", u"XYU", u""],
    [u"ゆ", u"YU", u""],
    [u"ょ", u"XYO", u""],
    [u"よ", u"YO", u""],
    [u"ら", u"RA", u""],
    [u"り", u"RI", u""],
    [u"る", u"RU", u""],
    [u"れ", u"RE", u""],
    [u"ろ", u"RO", u""],
    [u"ゎ", u"XWA", u""],
    [u"わ", u"WA", u""],
    [u"ゐ", u"WI", u""],
    [u"ゑ", u"WE", u""],
    [u"を", u"WO", u""],
    [u"ん", u"N", u""],
    [u"ー", u"-", u""],
    [u"〜", u"~", u""],
]


HIRAGANA_TO_ROMAJI_POST_PROCESS = [
    [r'AA', u'A'], [r'II', u'I'], [r'UU', u'U'], [r'EE', u'E'],
    [r'OO', u'O'], [r'OU', u'O'],
]


# Hirakana to katakana.
HIRAGANA_TO_KATAKANA = {
    u'ぁ': u'ァ', u'ぃ': u'ィ', u'ぅ': u'ゥ',
    u'ぇ': u'ェ', u'ぉ': u'ォ',
    u'っ': u'ッ', u'ゃ': u'ャ',
    u'ゅ': u'ュ', u'ょ': u'ョ',
    u'ゎ': u'ヮ', u'ヶ': u'ヶ', u'ヵ': u'ヵ',
    u'が': u'ガ', u'ぎ': u'ギ',
    u'ぐ': u'グ', u'げ': u'ゲ', u'ご': u'ゴ',
    u'ざ': u'ザ', u'じ': u'ジ',
    u'ず': u'ズ', u'ぜ': u'ゼ', u'ぞ': u'ゾ',
    u'だ': u'ダ', u'ぢ': u'ヂ',
    u'づ': u'ヅ', u'で': u'デ', u'ど': u'ド',
    u'ば': u'バ', u'び': u'ビ', u'ぶ': u'ブ',
    u'べ': u'ベ', u'ぼ': u'ボ',
    u'ぱ': u'パ', u'ぴ': u'ピ', u'ぷ': u'プ',
    u'ぺ': u'ペ', u'ぽ': u'ポ',
    u'ゔ': u'ヴ', u'ゐ': u'イ', u'ゑ': u'エ',
    u'あ': u'ア', u'い': u'イ', u'う': u'ウ',
    u'え': u'エ', u'お': u'オ',
    u'か': u'カ', u'き': u'キ', u'く': u'ク',
    u'け': u'ケ', u'こ': u'コ',
    u'さ': u'サ', u'し': u'シ', u'す': u'ス',
    u'せ': u'セ', u'そ': u'ソ',
    u'た': u'タ', u'ち': u'チ', u'つ': u'ツ',
    u'て': u'テ', u'と': u'ト',
    u'な': u'ナ', u'に': u'ニ', u'ぬ': u'ヌ',
    u'ね': u'ネ', u'の': u'ノ',
    u'は': u'ハ', u'ひ': u'ヒ', u'ふ': u'フ',
    u'へ': u'ヘ', u'ほ': u'ホ',
    u'ま': u'マ', u'み': u'ミ', u'む': u'ム',
    u'め': u'メ', u'も': u'モ',
    u'や': u'ヤ', u'ゆ': u'ユ', u'よ': u'ヨ',
    u'ら': u'ラ', u'り': u'リ', u'る': u'ル',
    u'れ': u'レ', u'ろ': u'ロ',
    u'わ': u'ワ', u'を': u'ヲ', u'ん': u'ン',
    u'ー': u'ー'}


# Katakana to hiragana.
KATAKANA_TO_HIRAGANA = {}
for key, value in HIRAGANA_TO_KATAKANA.iteritems():
    KATAKANA_TO_HIRAGANA[value] = key


def should_normalize(string):
    """Checks if the string should be normalized by jautils.normalize() as
    opposed to text_query.normalize().

    Args:
        string: a unicode string to check.
    Returns:
        True if the string should be normalized by jautils.normalize().
    """
    # Does the string contains any of the following characters?
    #  - hiragana
    #  - full/half width katakana
    #  - full width alphabets
    return re.search(ur'[\u3040-\u30ff\uff00-\uff9f]', string) != None


def normalize(string):
    """Normalizes the string with a Japanese specific logic.

    Args:
        string: a unicode string to normalize.
    Returns:
        a unicode string obtained by normalizing the input string.
    """
    # KFKC normalization does the followings:
    #  - Full width roman letter to ascii
    #  - Whitespace characters to " "
    #  - Half width katakana to full width
    letters = []
    for ch in unicodedata.normalize('NFKC', string):
        # Remove non-letter characters.
        category = unicodedata.category(ch)
        if category.startswith('L'):
            letters.append(ch)
        elif category != 'Mn' and ch != "'":  # Treat O'Hearn as OHEARN
            letters.append(' ')
    normalized = ''.join(letters).strip().upper()
    return katakana_to_hiragana(normalized)


def is_hiragana(string):
    """Returns True if the argument is a non-empty string of only
    hiragana characters."""
    return re.match(ur'^[\u3040-\u309f]+$', string) != None


def katakana_to_hiragana(string):
    """Replaces each occurrence of katakana in a unicode string with a hiragana.

    Args:
        string: a unicode string, possibly containing katakana characters.
    Returns:
        The replaced string.
    """
    replaced = u''
    for ch in string:
        replaced += KATAKANA_TO_HIRAGANA.get(ch, ch)
    return replaced


def hiragana_to_romaji(string):
    """Replaces each occurrence of hiragana in a unicode string with a romaji.

    Args:
        string: a unicode string, possibly containing hiragana characters.
    Returns:
        The replaced string.
    """
    remaining = string
    result = u''
    while remaining:
        longest = 0
        longest_data = None
        for (hira, rom, next) in HIRAGANA_TO_ROMAJI:
            if remaining.startswith(hira) and len(hira) > longest:
                longest_data = (hira, rom, next)
                longest = len(hira)
        if longest == 0:
            # erroneous info
            result += remaining[0]
            remaining = remaining[1:]
        else:
            result += longest_data[1]
            remaining = longest_data[2] + remaining[len(longest_data[0]):]
    for (pat, rep) in HIRAGANA_TO_ROMAJI_POST_PROCESS:
        result = re.sub(pat, rep, result)
    return result


def get_additional_tokens(tokens):
    """Generates new tokens by combining tokens and converting them to various
    character representations, which can be used as search index tokens.

    Args:
        tokens: a list or set of unicode strings to expand from.
    Returns:
        A set of newly generated tokens to add to the search index.
    """
    expanded_tokens = set()

    all_hiragana = True
    for token in tokens:
        if is_hiragana(token):
            # Adds romaji variation of the token so that people without an IME
            # can still search for Japanese names.
            expanded_tokens.add(hiragana_to_romaji(token))
        else:
            all_hiragana = False

    # Japanese users often search by hiragana's where a last name and a first
    # name is concatenated without a space in between.  Because a sequence of
    # hiragana's is not segmented at query time, we need to add those
    # concatenated tokens to the index to make them searchable.
    # len(tokens) == 2 should almost always hold when used against Japanese
    # alternate names (one hiragana token for first name and another hiragana
    # token for last name.)
    if all_hiragana and len(tokens) == 2:
        token_list = list(tokens)
        expanded_tokens.add(token_list[0] + token_list[1])
        expanded_tokens.add(token_list[1] + token_list[0])

    return expanded_tokens
