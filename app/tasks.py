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

from utils import *
from model import *
from google.appengine.api import quota
from google.appengine.api.labs import taskqueue


def count_records(kind_class, subdomain, last_key, cpu_megacycles):
    """Counts the entities of a given kind for a limited amount of CPU time."""
    FETCH_LIMIT = 100
    cpu_limit = quota.get_request_cpu_usage() + cpu_megacycles
    count = 0
    while quota.get_request_cpu_usage() < cpu_limit:
        # Get the next batch of keys.
        query = kind_class.all(keys_only=True)
        query = filter_by_prefix(query, subdomain + ':')
        if last_key:
            query = query.filter('__key__ >', last_key)
        fetched_keys = query.order('__key__').fetch(FETCH_LIMIT)
        if not fetched_keys:
            logging.debug('%s count for %s finished: %d' %
                          (kind_class.__name__, subdomain, count))
            return count, None

        # Count the keys and proceed.
        last_key = fetched_keys[-1]
        count += len(fetched_keys)
        logging.debug('%s count for %s: %d, last_key: %r' %
                      (kind_class.__name__, subdomain, count, last_key))

    return count, last_key


def start_counter(subdomain, kind_name):
    taskqueue.add(name='count-%s-%s' % (subdomain, kind_name),
                  method='GET',
                  url='/tasks/count',
                  params={'subdomain': subdomain, 'kind_name': kind_name})


class Count(Handler):
    env_required = False  # Run at the root domain, not a subdomain.

    def get(self):
        if self.subdomain:
            self.run_counter()
        else:
            self.start_all_counters()

    def start_all_counters(self):
        """Fires off counters for both entity kinds in each subdomain."""
        for key in Subdomain.all(keys_only=True):
            start_counter(key.name(), 'Person')
            start_counter(key.name(), 'Note')

    def run_counter(self):
        """Runs a counter for a single kind in a single subdomain."""
        kind_name = self.request.get('kind_name').strip()
        kind = {'Person': Person, 'Note': Note}[kind_name]

        # Pick up where this counter left off.
        counter = Counter.query_last(self.subdomain, kind).get()
        if not counter or not counter.last_key:
            counter = Counter(subdomain=self.subdomain, kind_name=kind_name)

        # Spend 1000 CPU megacycles counting entities.
        last_key = counter.last_key and db.Key(counter.last_key) or None
        count, last_key = count_records(kind, self.subdomain, last_key, 1000)

        # Store the results.
        counter.count += count
        counter.last_key = last_key and str(last_key) or ''
        counter.put()
        self.write('%s count for %s: %d (last_key=%r)' %
                   (kind_name, self.subdomain, counter.count, last_key))


if __name__ == '__main__':
    run(('/tasks/count', Count))
