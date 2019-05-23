# Copyright 2019 Google Inc.
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

"""Tests for the Searcher."""

import unittest

import mock

from search.searcher import Searcher


class SearcherTests(unittest.TestCase):
    # pylint: disable=no-self-use
    """Test cases for searcher.Searcher."""

    # Argument values
    REPO_NAME = 'haiti'
    MAX_RESULTS = 10
    # Return values
    FULLTEXT_RETURN_VALUE = ['full-text return value']
    INDEXING_RETURN_VALUE = ['indexing return value']

    def test_full_text_search_results(self):
        """Use full_text_search.search results when enabled."""
        with mock.patch('full_text_search.search') as full_text_search_mock:
            full_text_search_mock.return_value = (
                SearcherTests.FULLTEXT_RETURN_VALUE)
            searcher = Searcher(
                SearcherTests.REPO_NAME,
                enable_fulltext_search=True,
                max_results=SearcherTests.MAX_RESULTS)
            assert (
                searcher.search('matt') == SearcherTests.FULLTEXT_RETURN_VALUE)
            assert len(full_text_search_mock.call_args_list) == 1
            call_args, _ = full_text_search_mock.call_args_list[0]
            assert call_args[0] == SearcherTests.REPO_NAME
            assert call_args[1] == {'name': 'matt'}
            assert call_args[2] == SearcherTests.MAX_RESULTS

    def test_full_text_results_with_loc(self):
        """Use full_text_search.search results when enabled, including location.
        """
        with mock.patch('full_text_search.search') as full_text_search_mock:
            full_text_search_mock.return_value = (
                SearcherTests.FULLTEXT_RETURN_VALUE)
            searcher = Searcher(
                SearcherTests.REPO_NAME,
                enable_fulltext_search=True,
                max_results=SearcherTests.MAX_RESULTS)
            assert (searcher.search(
                'matt', 'schenectady') == SearcherTests.FULLTEXT_RETURN_VALUE)
            assert len(full_text_search_mock.call_args_list) == 1
            call_args, _ = full_text_search_mock.call_args_list[0]
            assert call_args[0] == SearcherTests.REPO_NAME
            assert call_args[1] == {'name': 'matt', 'location': 'schenectady'}
            assert call_args[2] == SearcherTests.MAX_RESULTS

    def test_indexing_results(self):
        """Fall back to indexing.search results.

        When full-text search is disabled, fall back to indexing.search.
        """
        with mock.patch('indexing.search') as indexing_mock:
            indexing_mock.return_value = SearcherTests.INDEXING_RETURN_VALUE
            searcher = Searcher(
                SearcherTests.REPO_NAME,
                enable_fulltext_search=False,
                max_results=SearcherTests.MAX_RESULTS)
            assert (
                searcher.search('matt') == SearcherTests.INDEXING_RETURN_VALUE)
            assert len(indexing_mock.call_args_list) == 1
            call_args, _ = indexing_mock.call_args_list[0]
            assert call_args[0] == SearcherTests.REPO_NAME
            assert call_args[1].query == 'matt'
            assert call_args[2] == SearcherTests.MAX_RESULTS

    def test_indexing_results_with_loc(self):
        """Fall back to indexing.search results, including a location value.

        When full-text search is disabled, fall back to indexing.search.
        """
        with mock.patch('indexing.search') as indexing_mock:
            indexing_mock.return_value = SearcherTests.INDEXING_RETURN_VALUE
            searcher = Searcher(
                SearcherTests.REPO_NAME,
                enable_fulltext_search=False,
                max_results=SearcherTests.MAX_RESULTS)
            assert (searcher.search(
                'matt', 'schenectady') == SearcherTests.INDEXING_RETURN_VALUE)
            assert len(indexing_mock.call_args_list) == 1
            call_args, _ = indexing_mock.call_args_list[0]
            assert call_args[0] == SearcherTests.REPO_NAME
            assert call_args[1].query == 'matt schenectady'
            assert call_args[2] == SearcherTests.MAX_RESULTS
