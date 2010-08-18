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
import logging
import prefix

MAX_RESULTS = 100


class Results(Handler):
  def search(self, query):
    return indexing.search(Person, query, MAX_RESULTS)

  def reject_query(self, query):
    return self.redirect(
        '/query', role=self.params.role, small=self.params.small,
        style=self.params.style, error='error', query=query.query)

  def get(self):
    if self.params.role == 'provide':
      query = TextQuery(self.params.first_name + ' ' + self.params.last_name)

      # Ensure that required parameters are present.
      if not self.params.first_name:
        return self.reject_query(query)
      if config.USE_FAMILY_NAME and not self.params.last_name:
        return self.reject_query(query)
      if (len(query.query_words) == 0 or
          max(map(len, query.query_words)) < config.MIN_QUERY_WORD_LENGTH):
        return self.reject_query(query)

      # Look for *similar* names, not prefix matches.
      # Eyalf: we need to full query string
      #for key in criteria:
      #  criteria[key] = criteria[key][:3]  # "similar" = same first 3 letters
      results = self.search(query)

      if results:
        # Perhaps the person you wanted to report has already been reported?
        return self.render('templates/results.html', params=self.params,
                           results=results, num_results=len(results))
      else:
        if self.params.small:
          # show a link to a create page.
          return self.render('templates/small-create.html', params=self.params)
        else:
          # No matches; proceed to create a new record.
          logging.info(repr(self.params.__dict__))
          return self.redirect('create', **self.params.__dict__)

    if self.params.role == 'seek':
      query = TextQuery(self.params.query) 
      # Ensure that required parameters are present.
      if len(query.query_words) == 0 or max(map(len, query.query_words)) < 2:
        logging.info('rejecting %s' % query.query)
        return self.reject_query(query)

      # Look for prefix matches.
      results = self.search(query)

      # Show the (possibly empty) matches.
      return self.render('templates/results.html', params=self.params,
                         results=results, num_results=len(results))

if __name__ == '__main__':
  run([('/results', Results)], debug=False)
