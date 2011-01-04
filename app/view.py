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
import sys

from google.appengine.api import datastore_errors

from model import *
from utils import *
import prefix
import reveal
import subscribe


class View(Handler):
    def get(self):
        # Check the request parameters.
        if not self.params.id:
            return self.error(404, 'No person id was specified.')
        try:
            person = Person.get(self.subdomain, self.params.id)
        except ValueError:
            return self.error(404, 'There is no record for the specified id.')
        if not person:
            return self.error(404, 'There is no record for the specified id.')
        standalone = self.request.get('standalone')

        # Check if private info should be revealed.
        content_id = 'view:' + self.params.id
        reveal_url = reveal.make_reveal_url(self, content_id)
        show_private_info = reveal.verify(content_id, self.params.signature)

        # Get the notes and duplicate links.
        try:
            notes = person.get_notes()
        except datastore_errors.NeedIndexError:
            notes = []
        person.sex_text = get_person_sex_text(person)
        for note in notes:
            note.status_text = get_note_status_text(note)
            note.linked_person_url = \
                self.get_url('/view', id=note.linked_person_record_id)
        try:
            linked_persons = person.get_linked_persons(note_limit=200)
        except datastore_errors.NeedIndexError:
            linked_persons = []
        linked_person_info = [
            dict(id=p.record_id,
                 name="%s %s" % (p.first_name, p.last_name),
                 view_url=self.get_url('/view', id=p.record_id))
            for p in linked_persons]

        # Render the page.
        dupe_notes_url = self.get_url(
            '/view', id=self.params.id, dupe_notes='yes')
        results_url = self.get_url(
            '/results',
            role=self.params.role,
            query=self.params.query,
            first_name=self.params.first_name,
            last_name=self.params.last_name)
        self.render('templates/view.html', params=self.params,
                    linked_person_info=linked_person_info,
                    person=person, notes=notes, standalone=standalone,
                    onload_function='view_page_loaded()',
                    reveal_url=reveal_url, show_private_info=show_private_info,
                    noindex=True,
                    admin=users.is_current_user_admin(),
                    dupe_notes_url=dupe_notes_url,
                    results_url=results_url)

    def post(self):
        #if it is request for notifying it will be hooked here
        if self.params.notify_person  == "yes":
            email = self.params.email_subscr
            person = Person.get(self.subdomain, self.params.id)
            if person:
                if model.is_valid_email(email) == True:
                    person.add_subscriber(email)
                    db.put(person)
                    return self.info(200, _('Your are succcessfully subscribed. Please go back.'))
                elif model.is_valid_email(email) == False:
                    return self.error(200, _('Your email is incorrect.  Please go back and check the email.'))
                else:
                    return self.error(200, _('You did not specify your email. Please go back and specify your email.'))
            else:
                return self.error(200, _('Something went wrong. Please go back and try again.'))
            
        if not self.params.text:
            return self.error(
                200, _('Message is required. Please go back and try again.'))

        if not self.params.author_name:
            return self.error(
                200, _('Your name is required in the "About you" section.  '
                       'Please go back and try again.'))

        if self.params.status == 'is_note_author' and not self.params.found:
            return self.error(
                200, _('Please check that you have been in contact with '
                       'the person after the earthquake, or change the '
                       '"Status of this person" field.'))
        note = Note.create_original(
            self.subdomain,
            person_record_id=self.params.id,
            author_name=self.params.author_name,
            author_email=self.params.author_email,
            author_phone=self.params.author_phone,
            source_date=datetime.utcnow(),
            found=bool(self.params.found),
            status=self.params.status,
            email_of_found_person=self.params.email_of_found_person,
            phone_of_found_person=self.params.phone_of_found_person,
            last_known_location=self.params.last_known_location,
            text=self.params.text)
        entities_to_put = [note]

        # Update the Person based on the Note.
        person = Person.get(self.subdomain, self.params.id)
        if person:
            person.update_from_note(note)
            #if the message sender wants to receive updates, he will be added to db
            if self.params.is_receive_updates  == "yes":
                result = person.add_subscriber(note.author_email)
                if result == False:
                    return self.error(
                        200, _('Your email is incorrect.  Please go back and check the email.'))
            #send notification to all people who wants to receive notification about this person
            subscribe.send_notifications(person, note, self)
            entities_to_put.append(person)

        # Write one or both entities to the store.
        db.put(entities_to_put)

        # Redirect to this page so the browser's back button works properly.
        self.redirect('/view', id=self.params.id, query=self.params.query)
    

if __name__ == '__main__':
    run(('/view', View))
