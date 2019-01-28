from mock import patch, MagicMock
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

    def test_external_search_backend_results(self):
        """Return external search backend results when available."""
        with patch('external_search.search') as external_search_mock, \
             patch('full_text_search.search') as full_text_search_mock, \
             patch('indexing.search') as indexing_mock:
            full_text_search_mock.return_value = []
            indexing_mock.return_value = []
            external_search_mock.return_value = (
                SearcherTests.EXTERNAL_SEARCH_RETURN_VALUE)
            external_search_backends_value = 'abc external search'
            searcher = Searcher(
                SearcherTests.REPO_NAME,
                external_search_backends=external_search_backends_value,
                enable_fulltext_search=False,
                max_results=SearcherTests.MAX_RESULTS)
            assert (searcher.search('matt') ==
                    SearcherTests.EXTERNAL_SEARCH_RETURN_VALUE)
            assert len(external_search_mock.call_args_list) == 1
            call_args, _ = external_search_mock.call_args_list[0]
            assert call_args[0] == SearcherTests.REPO_NAME
            assert call_args[1].query == 'matt'
            assert call_args[2] == SearcherTests.MAX_RESULTS
            assert call_args[3] == external_search_backends_value

    def test_external_search_backend_results_with_location(self):
        """Return external search backend results, including location."""
        with patch('external_search.search') as external_search_mock, \
             patch('full_text_search.search') as full_text_search_mock, \
             patch('indexing.search') as indexing_mock:
            full_text_search_mock.return_value = []
            indexing_mock.return_value = []
            external_search_mock.return_value = (
                SearcherTests.EXTERNAL_SEARCH_RETURN_VALUE)
            external_search_backends_value = 'abc external search'
            searcher = Searcher(
                SearcherTests.REPO_NAME,
                external_search_backends=external_search_backends_value,
                enable_fulltext_search=False,
                max_results=SearcherTests.MAX_RESULTS)
            assert (searcher.search('matt', 'schenectady') ==
                    SearcherTests.EXTERNAL_SEARCH_RETURN_VALUE)
            assert len(external_search_mock.call_args_list) == 1
            call_args, _ = external_search_mock.call_args_list[0]
            assert call_args[0] == SearcherTests.REPO_NAME
            assert call_args[1].query == 'matt schenectady'
            assert call_args[2] == SearcherTests.MAX_RESULTS
            assert call_args[3] == external_search_backends_value

    def test_indexing_results(self):
        """Fall back to indexing.search results.

        When external search backends don't return any results and full-text
        search is disabled, fall back to indexing.search.
        """
        with patch('external_search.search') as external_search_mock, \
             patch('full_text_search.search') as full_text_search_mock, \
             patch('indexing.search') as indexing_mock:
            external_search_mock.return_value = []
            indexing_mock.return_value = SearcherTests.INDEXING_RETURN_VALUE
            searcher = Searcher(
                SearcherTests.REPO_NAME,
                external_search_backends='any value',
                enable_fulltext_search=False,
                max_results=SearcherTests.MAX_RESULTS)
            assert (searcher.search('matt') ==
                    SearcherTests.INDEXING_RETURN_VALUE)
            assert len(indexing_mock.call_args_list) == 1
            call_args, _ = indexing_mock.call_args_list[0]
            assert call_args[0] == SearcherTests.REPO_NAME
            assert call_args[1].query == 'matt'
            assert call_args[2] == SearcherTests.MAX_RESULTS

    def test_indexing_results_with_location(self):
        """Fall back to indexing.search results, including a location value.

        When external search backends don't return any results and full-text
        search is disabled, fall back to indexing.search.
        """
        with patch('external_search.search') as external_search_mock, \
             patch('full_text_search.search') as full_text_search_mock, \
             patch('indexing.search') as indexing_mock:
            external_search_mock.return_value = []
            indexing_mock.return_value = SearcherTests.INDEXING_RETURN_VALUE
            searcher = Searcher(
                SearcherTests.REPO_NAME,
                external_search_backends='any value',
                enable_fulltext_search=False,
                max_results=SearcherTests.MAX_RESULTS)
            assert (searcher.search('matt', 'schenectady') ==
                    SearcherTests.INDEXING_RETURN_VALUE)
            assert len(indexing_mock.call_args_list) == 1
            call_args, _ = indexing_mock.call_args_list[0]
            assert call_args[0] == SearcherTests.REPO_NAME
            assert call_args[1].query == 'matt schenectady'
            assert call_args[2] == SearcherTests.MAX_RESULTS

    def test_full_text_search_results(self):
        """Fall back to full_text_search.search results.

        When external search backends don't return any results and full-text
        search is enabled, fall back to full_text_search.search.
        """
        with patch('external_search.search') as external_search_mock, \
             patch('full_text_search.search') as full_text_search_mock, \
             patch('indexing.search') as indexing_mock:
            external_search_mock.return_value = []
            full_text_search_mock.return_value = SearcherTests.FULLTEXT_RETURN_VALUE
            searcher = Searcher(
                SearcherTests.REPO_NAME,
                external_search_backends='any value',
                enable_fulltext_search=True,
                max_results=SearcherTests.MAX_RESULTS)
            assert (searcher.search('matt') ==
                    SearcherTests.FULLTEXT_RETURN_VALUE)
            assert len(full_text_search_mock.call_args_list) == 1
            call_args, _ = full_text_search_mock.call_args_list[0]
            assert call_args[0] == SearcherTests.REPO_NAME
            assert call_args[1] == {'name': 'matt'}
            assert call_args[2] == SearcherTests.MAX_RESULTS

    def test_full_text_search_results_with_location(self):
        """Fall back to full_text_search.search results, including location.

        When external search backends don't return any results and full-text
        search is enabled, fall back to full_text_search.search.
        """
        with patch('external_search.search') as external_search_mock, \
             patch('full_text_search.search') as full_text_search_mock, \
             patch('indexing.search') as indexing_mock:
            external_search_mock.return_value = []
            full_text_search_mock.return_value = SearcherTests.FULLTEXT_RETURN_VALUE
            searcher = Searcher(
                SearcherTests.REPO_NAME,
                external_search_backends='any value',
                enable_fulltext_search=True,
                max_results=SearcherTests.MAX_RESULTS)
            assert (searcher.search('matt', 'schenectady') ==
                    SearcherTests.FULLTEXT_RETURN_VALUE)
            assert len(full_text_search_mock.call_args_list) == 1
            call_args, _ = full_text_search_mock.call_args_list[0]
            assert call_args[0] == SearcherTests.REPO_NAME
            assert call_args[1] == {'name': 'matt', 'location': 'schenectady'}
            assert call_args[2] == SearcherTests.MAX_RESULTS
