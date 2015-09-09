#!/usr/bin/python2.7
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

# The index name for full text search.
# This index contains person name and location.
PERSON_LOCATION_FULL_TEXT_INDEX_NAME = 'person_location_information'

def make_or_regexp(query_txt):
    """
    Creates compiled regular expression for OR search.
    Args:
        query_txt: Search query

    Returns:
        query_word | query_word | ...
    """
    query_words = query_txt.split(' ')
    regexp = '|'.join([re.escape(word) for word in query_words if word])
    return re.compile(regexp, re.I)

def create_sort_expression(**kwargs):
    """
    Creates SortExpression's for ranking.
    Args:
        **kwargs: key=field_name, value=field_rank_value
    Returns:
        array of SortExpression
    """
    expressions = []
    for field in kwargs:
        expressions.append(appengine_search.SortExpression(
            expression=field,
            direction=appengine_search.SortExpression.ASCENDING,
            default_value=kwargs[field]))
    return expressions

def enclose_in_double_quotes(query_txt):
    """
    Encloses each word in query_txt in double quotes.
    Args:
        query_txt: Search query

    Returns:
        '"query_word1" "query_word2" ...'
    """
    query_words = query_txt.split(' ')
    return '"' + '" "'.join([word for word in query_words if word]) + '"'

def search(repo, query_txt, max_results):
    """
    Searches person with index.
    Query_txt must match at least a part of person name.
    (It's not allowed to search only by location.)
    Args:
        repo: The name of repository
        query_txt: Search query
        max_results: The max number of results you want.(Maximum: 1000)

    Returns:
        - Array of <model.Person> in datastore
        - []: If query_txt doesn't contain a part of person name

    Raises:
        search.Error: An error occurred when the index name is unknown
                      or the query has syntax error.
    """
    #TODO: Sanitaize query_txt
    if not query_txt:
        return []

    # Remove double quotes so that we can safely apply enclose_in_double_quotes().
    query_txt = re.sub('"', '', query_txt)

    person_location_index = appengine_search.Index(
        name=PERSON_LOCATION_FULL_TEXT_INDEX_NAME)

    expressions = create_sort_expression(
        given_name=1, family_name=1, full_name=1)
    sort_opt = appengine_search.SortOptions(expressions=expressions)

    options = appengine_search.QueryOptions(
        limit=max_results,
        returned_fields=['record_id', 'names'],
        sort_options=sort_opt)


    # enclose_in_double_quotes is used for avoiding query_txt
    # which specifies index field name, contains special symbol, ...
    # (e.g., "repo: repository_name", "test: test", "test AND test").
    and_query = enclose_in_double_quotes(query_txt) + ' AND (repo: ' + repo + ')'
    person_location_index_results = person_location_index.search(
        appengine_search.Query(
            query_string=and_query, options=options))
    index_results = []
    regexp = make_or_regexp(query_txt)
    for document in person_location_index_results:
        for field in document.fields:
            if field.name == 'names':
                names = field.value
            if field.name == 'record_id':
                id = field.value

        if regexp.search(names):
            index_results.append(id)

    results = []
    for id in index_results:
        result = model.Person.get(repo, id, filter_expired=True)
        if result:
            results.append(result)
    return results

def create_document(**kwargs):
    """
    Creates document for full text search.
    It should be called in add_record_to_index method.model.Person.get_by_key_name(repo + ':' + id
    """
    doc_id = kwargs['repo'] + ':' + kwargs['record_id']
    fields = []
    for field in kwargs:
        fields.append(
            appengine_search.TextField(name=field, value=kwargs[field]))
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
    name_params = [person.given_name,
                   person.family_name,
                   person.full_name,
                   person.alternate_names]
    names =  ':'.join([name for name in name_params if name])
    person_location_index.put(create_document(
        record_id=person.record_id,
        repo=person.repo,
        names=names,
        given_name=person.given_name,
        family_name=person.family_name,
        full_name=person.full_name,
        alternate_names=person.alternate_names,
        home_street=person.home_street,
        home_city=person.home_city,
        home_state=person.home_state,
        home_postal_code=person.home_postal_code,
        home_neighborhood=person.home_neighborhood,
        home_country=person.home_country))


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
