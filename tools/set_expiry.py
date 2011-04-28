#!/usr/bin/python2.5
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

"""Quick and dirty tool for setting expiry date.  Mostly a model for how to 
iterate over the data store"""

__author__ = 'lschumacher@google.com (Lee Schumacher) and kpy@google.com (Ka-Ping Yee)'


default_expiry_date = datetime.datetime(2011, 5, 31)
from model import Person

def fix_expiry(query, records=1000):
    """iterate through the query, set expiry_date to default_expiry_date"""
    start = time.time()
    results = query.fetch(records)
    n = 0
    while results:
        save = []
        for person in results:
            n += 1
            if not person.expiry_date:
                person.expiry_date = default_expiry_date
                save.append(person)
        if save:
            num_saved = len(save)
            print 'saving %s records, ending with %s' % (
                num_saved, save[num_saved-1].key)
            db.put(save)
        print '%.1f: %s' % (time.time() - start, n)
        results = query.with_cursor(query.cursor()).fetch(records)

def make_key(k):
    """Return a person key."""
    return db.Key.from_path('Person', k)

def next_person(key, reverse=False):
    """Find the next person after this key."""
    stop_key = make_key(key)
    query = Person.all(filter_expired=False, keys_only=True)
    query.filter('__key__ >', stop_key)
    if reverse:
        query.order('-__key__')
    else:
        query.order('__key__')
    result = query.fetch(1)
    if result:
        return result[0]
