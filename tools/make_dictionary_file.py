"""
Makes dictionary file from mozc
(https://github.com/google/mozc/tree/master/src/data/dictionary_oss)
"""

def make_jp_name_dictionary(input_file_name, output_file_name):
    """
    Makes japanese name dictionary.

    Out put format:
        kanji '\t' yomigana(hiragana) '\n'
        kanji '\t' yomigana(hiragana) '\n' ...
    """
    yomigana_list = []
    with open(input_file_name, 'r') as f:
        for line in f:
            splited_line = line.split('\t')
            left = splited_line[1]
            right = splited_line[2]
            if ((left == 1845 and right == 1845) or
                (left == 1846 and right == 1846)):
                    yomigana = splited_line[0]
                    kanji = splited_line[4]
                    yomigana_list.append(kanji + '\t' + yomigana)

    with open(output_file_name, 'w') as f:
        for yomigana in yomigana_list:
            w.write(yomigana)


def make_jp_location_dictionary(input_file_name, output_file_name):
    """
    Makes japanese location dictionary.

    Out put format:
        kanji '\t' yomigana(hiragana) '\n'
        kanji '\t' yomigana(hiragana) '\n' ...
    """
    yomigana_list = []
    with open(input_file_name, 'r') as f:
        for line in f:
            splited_line = line.split('\t')
            left = splited_line[1]
            right = splited_line[2]
            if ((left == 1847 and right == 1847) or
                (left == 1848 and right == 1848) or
                (left == 1849 and right == 1849) or
                (left == 1850 and right == 1850)):
                    yomigana = splited_line[0]
                    kanji = splited_line[4]
                    yomigana_list.append(kanji + '\t' + yomigana)

    with open(output_file_name, 'w') as f:
        for yomigana in yomigana_list:
            w.write(yomigana)
