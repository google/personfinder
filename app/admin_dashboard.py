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
    """Encodes Python dates as specially marked JavaScript strings."""
    if isinstance(object, datetime):
        y, l, d, h, m, s = object.timetuple()[:6]
        return '<<new Date(%d,%d,%d,%d,%d)>>' % (y, l - 1, d, h, m)


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

        # Encode the table as JSON.
        data = simplejson.dumps(data, default=encode_date)

        # Convert the specially marked JavaScript strings to JavaScript dates.
        data = data.replace('"<<', '').replace('>>"', '')

        # Save bandwidth by removing unnecessary spaces and punctuation.
        data = data.replace('{"c": ', '{c:').replace('{"v": ', '{v:')
        data = data.replace('}, {', '},{')

        # Replace "new Date(...)" with a shorter function call, "D(...)".
        data = ('(D = function(y,l,d,h,m) {return new Date(y,l,d,h,m);}) && ' +
                data.replace('new Date', 'D'))

        # Render the page with the JSON data in it.
        self.render('templates/admin_dashboard.html', data=data,
                    subdomains=simplejson.dumps(subdomains))


if __name__ == '__main__':
    run(('/admin/dashboard', Dashboard))
