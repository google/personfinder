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

"""Verify the messages in the en .po files after merging.

Usage:
    From the root directory: tools/verify_translation.py
    
Verify_translations takes no arguments.  To use:
	1. run find_missing_translations to generate a template .po file:
          find_missing_translations --format=po 
          This will generate a .po file with just the translated messages in order.

       2. Use the english person_finder.xml file and the template from step 1 to 
          'merge' the english translations into the english .po file.  This should 
          generate a .po file with the msg string set to the msg id value for each
          newly translated string.  Example command:
          'merge_translations translations/en/person_finder.xml app/locale/en/LC_MESSAGES/django'          

       3. run verify_translations to verify that the strings are actually the same.
          command: 'verify_translation'

       4. revert the app/locale/en changes (eg, don't check in the msgstrs 
          in the englis files).

PO file format:
    http://www.gnu.org/software/hello/manual/gettext/PO-Files.html
"""

from babel.messages import pofile
from find_missing_translations import get_po_filename
from test_pfif import text_diff

if __name__ == '__main__':
    filename = get_po_filename('en')
    english = pofile.read_po(open(filename))
    count = 0
    def printsep():
        if count > 0:
            print '-------------------------------------'

    for msg in english: 
        # Each newly translated string will have msg.string set
        # to the 'translated' english value.        
        if msg.id and msg.string and msg.string != msg.id:
            if isinstance(msg.id, tuple):
                # TODO(lschumacher): deal with plurals properly, 
                if msg.string[0] or msg.string[1]:
                    printsep()
                    print 'msg id: %s\nmsgstr: %s' % (msg.id, msg.string)
                    count += 1
            else:
                printsep()
                print text_diff(msg.id, msg.string)
                count += 1
    if count:
        printsep()
        print 'Found %s bad translations' % count
    else:
        print 'Translation OK'
