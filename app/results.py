# Copyright 2010 Google Inc.
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
import unicodedata

from django.utils.translation import ugettext as _

from model import *
from utils import *
from search.searcher import Searcher
from text_query import TextQuery
import config
import indexing
import full_text_search
import jp_mobile_carriers

MAX_RESULTS = 100
# U+2010: HYPHEN
# U+2012: FIGURE DASH
# U+2013: EN DASH
# U+2015: HORIZONTAL BAR
# U+2212: MINUS SIGN
# U+301C: WAVE DASH
# U+30FC: KATAKANA-HIRAGANA PROLONGED SOUND MARK
POSSIBLE_PHONE_NUMBER_RE = re.compile(
    ur'^[\d\(\)\.\-\s\u2010\u2012\u2013\u2015\u2212\u301c\u30fc]+$')


def has_possible_duplicates(results):
    """Returns True if it detects that there are possible duplicate records
    in the results i.e. identical full name."""
    full_names = set()
    for result in results:
        if result.full_name in full_names:
            return True
        full_names.add(result.full_name)
    return False


def is_possible_phone_number(query_str):
    return re.search(POSSIBLE_PHONE_NUMBER_RE,
        unicodedata.normalize('NFKC', unicode(query_str)))


def max_word_length(query_words):
    max_length = max(map(len, query_words))
    # Count series of CJK characters as one word. Do this because CJK
    # characters are treated as separate words even when there is no
    # whitespace between them. This also means that sequences of CJK characters
    # will be counted here as one word even if there was whitespace between
    # them originally.
    cjk_length = 0
    for word in query_words:
        # This CJK character range is copied from the logic in text_query.py.
        if u'\u3400' <= word <= u'\u9fff':
            cjk_length += 1
            max_length = max(max_length, cjk_length)
        else:
            cjk_length = 0
    return max_length


