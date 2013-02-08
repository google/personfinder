# Copyright 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import reveal

import model
import utils
from google.appengine.ext import db

from django.utils.translation import ugettext as _

def get_confirm_post_note_with_bad_words_url(handler, note, ttl=3*24*3600):
    note_id = note.get_record_id()
    data = 'confirm_post_note_with_bad_words:%s' % note_id
    token = reveal.sign(data, ttl)
    return handler.get_url('/confirm_post_flagged_note',
                           token=token,
                           id=note_id,
                           repo=handler.repo)


class PostNoteWithBadWordsError(Exception):
    """Container for user-facing error messages when a note is
    detected as having spam words and the note author is asked
    to provide email confirmation to post the note."""
    pass

class Handler(utils.BaseHandler):
    """This handler tells the note author that we can not post the note 
    without an email confirmation."""

    def get(self):
        keyname = "%s:%s" % (self.repo, self.params.id)
        note = model.NoteWithBadWords.get_by_key_name(keyname)
        if not note:
            return self.error(400, _(
                "Can not find note with id %(id)s") % {'id': keyname})

        self.render('post_flagged_note.html',
                    note=note,
                    author_email=self.params.author_email,
                    id=self.params.id,
                    repo=self.repo)


    def post(self):
        keyname = "%s:%s" % (self.repo, self.params.id)
        note = model.NoteWithBadWords.get_by_key_name(keyname)
        if not note:
            return self.error(400, _(
                "Can not find note with id %(id)s") % {'id': keyname})

        person = model.Person.get(self.repo, note.person_record_id)
        note.author_email = self.params.author_email
        db.put([note])
        # i18n: Subject line of an e-mail message that asks the note
        # author that he wants to post the note.
        subject = _('[Person Finder] Confirm your note on "%(full_name)s"'
                ) % {'full_name': person.primary_full_name}

        # send e-mail to note author confirming the posting of this note.
        template_name = 'confirm_post_flagged_note_email.txt'
        confirm_post_note_with_bad_words_url = \
            get_confirm_post_note_with_bad_words_url(self, note)
        self.send_mail(
            subject=subject,
            to=note.author_email,
            body=self.render_to_string(
                template_name,
                author_name=note.author_name,
                full_name=person.primary_full_name,
                site_url=self.get_url('/'),
                confirm_url=confirm_post_note_with_bad_words_url
            )
        )

        return self.info(
            200, _('Your request has been processed successfully. '
                   'Please check your inbox and confirm '
                   'that you want to post your note '
                   'by following the url embedded.'))
