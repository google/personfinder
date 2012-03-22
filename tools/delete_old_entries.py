#!/usr/bin/python2.5
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
    --host=mypersonfinder.appspot.com:80 \
    --repo=myrepo \
    --email=example@example.com \
    --password_path=password.txt \
    --expire_seconds=3600 \
    --action=preview

Example command to actually expire entries:
  $ ./tools/delete_old_entries.sh \
    --host=mypersonfinder.appspot.com:80 \
    --repo=myrepo \
    --email=example@example.com \
    --password_path=password.txt \
    --expire_seconds=3600 \
    --action=expire

NOTE: Execute delete_old_entries.sh instead of executing delete_old_entries.py
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


def expire_or_delete_person(person, action):
    """Expires or deletes a person record and associated data."""
    person_text = person_to_text(person)
    if action == 'expire' and person.is_original():
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
        db.delete([person] + person.get_notes(filter_expired=False))
        logging.info('Deleted completely: %s' % person_text)


def person_to_text(person):
    """Returns the person's information as string."""
    return ('id=%s first_name=%s last_name=%s last_modified=%s' % (
        person.get_record_id(),
        person.first_name,
        person.last_name,
        person.last_modified.isoformat(),
    ))


def main():
    logging.basicConfig(file=sys.stderr, level=logging.INFO)

    parser = optparse.OptionParser()
    parser.add_option('--host',
                      help='Host name. e.g. mypersonfinder.appspot.com:80')
    parser.add_option('--repo',
                      help='Name of the Person Finder repository.')
    parser.add_option('--email',
                      help=('Email address used to connect to AppEngine. '
                            'The user must be admin of the application.'))
    parser.add_option('--password_path',
                      help=('A text file which contains the password of '
                            'the user specified by --email.'))
    parser.add_option('--action',
                      type='choice',
                      choices=['expire', 'delete', 'preview'],
                      help=('Either of:\n'
                            'expire: Marks old entries as expired. They '
                            'disappear from front-end, but are kept in the '
                            'data store. They are automatically deleted '
                            'later. Note that clone records are deleted '
                            'immediately.\n'
                            'delete: Deletes old entries completely from the '
                            'data store immediately.\n'
                            'preview: Does nothing, but dumps entries which '
                            'will be deleted.'))
    parser.add_option('--expire_seconds',
                      type='int',
                      default=3600,
                      help=('Deletes/expires entries whose last modification '
                            'time is older than this value in seconds.'))
    parser.add_option('--id_whitelist',
                      help=('Comma-separated person IDs which are never '
                            'deleted. e.g. '
                            'example.personfinder.google.org/person.1234,'
                            'example.personfinder.google.org/person.5678'))
    parser.add_option('--include_expired',
                      default='false',
                      help='Includes expired entries as target.')
    parser.add_option('--dump_all',
                      default='false',
                      help='Also dumps entries which are not deleted.')
    options, args = parser.parse_args()

    if not options.host:
        logging.fatal('--host is missing.')
        sys.exit()
    if not options.repo:
        logging.fatal('--repo is missing.')
        sys.exit()
    if not options.email:
        logging.fatal('--email is missing.')
        sys.exit()
    if not options.password_path:
        logging.fatal('--password_path is missing.')
        sys.exit()
    if not options.action:
        logging.fatal('--action is missing.')
        sys.exit()

    f = open(options.password_path)
    password = f.read().rstrip('\n')
    f.close()
    if options.id_whitelist:
        id_whitelist = options.id_whitelist.split(',')
    else:
        id_whitelist = []

    remote_api.connect(options.host,
                       options.email, password)

    deleted_entries = []
    expire_time = (
            datetime.datetime.utcnow() -
            datetime.timedelta(seconds=options.expire_seconds))
    for person in model.Person.all_in_repo(
            options.repo, filter_expired=options.include_expired != 'true'):
        if (person.last_modified < expire_time and
                (not person.get_record_id() in id_whitelist)):
            logging.info('To be expired/deleted: %s' % person_to_text(person))
            # Appends the person to the list and deletes it later.
            # Deleting during iteration in the data store can cause unexpedted
            # result.
            deleted_entries.append(person)
        elif options.dump_all == 'true':
            logging.info('To be kept: %s' % person_to_text(person))

    if options.action in ('expire', 'delete'):
        for person in deleted_entries:
            expire_or_delete_person(person, options.action)


if __name__ == '__main__':
    main()
