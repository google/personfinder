# coding: utf-8
# Copyright 2015 Google Inc.
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

import logging
import re

from google.appengine.api import search as appengine_search

import model
import script_variant

# The index name for full text search.
# This index contains person name and location.
PERSON_LOCATION_FULL_TEXT_INDEX_NAME = 'person_location_information'

ROMANIZE_METHODS = [script_variant.romanize_word_by_unidecode,
                    script_variant.romanize_japanese_word,
                    script_variant.romanize_chinese_name]

# This is for ranking (person name match higher than location)
REPEAT_COUNT_FOR_RANK = 5


def create_sort_expressions():
    """
    Creates SortExpression's for ranking.
    Returns:
        array of SortExpression
    """
    return [appengine_search.SortExpression(
        expression='_score',
        direction=appengine_search.SortExpression.DESCENDING,
        default_value=0.0
    )]


def enclose_in_parenthesis(query_txt):
    """
    Encloses each word in query_txt in double quotes.
    Args:
        query_txt: Search query
    Returns:
        '(query_word1) AND (query_word2) ...'
    """
    query_words = query_txt.split(',')
    return '(' + ') AND ('.join([word for word in query_words if word]) + ')'


def enclose_in_double_quotes(query_txt):
    """
    Encloses each word in query_txt in double quotes.
    Args:
        query_txt: Search query
    Returns:
        '"query_word1"'
    """
    return '"' + query_txt + '"'


def create_non_romanized_query(query_txt):
    """
    Creates non romanized query txt.
    Args:
        query_txt: Search query
    Returns:
        '"query_word1" "query_word2" ...'
    """
    query_words = query_txt.split(' ')
    return ' '.join(enclose_in_double_quotes(word) for word in query_words)


def create_romanized_query_txt(query_txt):
    """
    Applies romanization to each word in query_txt.
    Args:
        query_txt: Search query
    Returns:
        script varianted query_txt
    """
    query_words = query_txt.split(' ')
    query_list = []
    for word in query_words:
        romanized_word_list = script_variant.romanize_search_query(word)
        romanized_word = ' OR '.join(enclose_in_double_quotes(word)
                                     for word in romanized_word_list)
        query_list.append(romanized_word)
    romanized_query = ','.join([word for word in query_list])
    return enclose_in_parenthesis(romanized_query)


def is_query_match(query_txt, romanized_values):
    """
    Checks if a query matches a record
    It should be called in get_person_ids_from_results method.
    Args:
        query_txt: Search query
        romanized_values: field values
    Returns:
        Boolean
    """
    # empty matches everything
    if not query_txt:
        return True

    romanized_query_list = (script_variant.romanize_search_query(query_txt))

    # A query matches a record if all search_terms appear in the record
    for search_terms in romanized_query_list:
        words = search_terms.split(" ")
        for word_index, word in enumerate(words):
            if not re.search(word, " ".join(romanized_values), re.I):
                break
            if word_index == len(words) - 1:
                return True
    return False


def get_person_ids_from_results(
    query_dict, results_list, romanized_name_fields, romanized_location_fields):
    """
    Returns person record_id of persons
    whose name contain in romanized_name_query and
    location contain in romanized_location_query.
    We use is_query_match to check if romanized_querys match
    at least a part of person name and location.
    To protect users' privacy, we should not return records
    which match location only.
    It also removes dups.
    (i.e., If results_list contains multiple results with the same index_results,
    it returns just one of them)
    """
    name_query_txt = query_dict.get('name', '')
    location_query_txt = query_dict.get('location', '')

    index_results = []
    added_results = set()
    for results in results_list:
        for document in results:
            fields = {field.name: field.value for field in
                          document.fields}

            record_id = fields['record_id']

            # use set to faster the speed.
            # average time complexity: set-O(1) list-O(n)
            if record_id in added_results:
                continue

            romanized_names = [value for name, value in fields.items()
                                        if name in romanized_name_fields]
            romanized_locations = [value for name, value in fields.items()
                                        if name in romanized_location_fields]

            if (is_query_match(name_query_txt, romanized_names) and
                is_query_match(location_query_txt, romanized_locations)):
                index_results.append(record_id)
                added_results.add(record_id)
    return index_results


