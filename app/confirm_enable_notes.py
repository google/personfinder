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

import model
import utils
from google.appengine.ext import db

from django.utils.translation import ugettext as _

from confirm_disable_notes import DisableAndEnableNotesError

class Handler(utils.BaseHandler):
    """This handler lets the author confirm to disable future nots 
    to a person record."""

    def get(self):
        try:
            person, token = self.get_person_and_verify_params()
        except DisableAndEnableNotesError, e:
            return self.error(400, unicode(e))

        # Log the user action.
        model.UserActionLog.put_new('enable_notes', person)

        #Update the notes_disabled flag in person record.
        person.notes_disabled = False
        db.put([person])

        record_url = self.get_url(
            '/view', id=person.record_id, repo=person.repo)

        # Send subscribers a notice email.
        subject = _('[Person Finder] Notes are now enabled on "%(full_name)s"'
                ) % {'full_name': person.primary_full_name}
        email_addresses = person.get_associated_emails()
        for address in email_addresses:
            self.send_mail(
                subject=subject,
                to=address,
                body=self.render_to_string(
                    'enable_notes_notice_email.txt',
                    full_name=person.primary_full_name,
                    record_url=record_url
                )
            )

        self.redirect(record_url)


    def post(self):
        try:
            person, token = self.get_person_and_verify_params()
        except DisableAndEnableNotesError, e:
            return self.error(400, unicode(e))

        # Log the user action.
        model.UserActionLog.put_new('enable_notes', person)

        # Update the notes_disabled flag in person record.
        person.notes_disabled = False
        db.put([person])

        record_url = self.get_url(
            '/view', id=person.record_id, repo=person.repo)

        # Send subscribers a notice email.
        subject = _('[Person Finder] Enabling notes notice for "%(full_name)s"'
                ) % {'full_name': person.primary_full_name}
        email_addresses = person.get_associated_emails()
        for address in email_addresses:
            self.send_mail(
                subject=subject,
                to=address,
                body=self.render_to_string(
                    'enable_notes_notice_email.txt',
                    full_name=person.primary_full_name,
                    record_url=record_url
                )
            )

        self.redirect(record_url)


    def get_person_and_verify_params(self):
        """Check the request for a valid person id and valid crypto token.

        Returns a tuple containing: (person, token)

        If there is an error we raise a DisableAndEnableNotesError. """
        person = model.Person.get_by_key_name(self.params.id)
        if not person:
            raise DisableAndEnableNotesError(
                _('No person with ID: %(id)s.') % {'id': self.params.id})

        token = self.request.get('token')
        data = 'enable_notes:%s' % self.params.id
        if not reveal.verify(data, token):
            raise DisableAndEnableNotesError(
                _('The token %(token)s was invalid') % {'token': token})

        return (person, token)
