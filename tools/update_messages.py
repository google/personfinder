#!/usr/bin/env python
# Copyright 2010 Google Inc.
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

"""
Extract messages from the source files, update all the .po files if needed,
and compile the .po files to produce .mo files.

This script first runs makemessages to produce an English .po file template.
If this new .po file has a different set of messages than the existing
English .po file, then this script updates all the .po files for the other
languages with the newly extracted messages, preserving the translations from
the existing files.

To minimize unnecessary changes from version to version, the resulting .po
files have no "#: filename:line" comments and the messages are sorted by msgid.

Usage:
    ../tools/update_messages

The arguments should be options to pass to the django "makemessages" command.
If no arguments are specified, -e '.py,.html,.txt,.template' is assumed.
"""

import datetime
import os
import sys

from babel.messages import pofile
from django.core import management

LOCALE_DIR = os.path.join(os.environ['APP_DIR'], 'locale')


def print_flush(text):
    sys.stdout.write(text)
    sys.stdout.flush()


def get_po_filename(locale):
    return os.path.join(LOCALE_DIR, locale, 'LC_MESSAGES', 'django.po')


def write_clean_po(filename, catalog):
    """Writes out a .po file in a canonical way, to minimize spurious diffs."""
    catalog.creation_date = datetime.datetime(2000, 1, 1, 0, 0, 0)
    file = open(filename, 'w')
    pofile.write_po(file, catalog,
                    no_location=True, sort_output=True, ignore_obsolete=True)
    file.close()


def update_po(locale, new_msgids, header_comment):
    """Updates a .po file to contain the given set of messages and the given
    header comment, and returns the number of missing translations."""
    filename = get_po_filename(locale)
    translations = pofile.read_po(open(filename))
    for message in translations:  # remove unused messages
        if message.id and message.id not in new_msgids:
            del translations[message.id]
    for id in new_msgids:  # add new messages
        if id and id not in translations:
            translations.add(id, '')
    translations.header_comment = header_comment
    write_clean_po(filename, translations)
    return len([message for message in translations
                if message.fuzzy or not message.string])


def django_admin(*args):
    """Executes a django admin tool from the app directory."""
    cwd = os.getcwd()
    os.chdir(os.environ['APP_DIR'])
    management.execute_from_command_line(['django-admin.py'] + list(args))
    os.chdir(cwd)


if __name__ == '__main__':
    args = sys.argv[1:] or ['-e', '.py,.html,.txt,.template']
    if '-h' in args or '--help' in args:
        print __doc__
        sys.exit(1)
    force = '-f' in args or '--force' in args
    args = [arg for arg in args if arg not in ['-f', '--force']]

    # Get the set of messages in the existing English .po file.
    en_filename = get_po_filename('en')
    old_template = pofile.read_po(open(en_filename))
    old_msgids = set(message.id for message in old_template)

    # Run makemessages to update the English .po file.
    django_admin('makemessages', '-l', 'en', *args)

    # Get the set of messages in the new English .po file.
    new_template = pofile.read_po(open(en_filename))
    new_msgids = set(message.id for message in new_template)

    # Write the English .po file in sorted order without file references.
    write_clean_po(en_filename, new_template)

    # Update the other .po files if necessary.
    if new_msgids != old_msgids or force:
        print '%d messages added, %d removed.' % (
            len(new_msgids - old_msgids), len(old_msgids - new_msgids))
        print_flush('Updating:')
        missing = {}
        for locale in sorted(os.listdir(LOCALE_DIR)):
            if locale != 'en':
                print_flush(' ' + locale)
                missing[locale] = update_po(
                    locale, new_msgids, new_template.header_comment)
        print
        for locale in sorted(missing):
            print '%s: %d missing' % (locale, missing[locale])
    else:
        print 'No messages have changed.'

    # Run compilemessages to generate all the .mo files.
    sys.stderr = open('/dev/null', 'w')  # suppress the listing of all files
    django_admin('compilemessages')
