#!/usr/bin/python2.5
# Copyright 2010 Google Inc.
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
import subscribe

import utils
import model
from google.appengine.ext import db

from django.utils.translation import ugettext as _

class ConfirmPostNoteWithBadWordsError(Exception):
    """Container for user-facing error messages when confirming to post
    a note with bad words."""
    pass

class Handler(utils.BaseHandler):
    """This handler lets the author confirm to post a note containing  
    bad words."""

    def get(self):
        try:
            note, token = self.get_note_and_verify_params()
        except ConfirmPostNoteWithBadWordsError, e:
            return self.error(400, unicode(e))

        self.confirm_note_with_bad_words(note)
        record_url = self.get_url(
            '/view', id=note.person_record_id, repo=note.repo)

        self.redirect(record_url)

    def post(self):
        try:
            note, token = self.get_note_and_verify_params()
        except ConfirmPostNoteWithBadWordsError, e:
            return self.error(400, unicode(e))

        self.confirm_note_with_bad_words(note)
        record_url = self.get_url(
            '/view', id=note.person_record_id, repo=note.repo)

        self.redirect(record_url)

    def get_note_and_verify_params(self):
        """Check the request for a valid note record_id and valid crypto token.
        Returns a tuple containing: (note, token)
        If there is an error we raise a ConfirmPostNoteWithBadWordsError. """
        keyname = "%s:%s" % (self.repo, self.params.id)
        note = model.NoteWithBadWords.get_by_key_name(keyname)
        if not note:
            raise ConfirmPostNoteWithBadWordsError(
                _('No note with ID: %(id)s.') % {'id': keyname})

        token = self.request.get('token')
        data = 'confirm_post_note_with_bad_words:%s' % self.params.id
        if not reveal.verify(data, token):
            raise ConfirmPostNoteWithBadWordsError(
                _("The token %(token)s was invalid.") % {'token': token})

        return (note, token)

    def confirm_note_with_bad_words(self, note):
        """After a note containing bad words is confirmed by the author,
        we will:
        (1) set note.confirmed = True;
        (2) copy the note from NoteWithBadWords to Note;
        (3) log user action;
        (4) update person record. """
        note.confirmed = True;

        # Check whether the record author disabled notes on
        # this record during the time between the note author inputs the
        # note in the UI and confirms the note through email.
        person = model.Person.get(self.repo, note.person_record_id)
        if person.notes_disabled:
            return self.error(
                200, _('The author has disabled notes on this record.'))

        # Check whether the admin disabled reporting "believed_dead"
        # during the time between the note author inputs the
        # note in the UI and confirms the note through email.
        if (self.params.status == 'believed_dead' and
            not self.config.allow_believed_dead_via_ui):
            return self.error(
                200, _('Not authorized to post notes with the status '
                       '"believed_dead".'))

        # clone the flagged note to Note table.
        note_confirmed = model.Note.create_original(
            self.repo,
            entry_date=note.entry_date,
            person_record_id=note.person_record_id,
            author_name=note.author_name,
            author_email=note.author_email,
            author_phone=note.author_phone,
            source_date=note.source_date,
            author_made_contact=note.author_made_contact,
            status=note.status,
            email_of_found_person=note.email_of_found_person,
            phone_of_found_person=note.phone_of_found_person,
            last_known_location=note.last_known_location,
            text=note.text)
        entities_to_put = [note_confirmed]

        note.confirmed_copy_id = note_confirmed.get_record_id()
        entities_to_put.append(note)

        # Specially log 'believed_dead'.
        if note_confirmed.status == 'believed_dead':
            detail = person.given_name + ' ' + person.family_name
            model.UserActionLog.put_new(
                'mark_dead', note_confirmed, detail, self.request.remote_addr)

        # Specially log a switch to an alive status.
        if (note_confirmed.status in ['believed_alive', 'is_note_author'] and
            person.latest_status not in ['believed_alive', 'is_note_author']):
            detail = person.given_name + ' ' + person.family_name
            model.UserActionLog.put_new('mark_alive', note_confirmed, detail)

        # Update the Person based on the Note.
        if person:
            person.update_from_note(note_confirmed)
            # Send notification to all people
            # who subscribed to updates on this person
            subscribe.send_notifications(self, person, [note_confirmed])
            entities_to_put.append(person)

        # Write one or both entities to the store.
        db.put(entities_to_put)
