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
Merge translations from a set of .po or XMB files into a set of .po files.

Usage:
    ../tools/merge_messages <source-dir> <template-file>
    ../tools/merge_messages <source-dir> <template-file> <target-dir>
    ../tools/merge_messages <source-po-file> <template-file> <target-po-file>

<source-dir> should be a directory containing a subdirectories named with
locale codes (e.g. pt_BR).  For each locale, this script looks for the first
.po or .xml file it finds anywhere under <source-dir>/<locale-code>/ and
adds all its messages and translations to the corresponding django.po file
in the target directory, at <target-dir>/<locale-code>/LC_MESSAGES/django.po.

<template-file> is the output file from running:
'find_missing_translations --format=po'
With the name that corresponds to the --format=xmb output.
Make sure to run this in a tree that corresponds to the version used for
generating the xmb file or the resulting merge will be wrong.  See 
validate_merge for directions on verifying the merge was correct.

If <target-dir> is unspecified, it defaults to the app/locale directory of
the current app.  Alternatively, you can specify a single source file and
a single target file to update.

When merging messages from a source file into a target file:

  - Empty messages and messages marked "fuzzy" in the source file are ignored.

  - Translations in the source file will replace any existing translations
    for the same messages in the target file.

  - Other translations in the source file will be added to the target file.

  - If the target file doesn't exist, it will be created.

  - To minimize unnecessary changes from version to version, the target file
    has no "#: filename:line" comments and the messages are sorted by msgid.
"""
from __future__ import print_function

import babel.messages
from babel.messages import pofile
import codecs
import os
import sys
import xml.sax


class XmbCatalogReader(xml.sax.handler.ContentHandler):
    """A SAX handler that populates a babel.messages.Catalog with messages
    read from an XMB file."""

    def __init__(self, template):
        """template should be a Catalog containing the untranslated messages
        in the same order as the corresponding messages in the XMB file."""
        self.tags = []
        self.catalog = babel.messages.Catalog()
        self.iter = iter(template)
        assert self.iter.next().id == ''  # skip the blank metadata message

    def startElement(self, tag, attrs):
        self.tags.append(tag)
        if tag == 'msg':
            self.string = ''
            self.message = babel.messages.Message(self.iter.next().id)
        if tag == 'ph':
            self.string += '%(' + attrs['name'] + ')s'
            self.message.flags.add('python-format')

    def endElement(self, tag):
        assert self.tags.pop() == tag
        if tag == 'msg':
            self.message.string = self.string
            self.catalog[self.message.id] = self.message

    def characters(self, content):
        if self.tags[-1] == 'msg':
            self.string += content
  

def log(text):
    """Prints out Unicode text."""
    print(text.encode('utf-8'))


def log_change(old_message, new_message):
    """Describes an update to a message."""
    if not old_message:
        if new_message.id:
            log('+ msgid "%s"' % str(new_message.id))
        else:
            print('no message id: %s' % new_message, file=sys.stderr)
        log('+ msgstr "%s"' % str(new_message.string.encode('ascii', 'ignore')))
        if new_message.flags:
            log('+ #, %s' % ', '.join(sorted(new_message.flags)))
    else:
        if (new_message.string != old_message.string or
            new_message.flags != old_message.flags):
            log('  msgid "%s"' % old_message.id)
            log('- msgstr "%s"' % old_message.string)
            if old_message.flags:
                log('- #, %s' % ', '.join(sorted(old_message.flags)))
            log('+ msgstr "%s"' % new_message.string)
            if new_message.flags:
                log('+ #, %s' % ', '.join(sorted(new_message.flags)))


def create_file(filename):
    """Opens a file for writing, creating any necessary parent directories."""
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    return open(filename, 'w')


def merge(source, target_filename):
    """Merges the messages from the source Catalog into a .po file at
    target_filename.  Creates the target file if it doesn't exist."""
    if os.path.exists(target_filename):
        target = pofile.read_po(open(target_filename))
        for message in source:
            if message.id and message.string and not message.fuzzy:
                log_change(message.id in target and target[message.id], message)

                # This doesn't actually replace the message!  It just updates
                # the fields other than the string.  See Catalog.__setitem__.
                target[message.id] = message

                # We have to mutate the message to update the string and flags.
                target[message.id].string = message.string
                target[message.id].flags = message.flags
    else:
        for message in source:
            log_change(None, message)
        target = source

    target_file = create_file(target_filename)
    pofile.write_po(target_file, target,
                    no_location=True, sort_output=True, ignore_obsolete=True)
    target_file.close()


def merge_file(source_filename, target_filename, template_filename):
    if source_filename.endswith('.po'):
        merge(pofile.read_po(open(source_filename)), target_filename)
    elif source_filename.endswith('.xml'):
        handler = XmbCatalogReader(pofile.read_po(open(template_filename)))
        xml.sax.parse(open(source_filename), handler)
        merge(handler.catalog, target_filename)


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) not in [1, 2, 3]:
        print(__doc__)
        sys.exit(1)
    args = (args + [None, None])[:3]
    source_path = args[0]
    template_path = args[1]
    target_path = args[2] or os.path.join(os.environ['APP_DIR'], 'locale')

    # If a single file is specified, merge it.
    if ((source_path.endswith('.po') or source_path.endswith('.xml')) and
        target_path.endswith('.po')):
        print(target_path)
        merge_file(source_path, target_path, template_path)
        sys.exit(0)

    # Otherwise, we expect two directories.
    if not os.path.isdir(source_path) or not os.path.isdir(target_path):
        print(__doc__)
        sys.exit(1)

    # Find all the source files.
    source_filenames = {}  # {locale: po_filename}
    def find_po_file(key, dir, filenames):
        """Looks for a .po file and records it in source_filenames."""
        for filename in filenames:
            if filename.endswith('.po') or filename.endswith('.xml'):
                source_filenames[key] = os.path.join(dir, filename)
    for locale in os.listdir(source_path):
        os.path.walk(os.path.join(source_path, locale), find_po_file,
                     locale.replace('-', '_'))

    # Merge them into the target files.
    for locale in sorted(source_filenames.keys()):
        target = os.path.join(target_path, locale, 'LC_MESSAGES', 'django.po')
        print(target)
        merge_file(source_filenames[locale], target, template_path)
