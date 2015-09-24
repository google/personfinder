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
import script_variant

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

    romanized_query = script_variant.romanize_text(query_txt)
    query_txt = re.sub('"', '', romanized_query)

    person_location_index = appengine_search.Index(
        name=PERSON_LOCATION_FULL_TEXT_INDEX_NAME)
    options = appengine_search.QueryOptions(
        limit=max_results,
        returned_fields=['record_id', 'names', 'romanized_jp_names'])

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
        romanized_jp_names = ''
        for field in document.fields:
            if field.name == 'names':
                names = field.value
            if field.name == 'record_id':
                id = field.value
            if field.name == 'romanized_jp_names':
                romanized_jp_names = field.value

        if regexp.search(names) or regexp.search(romanized_jp_names):
            index_results.append(id)

    results = []
    for id in index_results:
        result = model.Person.get(repo, id, filter_expired=True)
        if result:
            results.append(result)
    return results


def create_full_name_without_space(given_name, family_name):
    """
    Creates full name without white space.
    Returns:
        if given_name and family_name: 'given_name + family_name'
        else: None
    """
    full_name_without_space = ''
    if given_name and family_name:
        full_name_without_space = given_name + family_name
    return full_name_without_space


def create_jp_name_fields(**kwargs):
    """
    Creates fields(romanized_jp_names) for full text search.
    """
    fields = []
    romanized_names_list = []
    romanized_name_values = {}
    for field in kwargs:
        if kwargs[field] and (re.match(ur'([\u3400-\u9fff])', kwargs[field])):
            romanized_japanese_name = (
                script_variant.romanize_japanese_name_by_name_dict(
                    kwargs[field]))
            if romanized_japanese_name:
                fields.append(
                    appengine_search.TextField(
                        name=field+'_romanized_by_jp_name_dict',
                        value=romanized_japanese_name)
                )
                romanized_names_list.append(romanized_japanese_name)
                romanized_name_values[field] = romanized_japanese_name
        else:
            romanized_name_values[field] = kwargs[field]

    # fields for searching by full name without white space
    full_name_given_family = create_full_name_without_space(
        romanized_name_values['given_name'],
        romanized_name_values['family_name'])
    full_name_family_given = create_full_name_without_space(
        romanized_name_values['given_name'],
        romanized_name_values['family_name'])
    if full_name_given_family:
        fields.append(appengine_search.TextField(
            name='no_spacefull_name_romanized_jp_names1',
            value=full_name_given_family))
        romanized_names_list.append(full_name_given_family)
    if full_name_family_given:
        fields.append(appengine_search.TextField(
            name='no_spacefull_name_romanized_jp_name2',
            value=full_name_family_given))
        romanized_names_list.append(full_name_family_given)
            
    # field for checking if query words contian a part of person name.
    romanized_jp_names = (
            ':'.join([name for name in romanized_names_list if name]))
    fields.append(appengine_search.TextField(name='romanized_jp_names',
                                             value=romanized_jp_names))
    return fields


def create_jp_location_fields(**kwargs):
    """
    Creates fields(romanized jp location data) for full text search.
    It should be called in create_document method.
    """
    fields = []
    for field in kwargs:
        if (re.match(ur'([\u3400-\u9fff])', kwargs[field])):
            romanized_japanese_location = (
                script_variant.romanize_japanese_location(kwargs[field]))
            if romanized_japanese_location:
                fields.append(
                    appengine_search.TextField(
                        name=field+'_romanized_by_jp_location_dict',
                        value=romanized_japanese_location)
                )
    return fields

def create_document(record_id, repo, **kwargs):
    """
    Creates document for full text search.
    It should be called in add_record_to_index method.
    """
    fields = []

    # Add repo and record_id to fields
    doc_id = repo + ':' + record_id
    fields.append(appengine_search.TextField(name='repo', value=repo))
    fields.append(appengine_search.TextField(name='record_id', value=record_id))

    romanized_values = {}
    # Add name and location romanized by unidecode
    for field in kwargs:
        romanized_value = script_variant.romanize_word(kwargs[field])
        romanized_values[field] = romanized_value
        fields.append(
            appengine_search.TextField(name=field, value=romanized_value))

    # Add fullname without space romanized by unidecode
    full_name_without_space = create_full_name_without_space(
        kwargs['given_name'], kwargs['family_name'])
    romanized_full_name_without_space = script_variant.romanize_word(
        full_name_without_space)
    if romanized_full_name_without_space:
        fields.append(
            appengine_search.TextField(name='full_name_without_space',
                                       value=romanized_full_name_without_space))
    romanized_values['full_name_without_space'] = romanized_full_name_without_space

    name_params = [romanized_values['given_name'],
                   romanized_values['family_name'],
                   romanized_values['full_name'],
                   romanized_values['alternate_names'],
                   romanized_values['full_name_without_space']]
    names =  ':'.join([name for name in name_params if name])
    fields.append(
        appengine_search.TextField(name='names',
                                   value=script_variant.romanize_word(names)))

    # Add name romanized by japanese name dictionary
    fields.extend(create_jp_name_fields(
        given_name=kwargs['given_name'],
        family_name=kwargs['family_name'],
        full_name=kwargs['full_name'],
        alternate_names=kwargs['alternate_names']))

    # Add location romanized by japanese location dictionary
    fields.extend(create_jp_location_fields(
        home_street=kwargs['home_street'],
        home_city=kwargs['home_city'],
        home_state=kwargs['home_state'],
        home_postal_code=kwargs['home_postal_code'],
        home_neighborhood=kwargs['home_neighborhood'],
        home_country=kwargs['home_country']))

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
    person_location_index.put(create_document(
        person.record_id,
        person.repo,
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
