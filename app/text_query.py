#!/usr/bin/python2.5
#
# Copyright 2010 Google Inc. All Rights Reserved.

__author__ = 'eyalf@google.com (Eyal Fink)'

import unicodedata
import logging
import re


class TextQuery():
  """This class encapsulate the processing we are doing both for indexed strings
  like first_name and last_name and for a query string.
  Currently the processing includes normalization (see doc below) and splitting 
  to words.
  Future stuff we might add: indexing of phone numbers, extracting of locations
  for geo-search, synonym support"""
  def __init__(self, query):
    self.query = query
    self.normalized = normalize(query) 

    # Split out each CJK ideograph as its own word.
    # The main CJK ideograph range is from U+4E00 to U+9FFF.
    # CJK Extension A is from U+3400 to U+4DFF.
    cjk_separated = re.sub(ur'([\u3400-\u9fff])', r' \1 ', self.normalized)

    # Separate the query into words.
    self.words = cjk_separated.split()

    # query_words is redundant now but I'm leaving it since I don't want to
    # change the signature of TextQuery yet
    self.query_words = self.words


def normalize(string):
  """Normalize a string to all uppercase, remove accents, delete apostrophes,
  and replace non-letters with spaces."""
  string = unicode(string or '').strip().upper()
  letters = []
  """TODO(eyalf): we need to have a better list of types we are keeping
    one that will work for non latin languages"""
  for ch in unicodedata.normalize('NFD', string):
    category = unicodedata.category(ch)
    if category.startswith('L'):
      letters.append(ch)
    elif category != 'Mn' and ch != "'":  # Treat O'Hearn as OHEARN
      letters.append(' ')
  return ''.join(letters)
