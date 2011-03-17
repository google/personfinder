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

"""Unix command-line utility to download PFIF records from Atom feeds."""

__author__ = 'kpy@google.com (Ka-Ping Yee)'

import csv
import os
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


class FeedError(Exception):
    pass


# Parsers for both types of records.
class PersonParser:
    def parse_file(self, file):
        return pfif.parse_file(file)[0]

class NoteParser:
    def parse_file(self, file):
        return pfif.parse_file(file)[1]

parsers = {'person': PersonParser, 'note': NoteParser}


# Writers for both types of records.
class CsvWriter:
    def __init__(self, version, filename):
        try:
            self.pfif_version = pfif.PFIF_VERSIONS[version]
        except KeyError:
            raise FeedError('Invalid PFIF version: %s' % version)
        self.file = open(filename, 'w')
        self.writer = csv.DictWriter(self.file, self.fields)
        self.writer.writerow(dict((name, name) for name in self.fields))
        print >>sys.stderr, 'Writing CSV to: %s' % filename

    def write(self, records):
        for record in records:
          self.writer.writerow(dict(
              (name, value.encode('utf-8'))
              for name, value in record.items()))
        self.file.flush()

    def close(self):
        self.file.close()


class PersonCsvWriter(CsvWriter):
    fields = self.pfif_version.fields['person']


class NoteCsvWriter(CsvWriter):
    fields = self.pfif_version.fields['note']


class XmlWriter:
    def __init__(self, version, filename):
        try:
            self.pfif_version = pfif.PFIF_VERSIONS[version]
        except KeyError:
            raise FeedError('Invalid PFIF version: %s' % version)
        self.file = open(filename, 'w')
        self.file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.file.write('<pfif:pfif xmlns:pfif="%s">\n' % self.pfif_version.ns)
        print >>sys.stderr, 'Writing PFIF %s XML to: %s' % (version, filename)

    def write(self, records):
        for record in records:
            self.write_record(self.file, record, indent='  ')
        self.file.flush()

    def close(self):
        self.file.write('</pfif:pfif>\n')
        self.file.close()


class PersonXmlWriter(XmlWriter):
    write_record = self.pfif_version.write_person


class NoteXmlWriter(XmlWriter):
    write_record = self.pfif_version.write_note

writers = {
    'xml': {'person': PersonXmlWriter, 'note': NoteXmlWriter},
    'csv': {'person': PersonCsvWriter, 'note': NoteCsvWriter}
}


def download_batch(url, auth_key, min_entry_date, skip, parser):
    """Fetches and parses one batch of records from an Atom feed."""
    query_params = {
        'min_entry_date': min_entry_date,
        'skip': skip,
        'max_results': 200
        }
    # if an authorization key had been given, adds it to the query parameters
    if auth_key != '':
        query_params['key'] =  auth_key

    query = urllib.urlencode(query_params)
    if '?' in url:
        url += '&' + query
    else:
        url += '?' + query
    for attempt in range(5):
        try:
            return parser.parse_file(urllib.urlopen(url))
        except:
            continue
    raise RuntimeError('Failed to fetch %r after 5 attempts' % url)

def download_all_since(url, auth_key, min_entry_date, parser, writer):
    """Fetches and parses batches of records repeatedly until all records
    with an entry_date >= min_entry_date are retrieved."""
    start_time = time.time()
    print >>sys.stderr, '  entry_date >= %s:' % min_entry_date,
    records = download_batch(url, auth_key, min_entry_date, 0, parser)
    total = 0
    while records:
        writer.write(records)
        total += len(records)
        speed = total/float(time.time() - start_time)
        print >>sys.stderr, 'fetched %d (total %d, %.1f rec/s)' % (
            len(records), total, speed)
        min_entry_date = max(r['entry_date'] for r in records)
        skip = len([r for r in records if r['entry_date'] == min_entry_date])
        print >>sys.stderr, '  entry_date >= %s:' % min_entry_date,
        records = download_batch(url, auth_key, min_entry_date, skip, parser)
    print >>sys.stderr, 'done.'

def main():
    if (len(sys.argv) not in [7,8] or
        sys.argv[1] not in ['person', 'note'] or
        sys.argv[4] not in ['xml', 'csv']):
        raise SystemExit('''
Usage: %s <type> <feed_url> <min_entry_date> <format> <version> <filename> [auth_key]
    type: 'person' or 'note'
    feed_url: URL of the Person Finder Atom feed (as a shorthand, you can
        give just the domain name and the rest of the URL will be assumed)
    min_entry_date: retrieve only entries with entry_date >= this timestamp
        (specify the timestamp in RFC 3339 format)
    format: 'xml' or 'csv'
    version: PFIF version
    filename: filename of the file to write
    auth_key (optional): authorization key if data is protected with a read key
''' % sys.argv[0])

    type, feed_url, min_entry_date, format, version, filename = sys.argv[1:7]

    # retrieve authorization key if it has been specified
    auth_key = ''
    if len(sys.argv) == 7:
        auth_key = sys.argv[6]

    # If given a plain domain name, assume the usual feed path.
    if '/' not in feed_url:
        feed_url = 'https://' + feed_url + '/feeds/' + type
        print >>sys.stderr, 'Using feed URL: %s' % feed_url

    # If given a date only, assume midnight UTC.
    if 'T' not in min_entry_date:
        min_entry_date += 'T00:00:00Z'
        print >>sys.stderr, 'Using min_entry_date: %s' % min_entry_date

    if not version:
        version = pfif.DEFAULT_VERSION

    parser = parsers[type]()
    writer = writers[format][type](version, filename)

    print >>sys.stderr, 'Fetching %s records since %s:' % (type, min_entry_date)
    download_all_since(feed_url, auth_key, min_entry_date, parser, writer)
    writer.close()

if __name__ == '__main__':
    main()
