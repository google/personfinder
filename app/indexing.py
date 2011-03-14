#!/usr/bin/python2.5
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Support for approximate string prefix queries.

A hit is defined when the words entered in the query are all prefixes of one
of the words in the first and last names on the record.  For example, a
record with the fields:
    first_name: ABC 123
    last_name: DEF 456

will be retrieved by:
    "ABC 456"
    "45 ED"
    "123 ABC"
    "ABC 123 DEF"

but will not be retrieved by:
    "ABC 1234"
    "ABC 123 DEF 456 789"
"""

from text_query import TextQuery

from google.appengine.ext import db
import unicodedata
import logging
import model
import re


def update_index_properties(entity):
    """Finds and updates all prefix-related properties on the given entity."""
    # Using set to make sure I'm not adding the same string more than once.
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

    # Put a cap on the number of tokens, just as a precaution.
    MAX_TOKENS = 100
    entity.names_prefixes = list(names_prefixes)[:MAX_TOKENS]
    if len(names_prefixes) > MAX_TOKENS:
        logging.debug('MAX_TOKENS exceeded for %s' %
                      ' '.join(list(names_prefixes)))


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
            return cmp(r2, r1)

    
    def set_ranking_attr(self, person):
        """Consider save these into to db"""
        if not hasattr(person, '_normalized_first_name'):
            person._normalized_first_name = TextQuery(person.first_name)
            person._normalized_last_name = TextQuery(person.last_name)
            person._name_words = set(person._normalized_first_name.words +
                                     person._normalized_last_name.words)
            person._normalized_full_name = '%s %s' % (
                person._normalized_first_name.normalized, 
                person._normalized_last_name.normalized)

    def rank(self, person):
        # The normalized query words, in the order as entered.
        ordered_words = self.query.normalized.split()

        if (ordered_words ==
            person._normalized_first_name.words +
            person._normalized_last_name.words):
            # Matches a Latin name exactly (given name followed by surname).
            return 10

        if (re.match(ur'^[\u3400-\u9fff]$', person.last_name) and
            ordered_words in [
                [person.last_name + person.first_name],
                [person.last_name, person.first_name]
            ]):
            # Matches a CJK name exactly (surname followed by given name).
            return 10

        if (re.match(ur'^[\u3400-\u9fff]+$', person.last_name) and
            ordered_words in [
                [person.last_name + person.first_name],
                [person.last_name, person.first_name]
            ]):
            # Matches a CJK name exactly (surname followed by given name).
            # A multi-character surname is uncommon, so it is ranked a bit lower.
            return 9.5

        if (ordered_words ==
            person._normalized_last_name.words +
            person._normalized_first_name.words):
            # Matches a Latin name with first and last name switched.
            return 9

        if (re.match(ur'^[\u3400-\u9fff]$', person.first_name) and
            ordered_words in [
                    [person.first_name + person.last_name],
                    [person.first_name, person.last_name]
            ]):
            # Matches a CJK name with surname and given name switched.
            return 9

        if (re.match(ur'^[\u3400-\u9fff]+$', person.first_name) and
            ordered_words in [
                    [person.first_name + person.last_name],
                    [person.first_name, person.last_name]
            ]):
            # Matches a CJK name with surname and given name switched.
            # A multi-character surname is uncommon, so it's ranked a bit lower.
            return 8.5

        if person._name_words == self.query_words_set:
            # Matches all the words in the first and last name, out of order.
            return 8

        if self.query.normalized in [
            person._normalized_first_name.normalized,
            person._normalized_last_name.normalized,
        ]:
            # Matches the first name exactly or the last name exactly.
            return 7

        if person._name_words.issuperset(self.query_words_set):
            # All words in the query appear somewhere in the name.
            return 6

        # Count the number of words in the query that appear in the name.
        matched_words = person._name_words.intersection(self.query_words_set)
        return min(5, 1 + len(matched_words))


def rank_and_order(results, query, max_results):
    results.sort(CmpResults(query))
    return results[:max_results]


def search(subdomain, query_obj, max_results):
    query_words = list(reversed(sorted(query_obj.query_words, key=len)))
    logging.debug('query_words: %r' % query_words)

    # First try the query with all the filters, and then keep backing off
    # if we get NeedIndexError.
    filters_to_try = len(query_words)
    while filters_to_try:
        query = model.Person.all_in_subdomain(subdomain)
        for word in query_words[:filters_to_try]:
            query.filter('names_prefixes =', word)
        try:
            fetched = query.fetch(400)
            logging.debug('query succeeded with %d filters' % filters_to_try)
            break
        except db.NeedIndexError:
            filters_to_try -= 1
            continue
    logging.debug('fetched: %d' % len(fetched))

    # Now perform any filtering that App Engine was unable to do for us.
    matched = []
    for result in fetched:
        for word in query_words:
            if word not in result.names_prefixes:
                break
        else:
            matched.append(result)
    logging.debug('matched: %d' % len(matched))

    # Now rank and order the results.
    return rank_and_order(matched, query_obj, max_results)
