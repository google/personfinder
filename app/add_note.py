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

import create
from model import *
from photo import create_photo, PhotoError
from utils import *
from detect_spam import SpamDetector
import extend
import subscribe
import utils

from django.utils.translation import ugettext as _
from urlparse import urlparse

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
        # TODO(ichikawa) Consider removing this "except" clause.
        #     I don't think ValueError is thrown here.
        except ValueError:
            return self.error(404,
                _("This person's entry does not exist or has been deleted."))
        if not person:
            return self.error(404,
                _("This person's entry does not exist or has been deleted."))

        # Render the page.
        self.render('add_note.html', person=person)

    def post(self):
        """Post a note in person's record view page"""
        try:
            create.validate_note_data(
                config=self.config,
                status=self.params.status,
                author_name=self.params.author_name,
                author_email=self.params.author_email,
                author_made_contact=self.params.author_made_contact,
                text=self.params.text)
        except create.CreationError as e:
            return self.error(400, e.user_readable_message)

        person = Person.get(self.repo, self.params.id)
        if person.notes_disabled:
            return self.error(
                400, _('The author has disabled status updates '
                       'on this record.'))

        # If a photo was uploaded, create and store a new Photo entry and get
        # the URL where it's served; otherwise, use the note_photo_url provided.
        photo, photo_url = (None, self.params.note_photo_url)
        if self.params.note_photo is not None:
            try:
                photo, photo_url = create_photo(
                    self.params.note_photo, self.repo,
                    self.transitionary_get_url)
            except PhotoError, e:
                return self.error(400, e.message)
            photo.put()

        try:
            note = create.create_note(
                repo=self.repo,
                person=person,
                config=self.config,
                user_ip_address=self.request.remote_addr,
                status=self.params.status,
                source_date=get_utcnow(),
                author_name=self.params.author_name,
                author_email=self.params.author_email,
                author_phone=self.params.author_phone,
                author_made_contact=bool(self.params.author_made_contact),
                note_photo=photo,
                note_photo_url=photo_url,
                text=self.params.text,
                email_of_found_person=self.params.email_of_found_person,
                phone_of_found_person=self.params.phone_of_found_person,
                last_known_location=self.params.last_known_location,
                validate_data=False)
        except create.FlaggedNoteException as e:
            return self.redirect(
                '/post_flagged_note', id=e.note.get_record_id(),
                author_email=e.note.author_email, repo=self.repo)

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

        # Redirect to view page so the browser's back button works properly.
        self.redirect('/view', id=self.params.id, query=self.params.query)
