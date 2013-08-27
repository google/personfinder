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
from photo import create_photo, PhotoError
from utils import *
from detect_spam import SpamDetector
import simplejson

from django.utils.translation import ugettext as _

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
        profile_websites = [add_profile_icon_url(website, self)
                for website in self.config.profile_websites or []]
        self.render('create.html',
                    profile_websites=profile_websites,
                    profile_websites_json=simplejson.dumps(profile_websites),
                    onload_function='view_page_loaded()')

    def post(self):
        now = get_utcnow()

        # Several messages here exceed the 80-column limit because django's
        # makemessages script can't handle messages split across lines. :(
        if self.config.use_family_name:
            if not (self.params.given_name and self.params.family_name):
                return self.error(400, _('The Given name and Family name are both required.  Please go back and try again.'))
        else:
            if not self.params.given_name:
                return self.error(400, _('Name is required.  Please go back and try again.'))
        if not self.params.author_name:
            if self.params.clone:
                return self.error(400, _('The Original author\'s name is required.  Please go back and try again.'))
            else:
                return self.error(400, _('Your name is required in the "Source" section.  Please go back and try again.'))

        if self.params.add_note:
            if not self.params.text:
                return self.error(400, _('Message is required. Please go back and try again.'))
            if self.params.status == 'is_note_author' and \
                not self.params.author_made_contact:
                return self.error(400, _('Please check that you have been in contact with the person after the earthquake, or change the "Status of this person" field.'))
            if (self.params.status == 'believed_dead' and \
                not self.config.allow_believed_dead_via_ui):
                return self.error(400, _('Not authorized to post notes with the status "I have received information that this person is dead".'))

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
        photo, photo_url = (None, self.params.photo_url)
        note_photo, note_photo_url = (None, self.params.note_photo_url)
        try:
            # If a photo was uploaded, create a Photo entry and get the URL
            # where we serve it.
            if self.params.photo is not None:
                photo, photo_url = create_photo(self.params.photo, self)
            if self.params.note_photo is not None:
                note_photo, note_photo_url = \
                    create_photo(self.params.note_photo, self)
        except PhotoError, e:
            return self.error(400, e.message)
        # Finally, store the Photo. Past this point, we should NOT self.error.
        if photo:
            photo.put()
        if note_photo:
            note_photo.put()

        profile_urls = []
        if self.params.profile_url1:
            profile_urls.append(self.params.profile_url1)
        if self.params.profile_url2:
            profile_urls.append(self.params.profile_url2)
        if self.params.profile_url3:
            profile_urls.append(self.params.profile_url3)

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
            given_name=self.params.given_name,
            family_name=self.params.family_name,
            full_name=get_full_name(self.params.given_name,
                                    self.params.family_name,
                                    self.config),
            alternate_names=get_full_name(self.params.alternate_given_names,
                                          self.params.alternate_family_names,
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
            profile_urls='\n'.join(profile_urls),
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
                    photo=note_photo,
                    photo_url=note_photo_url,
                    spam_score=spam_score,
                    confirmed=False)

                # Write the new NoteWithBadWords to the datastore
                db.put(note)
                UserActionLog.put_new('add', note, copy_properties=False)
                # Write the person record to datastore before redirect
                db.put(person)
                UserActionLog.put_new('add', person, copy_properties=False)

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
                    photo=note_photo,
                    photo_url=note_photo_url)

                # Write the new Note to the datastore
                db.put(note)
                UserActionLog.put_new('add', note, copy_properties=False)
                person.update_from_note(note)

            # Specially log 'believed_dead'.
            if note.status == 'believed_dead':
                UserActionLog.put_new(
                    'mark_dead', note, person.primary_full_name,
                    self.request.remote_addr)

        # Write the person record to datastore
        db.put(person)
        UserActionLog.put_new('add', person, copy_properties=False)

        # TODO(ryok): we could do this earlier so we don't neet to db.put twice.
        if not person.source_url and not self.params.clone:
            # Put again with the URL, now that we have a person_record_id.
            person.source_url = self.get_url('/view', id=person.record_id)
            db.put(person)

        # TODO(ryok): batch-put person, note, photo, note_photo here.

        # If user wants to subscribe to updates, redirect to the subscribe page
        if self.params.subscribe:
            return self.redirect('/subscribe', id=person.record_id,
                                 subscribe_email=self.params.author_email)

        self.redirect('/view', id=person.record_id)
