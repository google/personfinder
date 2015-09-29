#!/usr/bin/python2.7
# Copyright 2015 Google Inc.
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

from google.appengine.api import datastore_errors

from model import *
from photo import create_photo, PhotoError
from utils import *
from detect_spam import SpamDetector
import extend
import reveal
import subscribe

from django.utils.translation import ugettext as _
from urlparse import urlparse

# TODO(jessien): Clean up duplicate code here and in create.py.
# https://github.com/google/personfinder/issues/157

# how many days left before we warn about imminent expiration.
# Make this at least 1.
EXPIRY_WARNING_THRESHOLD = 7


class Handler(BaseHandler):

    def get(self):
        # Check the request parameters.
        if not self.params.id:
            return self.error(404, _('No person id was specified.'))
        try:
            person = Person.get(self.repo, self.params.id)
        except ValueError:
            return self.error(404,
                _("This person's entry does not exist and has been deleted."))
        if not person:
            return self.error(404,
                _("This person's entry does not exist and has been deleted."))
        standalone = self.request.get('standalone')

        # Render the page.
        enable_notes_url = self.get_url('/enable_notes', id=self.params.id)

        self.render('add_note.html',
                    person=person,
                    standalone=standalone,
                    enable_notes_url=enable_notes_url)


    def post(self):
        if not self.params.text:
            return self.error(
                200, _('Message is required. Please go back and try again.'))

        if not self.params.author_name:
            return self.error(
                200, _('Your name is required in the "About you" section.  '
                       'Please go back and try again.'))

        if (self.params.status == 'is_note_author' and
            not self.params.author_made_contact):
            return self.error(
                200, _('Please check that you have been in contact with '
                       'the person after the disaster, or change the '
                       '"Status of this person" field.'))

        if (self.params.status == 'believed_dead' and
            not self.config.allow_believed_dead_via_ui):
            return self.error(
                200, _('Not authorized to post notes with the status '
                       '"believed_dead".'))

        person = Person.get(self.repo, self.params.id)
        if person.notes_disabled:
            return self.error(
                200, _('The author has disabled status updates '
                       'on this record.'))

        # If a photo was uploaded, create and store a new Photo entry and get
        # the URL where it's served; otherwise, use the note_photo_url provided.
        photo, photo_url = (None, self.params.note_photo_url)
        if self.params.note_photo is not None:
            try:
                photo, photo_url = create_photo(self.params.note_photo, self)
            except PhotoError, e:
                return self.error(400, e.message)
            photo.put()

        spam_detector = SpamDetector(self.config.bad_words)
        spam_score = spam_detector.estimate_spam_score(self.params.text)

        if (spam_score > 0):
            note = NoteWithBadWords.create_original(
                self.repo,
                entry_date=get_utcnow(),
                person_record_id=self.params.id,
                author_name=self.params.author_name,
                author_email=self.params.author_email,
                author_phone=self.params.author_phone,
                source_date=get_utcnow(),
                author_made_contact=bool(self.params.author_made_contact),
                status=self.params.status,
                email_of_found_person=self.params.email_of_found_person,
                phone_of_found_person=self.params.phone_of_found_person,
                last_known_location=self.params.last_known_location,
                text=self.params.text,
                photo=photo,
                photo_url=photo_url,
                spam_score=spam_score,
                confirmed=False)
            # Write the new NoteWithBadWords to the datastore
            db.put(note)
            UserActionLog.put_new('add', note, copy_properties=False)
            # When the note is detected as spam, we do not update person record
            # or log action. We ask the note author for confirmation first.
            return self.redirect('/post_flagged_note', id=note.get_record_id(),
                                 author_email=note.author_email,
                                 repo=self.repo)
        else:
            note = Note.create_original(
                self.repo,
                entry_date=get_utcnow(),
                person_record_id=self.params.id,
                author_name=self.params.author_name,
                author_email=self.params.author_email,
                author_phone=self.params.author_phone,
                source_date=get_utcnow(),
                author_made_contact=bool(self.params.author_made_contact),
                status=self.params.status,
                email_of_found_person=self.params.email_of_found_person,
                phone_of_found_person=self.params.phone_of_found_person,
                last_known_location=self.params.last_known_location,
                text=self.params.text,
                photo=photo,
                photo_url=photo_url)
            # Write the new regular Note to the datastore
            db.put(note)
            UserActionLog.put_new('add', note, copy_properties=False)

        # Specially log 'believed_dead'.
        if note.status == 'believed_dead':
            UserActionLog.put_new(
                'mark_dead', note, person.primary_full_name,
                self.request.remote_addr)

        # Specially log a switch to an alive status.
        if (note.status in ['believed_alive', 'is_note_author'] and
            person.latest_status not in ['believed_alive', 'is_note_author']):
            UserActionLog.put_new('mark_alive', note, person.primary_full_name)

        # Update the Person based on the Note.
        if person:
            person.update_from_note(note)
            # Send notification to all people
            # who subscribed to updates on this person
            subscribe.send_notifications(self, person, [note])
            # write the updated person record to datastore
            db.put(person)

        # If user wants to subscribe to updates, redirect to the subscribe page
        if self.params.subscribe:
            return self.redirect('/subscribe',
                                 id=person.record_id,
                                 subscribe_email=self.params.author_email,
                                 context='add_note')

        # Redirect to this page so the browser's back button works properly.
        self.redirect('/add_note', id=self.params.id, query=self.params.query)