#!/usr/bin/python2.7
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
of the words in the given and family names on the record.  For example, a
record with the fields:
    given_name: ABC 123
    family_name: DEF 456

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
from google.appengine.api import search
import unicodedata
import logging
import model
import re
import jautils

INDEX_NAME = 'personal_information'

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

    # Add alternate names to the index tokens.  We choose not to index prefixes
    # of alternate names so that we can keep the index size small.
    # TODI(ryok): This strategy works well for Japanese, but how about other
    # languages?
    names_prefixes |= get_alternate_name_tokens(entity)

    # Put a cap on the number of tokens, just as a precaution.
    MAX_TOKENS = 100
    entity.names_prefixes = list(names_prefixes)[:MAX_TOKENS]
    if len(names_prefixes) > MAX_TOKENS:
        logging.debug('MAX_TOKENS exceeded for %s' %
                      ' '.join(list(names_prefixes)))


def get_alternate_name_tokens(person):
    """Returns alternate name tokens and their variations."""
    tokens = set(TextQuery(person.alternate_names).query_words)
    # This is no-op for non-Japanese.
    tokens |= set(jautils.get_additional_tokens(tokens))
    return tokens


class CmpResults():
    def __init__(self, query):
        self.query = query
        self.query_words_set = set(query.words)

    def __call__(self, p1, p2):
        if ((p1.primary_full_name and
             p1.primary_full_name == p2.primary_full_name) or
            ((p1.given_name or p1.family_name) and
             p1.given_name == p2.given_name and
             p1.family_name == p2.family_name)):
            return 0
        self.set_ranking_attr(p1)
        self.set_ranking_attr(p2)
        r1 = self.rank(p1)
        r2 = self.rank(p2)

        if r1 == r2:
            # if rank is the same sort by name so same names will be together
            return cmp(p1._normalized_full_name.normalized,
                       p2._normalized_full_name.normalized)
        else:
            return cmp(r2, r1)


    def set_ranking_attr(self, person):
        """Consider save these into to db"""
        if not hasattr(person, '_normalized_given_name'):
            person._normalized_given_name = TextQuery(person.given_name)
            person._normalized_family_name = TextQuery(person.family_name)
            person._normalized_full_name = TextQuery(person.full_name)
            person._name_words = set(person._normalized_full_name.words)
            person._alt_name_words = set(
                    TextQuery(person.alternate_names).words)

    # TODO(ryok): re-consider the ranking putting more weight on full_name (a
    # required field) instead of given name and family name pair (optional).
    def rank(self, person):
        # The normalized query words, in the order as entered.
        ordered_words = self.query.normalized.split()

        if (ordered_words ==
            person._normalized_given_name.words +
            person._normalized_family_name.words):
            # Matches a Latin name exactly (given name followed by surname).
            return 10

        if (re.match(ur'^[\u3400-\u9fff]$', person.family_name) and
            ordered_words in [
                [person.family_name + person.given_name],
                [person.family_name, person.given_name]
            ]):
            # Matches a CJK name exactly (surname followed by given name).
            return 10

        if (re.match(ur'^[\u3400-\u9fff]+$', person.family_name) and
            ordered_words in [
                [person.family_name + person.given_name],
                [person.family_name, person.given_name]
            ]):
            # Matches a CJK name exactly (surname followed by given name).
            # A multi-character surname is uncommon, so it is ranked a bit lower.
            return 9.5

        if (ordered_words ==
            person._normalized_family_name.words +
            person._normalized_given_name.words):
            # Matches a Latin name with given and family name switched.
            return 9

        if (re.match(ur'^[\u3400-\u9fff]$', person.given_name) and
            ordered_words in [
                    [person.given_name + person.family_name],
                    [person.given_name, person.family_name]
            ]):
            # Matches a CJK name with surname and given name switched.
            return 9

        if (re.match(ur'^[\u3400-\u9fff]+$', person.given_name) and
            ordered_words in [
                    [person.given_name + person.family_name],
                    [person.given_name, person.family_name]
            ]):
            # Matches a CJK name with surname and given name switched.
            # A multi-character surname is uncommon, so it's ranked a bit lower.
            return 8.5

        if person._name_words == self.query_words_set:
            # Matches all the words in the given and family name, out of order.
            return 8

        if self.query.normalized in [
            person._normalized_given_name.normalized,
            person._normalized_family_name.normalized,
        ]:
            # Matches the given name exactly or the family name exactly.
            return 7

        if person._name_words.issuperset(self.query_words_set):
            # All words in the query appear somewhere in the name.
            return 6

        # Count the number of words in the query that appear in the name and
        # also in the alternate names.
        matched_words = person._name_words.union(
            person._alt_name_words).intersection(self.query_words_set)
        return min(5, 1 + len(matched_words))


