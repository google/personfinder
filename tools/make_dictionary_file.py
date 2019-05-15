# Copyright 2019 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Makes dictionary file from mozc files.

How to use this tool:
  $ git clone https://github.com/google/mozc.git
  $ tools/make_dictionary_file.py mozc/src/data/dictionary_oss/dictionary*.txt > app/japanese_name_location_dict.txt
"""

import sys

def make_dictionary(input_file_names, output_file_name, numbers):
    """Makes dictionary and writes it to output_file_name.

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
                split_line = line.split('\t')
                id1 = int(split_line[1])
                id2 = int(split_line[2])
                # e.g. (id1 == id2 == 1845) means "given name"
                if id1 in numbers and id1 == id2:
                    yomigana = split_line[0]
                    kanji = split_line[4]
                    yomigana_list.append(kanji + '\t' + yomigana + '\n')

    with open(output_file_name, 'w') as output_file:
        output_file.writelines(yomigana_list)


def make_jp_name_location_dictionary(input_file_names):
    """Makes japanese name and location dictionary."""
    # 1845: id for given names in mozc dictionary
    # 1846: id for family names in mozc dictionary
    # 1847 ~ 1850: ids for location names in mozc dictionary
    numbers = [1845, 1846, 1847, 1848, 1849, 1850]
    make_dictionary(input_file_names, 'app/japanese_name_location_dict.txt', numbers)


def main():
    dictionaries = sys.argv[1:]
    make_jp_name_location_dictionary(dictionaries)


if __name__ == '__main__':
    main()
