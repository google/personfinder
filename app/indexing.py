#!/usr/bin/python2.5
# Copyright 2010 Google Inc.
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

"""Support for approximate string prefix queries.

A hit is defined when the words entered in the query are all prefixes of one of
the words in the first and last names on the record
e.g.

a record with
first_name: ABC 123
last_name: DEF 456

will be retrieved by
"ABC 456"
"45 ED"
"123 ABC"
"ABC 123 DEF"

will not be retrieved by
"ABC 1234"
"ABC 123 DEF 456 789"
"""

from text_query import TextQuery

from google.appengine.ext import db
import unicodedata
import logging

def update_index_properties(entity):
  """Finds and updates all prefix-related properties on the given entity."""
  """Using the set to make sure I'm not adding the same string more than once"""
  names_prefixes = set()
  for property in entity._fields_to_index_properties:
    
    for value in TextQuery(getattr(entity, property)).query_words:
      if property in entity._fields_to_index_by_prefix_properties:
        for n in xrange(1,len(value)+1):
          pref = value[:n]
          if pref not in names_prefixes:
            names_prefixes.add(pref)
      else:
        if value not in names_prefixes:
          names_prefixes.add(value)

  """put a cap on the number of tokens just as a precaution """
  MAX_TOKENS = 100
  entity.names_prefixes = list(names_prefixes)[:MAX_TOKENS]
  if len(names_prefixes) > MAX_TOKENS:
    logging.debug('MAX_TOKENS exceeded for %s' %
                  (' '.join(list(names_prefixes))))

class CmpResults():
  def __init__(self, query):
    self.query = query
    self.query_words_set = set(query.words)

  def __call__(self, p1, p2):
    if p1.first_name == p2.first_name and p1.last_name == p2.last_name:
      return 0 
    self.set_ranking_attr(p1)
    self.set_ranking_attr(p2)
    r1 = self.rank(p1)
    r2 = self.rank(p2)
    
    if r1 == r2:
      # if rank is the same sort by name so same names will be together
      return cmp(p1._normalized_full_name, p2._normalized_full_name)
    else:
      return r2 - r1

  
  def set_ranking_attr(self, person):
    """Consider save these into to db"""
    if not hasattr(person, '_normalized_first_name'):
      person._normalized_first_name = TextQuery(person.first_name)
      person._normalized_last_name = TextQuery(person.last_name)
      person._name_words = set(person._normalized_first_name.words +
                               person._normalized_last_name.words)
      person._normalized_full_name = '%s %s'%(person._normalized_first_name.normalized, 
                                              person._normalized_last_name.normalized)

  def rank(self, person):
    if '%s %s' % (person.first_name, person.last_name) == self.query.query:
      return 10
    if '%s %s' % (person.last_name, person.first_name) == self.query.query:
      return 9
    if (person.first_name == self.query.query or
       person.last_name == self.query.query):
      return 8

    if (person._name_words == self.query_words_set):
      return 7

    if (person._name_words.issuperset(self.query_words_set)):
      return 6
    
    return min(5,
               1 + len(person._name_words.intersection(self.query_words_set)))

def rank_and_order(results, query, max_results):
  results.sort(CmpResults(query))
  return results[:max_results]


def search(model_class, query_obj, max_results):
  results_to_fetch = min(max_results * 3, 300)
  query = model_class.all()
  query_words = query_obj.query_words

  logging.debug("query_words: %s" % query_words)
  if len(query_words) == 0:
    return [];
  for word in reversed(sorted(query_words, key=len)):
    query.filter('names_prefixes = ', word);

  res = rank_and_order(query.fetch(results_to_fetch), query_obj, max_results);
  logging.info('n results=%d' % len(res))
  return list(res)