def search(repo, query_dict, max_results):
    """
    Searches person with index.
    Query_txt must match at least a part of person name.
    (It's not allowed to search only by location.)
    Args:
        repo: The name of repository
        query_dict: Search query dict, {name: name_query, location: location_query}
        max_results: The max number of results you want.(Maximum: 1000)
    Returns:
        - Array of <model.Person> in datastore
        - []: If query_txt doesn't contain a part of person name
    Raises:
        search.Error: An error occurred when the index name is unknown
                      or the query has syntax error.
    """
    name = query_dict.get('name', '')
    location = query_dict.get('location', '')
    if not name:
        return []

    # Order does not matter
    query_list= [name, location]
    query_list_cleaned = query_list if location else [name]

    # Remove double quotes so that we can safely apply
    # enclose_in_double_quotes().
    for index, query in enumerate(query_list_cleaned):
        query_list_cleaned[index] = re.sub('"', '', query)

    romanized_query_list = [create_romanized_query_txt(query)
                            for query in query_list_cleaned]
    non_romanized_query_list = [create_non_romanized_query(query)
                                for query in query_list_cleaned]

    # search and sort options
    person_location_index = appengine_search.Index(
        name=PERSON_LOCATION_FULL_TEXT_INDEX_NAME)
    expressions = create_sort_expressions()
    sort_opt = appengine_search.SortOptions(
        expressions=expressions, match_scorer=appengine_search.MatchScorer())


    # Define the fields need to be returned per romanzie method
    returned_name_fields = [u'names_romanized_by_' + method.__name__
                            for method in ROMANIZE_METHODS]

    returned_location_fields = [u'full_location_romanized_by_' + method.__name__
                            for method in ROMANIZE_METHODS]

    returned_fields = (returned_name_fields +
                       returned_location_fields + ['record_id'])

    options = appengine_search.QueryOptions(
        limit=max_results,
        sort_options=sort_opt,
        returned_fields=returned_fields)

    # enclose_in_double_quotes is used for avoiding query_txt
    # which specifies index field name, contains special symbol, ...
    # (e.g., "repo: repository_name", "test: test", "test AND test").
    and_query = ' AND '.join(
        romanized_query_list) + ' AND (repo: ' + repo + ')'
    person_location_index_results = person_location_index.search(
        appengine_search.Query(
            query_string=and_query, options=options))

    # To rank exact matches higher than
    # non-exact matches with the same romanization.
    non_romanized_and_query = (' AND '.join(non_romanized_query_list)
                                + ' AND (repo: ' + repo + ')')
    non_romanized_person_location_index_results = (
        person_location_index.search(appengine_search.Query(
            query_string=non_romanized_and_query, options=options)))

    results_list = [non_romanized_person_location_index_results,
                    person_location_index_results]

    index_results = get_person_ids_from_results(query_dict,
        results_list, returned_name_fields, returned_location_fields)

    results = []
    for record_id in index_results:
        result = model.Person.get(repo, record_id, filter_expired=True)
        if result:
            results.append(result)
    return results


def create_fields_for_rank(field_name, values):
    """
    Creates fields for ranking. (person name match > location match)
    MatchScorer class(assigns score) doesn't support to assign
    a score based on term frequency in a field.
    So we add 5 fields for each name params.
    Args:
        field_name: field name
        values: field values
    Returns:
        array of appengine_search.TextField(name=field_name, value=value)
           (length: REPEAT_COUNT_FOR_RANK)
    """
    if not values:
        return []

    fields = []
    for index, value in enumerate(values):
        for x in xrange(REPEAT_COUNT_FOR_RANK):
            fields.append(
                appengine_search.TextField(name='%s_%d_for_rank_%d' % (
                    field_name, index, x),
                                           value=value))
    return fields


def create_full_name_list_without_space(given_names, family_names):
    """
    Creates full name list without white space.
    Returns:
        ['given_name + family_name',
         'family_name + given_name',...]
    """
    full_names = []
    for given_name in given_names:
        for family_name in family_names:
            full_names.append(given_name + family_name)
            full_names.append(family_name + given_name)
    return full_names


def create_full_name_without_space_fields(romanize_method, given_name,
                                          family_name):
    """
    Creates fields with the full name without white spaces.
    Returns:
        fullname fields, romanized_name_list: (for check)
    """
    fields = []
    romanized_name_list = []
    romanized_given_names = romanize_method(given_name)
    romanized_family_names = romanize_method(family_name)
    romanize_method_name = romanize_method.__name__
    full_names = create_full_name_list_without_space(
        romanized_given_names, romanized_family_names)
    for index, full_name in enumerate(full_names):
        fields.append(appengine_search.TextField(
            name='no_space_full_name_romanized_by_%s_%d' % (
                romanize_method_name, index),
            value=full_name))
        romanized_name_list.append(full_name)
    return fields, romanized_name_list


