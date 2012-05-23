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

from datetime import datetime
from model import *
from photo import get_photo_url
from utils import *
from detect_spam import SpamDetector
from google.appengine.api import images
from google.appengine.runtime.apiproxy_errors import RequestTooLargeError
import indexing
import prefix

from django.utils.translation import ugettext as _

MAX_IMAGE_DIMENSION = 300

def validate_date(string):
    """Parses a date in YYYY-MM-DD format.    This is a special case for manual
    entry of the source_date in the creation form.    Unlike the validators in
    utils.py, this will throw an exception if the input is badly formatted."""
    year, month, day = map(int, string.strip().split('-'))
    return datetime(year, month, day)

def days_to_date(days):
    """Converts a duration signifying days-from-now to a datetime object.

    Returns:
      None if days is None, else now + days (in utc)"""
    return days and get_utcnow() + timedelta(days=days)


class Handler(BaseHandler):
    def get(self):
        self.params.create_mode = True
        self.render('create.html',
                    onload_function='view_page_loaded()')

    def post(self):
        now = get_utcnow()

        # Several messages here exceed the 80-column limit because django's
        # makemessages script can't handle messages split across lines. :(
        if self.config.use_family_name:
            if not (self.params.first_name and self.params.last_name):
                return self.error(400, _('The Given name and Family name are both required.  Please go back and try again.'))
        else:
            if not self.params.first_name:
                return self.error(400, _('Name is required.  Please go back and try again.'))
        if not self.params.author_name:
            if self.params.clone:
                return self.error(400, _('The Original author\'s name is required.  Please go back and try again.'))
            else:
                return self.error(400, _('Your name is required in the "Source" section.  Please go back and try again.'))

        if self.params.add_note:
            if self.params.status == 'is_note_author' and \
                not self.params.author_made_contact:
                return self.error(400, _('Please check that you have been in contact with the person after the earthquake, or change the "Status of this person" field.'))
            if (self.params.status == 'believed_dead' and \
                not self.config.allow_believed_dead_via_ui):
                return self.error(400, _('Not authorized to post notes with the status "believed_dead".'))

        source_date = None
        if self.params.source_date:
            try:
                source_date = validate_date(self.params.source_date)
            except ValueError:
                return self.error(400, _('Original posting date is not in YYYY-MM-DD format, or is a nonexistent date.  Please go back and try again.'))
            if source_date > now:
                return self.error(400, _('Date cannot be in the future.  Please go back and try again.'))

        expiry_date = days_to_date(self.params.expiry_option or
                                   self.config.default_expiry_days)

        # If nothing was uploaded, just use the photo_url that was provided.
        photo = None
        photo_url = self.params.photo_url

        # If a picture was uploaded, store it and the URL where we serve it.
        image = self.params.photo
        if image == False:  # False means it wasn't valid (see validate_image)
            return self.error(400, _('Photo uploaded is in an unrecognized format.  Please go back and try again.'))

        if image:
            if max(image.width, image.height) <= MAX_IMAGE_DIMENSION:
                # No resize needed.  Keep the same size but add a
                # transformation to force re-encoding.
                image.resize(image.width, image.height)
            elif image.width > image.height:
                image.resize(
                    MAX_IMAGE_DIMENSION,
                    image.height * MAX_IMAGE_DIMENSION / image.width)
            else:
                image.resize(
                    image.width * MAX_IMAGE_DIMENSION / image.height,
                    MAX_IMAGE_DIMENSION)

            try:
                image_data = \
                    image.execute_transforms(output_encoding=images.PNG)
            except RequestTooLargeError:
                return self.error(400, _('The provided image is too large.  Please upload a smaller one.'))
            except Exception:
                # There are various images.Error exceptions that can be raised,
                # as well as e.g. IOError if the image is corrupt.
                return self.error(400, _('There was a problem processing the image.  Please try a different image.'))

            photo = Photo.create(self.repo, image_data=image_data)
            photo.put()
            photo_url = get_photo_url(photo, self)

        # Person records have to have a source_date; if none entered, use now.
        source_date = source_date or now

        # Determine the source name, or fill it in if the record is original
        # (i.e. created for the first time here, not copied from elsewhere).
        source_name = self.params.source_name
        if not self.params.clone:
            source_name = self.env.netloc  # record originated here

        person = Person.create_original(
            self.repo,
            entry_date=now,
            expiry_date=expiry_date,
            first_name=self.params.first_name,
            last_name=self.params.last_name,
            alternate_names=get_full_name(self.params.alternate_first_names,
                                          self.params.alternate_last_names,
                                          self.config),
            description=self.params.description,
            sex=self.params.sex,
            date_of_birth=self.params.date_of_birth,
            age=self.params.age,
            home_street=self.params.home_street,
            home_city=self.params.home_city,
            home_state=self.params.home_state,
            home_postal_code=self.params.home_postal_code,
            home_neighborhood=self.params.home_neighborhood,
            home_country=self.params.home_country,
            author_name=self.params.author_name,
            author_phone=self.params.author_phone,
            author_email=self.params.author_email,
            source_url=self.params.source_url,
            source_date=source_date,
            source_name=source_name,
            photo=photo,
            photo_url=photo_url
        )
        person.update_index(['old', 'new'])

        if self.params.add_note:
            if person.notes_disabled:
                return self.error(403, _(
                    'The author has disabled notes on this record.'))

            spam_detector = SpamDetector(self.config.bad_words)
            spam_score = spam_detector.estimate_spam_score(self.params.text)
            if (spam_score > 0):
                note = NoteWithBadWords.create_original(
                    self.repo,
                    entry_date=get_utcnow(),
                    person_record_id=person.record_id,
                    author_name=self.params.author_name,
                    author_email=self.params.author_email,
                    author_phone=self.params.author_phone,
                    source_date=source_date,
                    author_made_contact=bool(self.params.author_made_contact),
                    status=self.params.status,
                    email_of_found_person=self.params.email_of_found_person,
                    phone_of_found_person=self.params.phone_of_found_person,
                    last_known_location=self.params.last_known_location,
                    text=self.params.text,
                    photo_url=self.params.photo_url,
                    spam_score=spam_score,
                    confirmed=False)

                # Write the new NoteWithBadWords to the datastore
                db.put(note)
                # Write the person record to datastore before redirect
                db.put(person)

                # When the note is detected as spam, we do not update person
                # record with this note or log action. We ask the note author
                # for confirmation first.
                return self.redirect('/post_flagged_note',
                                     id=note.get_record_id(),
                                     author_email=note.author_email,
                                     repo=self.repo)
            else:
                note = Note.create_original(
                    self.repo,
                    entry_date=get_utcnow(),
                    person_record_id=person.record_id,
                    author_name=self.params.author_name,
                    author_email=self.params.author_email,
                    author_phone=self.params.author_phone,
                    source_date=source_date,
                    author_made_contact=bool(self.params.author_made_contact),
                    status=self.params.status,
                    email_of_found_person=self.params.email_of_found_person,
                    phone_of_found_person=self.params.phone_of_found_person,
                    last_known_location=self.params.last_known_location,
                    text=self.params.text,
                    photo_url=self.params.photo_url)

                # Write the new NoteWithBadWords to the datastore
                db.put(note)
                person.update_from_note(note)

            # Specially log 'believed_dead'.
            if note.status == 'believed_dead':
                detail = person.first_name + ' ' + person.last_name
                UserActionLog.put_new(
                    'mark_dead', note, detail, self.request.remote_addr)

        # Write the person record to datastore
        db.put(person)

        if not person.source_url and not self.params.clone:
            # Put again with the URL, now that we have a person_record_id.
            person.source_url = self.get_url('/view', id=person.record_id)
            db.put(person)

        # If user wants to subscribe to updates, redirect to the subscribe page
        if self.params.subscribe:
            return self.redirect('/subscribe', id=person.record_id,
                                 subscribe_email=self.params.author_email)

        self.redirect('/view', id=person.record_id)