def rank_and_order(results, query, max_results):
    results.sort(CmpResults(query))
    return results[:max_results]


def sort_query_words(query_words):
    """Sort query_words so that the query filters created from query_words are
    more effective and consistent when truncated due to NeedIndexError, and
    return the sorted list."""
    #   (1) Sort them lexicographically so that we return consistent search
    #       results for query 'AA BB CC DD' and 'DD AA BB CC' even when filters
    #       are truncated.
    sorted_query_words = sorted(query_words)
    #   (2) Sort them according to popularity so that less popular query words,
    #       which are usually more effective filters, come first.
    sorted_query_words = jautils.sorted_by_popularity(sorted_query_words)
    #   (3) Sort them according to the lengths so that longer query words,
    #       which are usually more effective filters, come first.
    return sorted(sorted_query_words, key=len, reverse=True)

def create_and_query(query):
    return re.sub(r' ', ' AND ', query)

def create_or_query(query):
    name_params = ['given_name', 'family_name', 'full_name', 'alternate_names']
    or_query = re.sub(r' ', ' OR ', query)
    search_name_query = ''
    for param in name_params:
        search_name_query += param + ': ' + or_query + ' OR '
    return search_name_query[:-4]

def create_query(query):
    search_name_location_query = create_and_query(query)
    search_name_query = create_or_query(query)
    return search_name_location_query + ' AND (' + search_name_query + ')'

def search_with_index(repo, query_obj, max_results):
    results = []
    query = create_query(query_obj)
    logging.info(query)
    try:
        index = search.Index(name=INDEX_NAME)
        options = search.QueryOptions(
            limit=max_results,
            returned_fields=['record_id'])
        results_index = index.search(search.Query(
            query_string=query, options=options))
        record_ids = []
        for document in results_index:
            record_ids.append(document.fields[0].value)
        for id in record_ids:
            results.append(model.Person.get_by_key_name(repo + ':' + id))
    except search.Error:
        logging.exception('Search exception')
    return results

def search_debug(repo, query_obj, max_results):
    # As there are limits on the number of filters that we can apply and the
    # number of entries we can fetch at once, the order of query words could
    # potentially matter.  In particular, this is the case for most Japanese
    # names, many of which consist of 4 to 6 Chinese characters, each
    # coresponding to an additional filter.
    query_words = sort_query_words(query_obj.query_words)
    logging.debug('query_words: %r' % query_words)

    # First try the query with all the filters, and then keep backing off
    # if we get NeedIndexError.
    fetch_limit = 400
    fetched = []
    filters_to_try = len(query_words)
    while filters_to_try:
        query = model.Person.all_in_repo(repo)
        for word in query_words[:filters_to_try]:
            query.filter('names_prefixes =', word)
        try:
            fetched = query.fetch(fetch_limit)
            logging.debug('query succeeded with %d filters' % filters_to_try)
            break
        except db.NeedIndexError:
            filters_to_try -= 1
            continue
    logging.debug('indexing.search fetched: %d' % len(fetched))

    # Now perform any filtering that App Engine was unable to do for us.
    matched = []
    for result in fetched:
        for word in query_words:
            if word not in result.names_prefixes:
                break
        else:
            matched.append(result)
    logging.debug('indexing.search matched: %d' % len(matched))

    if len(fetched) == fetch_limit and len(matched) < max_results:
        logging.debug('Warning: Fetch reached a limit of %d, but only %d '
                      'exact-matched the query (max_results = %d).' %
                      (fetch_limit, len(matched), max_results))

    # Now rank and order the results.
    return rank_and_order(matched, query_obj, max_results)

def create_document(**kwargs):
    return search.Document(
        fields = [
            search.TextField(name='record_id', value=kwargs['record_id']),
            search.TextField(
                name='repo', value=kwargs['repo']),
            search.TextField(
                name='given_name', value=kwargs['given_name']),
            search.TextField(
                name='family_name', value=kwargs['family_name']),
            search.TextField(
                name='full_name', value=kwargs['full_name']),
            search.TextField(
                name='alternate_names', value=kwargs['alternate_names']),
            search.TextField(
                name='home_street', value=kwargs['home_street']),
            search.TextField(
                name='home_city', value=kwargs['home_city']),
            search.TextField(
                name='home_state', value=kwargs['home_state']),
            search.TextField(
                name='home_postal_code', value=kwargs['home_postal_code']),
            search.TextField(
                name='home_neighborhood', value=kwargs['home_neighborhood']),
            search.TextField(
                name='home_country', value=kwargs['home_country'])
        ])

def create_index(**kwargs):
    try:
        index_name = search.Index(name=INDEX_NAME)
        index_name.put(create_document(**kwargs))
    except search.Error:
        logging.exception('Put failed')
