#!/usr/bin/python2.5
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
Merge translations into the existing message files.

This script automates the task of integrating a new batch of translations
from the professional translators.  It accepts as an argument a directory
with one sub-directory per locale, and each of those directories containing
a single updated .po file, for example, /path/to/professional/translations
would look like:

/path/to/professional/translations/ar/django.po
/path/to/professional/translations/bg/django.po
/path/to/professional/translations/ca/django.po
...

Each of these django files are scanned and the new msgstr's are replaced into
the existing django.po files in app/locale/$LOCALE/LC_MESSAGES/django.po.

Usage:
    ../tools/merge_messages /path/to/professional/translations
"""

import codecs
import os
import re
import sys

DJANGO_STRING_PATTERN = '''['"](.*)['"]\s*$'''

class Message:
    """Describes a message"""

    def __init__(self, msgid, msgstr, refs, format):
        self.msgid = msgid
        self.msgstr = msgstr
        self.refs = refs
        self.format = format

    def __eq__(self, other):
        """Only message id factors into equality and hash."""
        if not isinstance(other, type(self)):
            return False
        return self.msgid == other.msgid

    def __hash__(self):
        """Only message id factors into equality and hash."""
        return hash(self.msgid)

    def __cmp__(self, other):
        """Compare based on msgid."""
        if type(other) is not type(self):
            return NotImplemented
        return cmp(self.msgid, other.msgid)

    def __repr__(self):
        return '[%r, %r, %r, %r]' % (
            self.msgid, self.msgstr, self.refs, self.format)

def parse_django_po(po_filename):
    """Return the header from the django-generated .po file
       and a dict from msgid to msgstr"""
    # Holds the header at the top of the django po file
    header = ''
    # A sentinel to know when to stop considering lines part of the header
    header_done = False
    # The return dict of msgid to Message
    msgid_to_msg = {}
    # The current file:line_num ref, which occurs on a previous line to it's
    # corresponding message
    current_refs = None
    # The current msgstr
    current_msgstr = None
    # The current msgid
    current_msgid = None
    # The current format string
    current_format = None

    for line in codecs.open(po_filename, encoding='utf-8'):
        if line.startswith('#:') or line.startswith('#.'):
            header_done = True
        if not header_done:
            if line.startswith('"POT-Creation-Date'):
                # The POT-Creation-Date line changes on every run to include
                # the current date and time, creating unnecessary changesets.
                # Skipping this line makes extract_messages idempotent.
                continue
            header += line
            continue
        line = line.strip()
        if not line.strip() and current_msgid:
            msgid_to_msg[current_msgid] = Message(
                current_msgid, current_msgstr, current_refs, current_format)
            current_msgid = None
            current_msgstr = None
            current_refs = None
            current_format = None
        elif line.startswith('#:'):
            current_refs = line[3:]
        elif line.startswith('#,'):
            current_format = line[3:]
        elif line.startswith('msgstr'):
            current_msgstr = parse_po_tagline(line, 'msgstr')
        elif current_msgstr is not None:
            current_msgstr += parse_po_tagline(line)
        elif line.startswith('msgid'):
            current_msgid = parse_po_tagline(line, 'msgid')
        elif current_msgid is not None:
            current_msgid += parse_po_tagline(line)

    if current_msgid:
        msgid_to_msg[current_msgid] = Message(
            current_msgid, current_msgstr, current_refs, current_format)

    return (header, msgid_to_msg)

def parse_po_tagline(line, tag=''):
    """Parses a line consisting of the given tag followed by a quoted string."""
    match = re.match((tag and (tag + ' ') or '') + DJANGO_STRING_PATTERN, line)
    return match and match.group(1) or ''

def output_po_file(output_filename, header, msgid_to_msg):
    """Write a po file to the file specified by output_filename, using the
    given header text and a msgid_to_msg dictionary that maps each msgid to
    msg where the message appears."""
    output = codecs.open(output_filename, 'w', 'utf-8')
    output.write(header)

    for msgid, msg in sorted(msgid_to_msg.iteritems()):
        print >>output, '#: %s' % msg.refs
        if msg.format:
            print >>output, '#, %s' % msg.format
        elif has_sh_placeholders(msgid):
            print >>output, '#, sh-format'
        elif has_python_placeholders(msgid):
            print >>output, '#, python-format'
        print >>output, 'msgid "%s"' % msgid
        print >>output, 'msgstr "%s"\n' % msg.msgstr
    output.close()

def has_sh_placeholders(message):
    """Returns true if the message has placeholders."""
    return re.search(r'\$\{(\w+)\}', message) is not None

def has_python_placeholders(message):
    """Returns true if the message has placeholders."""
    return re.search(r'%\(\w+\)s', message) is not None

def merge(to_file, from_file, out_file):
    """Merge translations from from_file into to_file and write to out_file."""
    to_header, to_map = parse_django_po(to_file)
    from_header, from_map = parse_django_po(from_file)

    for (msgid, msg) in to_map.iteritems():
        if msgid in from_map:
            print 'msgid:"%s"\n-  msgstr:"%s"\n+  msgstr:"%s"\n' % (
                msgid, to_map[msgid].msgstr, from_map[msgid].msgstr)
            to_map[msgid].msgstr = from_map[msgid].msgstr
            to_map[msgid].format = None

    output_po_file(out_file, to_header, to_map)


if __name__ == '__main__':
    if len(sys.argv) == 4:
        merge(sys.argv[1], sys.argv[2], sys.argv[3])
        sys.exit(0)
    elif len(sys.argv) != 2:
        print 'Usage: %s trans_dir' % sys.argv[0]
        sys.exit(1)

    trans_path = sys.argv[1]

    from_filenames = dict(
        (locale.replace('-', '_'), os.path.join(trans_path, locale,
                              os.listdir(os.path.join(trans_path, locale))[0]))
        for locale in os.listdir(trans_path)
        if os.path.isdir(os.path.join(trans_path, locale)))

    os.chdir(os.environ['APP_DIR'])
    to_filenames = dict(
        (locale, os.path.join('locale', locale, 'LC_MESSAGES', 'django.po'))
        for locale in os.listdir('locale'))

    for (locale, from_filename) in from_filenames.iteritems():
        if locale in to_filenames:
            print 'LANGUAGE %s' % locale
            merge(to_filenames[locale], from_filename, to_filenames[locale])
