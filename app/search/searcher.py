from text_query import TextQuery
import full_text_search
import indexing


class Searcher(object):
    """A utility class for searching person records in repositories."""

    def __init__(self, repo, enable_fulltext_search, max_results):
        self._repo = repo
        self._enable_fulltext_search = enable_fulltext_search
        self._max_results = max_results

    def search(self, query_name, query_location=None):
        """Get results for a query.

        Args:
          query_name: A name to query for (string).
          query_location: A location to query for (optional, string).
        """
        if self._enable_fulltext_search:
            query_dict = {'name': query_name}
            if query_location:
                query_dict['location'] = query_location
            return full_text_search.search(
                self._repo, query_dict, self._max_results)
        else:
            text_query = TextQuery(
                '%s %s' % (query_name, query_location)
                if query_location
                else query_name)
            return indexing.search(
                self._repo, text_query, self._max_results)
