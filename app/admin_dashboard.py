#!/usr/bin/python2.7
# Copyright 2011 Google Inc.
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


class Handler(BaseHandler):
    # If a repo is specified, this dashboard shows information about just that
    # repo; otherwise it shows information for all repositories by default.
    repo_required = False
    # Show stats even for deactivated repositories.
    ignore_deactivation = True

    def get(self):
        # Determine the time range to display.  We currently show the last
        # 7 days of data, which encodes to about 100 kb of JSON text.
        max_time = get_utcnow()
        min_time = max_time - timedelta(7)

        # Gather the data into a table, with a column for each repository.  See:
        # http://code.google.com/apis/visualization/documentation/reference.html#dataparam
        active_repos = sorted(Repo.list_active())
        launched_repos = sorted(Repo.list_launched())
        if self.repo:
            active_repos = launched_repos = [self.repo]
        data = {}
        for scan_name in ['person', 'note']:
            data[scan_name] = []
            blanks = []
            for repo in launched_repos:
                query = Counter.all_finished_counters(repo, scan_name)
                counters = query.filter('timestamp >', min_time).fetch(1000)
                data[scan_name] += [
                    {'c': [{'v': c.timestamp}] + blanks + [{'v': c.get('all')}]}
                    for c in counters
                ]

                # Move over one column for the next repository.
                blanks.append({})

        # Gather the counts as well.
        data['counts'] = {}
        counter_names = ['person.all', 'note.all']
        counter_names += ['person.status=' + status
                          for status in [''] + pfif.NOTE_STATUS_VALUES]
        counter_names += ['person.linked_persons=%d' % n for n in range(10)]
        counter_names += ['note.last_known_location', 'note.linked_person']
        counter_names += ['note.status=' + status
                          for status in [''] + pfif.NOTE_STATUS_VALUES]
        for repo in active_repos:
            data['counts'][repo] = dict(
                (name, Counter.get_count(repo, name))
                for name in counter_names)

        data['sources'] = {}
        for repo in active_repos:
            counts_by_source = {}
            for kind in ['person', 'note']:
                for name, count in Counter.get_all_counts(repo, kind).items():
                    if name.startswith('original_domain='):
                        source = name.split('=', 1)[1]
                        counts_by_source.setdefault(source, {})[kind] = count
            data['sources'][repo] = sorted(counts_by_source.items())

        # Encode the data as JSON.
        json = simplejson.dumps(data, default=encode_date)

        # Convert the specially marked JavaScript strings to JavaScript dates.
        json = json.replace('"<<', '').replace('>>"', '')

        # Render the page with the JSON data in it.
        self.render('admin_dashboard.html',
                    data_js=pack_json(json),
                    launched_repos_js=simplejson.dumps(launched_repos),
                    active_repos_js=simplejson.dumps(active_repos))
