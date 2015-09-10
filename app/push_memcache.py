# coding: utf-8

from google.appengine.api import memcache

def push_data_in_memcache():

    def get_dict_from_name_dict_file(file_name):
        dict = {}
        for line in open(file_name, 'r'):
            kanji, hiragana = line[:-1].split('\t')
            dict[kanji.decode('utf-8')] = hiragana.decode('utf-8')
        return dict

    dict1 = get_dict_from_name_dict_file('name_dict1.txt')
    dict2 = get_dict_from_name_dict_file('name_dict2.txt')

    memcache.add(key='dict1', value=dict1)
    memcache.add(key='dict2', value=dict2)
