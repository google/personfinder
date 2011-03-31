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
    u'ー': u'ー',
}


# Katakana to hiragana.
KATAKANA_TO_HIRAGANA = {}
for key, value in HIRAGANA_TO_KATAKANA.iteritems():
    KATAKANA_TO_HIRAGANA[value] = key
KATAKANA_TO_HIRAGANA[u'エ'] = u'え'
KATAKANA_TO_HIRAGANA[u'イ'] = u'い'


# Dictionary of characters ([\u3000-\u9fff]) that are popularly used as part
# of Japanese names with their relative frequency counts.  This dictionary is
# generated by aggregating names_prefixes of about 520k Person entries from the
# Japan instance as of 03-25-2011.  We retained only the ones with frequnecy
# counts >= 500.
NAME_CHAR_POPULARITY_MAP = {
    u'子': 125824, u'藤': 58115, u'田': 45545, u'佐': 43413, u'木': 39214,
    u'美': 37144, u'野': 32917, u'山': 26263, u'小': 23586, u'一': 21586,
    u'川': 20002, u'部': 19426, u'村': 18580, u'大': 16649, u'高': 16240,
    u'阿': 15842, u'々': 15668, u'橋': 14894, u'千': 14265, u'和': 13300,
    u'鈴': 13253, u'三': 12638, u'本': 12600, u'原': 12542, u'恵': 11862,
    u'幸': 10975, u'谷': 10926, u'井': 10918, u'松': 10633, u'正': 10329,
    u'雄': 10279, u'み': 10069, u'中': 9645, u'菅': 9505, u'夫': 9464,
    u'さ': 9359, u'渡': 9075, u'久': 9055, u'吉': 8925, u'郎': 8882,
    u'上': 8874, u'男': 8641, u'浦': 8208, u'あ': 8036, u'葉': 7945,
    u'伊': 7756, u'真': 7627, u'と': 7616, u'太': 7528, u'か': 7479,
    u'石': 7477, u'澤': 7365, u'ま': 7270, u'由': 7266, u'た': 7233,
    u'平': 7099, u'内': 7009, u'き': 6973, u'明': 6826, u'志': 6776,
    u'菊': 6750, u'勝': 6731, u'寺': 6682, u'崎': 6672, u'代': 6435,
    u'遠': 6407, u'江': 6298, u'ひ': 6085, u'辺': 6046, u'智': 5991,
    u'香': 5929, u'也': 5844, u'光': 5757, u'清': 5744, u'紀': 5629,
    u'ゆ': 5517, u'奈': 5263, u'弘': 5239, u'熊': 5221, u'武': 5218,
    u'治': 5175, u'裕': 5113, u'孝': 5061, u'沢': 5045, u'喜': 5018,
    u'洋': 5007, u'二': 4899, u'信': 4875, u'加': 4823, u'里': 4747,
    u'し': 4718, u'及': 4678, u'秀': 4655, u'よ': 4639, u'林': 4565,
    u'彦': 4550, u'文': 4516, u'義': 4503, u'樹': 4446, u'島': 4412,
    u'良': 4369, u'賀': 4342, u'岩': 4306, u'岡': 4245, u'森': 4218,
    u'昭': 4150, u'利': 4146, u'金': 4142, u'安': 4108, u'人': 4089,
    u'枝': 4067, u'坂': 4063, u'之': 4059, u'西': 3980, u'友': 3971,
    u'貴': 3948, u'池': 3925, u'沼': 3894, u'英': 3862, u'博': 3821,
    u'司': 3821, u'浩': 3789, u'保': 3765, u'今': 3753, u'新': 3695,
    u'地': 3660, u'は': 3636, u'佳': 3618, u'ち': 3600, u'海': 3542,
    u'芳': 3528, u'健': 3498, u'ふ': 3490, u'津': 3458, u'長': 3453,
    u'栄': 3448, u'俊': 3418, u'隆': 3417, u'斉': 3413, u'こ': 3406,
    u'敏': 3371, u'口': 3351, u'理': 3276, u'優': 3263, u'間': 3248,
    u'す': 3169, u'永': 3168, u'下': 3153, u'直': 3094, u'広': 3048,
    u'宏': 2995, u'や': 2987, u'春': 2953, u'愛': 2919, u'お': 2891,
    u'塚': 2887, u'富': 2879, u'畠': 2805, u'な': 2804, u'行': 2790,
    u'祐': 2789, u'い': 2787, u'尾': 2761, u'戸': 2753, u'宮': 2699,
    u'希': 2656, u'横': 2554, u'康': 2534, u'り': 2516, u'生': 2515,
    u'八': 2496, u'仁': 2495, u'の': 2469, u'輝': 2458, u'政': 2452,
    u'成': 2444, u'徳': 2436, u'後': 2398, u'水': 2390, u'雅': 2386,
    u'須': 2373, u'忠': 2370, u'悦': 2364, u'重': 2359, u'花': 2357,
    u'茂': 2352, u'福': 2315, u'陽': 2278, u'相': 2273, u'根': 2272,
    u'寿': 2263, u'倉': 2254, u'斎': 2244, u'馬': 2228, u'京': 2222,
    u'日': 2213, u'知': 2173, u'菜': 2145, u'介': 2129, u'次': 2119,
    u'泉': 2080, u'つ': 2076, u'く': 2074, u'東': 2052, u'星': 2040,
    u'実': 2023, u'け': 2007, u'黒': 1977, u'せ': 1969, u'豊': 1962,
    u'則': 1939, u'穂': 1913, u'齋': 1903, u'史': 1884, u'勇': 1873,
    u'門': 1842, u'昌': 1839, u'荒': 1831, u'誠': 1818, u'て': 1800,
    u'麻': 1788, u'形': 1784, u'純': 1780, u'伸': 1748, u'道': 1746,
    u'堀': 1743, u'典': 1741, u'ゐ': 1732, u'杉': 1732, u'城': 1728,
    u'竹': 1727, u'古': 1724, u'青': 1691, u'静': 1655, u'哲': 1648,
    u'克': 1647, u'泰': 1633, u'淳': 1629, u'早': 1628, u'関': 1611,
    u'前': 1601, u'畑': 1581, u'士': 1575, u'哉': 1573, u'白': 1565,
    u'亜': 1560, u'秋': 1559, u'拓': 1531, u'晴': 1525, u'幡': 1519,
    u'修': 1516, u'善': 1513, u'翔': 1498, u'節': 1489, u'弥': 1455,
    u'貞': 1424, u'順': 1418, u'見': 1416, u'場': 1415, u'沙': 1409,
    u'啓': 1403, u'市': 1402, u'舘': 1401, u'好': 1392, u'浅': 1387,
    u'瀬': 1386, u'達': 1378, u'猪': 1359, u'敬': 1354, u'有': 1353,
    u'元': 1353, u'照': 1329, u'公': 1323, u'多': 1310, u'合': 1309,
    u'庄': 1294, u'吾': 1290, u'え': 1282, u'工': 1281, u'矢': 1278,
    u'賢': 1271, u'笠': 1268, u'登': 1264, u'赤': 1260, u'土': 1255,
    u'織': 1247, u'五': 1245, u'嶋': 1244, u'斗': 1244, u'晃': 1221,
    u'う': 1213, u'桜': 1212, u'悠': 1202, u'狩': 1198, u'末': 1194,
    u'章': 1193, u'彩': 1191, u'綾': 1188, u'尚': 1188, u'近': 1181,
    u'丹': 1179, u'亀': 1173, u'亮': 1164, u'絵': 1149, u'寛': 1139,
    u'北': 1136, u'衣': 1133, u'邦': 1127, u'憲': 1127, u'米': 1118,
    u'輔': 1115, u'郁': 1108, u'玉': 1104, u'奥': 1095, u'国': 1094,
    u'妻': 1084, u'満': 1082, u'守': 1082, u'夏': 1082, u'羽': 1068,
    u'ゑ': 1060, u'百': 1046, u'鎌': 1045, u'河': 1021, u'玲': 1017,
    u'朗': 1007, u'梨': 997, u'乃': 994, u'わ': 966, u'家': 962, u'條': 960,
    u'華': 960, u'聖': 956, u'慶': 953, u'柴': 950, u'越': 945, u'咲': 944,
    u'も': 939, u'龍': 937, u'れ': 933, u'梅': 928, u'十': 922, u'未': 920,
    u'柳': 920, u'圭': 913, u'邊': 904, u'進': 902, u'嘉': 890, u'澄': 887,
    u'佑': 887, u'浜': 887, u'屋': 885, u'恭': 884, u'功': 876, u'敦': 875,
    u'剛': 874, u'若': 868, u'礼': 857, u'将': 833, u'南': 829, u'作': 828,
    u'蔵': 819, u'紗': 817, u'月': 814, u'髙': 800, u'細': 799, u'音': 796,
    u'名': 796, u'神': 791, u'出': 787, u'又': 785, u'結': 784, u'祥': 784,
    u'四': 783, u'歩': 781, u'梶': 775, u'莉': 775, u'め': 769, u'渕': 768,
    u'聡': 764, u'宗': 763, u'央': 761, u'片': 757, u'昆': 757, u'稲': 752,
    u'る': 751, u'廣': 751, u'ほ': 750, u'鶴': 744, u'目': 738, u'紺': 737,
    u'来': 731, u'丸': 726, u'七': 726, u'那': 721, u'じ': 714, u'櫻': 712,
    u'繁': 708, u'瑞': 705, u'世': 703, u'飯': 700, u'酒': 699, u'半': 698,
    u'植': 685, u'朋': 682, u'助': 681, u'初': 676, u'睦': 673, u'眞': 671,
    u'竜': 663, u'悟': 663, u'靖': 658, u'盛': 655, u'卓': 655, u'定': 650,
    u'板': 649, u'都': 645, u'宇': 643, u'慎': 642, u'宍': 638, u'学': 636,
    u'力': 635, u'柏': 631, u'立': 628, u'草': 626, u'鳥': 624, u'嵐': 621,
    u'充': 617, u'昇': 615, u'徹': 608, u'朝': 607, u'栗': 605, u'邉': 599,
    u'緒': 596, u'律': 595, u'妙': 593, u'辰': 593, u'濱': 592, u'む': 585,
    u'岸': 584, u'天': 580, u'旧': 580, u'君': 577, u'涼': 572, u'稔': 567,
    u'雪': 564, u'彰': 563, u'心': 557, u'槻': 556, u'己': 555, u'勉': 544,
    u'冨': 542, u'居': 541, u'房': 539, u'姓': 539, u'恒': 538, u'征': 538,
    u'桂': 535, u'に': 534, u'薫': 531, u'望': 529, u'垣': 526, u'厚': 524,
    u'笹': 523, u'巳': 522, u'渋': 518, u'瓶': 506, u'洞': 505, u'湊': 505,
    u'瑠': 505, u'波': 505, u'幹': 504, u'角': 501, u'弓': 500,
}
assert len(NAME_CHAR_POPULARITY_MAP) == 474


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
    # NFKC normalization does the followings:
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


def sorted_by_popularity(tokens):
    """Sort tokens according to popularity (see NAME_CHAR_POPULARITY_MAP) so
    that tokens that are LESS popular in Japanese names come first, and return
    the sorted tokens.

    Args:
        tokens: tokens to sort.
    Returns:
        Sorted tokens.
    """
    return sorted(tokens, key=lambda t: NAME_CHAR_POPULARITY_MAP.get(t, 0))
