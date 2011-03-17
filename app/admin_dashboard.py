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


def pack_json(json):
    """Compacts JSON to save bandwidth (currently saves about 40%)."""

    # Remove unnecessary spaces and punctuation.
    json = json.replace('{"c": ', '{c:').replace('{"v": ', '{v:')
    json = json.replace('}, {', '},{')

    # Replace "new Date(...)" with a shorter function call, "D(...)".
    json = ('(D = function(y,l,d,h,m) {return new Date(y,l,d,h,m);}) && ' +
            json.replace('new Date(', 'D('))

    return json


class Dashboard(Handler):
    # This dashboard shows information for all subdomains.
    subdomain_required = False

    def get(self):
        # Determine the time range to display.  We currently show the last
        # 7 days of data, which encodes to about 100 kb of JSON text.
        max_time = get_utcnow()
        min_time = max_time - timedelta(7)

        # Gather the data into a table, with a column for each subdomain.  See:
        # http://code.google.com/apis/visualization/documentation/reference.html#dataparam
        subdomains = sorted(s.key().name() for s in Subdomain.all())
        active_subdomains = [s for s in subdomains
                             if not config.get_for_subdomain(s, 'deactivated')]
        data = {}
        for scan_name in ['person', 'note']:
            data[scan_name] = []
            blanks = []
            for subdomain in active_subdomains:
                query = Counter.all_finished_counters(subdomain, scan_name)
                counters = query.filter('timestamp >', min_time).fetch(1000)
                data[scan_name] += [
                    {'c': [{'v': c.timestamp}] + blanks + [{'v': c.get('all')}]}
                    for c in counters
                ]

                # Move over one column for the next subdomain.
                blanks.append({})

        # Gather the counts as well.
        data['counts'] = {}
        counter_names = ['person.all', 'note.all']
        counter_names += ['person.status=' + status
                          for status in [''] + pfif.NOTE_STATUS_VALUES]
        counter_names += ['note.status=' + status
                          for status in [''] + pfif.NOTE_STATUS_VALUES]
        counter_names += ['note.location=', 'note.location=present']
        for subdomain in subdomains:
            data['counts'][subdomain] = dict(
                (name, Counter.get_count(subdomain, name))
                for name in counter_names)

        data['original_domains'] = {}
        for subdomain in subdomains:
            counts = Counter.get_all_counts(subdomain, 'person')
            domain_count_pairs = [
                (name.split('=', 1)[1], counts[name])
                for name in counts if name.startswith('original_domain=')]
            data['original_domains'][subdomain] = sorted(
                domain_count_pairs, key=lambda pair: -pair[1])

        # Encode the data as JSON.
        json = simplejson.dumps(data, default=encode_date)

        # Convert the specially marked JavaScript strings to JavaScript dates.
        json = json.replace('"<<', '').replace('>>"', '')

        # Render the page with the JSON data in it.
        self.render('templates/admin_dashboard.html',
                    data_js=pack_json(json),
                    active_subdomains_js=simplejson.dumps(active_subdomains),
                    subdomains_js=simplejson.dumps(subdomains))


if __name__ == '__main__':
    run(('/admin/dashboard', Dashboard))
