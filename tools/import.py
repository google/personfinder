#!/usr/bin/python2.5
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unix command-line utility: import CSV files into the datastore."""

import remote_api

import csv
import importer
import sys

SHOW_ERRORS = 5

def import_from_file(host, subdomain, kind, converter, filename):
    print '%s: importing %s records from %s' % (host, kind, filename)
    written, skipped, total = importer.import_records(
        subdomain, source_domain, converter,
        importer.utf8_decoder(csv.DictReader(open(filename))))
    for error, record in skipped[:SHOW_ERRORS]:
        print '    - %s: %r' % (error, record)
    if len(skipped) > SHOW_ERRORS:
        print '    (more errors not shown)'

    print 'wrote %d of %d (skipped %d with errors)' % (
        written, total, len(skipped))

if __name__ == '__main__':
    if len(sys.argv) < 6:
        raise SystemExit(
            'Usage: %s app_id host subdomain source_domain person.csv note.csv'
            % sys.argv[0])
    app_id, host, subdomain, source_domain, person_file, note_file = \
        sys.argv[1:]
    host = remote_api.connect(host, app_id)
    if person_file:
        import_from_file(
            host, subdomain, 'Person', importer.create_person, person_file, None)
    if note_file:
        import_from_file(
            host, subdomain, 'Note', importer.create_note, note_file, None)