class Handler(BaseHandler):

    def search(self, query_dict):
        """
        Performs a search and adds view_url attributes to the results.
        Args:
            query_dict: A list contains two queries: Name query and Location query
        """

        searcher = Searcher(
            self.repo, config.get('enable_fulltext_search'), MAX_RESULTS)
        results = searcher.search(
            query_dict['name'],
            query_dict.get('location'))

        query_name = self.get_query_value()
        for result in results:
            result.view_url = self.get_url('/view',
                                           id=result.record_id,
                                           role=self.params.role,
                                           query_name=query_name,
                                           query_location=
                                               self.params.query_location,
                                           given_name=self.params.given_name,
                                           family_name=self.params.family_name)
            result.latest_note_status = get_person_status_text(result)
            if result.is_clone():
                result.provider_name = result.get_original_domain()
            result.should_show_inline_photo = (
                self.should_show_inline_photo(result.photo_url))
            if result.should_show_inline_photo and result.photo:
                # Only use a thumbnail URL if the photo was uploaded; we don't
                # have thumbnails for other photos.
                result.thumbnail_url = self.get_thumbnail_url(result.photo_url)
            sanitize_urls(result)
        return results

    def reject_query(self, query):
        # NOTE: Parameters such as 'ui' are automatically preserved in
        #       redirect().
        return self.redirect(
            '/query', role=self.params.role, error='error', query=query.query)

    def get_query_value(self):
        # The query_name parameter used to be called simply "query", and we
        # continue to accept it because some third-parties have links that
        # depend on it.
        return self.params.query_name or self.params.query

    def get_results_url(self, query_name, query_location):
        params = {
            'query_name': query_name,
            'query_location': query_location,
            'role': self.params.role,
            'given_name': self.params.given_name,
            'family_name': self.params.family_name,
        }
        # Links to the default UI from the small UI. Otherwise preserves "ui"
        # param of the current page. Note that get_url() preserves "ui" param
        # by default (i.e., when it's not specified in +params+).
        if self.env.ui == 'small':
            params['ui'] = None
        return self.get_url('/results', **params)

    def get(self):
        params = {
            'role': self.params.role,
            'given_name': self.params.given_name,
            'family_name': self.params.family_name,
        }
        # Links to the default UI from the small UI. Otherwise preserves "ui"
        # param of the current page. Note that get_url() preserves "ui" param
        # by default (i.e., when it's not specified in +params+).
        if self.env.ui == 'small':
            params['ui'] = None
        create_url = self.get_url('/create', **params)

        min_query_word_length = self.config.min_query_word_length

        third_party_search_engines = []
        for i, search_engine in enumerate(
                self.config.third_party_search_engines or []):
            third_party_search_engines.append(
                {'id': i, 'name': search_engine.get('name', '')})

        if self.params.role == 'provide':
            # The order of family name and given name does matter (see the
            # scoring function in indexing.py).
            query_txt = get_full_name(
                self.params.given_name, self.params.family_name, self.config)

            query = TextQuery(query_txt)
            results_url = self.get_results_url(query_txt, '')
            # Ensure that required parameters are present.
            if not self.params.given_name:
                return self.reject_query(query)
            if self.config.use_family_name and not self.params.family_name:
                return self.reject_query(query)
            if (len(query.query_words) == 0 or
                max_word_length(query.query_words) < min_query_word_length):
                return self.reject_query(query)

            # Look for *similar* names, not prefix matches.
            # Eyalf: we need to full query string
            # for key in criteria:
            #     criteria[key] = criteria[key][:3]
            # "similar" = same first 3 letters
            results = self.search({'name':query_txt})
            # Filter out results with addresses matching part of the query.
            results = [result for result in results
                       if not getattr(result, 'is_address_match', False)]

            if results:
                # Perhaps the person you wanted to report has already been
                # reported?
                return self.render(
                    'results.html',
                    results=results,
                    num_results=len(results),
                    has_possible_duplicates=
                        has_possible_duplicates(results),
                    results_url=results_url,
                    create_url=create_url,
                    third_party_search_engines=
                        third_party_search_engines,
                    query_name=self.get_query_value(),
                    query_location=self.params.query_location,)
            else:
                if self.env.ui == 'small':
                    # show a link to a create page.
                    return self.render('small-create.html',
                                       create_url=create_url)
                else:
                    # No matches; proceed to create a new record.
                    return self.redirect(create_url)

        if self.params.role == 'seek':
            # The query_name parameter was previously called "query", and we
            # continue to support it for third-parties that link directly to
            # search results pages.
            query_name = self.get_query_value()
            query_dict = {'name': query_name,
                          'location': self.params.query_location}
            query = TextQuery(" ".join(q for q in query_dict.values() if q))
            results_based_on_input = True

            # If a query looks like a phone number, show the user a result
            # of looking up the number in the carriers-provided BBS system.
            if self.config.jp_mobile_carrier_redirect:
                try:
                    if jp_mobile_carriers.handle_phone_number(
                            self, query.query):
                        return
                except Exception as e:
                    logging.exception(
                        'failed to scrape search result for the phone number.')
                    return self.error(
                        # Translators: An error message indicating that we
                        # failed to obtain search result for the phone number
                        # given by the user.
                        500, _('Failed to obtain search result '
                               'for the phone number.'))

            if is_possible_phone_number(query.query):
                # If the query looks like a phone number, we show an empty
                # result page instead of rejecting it. We don't support
                # search by phone numbers, but third party search engines
                # may support it.
                results = []
                results_url = None
                third_party_query_type = 'tel'
            elif (len(query.query_words) == 0 or
                  max_word_length(query.query_words) < min_query_word_length):
                logging.info('rejecting %s' % query.query)
                return self.reject_query(query)
            else:
                # Look for prefix matches.
                results = self.search(query_dict)
                results_url = self.get_results_url(query_name,
                                                   self.params.query_location)
                third_party_query_type = ''

                # If there is no results match for both name and location
                # Check if there have results match for name
                if not results:
                    if self.params.query_location:
                        query_dict = {'name': query_name, 'location': ''}
                        results = self.search(query_dict)
                        # search result not based on the user input
                        results_based_on_input = False

            concatenated_query = (
                ('%s %s' % (query_name, self.params.query_location))
                    .strip())

            # Show the (possibly empty) matches.
            return self.render('results.html',
                               results=results,
                               num_results=len(results),
                               has_possible_duplicates=
                                   has_possible_duplicates(results),
                               results_url=results_url,
                               create_url=create_url,
                               third_party_search_engines=
                                   third_party_search_engines,
                               query_name=query_name,
                               query=concatenated_query,
                               third_party_query_type=third_party_query_type,
                               results_based_on_input=results_based_on_input)
