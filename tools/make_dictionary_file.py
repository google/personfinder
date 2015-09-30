"""
Makes dictionary file from mozc
(https://github.com/google/mozc/tree/master/src/data/dictionary_oss)
"""

def check_number(id1, id2, numbers):
    """
    checks id1 == id2 == numbers
    """
    if id1 != id2:
        return False

    if id1 in numbers and id2 in numbers:
        return id1 == id2

    return False


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
        input_file = open(input_file_name, 'r')
        for line in input_file:
            line = line.rstrip()
            splited_line = line.split('\t')
            id1 = int(splited_line[1])
            id2 = int(splited_line[2])
            if (check_number(id1, id2, numbers)):
                yomigana = splited_line[0]
                kanji = splited_line[4]
                yomigana_list.append(kanji + '\t' + yomigana + '\n')

    output_file = open(output_file_name, 'w')
    output_file.writelines(yomigana_list)


def make_jp_name_dictionary(input_file_names):
    """
    Makes japanese name dictionary.
    """
    # 1845: id for given name in mozc dictionary
    # 1846: id for family name in mozc dictionary
    # if we want to get given name, we need to get results (id1 == id2 == 1845)
    numbers = [1845, 1846]
    make_dictionary(input_file_names, 'japanese_name_dict.txt', numbers)


def make_jp_location_dictionary(input_file_names):
    """
    Makes japanese location dictionary.
    """
    # 1847 ~ 1850: ids for location in mozc dictionary
    # if we want to get location, we need to get results
    # (id1 == id2 == 1847 ~ 1850)
    numbers = [1847, 1848, 1849, 1850]
    make_dictionary(input_file_names, 'jp_location_dict.txt', numbers)
