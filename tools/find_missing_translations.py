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

"""Finds the messages that are missing translations in the locale *.po files.

Usage:
    From the personfinder root directory:
    tools/find_missing_translations.py

PO file format:
    http://www.gnu.org/software/hello/manual/gettext/PO-Files.html
"""

import optparse
import os
import sys

from babel.messages import pofile

LOCALE_DIR = os.path.join(os.environ['APP_DIR'], 'locale')


def get_po_filename(locale):
    return os.path.join(LOCALE_DIR, locale, 'LC_MESSAGES', 'django.po')


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('--template', action='store_true', default=False,
                      help='format output as a template to be filled in')
    options, args = parser.parse_args()
    if args:
        parser.print_help()
        sys.exit(1)

    for locale in sorted(os.listdir(LOCALE_DIR)):
        if locale != 'en':
            filename = get_po_filename(locale)
            translations = pofile.read_po(open(filename))
            ids = set(message.id for message in translations)
            missing_ids = set(message.id for message in translations
                              if message.fuzzy or not message.string)
            if options.template:
                print '\n\n# LANGUAGE = %s\n' % locale

                # Print out just the missing messages.
                for id in missing_ids:
                    translations[id].string = ''  # remove fuzzy translations
                    translations[id].flags = []
                for id in ids - missing_ids:
                    del translations[id]
                pofile.write_po(sys.stdout, translations, no_location=True,
                                omit_header=True, sort_output=True)
            else:
                if missing_ids:
                    print '%s: %d missing' % (locale, len(missing_ids))
                else:
                    print '%s: ok' % locale
