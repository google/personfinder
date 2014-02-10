#!/usr/bin/python2.7
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

# The app's locale directory, containing one subdirectory for each locale.
LOCALE_DIR = os.path.join(os.environ['APP_DIR'], 'locale')

# A pattern that tokenizes a string with Python-style percent-substitution.
PYTHON_FORMAT_RE = re.compile(r'([^%]+|%%|%\(\w+\)s)')


def get_po_filename(locale):
    return os.path.join(LOCALE_DIR, locale, 'LC_MESSAGES', 'django.po')


# For more information on the XMB format, see:
# http://cldr.unicode.org/development/development-process/design-proposals/xmb
def message_to_xmb(message):
    """Converts a single message object to a <msg> tag in the XMB format."""
    # TODO(lschumacher) handle plurals
    message_id = message.id
    if isinstance(message_id, tuple):
        message_id = message_id[0]

    if 'python-format' in message.flags:
        xml_parts = []
        ph_index = 0
        for token in PYTHON_FORMAT_RE.split(message_id):
            if token.startswith('%(') and token.endswith(')s'):
                name = token[2:-2]
                ph_index += 1
                xml_parts.append('<ph name="%s"><ex>%s</ex>%%%d</ph>' %
                                 (name, name, ph_index))
            elif token == '%%':
                xml_parts.append('%')
            elif token:
                xml_parts.append(escape(token))
        xml_message = ''.join(xml_parts) 
    else:
        xml_message = escape(message_id)
    return '<msg desc=%s>%s</msg>' % (
        quoteattr(' '.join(message.user_comments)), xml_message)


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('--format', type='choice', default='summary',
                      choices=['summary', 'list', 'po', 'xmb'], help='''\
specify 'summary' to get a summary of how many translations are missing,
or 'list' to get a list of all the missing messages,
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
                              if message.id and (not message.string or
                              message.fuzzy))
            locales_by_missing_ids.setdefault(
                tuple(sorted(missing_ids)), []).append(locale)

            # Remove all but the missing messages.
            for id in missing_ids:
                if not translations[id]: 
                    print >>sys.stderr, 'missing id: %s' % id
                    continue
                translations[id].string = ''  # remove fuzzy translations
                if 'fuzzy' in translations[id].flags:  # remove the fuzzy flag
                    translations[id].flags.remove('fuzzy')
                messages[id] = translations[id]  # collect the message objects
            for id in ids - missing_ids:
                del translations[id]

    if options.format == 'po':
        # Produce one po file for each set of locales that have the same
        # set of missing messages.  This is for use as the template 
        # to merge_messages.
        for missing_ids in sorted(locales_by_missing_ids,
                                  key=lambda t: (len(t), t)):
            filename = '.'.join(locales_by_missing_ids[missing_ids]) + '.po'
            translations = pofile.read_po(open(get_po_filename('en')))
            ids = set(message.id for message in translations)
            if missing_ids:
                print '%s: %d missing' % (filename, len(missing_ids))
            new_file = open(filename, 'w')
            for id in ids - set(missing_ids):
                del translations[id]
            pofile.write_po(new_file, translations, no_location=True,
                            omit_header=True, sort_output=True)
            new_file.close()
        print '\n\n# LANGUAGE = %s\n' % locale

    if options.format == 'xmb':
        # Produce one XMB file for each set of locales that have the same
        # set of missing messages.
        for missing_ids in sorted(locales_by_missing_ids,
                                  key=lambda t: (len(t), t)):
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
                    if isinstance(id, tuple):
                        id = id[0]
                    id_repr = repr(id.encode('ascii', 'ignore'))
                    truncated = len(id_repr) > 70
                    print '    %s%s' % (id_repr[:70], truncated and '...' or '')
                if len(missing_ids) > 10:
                    print '    ... (%d more)' % (len(missing_ids) - 10)
            else:
                print '%s: ok' % locales

    if options.format == 'list':
        # List all the missing messages, collecting together the locales
        # that have the same set of missing messages.
        for missing_ids in sorted(
            locales_by_missing_ids, key=lambda t: (len(t), t)):
            locales = ' '.join(locales_by_missing_ids[missing_ids])
            if missing_ids:
                print '%s: %d missing' % (locales, len(missing_ids))
                for id in sorted(missing_ids):
                    print '    ' + repr(id.encode('ascii', 'ignore'))
            else:
                print '%s: ok' % locales
