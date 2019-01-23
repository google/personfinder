from mock import patch
import unittest

from search.searcher import Searcher


class SearcherTests(unittest.TestCase):

    # Argument values
    REPO_NAME = 'haiti'
    MAX_RESULTS = 10
    # Return values
    EXTERNAL_SEARCH_RETURN_VALUE = ['external search return value']
    FULLTEXT_RETURN_VALUE = ['full-text return value']
    INDEXING_RETURN_VALUE = ['indexing return value']

    def setUp(self):
        pass

    @patch('external_search.search')
    def test_external_search_backend_results(self, external_search_mock):
        """Return external search backend results when available."""
        external_search_mock.return_value = (
            SearcherTests.EXTERNAL_SEARCH_RETURN_VALUE)
        external_search_value = 'abc external search'
        searcher = Searcher(
            SearcherTests.REPO_NAME, external_search_value, False,
            SearcherTests.MAX_RESULTS)
        assert (searcher.search({'name': 'matt'}) ==
                SearcherTests.EXTERNAL_SEARCH_RETURN_VALUE)
        assert 1 == len(external_search_mock.call_args_list)
        call_args, _ = external_search_mock.call_args_list[0]
        assert call_args[0] == SearcherTests.REPO_NAME
        assert call_args[1].query == 'matt'
        assert call_args[2] == SearcherTests.MAX_RESULTS
        assert call_args[3] == external_search_value

    @patch('external_search.search')
    @patch('indexing.search')
    def test_indexing_results(self, external_search_mock, indexing_mock):
        """Fall back to indexing.search results.

        When external search backends don't return any results and full-text
        search is disabled, fall back to indexing.search.
        """
        external_search_mock.return_value = []
        indexing_mock.return_value = SearcherTests.INDEXING_RETURN_VALUE
        searcher = Searcher(
            SearcherTests.REPO_NAME, 'any value', False,
            SearcherTests.MAX_RESULTS)
        assert (searcher.search({'name': 'matt'}) ==
                SearcherTests.INDEXING_RETURN_VALUE)
        assert 1 == len(indexing_mock.call_args_list)
        call_args, _ = indexing_mock.call_args_list[0]
        assert call_args[0] == SearcherTests.REPO_NAME
        assert call_args[1].query == 'matt'
        assert call_args[2] == SearcherTests.MAX_RESULTS

    @patch('external_search.search')
    @patch('full_text_search.search')
    def test_full_text_search_results(
        self, external_search_mock, full_text_search_mock):
        """Fall back to full_text_search.search results.

        When external search backends don't return any results and full-text
        search is enabled, fall back to full_text_search.search.
        """
        external_search_mock.return_value = []
        full_text_search_mock.return_value = SearcherTests.FULLTEXT_RETURN_VALUE
        searcher = Searcher(
            SearcherTests.REPO_NAME, 'any value', False,
            SearcherTests.MAX_RESULTS)
        assert (searcher.search({'name': 'matt'}) ==
                SearcherTests.FULLTEXT_RETURN_VALUE)
        assert 1 == len(full_text_search_mock.call_args_list)
        call_args, _ = full_text_search_mock.call_args_list[0]
        assert call_args[0] == SearcherTests.REPO_NAME
        assert call_args[1].query == 'matt'
        assert call_args[2] == SearcherTests.MAX_RESULTS
