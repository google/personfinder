#!/usr/bin/python2.5
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
import indexing
import jp_mobile_carriers
import logging
import prefix

MAX_RESULTS = 100


class Results(Handler):
    def search(self, query):
        """Performs a search and adds view_url attributes to the results."""
        results = indexing.search(self.subdomain, query, MAX_RESULTS)
        for result in results:
            result.view_url = self.get_url('/view',
                                           id=result.record_id,
                                           role=self.params.role,
                                           query=self.params.query,
                                           first_name=self.params.first_name,
                                           last_name=self.params.last_name)
            result.latest_note_status = get_person_status_text(result)
            if result.is_clone():
                result.provider_name = result.get_original_domain()
        return results

    def reject_query(self, query):
        return self.redirect(
            '/query', role=self.params.role, small=self.params.small,
            style=self.params.style, error='error', query=query.query,
            mobile_carrier_redirect=self.config.jp_mobile_carrier_redirect)

    def get(self):
        # If a query looks like a phone number, redirects the user to an
        # appropriate mobile carrier's page for the number.
        do_redirect = self.config.jp_mobile_carrier_redirect
        if do_redirect:
            phone = jp_mobile_carriers.get_phone_number(self.params.query)
            if phone:
                if jp_mobile_carriers.is_mobile_number(phone):
                    return self.redirect(
                        jp_mobile_carriers.get_redirect_url(phone))
                else:
                    return self.render('templates/query.html',
                        role='seek',
                        query=self.params.query,
                        mobile_carrier_redirect=do_redirect,
                        not_mobile=True)

        results_url = self.get_url('/results',
                                   small='no',
                                   query=self.params.query,
                                   first_name=self.params.first_name,
                                   last_name=self.params.last_name,
                                   mobile_carrier_redirect=do_redirect)
        create_url = self.get_url('/create',
                                  small='no',
                                  role=self.params.role,
                                  first_name=self.params.first_name,
                                  last_name=self.params.last_name)
        min_query_word_length = self.config.min_query_word_length

        if self.params.role == 'provide':
            query = TextQuery(
                self.params.first_name + ' ' + self.params.last_name)

            # Ensure that required parameters are present.
            if not self.params.first_name:
                return self.reject_query(query)
            if self.config.use_family_name and not self.params.last_name:
                return self.reject_query(query)
            if (len(query.query_words) == 0 or
                max(map(len, query.query_words)) < min_query_word_length):
                return self.reject_query(query)

            # Look for *similar* names, not prefix matches.
            # Eyalf: we need to full query string
            # for key in criteria:
            #     criteria[key] = criteria[key][:3]  # "similar" = same first 3 letters
            results = self.search(query)

            if results:
                # Perhaps the person you wanted to report has already been
                # reported?
                return self.render('templates/results.html',
                                   results=results, num_results=len(results),
                                   results_url=results_url,
                                   create_url=create_url,
                                   mobile_carrier_redirect=do_redirect)
            else:
                if self.params.small:
                    # show a link to a create page.
                    create_url = self.get_url(
                        '/create', query=self.params.query)
                    return self.render('templates/small-create.html',
                                       create_url=create_url)
                else:
                    # No matches; proceed to create a new record.
                    logging.info(repr(self.params.__dict__))
                    return self.redirect('/create', **self.params.__dict__)

        if self.params.role == 'seek':
            query = TextQuery(self.params.query) 
            # Ensure that required parameters are present.
            if (len(query.query_words) == 0 or
                max(map(len, query.query_words)) < min_query_word_length):
                logging.info('rejecting %s' % query.query)
                return self.reject_query(query)

            # Look for prefix matches.
            results = self.search(query)
            
            # Show the (possibly empty) matches.
            return self.render('templates/results.html',
                               results=results, num_results=len(results),
                               results_url=results_url, create_url=create_url,
                               mobile_carrier_redirect=do_redirect)

if __name__ == '__main__':
    run(('/results', Results))