def create_romanized_name_fields(romanize_method, **kwargs):
    """
    Creates romanized name fields (romanized by romanize_method)
    for full text search.
    """
    fields = []
    romanized_names_list = []
    romanize_method_name = romanize_method.__name__

    for field_name, field_value in kwargs.iteritems():
        romanized_names = romanize_method(field_value)
        for index, romanized_name in enumerate(romanized_names):
            fields.extend(create_fields_for_rank('%s_romanized_by_%s_%d' %
                                                 (field_name,
                                                  romanize_method_name,
                                                  index),
                                                 romanized_name))
        romanized_names_list.extend(romanized_names)

    full_name_fields, romanized_full_names = (
        create_full_name_without_space_fields(
            romanize_method, kwargs['given_name'], kwargs['family_name']))
    fields.extend(full_name_fields)
    romanized_names_list.extend(romanized_full_names)

    names = ':'.join([name for name in romanized_names_list if name])
    fields.append(
        appengine_search.TextField(
            name='names_romanized_by_' + romanize_method_name,
            value=names))

    return fields


def create_romanized_location_fields(romanize_method, **kwargs):
    """
    Creates romanized location fields (romanized by romanize_method)
    for full text search.
    """
    fields = []
    romanize_method_name = romanize_method.__name__
    for field in kwargs:
        romanized_locations = romanize_method(kwargs[field])
        for index, romanized_location in enumerate(romanized_locations):
            fields.append(
                appengine_search.TextField(
                    name='%s_romanized_by_%s_%d' % (
                        field, romanize_method_name, index),
                    value=romanized_location)
            )
    full_romanized_location = ':'.join(
        location.value for location in fields if location.value)
    fields.append(appengine_search.TextField(
        name='full_location_romanized_by_' + romanize_method_name,
        value=full_romanized_location))
    return fields


def create_non_romanized_fields(**kwargs):
    """
    Creates non romanized fields to rank exact matches higher than
    non-exact matches with the same romanization.
    e.g.,
    if there are records record1:[name=菊地真], record2:[name=菊地眞],
    get results(1st: 菊地真、2nd: 菊地眞) when search by "菊地 真"
    """
    fields = []
    for field_name in kwargs:
        fields.append(appengine_search.TextField(
            name=field_name, value=kwargs[field_name]))
    return fields


def create_document(person):
    """
    Creates document for full text search.
    It should be called in add_record_to_index method.
    """
    fields = []

    # Add repo and record_id to fields
    repo = person.repo
    record_id = person.record_id
    doc_id = repo + ':' + record_id
    fields.append(appengine_search.TextField(name='repo', value=repo))
    fields.append(
        appengine_search.TextField(name='record_id', value=record_id))

    fields.extend(create_non_romanized_fields(
        given_name=person.given_name,
        family_name=person.family_name,
        full_name=person.full_name,
        alternate_names=person.alternate_names,
        home_city=person.home_city,
        home_state=person.home_state,
        home_postal_code=person.home_postal_code,
        home_neighborhood=person.home_neighborhood,
        home_country=person.home_country))

    # Applies two methods because kanji is used in Chinese and Japanese,
    # and romanizing in chinese and japanese is different.

    for romanize_method in ROMANIZE_METHODS:
        fields.extend(create_romanized_name_fields(
            romanize_method,
            given_name=person.given_name,
            family_name=person.family_name,
            full_name=person.full_name,
            alternate_names=person.alternate_names))
        fields.extend(create_romanized_location_fields(
            romanize_method,
            home_city=person.home_city,
            home_state=person.home_state,
            home_postal_code=person.home_postal_code,
            home_neighborhood=person.home_neighborhood,
            home_country=person.home_country))

    return appengine_search.Document(doc_id=doc_id, fields=fields)


def add_record_to_index(person):
    """
    Adds person record to index.
    Raises:
        search.Error: An error occurred when the document could not be indexed
                      or the query has a syntax error.
    """
    person_location_index = appengine_search.Index(
        name=PERSON_LOCATION_FULL_TEXT_INDEX_NAME)
    person_location_index.put(create_document(person))


def delete_record_from_index(person):
    """
    Deletes person record from index.
    Args:
        person: Person who should be removed
    Raises:
        search.Error: An error occurred when the index name is unknown
                      or the query has a syntax error.
    """
    doc_id = person.repo + ':' + person.record_id
    person_location_index = appengine_search.Index(
        name=PERSON_LOCATION_FULL_TEXT_INDEX_NAME)
    person_location_index.delete(doc_id)
