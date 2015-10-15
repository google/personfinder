#!/usr/bin/python2.7
"""
Makes dictionary file from mozc
(dictionary*.txt in https://github.com/google/mozc/tree/master/src/data/dictionary_oss/)

command line example: tools/make_dictionary_file.py dictionary*.txt

The path to the output file: app/japanese_name_location_dict.txt
"""
import sys

def check_number(id1, id2, numbers):
    """
    checks id1 == id2 (id1 and id2 are in numbers)
    """
    return id1 in numbers and id1 == id2


def make_dictionary(input_file_names, output_file_name, numbers):
    """
    Makes dictionary.

    Args:
        input_file_names: a list of file names

    Output format:
        kanji '\t' yomigana(hiragana) '\n'
        kanji '\t' yomigana(hiragana) '\n' ...
    """
    yomigana_list = []
    for input_file_name in input_file_names:
        with open(input_file_name, 'r') as input_file:
            for line in input_file:
                line = line.rstrip()
                splited_line = line.split('\t')
                id1 = int(splited_line[1])
                id2 = int(splited_line[2])
                if (check_number(id1, id2, numbers)):
                    yomigana = splited_line[0]
                    kanji = splited_line[4]
                    yomigana_list.append(kanji + '\t' + yomigana + '\n')

    with open(output_file_name, 'w') as output_file:
        output_file.writelines(yomigana_list)


def make_jp_name_location_dictionary(input_file_names):
    """
    Makes japanese name and location dictionary.
    """
    # 1845: id for given name in mozc dictionary
    # 1846: id for family name in mozc dictionary
    # 1847 ~ 1850: ids for location in mozc dictionary
    # if we want to get given name, we need to get results (id1 == id2 == 1845)
    numbers = [1845, 1846, 1847, 1848, 1849, 1850]
    make_dictionary(input_file_names, 'app/japanese_name_location_dict.txt', numbers)


def main():
    dictionaries = sys.argv[1:]
    make_jp_name_location_dictionary(dictionaries)


if __name__ == '__main__':
    main()
