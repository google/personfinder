import logging
import re

from google.appengine.api import search as appengine_search

import model

# The index name for full text search
PERSON_FULLTEXT_INDEX_NAME = 'person_information'

def search(repo, query_obj, max_results):
    """
    Searches person with index.
    Args:
        repo: The name of repository
        query_obj: Search word
        max_results: The max results you want.(Maximum: 1000)

    Returns:
        results[<model.Person>, ...]

    Raises:
        search.Error: An error occurred search unknown index, syntax error
    """
    #TODO: Sanitaize query_obj
    results = []
    if not query_obj:
        return results
    index = appengine_search.Index(name=PERSON_FULLTEXT_INDEX_NAME)
    options = appengine_search.QueryOptions(
        limit=max_results,
        returned_fields=['record_id'])
    index_results = index.search(appengine_search.Query(
        query_string=query_obj, options=options))
    record_ids = []
    for document in index_results:
        record_ids.append(document.fields[0].value)
    for id in record_ids:
        results.append(model.Person.get_by_key_name(repo + ':' + id))
    return results


def create_document(**kwargs):
    """
    Creates document for full text search.
    It should be called in add_record_to_index method.
    """
    doc_id = kwargs['repo'] + ':' + kwargs['record_id']
    TEXT_FIELD_TABLE = ['record_id', 'repo', 'given_name', 'family_name',
                        'full_name', 'alternate_names']
    fields = []
    for field in TEXT_FIELD_TABLE:
        if field in kwargs:
            fields.append(appengine_search.TextField(name=field, value=kwargs[field]))
    return appengine_search.Document(doc_id=doc_id, fields=fields)


def add_record_to_index(person):
    """
    Creates index.
    (Field: record_id, repo, given_name, family_name, full_name, alternate?name)
    Raises:
        search.Error: An error occurred putting the document could not be indexed, syntax error
    """
    index = appengine_search.Index(name=PERSON_FULLTEXT_INDEX_NAME)
    index.put(create_document(
        record_id = person.record_id,
        repo = person.repo,
        given_name = person.given_name,
        family_name = person.family_name,
        full_name = person.full_name,
        alternate_names = person.alternate_names))


def delete_index(person):
    """Deletes index.
    Args:
        person: Person who should be removed
    Raises:
        search.Error: An error occurred search unknown index, syntax error
    """
    index = appengine_search.Index(name=PERSON_FULLTEXT_INDEX_NAME)
    repo = person.repo
    person_record_id = person.record_id
    doc_id = repo + ':' + person_record_id
    doc = index.get(doc_id)
    index.delete(doc_id)
