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

def make_key_query(model_type, last_key=None):
  """Makes a query on all the keys of a given kind, in ascending order."""
  query = db.Query(model_type, keys_only=True).order('__key__')
  if last_key:
    query = query.filter('__key__ >', last_key)
  return query

def count_records(kind_class, last_key, cpu_megacycles):
  """Counts the entities of a given kind for a limited amount of CPU time."""
  FETCH_LIMIT = 100
  cpu_limit = quota.get_request_cpu_usage() + cpu_megacycles
  count = 0
  while quota.get_request_cpu_usage() < cpu_limit:
    # Get the next batch of keys.
    fetched_keys = make_key_query(kind_class, last_key).fetch(FETCH_LIMIT)
    if not fetched_keys:
      logging.debug('%s count finished: %d' % (kind_class, count))
      return count, None

    # Count the keys and proceed.
    last_key = fetched_keys[-1]
    count += len(fetched_keys)
    logging.debug('%s count: %d, last_key: %r' % (kind_class, count, last_key))

  return count, last_key


class Count(Handler):
  def get(self):
    kind_name = self.request.get('kind_name').strip()
    kind = {'Person': Person, 'Note': Note}[kind_name]

    # Pick up where we left off.
    counter = EntityCounter.query_last(kind).get()
    if not counter or not counter.last_key:
      counter = EntityCounter(kind_name=kind_name)

    # Spend 1000 CPU megacycles counting entities.
    last_key = counter.last_key and db.Key(counter.last_key) or None
    count, last_key = count_records(kind, last_key, 1000)

    # Store the results.
    counter.count += count
    counter.last_key = last_key and str(last_key) or ''
    counter.put()
    self.write('%s count: %d (last: %r)' % (kind_name, counter.count, last_key))


if __name__ == '__main__':
  run([('/tasks/count', Count)], debug=True)
