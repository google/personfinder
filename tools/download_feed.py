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

"""Command-line utility to download PFIF records from Atom feeds."""

__author__ = 'kpy@google.com (Ka-Ping Yee)'

import csv
import optparse
import os
import re
import sys
import time

# This script is in a tools directory below the root project directory.
TOOLS_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = os.path.dirname(TOOLS_DIR)
APP_DIR = os.path.join(PROJECT_DIR, 'app')
# Make imports work for Python modules that are part of this app.
sys.path.append(APP_DIR)

import pfif
import urllib
import urlparse

PFIF = pfif.PFIF_VERSIONS[pfif.PFIF_DEFAULT_VERSION]

quiet_mode = False


def log(message):
    """Optionally prints a status message to sys.stderr."""
    if not quiet_mode:
        sys.stderr.write(message)
        sys.stderr.flush()

# Parsers for both types of records.
class PersonParser:
    def parse_file(self, file):
        # Do not rename fields to PFIF 1.4
        return pfif.parse_file(file, rename_fields=False)[0]

class NoteParser:
    def parse_file(self, file):
        # Do not rename fields to PFIF 1.4
        return pfif.parse_file(file, rename_fields=False)[1]

parsers = {'person': PersonParser, 'note': NoteParser}


# Writers for both types of records.
class CsvWriter:
    def __init__(self, file, fields=None):
        self.file = file
        if fields:
            self.fields = fields
        self.writer = csv.DictWriter(self.file, self.fields)
        self.writer.writerow(dict((name, name) for name in self.fields))

    def write(self, records):
        for record in records:
            self.writer.writerow(dict(
                (name, record.get(name, '').encode('utf-8'))
                for name in self.fields))
        self.file.flush()

    def close(self):
        self.file.close()


class PersonCsvWriter(CsvWriter):
    fields = PFIF.fields['person']


class NoteCsvWriter(CsvWriter):
    fields = PFIF.fields['note']


class XmlWriter:
    def __init__(self, file, fields=None):
        self.file = file
        self.file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.file.write('<pfif:pfif xmlns:pfif="%s">\n' % PFIF.ns)

    def write(self, records):
        for record in records:
            self.write_record(self.file, record, indent='  ')
        self.file.flush()

    def close(self):
        self.file.write('</pfif:pfif>\n')
        self.file.close()


class PersonXmlWriter(XmlWriter):
    write_record = PFIF.write_person


class NoteXmlWriter(XmlWriter):
    write_record = PFIF.write_note

writers = {
    'xml': {'person': PersonXmlWriter, 'note': NoteXmlWriter},
    'csv': {'person': PersonCsvWriter, 'note': NoteCsvWriter}
}


def fetch_records(parser, url, **params):
    """Fetches and parses one batch of records from an Atom feed."""
    query = urllib.urlencode(dict((k, v) for k, v in params.items() if v))
    if query:
        url += ('?' in url and '&' or '?') + query
    for attempt in range(5):
        try:
            return parser.parse_file(urllib.urlopen(url))
        except:
            continue
    raise RuntimeError('Failed to fetch %r after 5 attempts' % url)

def download_file(parser, writer, url, key=None):
    """Fetches and writes one batch of records."""
    start_time = time.time()
    records = fetch_records(parser, url, key=key)
    writer.write(records)
    speed = len(records)/float(time.time() - start_time)
    log('Fetched %d (%.1f rec/s).\n' % (len(records), speed))

def download_since(parser, writer, url, min_entry_date, key=None):
    """Fetches and writes batches of records repeatedly until all records
    with an entry_date >= min_entry_date are retrieved."""
    start_time = time.time()
    total = skip = 0
    while True:
        log('Records with entry_date >= %s: ' % min_entry_date)
        records = fetch_records(parser, url, key=key, max_results=200,
                                min_entry_date=min_entry_date, skip=skip)
        writer.write(records)
        total += len(records)
        speed = total/float(time.time() - start_time)
        log('%d (total %d, %.1f rec/s).\n' % (len(records), total, speed))
        if not records:
            break
        min_entry_date = max(r['entry_date'] for r in records)
        skip = len([r for r in records if r['entry_date'] == min_entry_date])
    log('Done.\n')

