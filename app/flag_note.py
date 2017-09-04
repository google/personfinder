#!/usr/bin/python2.7
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
from recaptcha.client import captcha

import model
import reveal
import utils

class Handler(utils.BaseHandler):
    """Marks a specified note as hidden (spam)."""
    def get(self):
        note = model.Note.get(self.repo, self.params.id)
        if not note:
            return self.error(400, 'No note with ID: %r' % self.params.id)
        note.status_text = utils.get_note_status_text(note)
        note.source_date_local = self.to_local_time(note.source_date)
        captcha_html = note.hidden and self.get_captcha_html() or ''

        # Check if private info should be revealed.
        content_id = 'view:' + note.person_record_id
        reveal_url = reveal.make_reveal_url(self, content_id)
        show_private_info = reveal.verify(content_id, self.params.signature)

        self.render('flag_note.html',
                    note=note,
                    captcha_html=captcha_html,
                    reveal_url=reveal_url,
                    flag_note_page=True,
                    show_private_info=show_private_info,
                    signature=self.params.signature)

    def post(self):
        note = model.Note.get(self.repo, self.params.id)
        if not note:
            return self.error(400, 'No note with ID: %r' % self.params.id)

        captcha_response = note.hidden and self.get_captcha_response()
        if not note.hidden or captcha_response.is_valid:
            note.hidden = not note.hidden
            # When "hidden" changes, update source_date and entry_date (melwitt)
            # http://code.google.com/p/googlepersonfinder/issues/detail?id=58
            now = utils.get_utcnow()
            note.source_date = now
            note.entry_date = now
            db.put(note)

            model.UserActionLog.put_new(
                (note.hidden and 'hide') or 'unhide',
                note, self.request.get('reason_for_report', ''))

            person = model.Person.get(self.repo, note.person_record_id)
            if person:
                person.update_latest_status(note)

            self.redirect(self.get_url('/view', id=note.person_record_id,
                                       signature=self.params.signature))
        elif not captcha_response.is_valid:
            captcha_html = self.get_captcha_html(captcha_response.error_code)
            self.render('flag_note.html',
                        note=note,
                        captcha_html=captcha_html,
                        signature=self.params.signature)
