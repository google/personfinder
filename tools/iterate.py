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


# regex for matching a url that links to our photo db.
# match group 1 will be the id of the photo.
PHOTO_REGEX = re.compile('http://.*\.person-finder.appspot.com/photo\?id=(.*)')

class PhotoFilter(object):
    """Utility for finding photos with dangling URLs.

    Use filter_photo_url as the parameter to iterate, ppl_count will contain 
    count of persons updated.
    """

    # batch size.
    MAX_PPL_COUNT = 1000

    def __init__(self, out_file):
        """Write list of people updated to out_file."""
        self.ppl = []
        self.ppl_count = 0
        self.output = out_file

    def write_ppl(self):
        """Write record of users modified """
        for p in self.ppl:
            if p.photo_url and p.photo:
                self.output.write('%s: %s; %s\n' % (p.record_id, p.photo_url, 
                                                    p.photo.id()))

    def save_person(self, person):
        """Handle batch write back to db."""
        if person:
            self.ppl.append(person)
            sefl.ppl_count += 1
        if not person or len(self.ppl) >= MAX_PPL_COUNT:
            if self.ppl:
                print >>sys.stderr, 'saving %s records' % len(self.ppl)
                db.put(self.ppl)
                self.write_ppl()
            self.ppl = []

    def filter_photo_url(self, p):
        """Decide if this person needs its photo link updated. 

        Use None parameter to flush results at the end."""

        if not p:
            # write out remaining records.
            self.save_person()
            return
        if p.photo_url:
            match = PHOTO_REGEX.match(p.photo_url)
            if match:
                try:
                    photo_id = int(match.group(1))
                    p.photo = db.Key('Photo', photo_id)
                    save_person(p)
                except Exception:
                    pass


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
