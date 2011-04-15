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
import re
import sys
from xml.sax.saxutils import escape, quoteattr

from babel.messages import pofile

LOCALE_DIR = os.path.join(os.environ['APP_DIR'], 'locale')


def get_po_filename(locale):
    return os.path.join(LOCALE_DIR, locale, 'LC_MESSAGES', 'django.po')


def message_to_xmb(message):
    """Converts a single message object to a <msg> tag in the XMB format."""
    if 'python-format' in message.flags:
        xml_parts = []
        ph_index = 0
        for part in re.split('([^%]+|%%|%\(\w+\))', message.id):
            if part.startswith('%('):
                ph_index += 1
                xml_parts.append('<ph name="%s"><ex>%s</ex>%%%d</ph>' %
                                 (part[2:-1], part[2:-1], ph_index))
            elif part == '%%':
                xml_parts.append('%')
            else:
                xml_parts.append(escape(part))
        xml_message = ''.join(xml_parts) 
    else:
        xml_message = escape(message.id)
    return '<msg desc=%s>%s</msg>' % (
        quoteattr(' '.join(message.user_comments)), xml_message)


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('--format', type='choice', default='summary',
                      choices=['summary', 'po', 'xmb'], help='''\
specify 'summary' to get a summary of how many translations are missing,
or 'po' to get a template file in .po format to be filled in,
or 'xmb' to get a file of the missing translations in XMB format''')
    options, args = parser.parse_args()
    if args:
        parser.print_help()
        sys.exit(1)

    locales_by_missing_ids = {}  # for gathering identical sets of messages
    messages = {}  # message objects keyed by message id

    for locale in sorted(os.listdir(LOCALE_DIR)):
        if locale != 'en':
            filename = get_po_filename(locale)
            translations = pofile.read_po(open(filename))
            ids = set(message.id for message in translations)
            missing_ids = set(message.id for message in translations
                              if message.fuzzy or not message.string)
            locales_by_missing_ids.setdefault(
                tuple(sorted(missing_ids)), []).append(locale)

            # Remove all but the missing messages.
            for id in missing_ids:
                translations[id].string = ''  # remove fuzzy translations
                translations[id].flags = []  # remove the fuzzy flag
                messages[id] = translations[id]  # collect the message objects
            for id in ids - missing_ids:
                del translations[id]

            if options.format == 'po':
                # Print one big .po file with a section for each language.
                print '\n\n# LANGUAGE = %s\n' % locale
                pofile.write_po(sys.stdout, translations, no_location=True,
                                omit_header=True, sort_output=True)

    if options.format == 'xmb':
        # Produce one XMB file for each set of locales that have the same
        # set of missing messages.
        for missing_ids in sorted(
            locales_by_missing_ids, key=lambda t: (len(t), t)):
            filename = '.'.join(locales_by_missing_ids[missing_ids]) + '.xmb'
            if missing_ids:
                print '%s: %d missing' % (filename, len(missing_ids))
            file = open(filename, 'w')
            file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            file.write('<messagebundle>\n')
            for id in sorted(missing_ids):
                file.write(message_to_xmb(messages[id]) + '\n')
            file.write('</messagebundle>\n')
            file.close()

    if options.format == 'summary':
        # Summarize the missing messages, collecting together the locales
        # that have the same set of missing messages.
        for missing_ids in sorted(
            locales_by_missing_ids, key=lambda t: (len(t), t)):
            locales = ' '.join(locales_by_missing_ids[missing_ids])
            if missing_ids:
                print '%s: %d missing' % (locales, len(missing_ids))
                for id in sorted(missing_ids)[:10]:
                    id_repr = repr(id.encode('ascii', 'ignore'))
                    truncated = len(id_repr) > 70
                    print '    %s%s' % (id_repr[:70], truncated and '...' or '')
                if len(missing_ids) > 10:
                    print '    ... (%d more)' % (len(missing_ids) - 10)
            else:
                print '%s: ok' % locales
