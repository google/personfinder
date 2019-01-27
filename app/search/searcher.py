from text_query import TextQuery
import external_search
import full_text_search
import indexing


class Searcher(object):
    """A utility class for searching person records in repositories."""

    def __init__(
        self, repo, external_search_backends, enable_fulltext_search,
        max_results):
        self._repo = repo
        self._external_search_backends = external_search_backends
        self._enable_fulltext_search = enable_fulltext_search
        self._max_results = max_results

    def search(self, query_name, query_location=None):
        """Get results for a query.

        Args:
          query_name: A name to query for.
          query_location: A location to query for (optional).
        """
        text_query = TextQuery(
            '%s %s' % (query_name, query_location)
            if query_location
            else query_name)
        results = None
        if self._external_search_backends:
            results = external_search.search(
                self._repo, text_query, self._max_results,
                self._external_search_backends)
        # External search backends are not always complete. Fall back to the
        # original search when they fail or return no results.
        if not results:
            query_dict = {'name': query_name}
            if query_location:
                query_dict['location'] = query_location
            if self._enable_fulltext_search:
                results = full_text_search.search(
                    self._repo, query_dict, self._max_results)
            else:
                results = indexing.search(
                    self._repo, text_query, self._max_results)
        return results
