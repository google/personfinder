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

MAX_RESULTS = 10


class Review(Handler):
    def get(self):
        results_url = self.get_url('/review',
                                   query=self.params.query)

        query = model.Note.all_in_subdomain(self.subdomain)
        query = query.order('-entry_date')
        # add filters
        notes = query.fetch(MAX_RESULTS)
        return self.render('templates/review.html',
                           notes=notes, num_notes=len(notes))

if __name__ == '__main__':
    run(('/review', Review))