def main(*args):
    parser = optparse.OptionParser(usage='''%prog [options] <feed_url>

Downloads the records in a PFIF Person or Note feed into an XML or CSV file.
By default, this fetches the specified <feed_url> once and saves the contents.
If you specify the --min_entry_date option, this will make multiple fetches
as necessary to retrieve all the records with an entry_date >= min_entry_date.
Examples:

  # Make one request for recent Person records in the 'test-nokey' repository
  # and print the XML to stdout.  (This gets the last 200 entered records.)
  % %prog https://www.google.org/personfinder/test-nokey/feeds/person

  # Convert the Person records in a PFIF XML file to CSV format.
  % %prog https://example.org/data.xml --out=data.csv

  # Download all the Person records entered since Jan 1, 2010 to a CSV file.
  % %prog --min_entry_date=2010-01-01 --out=persons.csv \\
        https://www.google.org/personfinder/test-nokey/feeds/person

  # Download all the Note records entered since Jan 1, 2010 to an XML file.
  % %prog --notes --min_entry_date=2010-01-01 --out=notes.xml \\
        https://www.google.org/personfinder/test-nokey/feeds/note''')
    parser.add_option('-n', '--notes', action='store_true',
                      help='download Notes (default: download Persons)')
    parser.add_option('-f', '--format',
                      help='"xml" or "csv" (default: "xml", unless --out is ' +
                           'specified with a filename ending in ".csv")')
    parser.add_option('-F', '--fields',
                      help='comma-separated list of fields to include in the ' +
                           'output (CSV only, default: include everything)')
    parser.add_option('-o', '--out',
                      help='output filename (default: write output to stdout)')
    parser.add_option('-q', '--quiet', action='store_true',
                      help='don\'t print status messages')
    parser.add_option('-m', '--min_entry_date',
                      help='for Person Finder only: '
                           'download all records with entry_date >= this date '
                           '(UTC, in yyyy-mm-dd or yyyy-mm-ddThh:mm:ss format)')
    parser.add_option('-k', '--key', help='for Person Finder only: API key')
    options, args = parser.parse_args(list(args))

    # Get the feed URL.
    if len(args) != 1:
        parser.error('Feed URL not specified; try -h for help')
    feed_url = args[0]

    # Select the record type.
    type = options.notes and 'note' or 'person'

    # Determine the output format.
    default_format = 'xml'
    if options.out and options.out.lower().endswith('.csv'):
        default_format = 'csv'
    if options.format and options.format not in ['xml', 'csv']:
        parser.error('Format should be "xml" or "csv"; try -h for help')
    format = options.format or default_format

    # Validate the selected fields.
    fields = options.fields and options.fields.split(',')
    if fields:
        if format != 'csv':
            parser.error('Selecting fields only works for CSV; try -h for help')
        for field in fields:
            if field not in PFIF.fields[type]:
                parser.error('Invalid field %r (available fields: %s)' %
                             (field, ', '.join(PFIF.fields[type])))

    # Validate min_entry_date.
    min_entry_date = options.min_entry_date
    if min_entry_date:
        min_entry_date = min_entry_date.rstrip('Z')
        if not re.match(r'\d{4}-\d\d-\d\d(T\d\d:\d\d:\d\d)?$', min_entry_date):
            parser.error('Invalid date; try -h for help')
        if 'T' not in min_entry_date:
            min_entry_date += 'T00:00:00Z'
        if 'Z' not in min_entry_date:
            min_entry_date += 'Z'

    global quiet_mode
    quiet_mode = options.quiet

    # Open the output file.
    if options.out:
        file = open(options.out, 'w')
        log('Writing PFIF %s %s %s records to: %s\n' %
            (PFIF.version, format.upper(), type, options.out))
    else:
        file = sys.stdout
        log('Writing PFIF %s %s %s records to stdout.\n' %
            (PFIF.version, format.upper(), type))

    parser = parsers[type]()
    writer = writers[format][type](file, fields=fields)

    if min_entry_date:
        download_since(parser, writer, feed_url, min_entry_date, options.key)
    else:
        download_file(parser, writer, feed_url, options.key)
    writer.close()

if __name__ == '__main__':
    main(*sys.argv[1:])
