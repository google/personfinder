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

# The index name for full text search. This index contains name.
PERSON_FULL_TEXT_INDEX_NAME = 'person_information'
# The index name for full text search. This index contains name and location.
PERSON_LOCATION_FULL_TEXT_INDEX_NAME = 'person_location_information'

def create_or_query(query_txt):
    """
    Creates query for person_information index.
    Args:
        query_txt: Search query

    Returns:
        query_word OR query_word OR ...
    """
    query_words = query_txt.split(' ')
    query_string = ''
    for word in query_words:
        if (word != ''):
            query_string += word + ' OR '
    return query_string[:-4]

def search(repo, query_txt, max_results):
    """
    Searches person with index.
    Args:
        repo: The name of repository
        query_txt: Search query
        max_results: The max number of results you want.(Maximum: 1000)

    Returns:
        results[<model.Person>, ...]

    Raises:
        search.Error: An error occurred when the index name is unknown
                      or the query has syntax error.
    """
    #TODO: Sanitaize query_txt
    results = []
    if not query_txt:
        return results
    person_index = appengine_search.Index(name=PERSON_FULL_TEXT_INDEX_NAME)
    person_location_index = appengine_search.Index(
        name=PERSON_LOCATION_FULL_TEXT_INDEX_NAME)
    options = appengine_search.QueryOptions(
        limit=max_results,
        returned_fields=['record_id'])
    or_query = create_or_query(query_txt) + ' AND (repo: ' + repo + ')'
    person_index_results = person_index.search(appengine_search.Query(
        query_string=or_query, options=options))
    query_txt += ' AND (repo: ' + repo + ')'
    person_location_index_results = person_location_index.search(
        appengine_search.Query(
            query_string=query_txt, options=options))
    index_results = list(
        set(person_index_results) & set(person_location_index_results))
    for document in index_results:
        id = document.fields[0].value
        results.append(model.Person.get_by_key_name(repo + ':' + id))
    return results


def create_document(**kwargs):
    """
    Creates document for full text search.
    It should be called in add_record_to_index method.
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
    person_index = appengine_search.Index(name=PERSON_FULL_TEXT_INDEX_NAME)
    person_index.put(create_document(
        record_id=person.record_id,
        repo=person.repo,
        given_name=person.given_name,
        family_name=person.family_name,
        full_name=person.full_name,
        alternate_names=person.alternate_names))
    person_location_index = appengine_search.Index(
        name=PERSON_LOCATION_FULL_TEXT_INDEX_NAME)
    person_location_index.put(create_document(
        record_id=person.record_id,
        repo=person.repo,
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
    person_index = appengine_search.Index(name=PERSON_FULL_TEXT_INDEX_NAME)
    doc_id = person.repo + ':' + person.record_id
    person_index.delete(doc_id)
    person_location_index = appengine_search.Index(
        name=PERSON_LOCATION_FULL_TEXT_INDEX_NAME)
    person_location_index.delete(doc_id)
