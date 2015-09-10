import logging

from google.appengine.api import memcache

def push_data_in_memcache():
    for line in open('japanese_name_dict.txt', 'r'):
        kanji, hiragana = line[:-1].split('\t')
        memcache.add(key=kanji, value=hiragana)
