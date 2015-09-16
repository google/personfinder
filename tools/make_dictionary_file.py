"""
Makes dictionary file from mozc
(https://github.com/google/mozc/tree/master/src/data/dictionary_oss)
"""

def make_jp_name_dictionary(input_file_names):
    """
    Makes japanese name dictionary.

    Args:
        input_file_names: a list of file names

    Out put format:
        kanji '\t' yomigana(hiragana) '\n'
        kanji '\t' yomigana(hiragana) '\n' ...
    """

    yomigana_list = []
    for input_file_name in input_file_names:

        with open(input_file_name, 'r') as f:
            for line in f:
                line = line.rstrip()
                splited_line = line.split('\t')
                left = int(splited_line[1])
                right = int(splited_line[2])

                if ((left == 1845 and right == 1845) or
                    (left == 1846 and right == 1846)):
                    yomigana = splited_line[0]
                    kanji = splited_line[4]
                    yomigana_list.append(kanji + '\t' + yomigana + '\n')

    with open('japanese_name_dict.txt', 'w') as f:
        f.writelines(yomigana_list)


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
        with open(input_file_name, 'r') as f:
            for line in f:
                line = line.rstrip()
                splited_line = line.split('\t')
                left = int(splited_line[1])
                right = int(splited_line[2])
                if ((left == 1847 and right == 1847) or
                    (left == 1848 and right == 1848) or
                    (left == 1849 and right == 1849) or
                    (left == 1850 and right == 1850)):
                    yomigana = splited_line[0]
                    kanji = splited_line[4]
                    yomigana_list.append(kanji + '\t' + yomigana + '\n')

    with open('jp_location_dict.txt', 'w') as f:
        f.writelines(yomigana_list)
