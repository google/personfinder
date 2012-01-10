#!/usr/bin/env python
# Copyright 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import re
import sys
from google.appengine.ext import db

def iterate(query, callback=lambda x: x, batch_size=1000, verbose=True):
    """Utility for iterating over a query, applying the callback to each row."""
    start = time.time()
    count = 0
    results = query.fetch(batch_size)
    while results:
        rstart = time.time()
        for row in results:
            output = callback(row)
            if output:
                print output
            count += 1
        if verbose:
            print '%s rows processed in %.1fs' % (count, time.time() - rstart)
            print 'total time: %.1fs' % (time.time() - start)
        results = query.with_cursor(query.cursor()).fetch(batch_size)
    callback()
    print 'total rows: %s, total time: %.1fs' % (count, time.time() - start)


def dangling_pic(pic):
    """Filter for photos with no referencing person."""
    ppl = pic.person_set.fetch(100)
    if not ppl:
        return pic.key().id()

ids = []
def dangling_pic_list(pic):
    """Track photos with no referencing person."""
    if pic and not pic.person_set.count():
      ids.append(pic.key().id())
