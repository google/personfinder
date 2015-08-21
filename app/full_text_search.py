import logging
import re

from google.appengine.api import search

import model

# The index name for full text search
PERSON_FULLTEXT_INDEX_NAME = 'person_information'

def search_with_index(repo, query_obj, max_results):
    """
    Searches person with index.
    Args:
        repo: The name of repository
        query_obj: Search word
        max_results: The max results you want.(Maximum: 1000)
    Returns:
        results[<model.Person>, ...]
    """
    #TODO: Sanitaize query_obj
    results = []
    if not query_obj:
        return results
    try:
        index = search.Index(name=PERSON_FULLTEXT_INDEX_NAME)
        options = search.QueryOptions(
            limit=max_results,
            returned_fields=['record_id'])
        results_index = index.search(search.Query(
            query_string=query_obj, options=options))
        record_ids = []
        for document in results_index:
            record_ids.append(document.fields[0].value)
        for id in record_ids:
            results.append(model.Person.get_by_key_name(repo + ':' + id))
    except search.Error:
        logging.exception('Search exception')
    return results


def create_document(**kwargs):
    """
    Creates document for full text search.
    It should be called in creat_index method.
    """
    TEXT_FIELD_TABLE = ['record_id', 'repo', 'given_name', 'family_name',
                       'full_name', 'alternate_names']
    fields = []
    for field in TEXT_FIELD_TABLE:
        if field in kwargs:
            fields.append(search.TextField(name=field, value=kwargs[field]))
    return search.Document(fields=fields)


def create_index(**kwargs):
    """
    Creates index.
    (Field: record_id, repo, given_name, family_name, full_name, alternate?name)
    """
    try:
        index_name = search.Index(name=PERSON_FULLTEXT_INDEX_NAME)
        index_name.put(create_document(**kwargs))
    except search.Error:
        logging.exception('Put failed')


def delete_index(person):
    """Deletes index.
    Args:
        person: Person who should be removed
    """
    index = search.Index(name=PERSON_FULLTEXT_INDEX_NAME)
    splited_record = re.compile(r'[:./]').split(person.key().name())
    repo = splited_record[0]
    person_record_id = splited_record[-1]
    try:
        result = index.search(
            'repo:' + repo + ' AND record_id:' + person_record_id)
        if result.results:
            document_id = result.results[0].doc_id
            index.delete(document_id)
    except search.Error:
        logging.exception('Search failed')
