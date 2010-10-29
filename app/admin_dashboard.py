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

import logging
import simplejson
import sys

from model import *
from utils import *


def encode_date(object):
    """Encodes Python dates as JavaScript strings."""
    if isinstance(object, datetime):
        y, l, d, h, m, s = object.timetuple()[:6]
        return '<date>%d, %d, %d, %d, %d, %d</date>' % (y, l - 1, d, h, m, s)


class Dashboard(Handler):
    subdomain_required = False

    def get(self):
        # Determine the time range to display.
        max_time = datetime.now()
        min_time = max_time - timedelta(10)  # show 10 days

        # Gather the data into a table, with a column for each subdomain.  See:
        # http://code.google.com/apis/visualization/documentation/reference.html#dataparam
        subdomains = sorted([s.key().name() for s in Subdomain.all()])
        data = {}
        for kind in ['Person', 'Note']:
            data[kind] = []
            blanks = []
            for subdomain in subdomains:
                query = Counter.all().filter('subdomain =', subdomain
                                    ).filter('kind_name =', kind
                                    ).filter('timestamp >', min_time
                                    ).filter('last_key =', '')
                data[kind] += [
                    {'c': [{'v': c.timestamp}] + blanks + [{'v': c.count}]}
                    for c in query.fetch(1000)
                ]

                # Move over one column for the next subdomain.
                blanks.append({})

        # Encode this to JSON.
        data = simplejson.dumps(data, default=encode_date)

        # Convert the specially marked JavaScript strings to JavaScript dates.
        data = data.replace('"<date>', 'new Date(').replace('</date>"', ')')

        # Render the page with the JSON data in it.
        self.render('templates/admin_dashboard.html', data=data,
                    subdomains=simplejson.dumps(subdomains))


if __name__ == '__main__':
    run(('/admin/dashboard', Dashboard))
