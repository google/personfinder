#!/usr/bin/python2.7
# Copyright 2012 Google Inc.
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

"""Deletes or expires person entries older than the specified age e.g. 1 hour.

Example command to preview expired/deleted entries:
  $ ./tools/delete_old_entries.sh \
    mypersonfinder.appspot.com \
    --repo=myrepo \
    --email=example@example.com \
    --min_age_seconds=3600 \
    --action=preview

Example command to actually expire entries:
  $ ./tools/delete_old_entries.sh \
    mypersonfinder.appspot.com \
    --repo=myrepo \
    --email=example@example.com \
    --min_age_seconds=3600 \
    --action=expire

NOTE: Execute delete_old_entries instead of executing delete_old_entries.py
      directly.
"""

import datetime
import logging
import optparse
import os
import sys
import time

from google.appengine.ext import db

import model
import pfif
import remote_api
import utils


# Max number of entities in one fetch. Fetch fails if we fetch too many
# entities at once.
MAX_ENTITIES_PER_REQUEST = 100


def expire_person(person):
    """Expires a person record and associated data."""
    person_text = person_to_text(person)
    if person.is_original():
        # Set the expiry_date to now, and set is_expired flags to match.
        # (The externally visible result will be as if we overwrote the
        # record with an expiry date and blank fields.)
        person.expiry_date = utils.get_utcnow()
        person.put_expiry_flags()
        logging.info('Expired: %s' % person_text)

    else:
        # For a clone record, we don't have authority to change the
        # expiry_date, so we just delete the record now.  (The externally
        # visible result will be as if we had never received a copy of it.)
        person.delete_related_entities(delete_self=True)
        logging.info('Deleted completely: %s' % person_text)


def person_to_text(person):
    """Returns the person's information as string."""
    return ('id=%s full_name=%s entry_date=%s' % (
        person.get_record_id(),
        person.primary_full_name,
        person.entry_date.isoformat(),
    ))


def main():
    logging.basicConfig(file=sys.stderr, level=logging.INFO)

    parser = optparse.OptionParser(usage='%prog [options] <appserver_url>')
    parser.add_option('--host',
                      help='Host name. e.g. mypersonfinder.appspot.com:80')
    parser.add_option('--repo',
                      help='Name of the Person Finder repository.')
    parser.add_option('--email',
                      help=('Email address used to connect to AppEngine. '
                            'The user must be admin of the application.'))
    parser.add_option('--password_path',
                      help=('A text file which contains the password of '
                            'the user specified by --email. If omitted, '
                            'the command prompts you to input password.'))
    parser.add_option('--action',
                      type='choice',
                      choices=['expire', 'preview'],
                      help=('Either of:\n'
                            'expire: Marks old entries as expired. They '
                            'disappear from the UI and the API, but are kept '
                            'in the data store. They are automatically '
                            'deleted later. Note that clone records are '
                            'deleted immediately.\n'
                            'preview: Does nothing, but dumps entries which '
                            'will be marked as expired.'))
    parser.add_option('--min_age_seconds',
                      type='int',
                      default=3600,
                      help=('Expires entries whose entry_date '
                            'is older than this value in seconds.'))
    parser.add_option('--id_whitelist',
                      help=('Comma-separated person IDs which are never '
                            'deleted. e.g. '
                            'example.personfinder.google.org/person.1234,'
                            'example.personfinder.google.org/person.5678'))
    parser.add_option('--dump_all',
                      default='false',
                      help='Also dumps entries which are not deleted.')
    parser.add_option('--include_expired',
                      default='false',
                      help='Includes expired entries on --dump_all.')
    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error('Just one argument must be given.')
    host = args[0]
    if not options.repo:
        parser.error('--repo is missing.')
    if not options.action:
        parser.error('--action is missing.')

    if options.password_path:
      f = open(options.password_path)
      password = f.read().rstrip('\n')
      f.close()
    else:
      password = None

    if options.id_whitelist:
        id_whitelist = options.id_whitelist.split(',')
    else:
        id_whitelist = []

    remote_api.connect(host, options.email, password)

    expired_entries = []
    max_entry_date = (
            datetime.datetime.utcnow() -
            datetime.timedelta(seconds=options.min_age_seconds))
    query = model.Person.all_in_repo(
            options.repo, filter_expired=options.include_expired != 'true')
    if options.dump_all != 'true':
        query.filter('entry_date <=', max_entry_date)

    while True:
        people = query.fetch(MAX_ENTITIES_PER_REQUEST)
        if not people:
            break
        for person in people:
            # Checks entry_date again because the filter is not applied when
            # --dump_all=true.
            if (person.entry_date <= max_entry_date and
                person.get_record_id() not in id_whitelist):
                logging.info('To be expired: %s' % person_to_text(person))
                expired_entries.append(person)
            elif options.dump_all == 'true':
                logging.info('To be kept: %s' % person_to_text(person))
        query = query.with_cursor(query.cursor())

    if options.action == 'expire':
        for person in expired_entries:
            expire_person(person)


if __name__ == '__main__':
    main()
