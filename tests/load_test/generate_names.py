# Copyright 2016 Google Inc.
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

"""A script to generate names_in_db.txt and names_not_in_db.txt, name lists
used in load_test.py.

Usage:
  $ python tests/load_test/generate_names.py

It generates mixture of English and Japanese names. Japanese names are added
because Person Finder performs some Japanese specific handling in search.

English names are generated using random 3-10 Latin alphabet characters. This
is because it should not matter whether the generated names are natural or not.

Japanese names are generated using the name dictionary we use to get sound of
names. This is because we believe that most of the names are covered by the
dictionary. (But we may want to consider adding names not in the dictionary
too.)

It picks up two names in the dictionary and joins them to generate a full name,
without distinguishing first/last/location names. So generated names are
often unnatural, but it doesn't matter much in terms of performance, we
believe.
"""

import random


NUM_NAMES_PER_LANGUAGE = 1000000
ENGLISH_NAME_MIN_LENGTH = 3
ENGLISH_NAME_MAX_LENGTH = 10
LATIN_ALPHABETS = 'abcdefghijklmnopqrstuvwxyz'


def generate_english_name_component():
    name_len = random.randint(ENGLISH_NAME_MIN_LENGTH, ENGLISH_NAME_MAX_LENGTH)
    return ''.join(random.choice(LATIN_ALPHABETS) for _ in xrange(name_len))


if __name__ == '__main__':
    # To get reproducible output.
    random.seed(0)
    
    with open('app/japanese_name_location_dict.txt') as f:
        ja_words = [line.rstrip('\n').split('\t')[0] for line in f]
    ja_output_names = set()
    while len(ja_output_names) < NUM_NAMES_PER_LANGUAGE:
        ja_output_names.add(
            '%s %s' % (random.choice(ja_words), random.choice(ja_words)))

    en_output_names = set()
    while len(en_output_names) < NUM_NAMES_PER_LANGUAGE:
        en_output_names.add('%s %s' % (
            generate_english_name_component(),
            generate_english_name_component()))

    output_names = ja_output_names | en_output_names
    shuffled_names = random.sample(output_names, len(output_names))

    with open('tests/load_test/names_in_db.txt', 'w') as f:
        for name in shuffled_names[:len(shuffled_names) / 2]:
            f.write(name + '\n')
    with open('tests/load_test/names_not_in_db.txt', 'w') as f:
        for name in shuffled_names[len(shuffled_names) / 2:]:
            f.write(name + '\n')
