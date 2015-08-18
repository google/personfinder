from const import PERSON_FULLTEXT_INDEX_NAME

from google.appengine.api import search
import re
import model

def search_with_index(repo, query_obj, max_results):

    def create_query(query):
        return re.sub(r' ', ' AND ', query)

    results = []
    query = create_query(query_obj)
    try:
        index = search.Index(name=PERSON_FULLTEXT_INDEX_NAME)
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


def create_document(**kwargs):
    return search.Document(
        fields = [search.TextField(name='record_id', value=kwargs['record_id']),
                  search.TextField(name='repo', value=kwargs['repo']),
                  search.TextField(name='given_name', value=kwargs['given_name']),
                  search.TextField(name='family_name', value=kwargs['family_name']),
                  search.TextField(name='full_name', value=kwargs['full_name']),
                  search.TextField(name='alternate_names', value=kwargs['alternate_names'])
              ])


def create_index(**kwargs):
    try:
        index_name = search.Index(name=PERSON_FULLTEXT_INDEX_NAME)
        index_name.put(create_document(**kwargs))
    except search.Error:
        logging.exception('Put failed')

