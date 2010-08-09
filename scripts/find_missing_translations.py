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
  scripts/find_missing_translations.py

PO file format:
  http://www.gnu.org/software/hello/manual/gettext/PO-Files.html
"""

import codecs
import copy
import optparse
import os
import re
import sys

TRANSLATION_FILE = 'LC_MESSAGES/django.po'
MSG_ID_TOKEN = 'msgid'
MSG_STR_TOKEN = 'msgstr'
FUZZY_TOKEN = '#, fuzzy'

def check_key_value(option, opt, value):
  """Checks value is split in two by a ':', returns the parts in a tuple."""
  result = value.split(':');
  if not len(result) == 2:
    raise optparse.OptionValueError(
        "option %s: invalid value: %s should be of the form '<key>:<value>'"
        % (opt, value))
  return tuple(result)


class ExtraOptions(optparse.Option):
  """Extends base class to allow stringified key-value pairs as a type."""
  TYPES = optparse.Option.TYPES + ("key_values",)
  TYPE_CHECKER = copy.copy(optparse.Option.TYPE_CHECKER)
  TYPE_CHECKER["key_values"] = check_key_value


def OptParseDefinitions():
  parser = optparse.OptionParser(option_class=ExtraOptions)
  parser.add_option('--locale_dir', default='locale',
                    help='Directory for the translation files (*.po, *.mo).')
  parser.add_option('--template', action='store_true', default=False,
                    help='If true, it outputs as a template to be filled in.')
  parser.add_option('--fuzzy_ok', action='store_true', default=False,
                    help='if true, don\'t report fuzzy translations as'
                    'missing.')
  parser.add_option('--exclude', action='append', type="key_values",
                    default=[],
                    help='indicates which files should not be translated')
  return parser.parse_args()


def get_translation_files(locale_dir):
  """Yields (lang, .po file path) tuples for the given --locale_dir."""
  for lang in os.listdir(locale_dir):
    po_file = os.path.join(locale_dir, lang, TRANSLATION_FILE)
    if os.path.isfile(po_file):
      yield lang, po_file


def get_untranslated_msg_ids_from_file(po_file, fuzzy_ok):
  """Yields msg id's defined in the po_file that are missing translations."""

  def get_messages(po_file):
    """Yields (msg id, msg str, comment, is_fuzzy) tuples as defined in the
    po_file."""
    msg_id, msg_str, comment, is_fuzzy = '', '', '', False
    for line in codecs.open(po_file, 'r', 'utf8'):
      if line.startswith('#'):
        # comments start a new "block", so yield a result at this point if we've
        # completed a block
        if msg_id:
          yield msg_id, msg_str, comment, is_fuzzy
          msg_id, msg_str, comment, is_fuzzy = '', '', '', False
        if line.startswith(FUZZY_TOKEN):
          is_fuzzy = True
        else:
          comment += line
        continue
      if line:
        if line.startswith(MSG_ID_TOKEN):
          msg_id = line.replace(MSG_ID_TOKEN, '').strip().strip('"')
          current = 'id'
        elif line.startswith(MSG_STR_TOKEN):
          msg_str = line.replace(MSG_STR_TOKEN, '').strip().strip('"')
          current = 'str'
        else:
          if current == 'id':
            msg_id += line.strip().strip('"')
          elif current == 'str':
            msg_str += line.strip().strip('"')
          else:
            print >>sys.stderr, (
                'Parsing error at line (%s) of .po file (%s)' % (line, po_file))
    yield msg_id, msg_str, comment, is_fuzzy

  for msg_id, msg_str, comment, is_fuzzy in get_messages(po_file):
    if msg_id and (not msg_str or (is_fuzzy and not fuzzy_ok)):
      yield msg_id, comment


_FILENAME_FROM_COMMENT = re.compile("#: ([^:]*):\d+")


def find_missing_translations(locale_dir, template, fuzzy_ok, excluded_files):
  """Output to stdout the message id's that are missing translations."""
  for lang, po_file in get_translation_files(locale_dir):
    if lang != 'en':
      print "LANGUAGE = %s" % lang
      num_missing = 0
      for msg_id, comment in get_untranslated_msg_ids_from_file(po_file,
                                                                fuzzy_ok):
        filename_match = _FILENAME_FROM_COMMENT.match(comment)
        if filename_match and (lang, filename_match.group(1)) in excluded_files:
          continue
        num_missing += 1
        quoted_msg = msg_id.replace('"', '\"')
        if template:
          print '\n%s%s "%s"\n%s ""' \
                % (comment, MSG_ID_TOKEN, quoted_msg, MSG_STR_TOKEN)
        else:
          print '  missing: "%s"' % quoted_msg
      if not num_missing:
        print "  ok"

def main():
  options, args = OptParseDefinitions()
  assert not args
  find_missing_translations(options.locale_dir, options.template,
                            options.fuzzy_ok, options.exclude)


if __name__ == '__main__':
  main()
