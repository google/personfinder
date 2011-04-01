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
Merge translations from one set of .po files into another.

The first argument should be a directory containing a subdirectory for each
locale, named with a locale code (e.g. pt_BR).  For each locale, this script
looks for the first .po file it finds anywhere under the locale directory
and adds all its messages and translations to the django.po file in the
corresponding subdirectory of the target directory.

  - Empty messages and messages marked "fuzzy" in the source file are ignored.

  - Translations in the source file will replace any existing translations
    for the same messages in the target file.

  - Other translations in the source file will be added to the target file.

  - To minimize unnecessary changes from version to version, the target file
    has no "#: filename:line" comments and the messages are sorted by msgid.

Usage:
    ../tools/merge_messages /path/to/source
    ../tools/merge_messages /path/to/source /path/to/target
    ../tools/merge_messages /path/to/source/file.po /path/to/target/file.po

If no target directory is specified, it defaults to the app/locale directory
of the current app.  
"""

from babel.messages import pofile
import codecs
import os
import sys


def log(text):
    """Prints out Unicode text."""
    print text.encode('utf-8')


def log_change(old_message, new_message):
    """Describes an update to a message."""
    if not old_message:
        log('+ msgid "%s"' % new_message.id)
        log('+ msgstr "%s"' % new_message.string)
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


def merge(source_filename, target_filename):
    """Merges the messages from source_filename into target_filename.
    Creates the target file if it doesn't exist."""
    source = pofile.read_po(open(source_filename))
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


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) < 2:
        args.append(None)
    if len(args) != 2:
        print __doc__
        sys.exit(1)
    source_path = args[0]
    target_path = args[1] or os.path.join(os.environ['APP_DIR'], 'locale')

    # If a single file is specified, merge it.
    if source_path.endswith('.po') and target_path.endswith('.po'):
        print target_path
        merge(source_path, target_path)
        sys.exit(0)

    # Otherwise, we expect two directories.
    if not os.path.isdir(source_path) or not os.path.isdir(target_path):
        print __doc__
        sys.exit(1)

    # Find all the source files.
    source_filenames = {}  # {locale: po_filename}
    def find_po_file(key, dir, filenames):
        """Looks for a .po file and records it in source_filenames."""
        for filename in filenames:
            if filename.endswith('.po'):
                source_filenames[key] = os.path.join(dir, filename)
    for locale in os.listdir(source_path):
        os.path.walk(os.path.join(source_path, locale), find_po_file,
                     locale.replace('-', '_'))

    # Merge them into the target files.
    for locale in sorted(source_filenames.keys()):
        target = os.path.join(target_path, locale, 'LC_MESSAGES', 'django.po')
        print target
        merge(source_filenames[locale], target)
