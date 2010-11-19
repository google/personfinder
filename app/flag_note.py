#!/usr/bin/python2.5
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.appengine.ext import db

import model
import utils
from utils import datetime

class FlagNote(utils.Handler):
    """Marks a specified note as hidden [spam], and tracks it in the
    FlagNote table."""
    def get(self):
        note_record_id = self.request.get('note_record_id', '')
        note = model.Note.get(self.subdomain, note_record_id)
        if not note:
            return self.error(400, 'No note with ID: %r' % note_record_id)

        # Mark note as spam
        hide = self.request.get('hide', '') == 'yes' 
        note.hidden = hide
        db.put(note)

        # Track change in FlagNote table
        model.NoteFlag(subdomain=self.subdomain, note_record_id=note_record_id,
                       time=datetime.now(), spam=hide).put()
        self.redirect(self.request.headers['Referer'])


if __name__ == '__main__':
    utils.run(('/flag_note', FlagNote))
