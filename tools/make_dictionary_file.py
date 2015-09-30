"""
Makes dictionary file from mozc
(https://github.com/google/mozc/tree/master/src/data/dictionary_oss)
"""

def check_number(id1, id2, numbers):
    """
    checks id1 == id2 == numbers
    """
    for number in numbers:
        if id1 != id2:
            return False
    return True


def make_jp_name_dictionary(input_file_names):
    """
    Makes japanese name dictionary.

    Args:
        input_file_names: a list of file names

    Output format:
        kanji '\t' yomigana(hiragana) '\n'
        kanji '\t' yomigana(hiragana) '\n' ...
    """

    yomigana_list = []
    for input_file_name in input_file_names:
        input_file = open(input_file_name, 'r')
        for line in input_file:
            line = line.rstrip()
            splited_line = line.split('\t')
            id1 = int(splited_line[1])
            id2 = int(splited_line[2])
            # 1845: id for given name
            # 1846: id for family name
            numbers = [1845, 1846]
            if (check_number(id1, id2, numbers)):
                yomigana = splited_line[0]
                kanji = splited_line[4]
                yomigana_list.append(kanji + '\t' + yomigana + '\n')

    output_file = open('japanese_name_dict.txt', 'w')
    output_file.writelines(yomigana_list)


def make_jp_location_dictionary(input_file_names):
    """
    Makes japanese location dictionary.

    Args:
        input_file_names: a list of input file names
    Out put format:
        kanji '\t' yomigana(hiragana) '\n'
        kanji '\t' yomigana(hiragana) '\n' ...
    """
    yomigana_list = []
    for input_file_name in input_file_names:
        input_file = open(input_file_name, 'r')
        for line in f:
            line = line.rstrip()
            splited_line = line.split('\t')
            id1 = int(splited_line[1])
            id2 = int(splited_line[2])
            # 1847 ~ 1850: ids for location
            numbers = [1847, 1848, 1849, 1850]
            if (check_number(id1, id2, numbers)):
                yomigana = splited_line[0]
                kanji = splited_line[4]
                yomigana_list.append(kanji + '\t' + yomigana + '\n')

    output_file = open('jp_location_dict.txt', 'w')
    output_file.writelines(yomigana_list)
