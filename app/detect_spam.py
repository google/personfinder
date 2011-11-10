#!/usr/bin/python2.5
# Copyright 2011 Google Inc.
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

"""Handler for spam note detection, store bad word list and provide
   utilities to evaluate the quality of notes."""

__author__ = 'shaomei@google.com (Shaomei Wu)'

import unicodedata
import logging
import re
import jautils

def normalize(string):
    """Normalize a string to all lowercase and remove accents. """
    string = unicode(string or '').strip().lower()
    # Normalize unicode to normal form D (NDF) - canonical decomposition.
    # Translate each character into its decomposed form (accents removed).
    string = unicodedata.normalize('NFD', string)
    return string


class SpamDetector():
    bad_words_set = set()
    def __init__(self, badwords):
        if badwords == '' or badwords == None:
            return

        # Input bad words are seperated by comma.
        for word in re.split(',\s*', badwords):
            # Normalized the bad word and add it to the list.
            normalized_word = normalize(word)
            self.bad_words_set.add(normalized_word)

    def estimate_spam_score(self, text):
        """Estimate the probability of the input text being spam.
        Returns:
           a float score between [0,1], or None if text is empty 
           after normalization.
        """
        # Normalize text
        normalized_text = normalize(text)

        # Tokenize the text into words. Currently we keep hypen and 
        # apostrophe in the words but filter all the other punctuation marks.
        # TODO(shaomei): better ways to tokenize CJK text.
        # Split out each CJK ideograph as its own word probably
        # is not he best way of tokenization. We can do bigram in 
        # the future.
        words = re.findall("\w+-\w+|[\w']+", normalized_text)

        # Look for bad word in the text by string match.
        bad_words_matched = self.bad_words_set.intersection( set(words) )
            
        # Simple way to calculate spam score for now.
        if len(words) == 0:
            logging.debug('input text contains no words.')
            return None
        else:
            spam_score = float(len(bad_words_matched))/float(len(words))
            return spam_score
