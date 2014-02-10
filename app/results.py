#!/usr/bin/python2.7
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

from model import *
from utils import *
from text_query import TextQuery
import external_search
import indexing
import jp_mobile_carriers
import logging

MAX_RESULTS = 100


def has_possible_duplicates(results):
    """Returns True if it detects that there are possible duplicate records
    in the results i.e. identical full name."""
    full_names = set()
    for result in results:
        if result.full_name in full_names:
            return True
        full_names.add(result.full_name)
    return False


class Handler(BaseHandler):
    def search(self, query):
        """Performs a search and adds view_url attributes to the results."""
        results = None
        if self.config.external_search_backends:
            results = external_search.search(
                self.repo, query, MAX_RESULTS,
                self.config.external_search_backends)
        # External search backends are not always complete. Fall back to the
        # original search when they fail or return no results.
        if not results:
            results = indexing.search(self.repo, query, MAX_RESULTS)

        for result in results:
            result.view_url = self.get_url('/view',
                                           id=result.record_id,
                                           role=self.params.role,
                                           query=self.params.query,
                                           given_name=self.params.given_name,
                                           family_name=self.params.family_name)
            result.latest_note_status = get_person_status_text(result)
            if result.is_clone():
                result.provider_name = result.get_original_domain()
            sanitize_urls(result)
        return results

    def reject_query(self, query):
        # NOTE: Parameters such as 'ui' are automatically preserved in
        #       redirect().
        return self.redirect(
            '/query', role=self.params.role, error='error', query=query.query)

    def get_results_url(self, query):
        return self.get_url(
            '/results',
            ui='' if self.env.ui == 'small' else self.env.ui,
            query=query,
            given_name=self.params.given_name,
            family_name=self.params.family_name)

    def get(self):
        create_url = self.get_url(
            '/create',
            ui='' if self.env.ui == 'small' else self.env.ui,
            role=self.params.role,
            given_name=self.params.given_name,
            family_name=self.params.family_name)
        min_query_word_length = self.config.min_query_word_length

        if self.params.role == 'provide':
            # The order of family name and given name does matter (see the
            # scoring function in indexing.py).
            query_txt = get_full_name(
                self.params.given_name, self.params.family_name, self.config)
            query = TextQuery(query_txt)
            results_url = self.get_results_url(query_txt)
            # Ensure that required parameters are present.
            if not self.params.given_name:
                return self.reject_query(query)
            if self.config.use_family_name and not self.params.family_name:
                return self.reject_query(query)
            if (len(query.query_words) == 0 or
                max(map(len, query.query_words)) < min_query_word_length):
                return self.reject_query(query)

            # Look for *similar* names, not prefix matches.
            # Eyalf: we need to full query string
            # for key in criteria:
            #     criteria[key] = criteria[key][:3]  
            # "similar" = same first 3 letters
            results = self.search(query)
            # Filter out results with addresses matching part of the query.
            results = [result for result in results
                       if not getattr(result, 'is_address_match', False)]

            if results:
                # Perhaps the person you wanted to report has already been
                # reported?
                return self.render('results.html',
                                   results=results,
                                   num_results=len(results),
                                   has_possible_duplicates=
                                        has_possible_duplicates(results),
                                   results_url=results_url,
                                   create_url=create_url)
            else:
                if self.env.ui == 'small':
                    # show a link to a create page.
                    return self.render('small-create.html',
                                       create_url=create_url)
                else:
                    # No matches; proceed to create a new record.
                    logging.info(repr(self.params.__dict__))
                    return self.redirect('/create', **self.params.__dict__)

        if self.params.role == 'seek':
            query = TextQuery(self.params.query) 
            # If a query looks like a phone number, show the user a result
            # of looking up the number in the carriers-provided BBS system.
            if self.config.jp_mobile_carrier_redirect:
                if jp_mobile_carriers.handle_phone_number(self, query.query):
                    return 

            # Ensure that required parameters are present.
            if (len(query.query_words) == 0 or
                max(map(len, query.query_words)) < min_query_word_length):
                logging.info('rejecting %s' % query.query)
                return self.reject_query(query)

            # Look for prefix matches.
            results = self.search(query)
            results_url = self.get_results_url(self.params.query)

            # Show the (possibly empty) matches.
            return self.render('results.html',
                               results=results,
                               num_results=len(results),
                               has_possible_duplicates=
                                    has_possible_duplicates(results),
                               results_url=results_url,
                               create_url=create_url)
